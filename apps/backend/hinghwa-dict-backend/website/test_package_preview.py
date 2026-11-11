"""Synthetic ZIP-preview regression cases.

Covers permissions, no business writes, bounded input and temporary cleanup.
"""
import io
from pathlib import Path
import stat
import tempfile
import zipfile
from unittest.mock import patch
from django.contrib.auth.models import Permission, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from word.models import ResourcePackage, Word, Pronunciation
from word.resource_packages import PackageError
from word.test_resource_packages import fixture
from website.package_preview import preview_upload, PackagePreviewForm, MAX_WEB_ZIP_BYTES


class PackagePreviewTests(TestCase):
    url = '/admin/website/website/package-preview/'

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.media = self.root / 'data/media'
        self.media.mkdir(parents=True)
        self.scratch = self.root / 'scratch'
        self.scratch.mkdir()
        self.package = self.root / 'package'
        fixture(self.package, 'synthetic-web-preview')
        self.override = override_settings(MEDIA_ROOT=str(self.media), DATA_DIR=self.root / 'data')
        self.override.enable(); self.addCleanup(self.override.disable)
        self.operator = User.objects.create_user('synthetic-preview', password=None, is_staff=True)
        self.operator.user_permissions.add(Permission.objects.get(codename='view_resourcepackage'))
        self.client.force_login(self.operator)
        self.original_tempdir = tempfile.TemporaryDirectory

    def upload(self, mutation=None):
        contents = io.BytesIO()
        with zipfile.ZipFile(contents, 'w') as archive:
            for path in self.package.rglob('*'):
                if path.is_file():
                    archive.write(path, path.relative_to(self.package).as_posix())
            if mutation:
                mutation(archive)
        return SimpleUploadedFile('synthetic.zip', contents.getvalue(), content_type='application/zip')

    def private_temporary(self, **kwargs):
        return self.original_tempdir(dir=self.scratch, **kwargs)

    def test_preview_has_no_business_or_media_writes_and_preserves_ipa(self):
        before = (ResourcePackage.objects.count(), Word.objects.count(), Pronunciation.objects.count())
        with patch('website.package_preview.tempfile.TemporaryDirectory', side_effect=self.private_temporary):
            response = self.client.post(self.url, {'package': self.upload()})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['result']['error_count'], 0)
        self.assertEqual(response.context_data['result']['rows'][0]['ipa'], 't ɛ s t 1')
        self.assertContains(response, '没有导入、没有公开')
        self.assertIn('private', response['Cache-Control'])
        self.assertIn('no-store', response['Cache-Control'])
        self.assertEqual(before, (ResourcePackage.objects.count(), Word.objects.count(), Pronunciation.objects.count()))
        self.assertFalse(list(self.media.rglob('*')))
        self.assertEqual(list(self.scratch.iterdir()), [])
        self.assertFalse((self.root / 'data/private-imports').exists())
        self.assertFalse((self.root / 'data/exports').exists())

    def test_anonymous_permission_and_csrf_boundaries(self):
        self.client.logout(); self.assertEqual(self.client.get(self.url).status_code, 302)
        staff = User.objects.create_user('synthetic-no-package-permission', password=None, is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.post(self.url, {'package': self.upload()}).status_code, 403)
        strict = Client(enforce_csrf_checks=True); strict.force_login(self.operator)
        self.assertEqual(strict.post(self.url, {'package': self.upload()}).status_code, 403)
        self.client.force_login(self.operator)
        self.assertEqual(self.client.put(self.url).status_code, 405)

    def test_invalid_zip_and_path_link_members_leave_no_temporary_files(self):
        def link(archive):
            item = zipfile.ZipInfo('audio/link.wav')
            item.create_system = 3; item.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(item, 'outside')
        cases = [SimpleUploadedFile('broken.zip', b'not a zip'),
                 self.upload(lambda archive: archive.writestr('../outside', 'bad')),
                 self.upload(link)]
        for upload in cases:
            with self.subTest(name=upload.name), patch('website.package_preview.tempfile.TemporaryDirectory', side_effect=self.private_temporary):
                with self.assertRaises(PackageError): preview_upload(upload)
            self.assertEqual(list(self.scratch.iterdir()), [])
            self.assertFalse(list(self.media.rglob('*')))

    def test_corrupt_compression_is_reported_and_temporary_files_are_removed(self):
        import struct
        for compression in (zipfile.ZIP_DEFLATED, zipfile.ZIP_LZMA):
            contents = io.BytesIO()
            with zipfile.ZipFile(contents, 'w', compression=compression) as archive:
                archive.writestr('metadata.json', b'{}')
            damaged = bytearray(contents.getvalue())
            name_length, extra_length = struct.unpack_from('<HH', damaged, 26)
            payload_offset = 30 + name_length + extra_length
            if compression == zipfile.ZIP_DEFLATED:
                damaged[payload_offset] = (damaged[payload_offset] & 0xf8) | 0x07
            else:
                damaged[payload_offset + 4] = 255  # Invalid LZMA properties.
            upload = SimpleUploadedFile('damaged-compression.zip', bytes(damaged))
            with self.subTest(compression=compression), patch(
                'website.package_preview.tempfile.TemporaryDirectory',
                side_effect=self.private_temporary,
            ):
                response = self.client.post(self.url, {'package': upload})
                self.assertEqual(response.status_code, 200, response.content)
                self.assertIsNone(response.context_data['result'])
                self.assertIn('无法校验', str(response.context_data['form'].errors))
                self.assertEqual(list(self.scratch.iterdir()), [])
                self.assertFalse(ResourcePackage.objects.exists())

    def test_malformed_rows_still_count_toward_record_limit(self):
        from word.resource_packages import HEADER, MAX_FILES, validate_package
        (self.package / 'words.tsv').write_text(
            '\t'.join(HEADER) + '\n' + 'x\n' * (MAX_FILES + 20), encoding='utf-8')
        plan = validate_package(self.package)
        self.assertTrue(any('exceeds 5000 rows' in error for error in plan['errors']))
        self.assertLessEqual(len(plan['errors']), MAX_FILES + 5)
        self.assertFalse(ResourcePackage.objects.exists())

    def test_request_upload_stream_and_expanded_limits_are_distinct(self):
        upload = SimpleUploadedFile('large.zip', b'x')
        upload.size = MAX_WEB_ZIP_BYTES + 1
        form = PackagePreviewForm(files={'package': upload})
        self.assertFalse(form.is_valid()); self.assertIn('19 MiB', str(form.errors))
        with patch('website.package_preview.MAX_WEB_REQUEST_BYTES', 10):
            response = self.client.post(self.url, {'package': self.upload()})
            self.assertEqual(response.status_code, 413)
        with patch('website.package_preview.MAX_WEB_ZIP_BYTES', 10), patch('website.package_preview.tempfile.TemporaryDirectory', side_effect=self.private_temporary):
            with self.assertRaises(PackageError): preview_upload(self.upload())
        with patch('word.resource_packages.MAX_TOTAL', 10):
            response = self.client.post(self.url, {'package': self.upload()})
            self.assertIsNone(response.context_data['result'])
            self.assertIn('128 MiB', str(response.context_data['form'].errors))
        self.assertEqual(list(self.scratch.iterdir()), [])

    def test_source_encoding_errors_and_recursive_metadata_are_friendly(self):
        (self.package / 'metadata.json').write_text('{"profile":"legacy-tsv-v1"}', encoding='utf-8')
        (self.package / 'words.tsv').write_bytes(b'\xffinvalid encoding')
        response = self.client.post(self.url, {'package': self.upload()})
        result = response.context_data['result']
        self.assertGreater(result['error_count'], 0)
        self.assertTrue(any('metadata.source' in error for error in result['errors']))
        self.assertTrue(any('decode/parse' in error for error in result['errors']))
        with patch('website.package_preview.validate_package', side_effect=RecursionError), patch('website.package_preview.tempfile.TemporaryDirectory', side_effect=self.private_temporary):
            response = self.client.post(self.url, {'package': self.upload()})
        self.assertIsNone(response.context_data['result'])
        self.assertIn('无法校验', str(response.context_data['form'].errors))
        self.assertEqual(list(self.scratch.iterdir()), [])

    def test_untrusted_text_is_escaped_and_cancel_has_no_mutating_endpoint(self):
        metadata = self.package / 'metadata.json'
        import json
        values = json.loads(metadata.read_text())
        values['source'] = '<script>synthetic_preview()</script>'
        metadata.write_text(json.dumps(values), encoding='utf-8')
        response = self.client.post(self.url, {'package': self.upload()})
        self.assertNotContains(response, '<script>synthetic_preview()</script>')
        self.assertContains(response, '&lt;script&gt;synthetic_preview()&lt;/script&gt;')
        self.assertContains(response, '取消/返回后台首页')
        self.assertFalse(ResourcePackage.objects.exists())
