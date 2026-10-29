"""All words, tones, credentials and files are synthetic; no Rime/device install."""
import io
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
import zipfile
from django.core.management import call_command, CommandError
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from word.models import Word, ResourcePackage
from word.resource_packages import apply_package, validate_package
from word.test_resource_packages import fixture
from word.ime_export import ExportError, prepare_export, archive_bytes, write_export, verify_archive


class ImeExportTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.override = override_settings(DATA_DIR=self.root/'data', MEDIA_ROOT=str(self.root/'data/media'))
        self.override.enable(); self.addCleanup(self.override.disable)
        self.owner = User.objects.create_user(username='synthetic-ime-owner', password=None)
        self.other = User.objects.create_user(username='synthetic-ime-other', password=None)
        self.admin = User.objects.create_user(username='synthetic-ime-admin', password=None, is_superuser=True)
        self.package = self.root/'package'; fixture(self.package, 'synthetic-ime')
        self.mapping = self.root/'codes.tsv'; self.mapping.write_text('external_id\tcode\n0001\tceh6 si4\n')

    def load(self, published=True):
        return apply_package(validate_package(self.package, publish=published), self.owner.username, publish=published)[0]

    def plan(self, actor=None, private=False, version='synthetic.1'):
        return prepare_export('synthetic-ime', (actor or self.owner).username, self.mapping, version, private)

    def test_preview_no_writes_and_deterministic_tones_and_provenance(self):
        self.load()
        before = list(Word.objects.values())
        plan = self.plan()
        self.assertEqual(list(Word.objects.values()), before)
        self.assertEqual(plan['rows'][0]['standard_ipa'], 't ɛ s t 1')
        self.assertEqual(plan['rows'][0]['standard_pinyin'], '')
        self.assertEqual(plan['rows'][0]['code'], 'ceh6 si4')
        first = archive_bytes(plan, 'Synthetic fixture author permits local testing')
        self.assertEqual(first, archive_bytes(plan, 'Synthetic fixture author permits local testing'))
        with zipfile.ZipFile(io.BytesIO(first)) as archive:
            name = next(n for n in archive.namelist() if n.endswith('.dict.yaml'))
            text = archive.read(name).decode()
            self.assertIn('合成词\tceh6 si4\t100\n', text)
            source = json.loads(archive.read('source.json'))
            self.assertIn('CC0', source['metadata']['license'])
            self.assertNotIn('storage_path', source)

    def test_private_requires_explicit_flag_and_importer_or_superuser(self):
        self.load(False)
        for actor in [self.owner, self.other, self.admin]:
            with self.assertRaises(ExportError): self.plan(actor)
        with self.assertRaises(ExportError): self.plan(self.other, True)
        self.assertTrue(self.plan(self.owner, True)['includes_private'])
        self.assertTrue(self.plan(self.admin, True)['includes_private'])
        self.owner.is_active = False; self.owner.save()
        with self.assertRaises(ExportError): self.plan(self.owner, True)

    def test_revoked_entry_not_silently_skipped(self):
        self.load(); Word.objects.update(visibility=False)
        with self.assertRaisesRegex(ExportError, 'not fully public'): self.plan(self.other)
        self.assertEqual(len(self.plan(private=True)['rows']), 1)

    def test_mapping_invalid_encoding_tone_injection_missing_extra_duplicate(self):
        self.load()
        cases = ['external_id\tcode\n0001\tt ɛ s t 1\n', 'external_id\tcode\n0001\tceh9\n',
                 'external_id\tcode\n0001\t ceh6\n', 'external_id\tcode\n0001\tceh6\n0001\tceh6\n',
                 'external_id\tcode\n0002\tceh6\n', 'external_id\tcode\n0001\tceh6\n0002\tsi4\n']
        for value in cases:
            with self.subTest(value=value):
                self.mapping.write_text(value)
                with self.assertRaises(ExportError): self.plan()
        self.mapping.write_bytes(b'\xff\xfeinvalid')
        with self.assertRaises(ExportError): self.plan()

    def test_unsafe_words_version_and_no_implicit_ipa_conversion(self):
        self.load()
        with self.assertRaises(ExportError): self.plan(version='bad\nversion')
        for text in ['#comment', 'bad\ttext', 'bad\ntext', 'bad\x00text', ' word ']:
            Word.objects.update(word=text)
            with self.assertRaises(ExportError): self.plan()

    def test_atomic_private_output_rejects_public_path_overwrite_and_no_authorization(self):
        self.load(); plan = self.plan(); path = self.root/'export.zip'
        with self.assertRaises(ExportError): write_export(plan, path, '')
        self.assertFalse(path.exists())
        with self.assertRaises(ExportError): write_export(plan, self.root/'data/media/x.zip', 'synthetic')
        with patch('word.ime_export.os.link', side_effect=OSError('simulated interrupted install')):
            with self.assertRaises(OSError): write_export(plan, path, 'synthetic')
        self.assertFalse(path.exists()); self.assertFalse(list(self.root.glob('.ime-export-*')))
        result = write_export(plan, path, 'synthetic')
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(verify_archive(path)['version'], 'synthetic.1')
        old = path.read_bytes()
        with self.assertRaises(FileExistsError): write_export(plan, path, 'synthetic')
        self.assertEqual(path.read_bytes(), old)
        self.assertEqual(len(result['sha256']), 64)
        self.assertEqual(ResourcePackage.objects.count(), 1)

    def test_corrupt_and_traversal_archives_are_rejected(self):
        self.load(); data = archive_bytes(self.plan(), 'synthetic')
        path = self.root/'changed.zip'
        with zipfile.ZipFile(io.BytesIO(data)) as source, zipfile.ZipFile(path, 'w') as target:
            for name in source.namelist():
                value = source.read(name)
                target.writestr(name, value + b'changed' if name.endswith('.dict.yaml') else value)
        with self.assertRaises(ExportError): verify_archive(path)
        with zipfile.ZipFile(path, 'w') as target:
            for name in ['../x', 'source.json', 'MANIFEST.json', 'INSTALL.txt', 'x.dict.yaml']: target.writestr(name, '{}')
        with self.assertRaises(ExportError): verify_archive(path)

    def test_real_management_argument_parser_and_preview_privacy(self):
        self.load(False)
        args = ['synthetic-ime', '--mapping', str(self.mapping), '--requester', self.owner.username, '--export-version', 'synthetic.1', '--preview']
        with self.assertRaisesRegex(CommandError, 'not fully public'):
            call_command('export_ime_dictionary', *args, stdout=io.StringIO())
        output = io.StringIO()
        call_command('export_ime_dictionary', *args, '--include-private', stdout=output)
        self.assertEqual(json.loads(output.getvalue())['rows'][0]['code'], 'ceh6 si4')
