"""Synthetic-only package validation and transactional privacy regressions."""
import copy
import io
import json
from pathlib import Path
import tempfile
import wave
import zipfile
from unittest.mock import patch
from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from word.models import Word, Pronunciation, ResourcePackage
from word.resource_packages import PackageError, apply_package, validate_package, read_package, package_lock


def fixture(root, package_id='synthetic-test'):
    root.mkdir(exist_ok=True)
    (root / 'audio').mkdir(exist_ok=True)
    metadata = {'profile': 'legacy-tsv-v1', 'package_id': package_id, 'source': 'Self-written synthetic words and generated digital silence', 'license': 'CC0-1.0 synthetic fixture only', 'dialect': {'county': '合成县', 'town': '合成镇', 'mapping_note': 'Synthetic mapping, not a real dialect'}, 'publication': {'authorized': True, 'statement': 'The fixture author permits publication of this synthetic text and digital silence.'}}
    (root / 'metadata.json').write_text(json.dumps(metadata), encoding='utf-8')
    (root / 'words.tsv').write_text('编号\t普通话\t方言\t发音\t注释\n0001\t合成示例\t合成词\tt ɛ s t 1\t仅供导入测试\n', encoding='utf-8')
    with wave.open(str(root / 'audio/0001synthetic.wav'), 'wb') as audio:
        audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(8000); audio.writeframes(b'\0\0' * 800)
    return metadata


class PackageImportTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.package = self.root / 'package'
        fixture(self.package)
        self.media = self.root / 'data/media'
        self.media.mkdir(parents=True)
        self.override = override_settings(DATA_DIR=self.root / 'data', MEDIA_ROOT=str(self.media), PUBLIC_API_BASE='http://localhost:18080/api')
        self.override.enable(); self.addCleanup(self.override.disable)
        self.user = User.objects.create_user(username='synthetic-importer', password=None)

    def test_preview_is_no_write_and_preserves_encoding_and_ipa(self):
        before = set(self.root.rglob('*'))
        with self.assertNumQueries(0):
            plan = validate_package(self.package)
        self.assertEqual(plan['errors'], [])
        self.assertEqual(plan['rows'][0]['ipa'], 't ɛ s t 1')
        self.assertEqual(set(self.root.rglob('*')), before)
        self.assertFalse(ResourcePackage.objects.exists())
        raw = (self.package / 'words.tsv').read_text()
        for encoding in ['utf-8-sig', 'utf-16', 'utf-16-be']:
            data = raw.encode(encoding)
            if encoding == 'utf-16-be': data = b'\xfe\xff' + data
            (self.package / 'words.tsv').write_bytes(data)
            self.assertEqual(validate_package(self.package)['errors'], [])

    def test_private_import_never_uses_public_media_and_is_idempotent(self):
        plan = validate_package(self.package)
        receipt, created = apply_package(plan, self.user.username)
        self.assertTrue(created); self.assertFalse(receipt.published)
        self.assertFalse(Word.objects.get().visibility)
        self.assertEqual(Word.objects.get().standard_ipa, 't ɛ s t 1')
        self.assertEqual(Pronunciation.objects.get().source, '')
        self.assertEqual(Pronunciation.objects.get().ipa, 't ɛ s t 1')
        self.assertEqual(self.client.get('/pronunciation/' + str(Pronunciation.objects.get().pk)).status_code, 403)
        self.assertFalse(list(self.media.rglob('*.wav')))
        self.assertTrue(list((self.root/'data/private-imports').rglob('*.wav')))
        self.assertEqual(self.client.get('/media/' + Path(receipt.storage_path).name + '/0001synthetic.wav').status_code, 404)
        self.assertFalse(apply_package(plan, self.user.username)[1])
        self.assertEqual(Word.objects.count(), 1)
        (self.package / 'words.tsv').write_text((self.package/'words.tsv').read_text() + '0002\t新\t新\tt\t变更\n')
        altered = validate_package(self.package); altered['errors'] = []
        with self.assertRaisesRegex(PackageError, 'different digest'):
            apply_package(altered, self.user.username)

    def test_public_requires_authorization_and_two_package_ids_coexist(self):
        metadata = json.loads((self.package/'metadata.json').read_text())
        metadata['publication']['authorized'] = False
        (self.package/'metadata.json').write_text(json.dumps(metadata))
        denied = validate_package(self.package, publish=True)
        self.assertTrue(denied['errors'])
        with self.assertRaises(PackageError): apply_package(denied, self.user.username, publish=True)
        self.assertFalse(list(self.media.rglob('*.wav')))
        fixture(self.package)
        for package_id in ['first-package', 'second-package']:
            metadata = json.loads((self.package/'metadata.json').read_text()); metadata['package_id'] = package_id
            (self.package/'metadata.json').write_text(json.dumps(metadata))
            receipt, _ = apply_package(validate_package(self.package, publish=True), self.user.username, publish=True)
            item = receipt.entries.get()
            self.assertTrue(item.word.visibility); self.assertEqual(item.external_id, '0001')
            detail = self.client.get('/words/' + str(item.word_id))
            self.assertEqual(detail.status_code, 200)
            self.assertEqual(detail.json()['word']['standard_ipa'], 't ɛ s t 1')
            self.assertEqual(detail.json()['word']['source'], item.pronunciation.source)
            pronunciation_detail = self.client.get('/pronunciation/' + str(item.pronunciation_id))
            self.assertEqual(pronunciation_detail.status_code, 200)
            item.word.refresh_from_db(); item.pronunciation.refresh_from_db()
            self.assertEqual(item.word.standard_ipa, 't ɛ s t 1')
            self.assertEqual(item.pronunciation.ipa, 't ɛ s t 1')
            self.assertIn('/api/media/imports/', item.pronunciation.source)
            self.assertTrue((Path(receipt.storage_path)/item.audio_name).is_file())
        self.assertEqual(Word.objects.count(), 2)
        self.assertEqual(self.client.get('/words').status_code, 200)
        item = receipt.entries.get()
        self.assertEqual(self.client.get('/words/' + str(item.word.pk)).status_code, 200)
        self.assertNotEqual(*list(Word.objects.values_list('id', flat=True)))

    def test_database_and_files_cleaned_on_failure(self):
        for publish in [False, True]:
            with patch('word.models.ResourcePackageEntry.objects.create', side_effect=RuntimeError('injected after DB word and file stage')):
                with self.assertRaises(RuntimeError): apply_package(validate_package(self.package, publish=publish), self.user.username, publish=publish)
            self.assertFalse(ResourcePackage.objects.exists()); self.assertFalse(Word.objects.exists()); self.assertFalse(Pronunciation.objects.exists())
            self.assertFalse(list(self.media.rglob('*.wav')))
            self.assertFalse(list((self.root/'data/private-imports').rglob('*.wav')))

    def test_invalid_mappings_and_flv_are_preview_errors(self):
        (self.package/'audio/0001synthetic.wav').rename(self.package/'audio/0002synthetic.wav')
        errors = '\n'.join(validate_package(self.package)['errors'])
        self.assertIn('line 2: missing audio', errors); self.assertIn('Extra audio', errors)
        (self.package/'audio/0002synthetic.wav').rename(self.package/'audio/0001synthetic.flv')
        self.assertIn('FLV', '\n'.join(validate_package(self.package)['errors']))
        self.assertFalse(list(self.media.rglob('*')))

    def test_zip_and_path_link_size_limits(self):
        archive = self.root/'valid.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            for p in self.package.rglob('*'):
                if p.is_file(): z.write(p, p.relative_to(self.package).as_posix())
        self.assertEqual(validate_package(archive)['errors'], [])
        for name in ['../escape', '/absolute', 'C:/absolute']:
            with zipfile.ZipFile(self.root/'bad.zip', 'w') as z: z.writestr(name, b'bad')
            with self.assertRaises(PackageError): read_package(self.root/'bad.zip')
        (self.package/'linked').symlink_to(self.package/'words.tsv')
        with self.assertRaisesRegex(PackageError, 'Symlink'): validate_package(self.package)
        (self.package/'linked').unlink()
        with patch('word.resource_packages.MAX_TOTAL', 4):
            with self.assertRaises(PackageError): validate_package(archive)
        with self.assertRaisesRegex(PackageError, 'does not exist'): apply_package(validate_package(self.package), 'absent-user')
        self.assertFalse(Word.objects.exists())

    def test_short_source_id_preserved_and_filesystem_failure_cleans(self):
        table = self.package/'words.tsv'
        table.write_text(table.read_text().replace('0001\t', '1\t'))
        plan = validate_package(self.package)
        self.assertEqual(plan['errors'], [])
        self.assertEqual(plan['rows'][0]['external_id'], '1')
        self.assertEqual(plan['rows'][0]['audio'], 'audio/0001synthetic.wav')
        for publish in [False, True]:
            with patch('pathlib.Path.rename', side_effect=OSError('injected file move failure')):
                with self.assertRaises(OSError): apply_package(plan, self.user.username, publish=publish)
            self.assertFalse(ResourcePackage.objects.exists())
            self.assertFalse(list(self.media.rglob('*.wav')))
            self.assertFalse(list((self.root/'data/private-imports').rglob('*.wav')))
        receipt, _ = apply_package(plan, self.user.username)
        self.assertEqual(receipt.entries.get().external_id, '1')

    def test_corrupt_and_unsupported_zip_are_actionable_errors(self):
        archive = self.root/'corrupt.zip'
        with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_STORED) as z:
            for p in self.package.rglob('*'):
                if p.is_file(): z.write(p, p.relative_to(self.package).as_posix())
        content = bytearray(archive.read_bytes())
        payload = (self.package/'words.tsv').read_bytes()
        offset = content.index(payload)
        content[offset] ^= 1
        archive.write_bytes(content)
        with self.assertRaisesRegex(PackageError, 'ZIP'):
            validate_package(archive)
        with patch('word.resource_packages.zipfile.ZipFile', side_effect=NotImplementedError('unsupported compression')):
            # The directory route is unrelated; use a ZIP signature to enter ZIP handling.
            with patch('word.resource_packages.zipfile.is_zipfile', return_value=True):
                with self.assertRaisesRegex(PackageError, 'unsupported ZIP'):
                    validate_package(archive)
        self.assertFalse(ResourcePackage.objects.exists())
        self.assertFalse(list(self.media.rglob('*')))

    def interrupted_destination(self, plan):
        # A controlled cleanup omission stands in for a terminated process. No real kill.
        with patch('word.models.ResourcePackageEntry.objects.create', side_effect=RuntimeError('interrupted before commit')):
            with patch('word.resource_packages.shutil.rmtree'):
                with self.assertRaises(RuntimeError):
                    apply_package(plan, self.user.username, publish=True)
        self.assertFalse(ResourcePackage.objects.exists())
        files = list((self.root/'data/private-imports').rglob('*.wav'))
        self.assertEqual(len(files), 1)
        self.assertFalse(list(self.media.rglob('*.wav')))
        return files[0]

    def test_interrupted_public_import_retries_identical_bytes_and_fills_missing(self):
        plan = validate_package(self.package, publish=True)
        leftover = self.interrupted_destination(plan)
        original = leftover.read_bytes()
        leftover.unlink()  # Simulate interruption before the last expected file was installed.
        receipt, created = apply_package(plan, self.user.username, publish=True)
        self.assertTrue(created)
        self.assertEqual((Path(receipt.storage_path)/leftover.name).read_bytes(), original)
        self.assertTrue(Path(receipt.storage_path).is_relative_to(self.root/'data/private-imports'))
        self.assertFalse(list(self.media.rglob('*.wav')))
        self.assertFalse(apply_package(plan, self.user.username, publish=True)[1])
        self.assertEqual(Word.objects.count(), 1)

    def test_adopted_bytes_survive_retry_failure_then_success(self):
        plan = validate_package(self.package, publish=True)
        leftover = self.interrupted_destination(plan)
        before = leftover.read_bytes()
        with patch('word.models.ResourcePackageEntry.objects.create', side_effect=RuntimeError('retry fails after adopting')):
            with self.assertRaises(RuntimeError): apply_package(plan, self.user.username, publish=True)
        self.assertEqual(leftover.read_bytes(), before)
        self.assertFalse(ResourcePackage.objects.exists())
        receipt, _ = apply_package(plan, self.user.username, publish=True)
        self.assertEqual(Path(receipt.storage_path), leftover.parent)
        self.assertEqual(leftover.read_bytes(), before)

    def test_residual_unknown_mismatch_or_link_is_not_overwritten(self):
        plan = validate_package(self.package, publish=True)
        leftover = self.interrupted_destination(plan)
        original = leftover.read_bytes()
        alien = leftover.parent/'unknown.txt'
        alien.write_bytes(b'leave my unrelated bytes alone')
        with self.assertRaisesRegex(PackageError, 'unknown or linked'):
            apply_package(plan, self.user.username, publish=True)
        self.assertEqual(alien.read_bytes(), b'leave my unrelated bytes alone')
        alien.unlink()
        leftover.write_bytes(b'unexpected modified media')
        with self.assertRaisesRegex(PackageError, 'bytes differ'):
            apply_package(plan, self.user.username, publish=True)
        self.assertEqual(leftover.read_bytes(), b'unexpected modified media')
        leftover.unlink()
        external = self.root/'external.wav'; external.write_bytes(original)
        leftover.symlink_to(external)
        with self.assertRaisesRegex(PackageError, 'unknown or linked'):
            apply_package(plan, self.user.username, publish=True)
        self.assertTrue(leftover.is_symlink())
        self.assertEqual(external.read_bytes(), original)
        self.assertFalse(ResourcePackage.objects.exists())

    def test_same_package_busy_lock_is_actionable_and_released(self):
        plan = validate_package(self.package)
        private = self.root/'data/private-imports'; private.mkdir()
        with package_lock(private, plan['metadata']['package_id']):
            with self.assertRaisesRegex(PackageError, 'Import busy'):
                apply_package(plan, self.user.username)
            self.assertFalse(ResourcePackage.objects.exists())
            self.assertFalse(list(private.glob('.stage-*')))
        self.assertTrue(apply_package(plan, self.user.username)[1])
