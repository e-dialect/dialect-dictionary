"""Standalone legacy aliases must not bypass import publication consistency."""
from pathlib import Path
import tempfile
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import resolve
from word.models import ResourcePackage, ResourcePackageEntry, Word
from word.resource_packages import apply_package, validate_package
from word.test_resource_packages import fixture
from website.views import openUrl


class LegacyImportAliasTests(TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.media=self.root/'data/media';self.media.mkdir(parents=True)
        self.settings_override=override_settings(DATA_DIR=self.root/'data',MEDIA_ROOT=str(self.media),PUBLIC_API_BASE='http://localhost:18080/api')
        self.settings_override.enable();self.addCleanup(self.settings_override.disable)
        self.user=User.objects.create_user(username='synthetic-alias-owner',password=None)
        self.package=self.root/'package';fixture(self.package,'synthetic-legacy-alias')

    def alias(self,folder):
        return '/files/imports/'+folder+'/0001/a/b/c.wav'

    def test_orphan_alias_and_physical_alias_cannot_read_import(self):
        folder=self.media/'imports/orphan';folder.mkdir(parents=True)
        (folder/'0001_a_b_c.wav').write_bytes(b'synthetic-orphan')
        self.assertEqual(self.client.get(self.alias('orphan')).status_code,404)
        self.assertEqual(self.client.get('/media/imports/orphan/0001_a_b_c.wav').status_code,404)
        (self.media/'alias').symlink_to(self.media/'imports',target_is_directory=True)
        self.assertEqual(self.client.get('/files/alias/orphan/0001/a/b/c.wav').status_code,404)
        self.assertTrue((folder/'0001_a_b_c.wav').is_file())
        self.assertFalse(ResourcePackage.objects.exists())

    def test_committed_legacy_import_alias_respects_private_and_revoked_state(self):
        receipt,_=apply_package(validate_package(self.package,publish=True),self.user.username,publish=True)
        entry=receipt.entries.get();directory=Path(receipt.storage_path)
        (directory/entry.audio_name).rename(directory/'0001_a_b_c.wav')
        ResourcePackageEntry.objects.filter(pk=entry.pk).update(audio_name='0001_a_b_c.wav')
        old=self.media/'imports'/directory.name;old.parent.mkdir(exist_ok=True);directory.rename(old)
        ResourcePackage.objects.filter(pk=receipt.pk).update(storage_path=str(old))
        url=self.alias(old.name)
        response=self.client.get(url);self.assertEqual(response.status_code,200)
        self.assertEqual(b''.join(response.streaming_content),(self.package/'audio/0001synthetic.wav').read_bytes());response.close()
        ResourcePackage.objects.filter(pk=receipt.pk).update(published=False)
        self.assertEqual(self.client.get(url).status_code,404)
        ResourcePackage.objects.filter(pk=receipt.pk).update(published=True)
        Word.objects.filter(pk=entry.word_id).update(visibility=False)
        self.assertEqual(self.client.get(url).status_code,404)

    def test_ordinary_legacy_media_and_nonstandalone_handler_stay_compatible(self):
        directory=self.media/'files/legacy';directory.mkdir(parents=True)
        (directory/'2026_01_02_old.wav').write_bytes(b'synthetic-ordinary-legacy')
        response=self.client.get('/files/files/legacy/2026/01/02/old.wav')
        self.assertEqual(response.status_code,200)
        self.assertEqual(b''.join(response.streaming_content),b'synthetic-ordinary-legacy')
        self.assertEqual(response['Content-Type'],'application/octet-stream')
        self.assertIn('old.wav',response['Content-Disposition']);response.close()
        self.assertIs(resolve('/files/imports/orphan/0001/a/b/c.wav',urlconf='HinghwaDict.urls').func,openUrl)
