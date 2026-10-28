"""Synthetic staged/orphan files never bypass a committed package receipt."""
from pathlib import Path
import tempfile
from unittest.mock import patch
from threading import Thread

from django.contrib.auth.models import User
from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase, override_settings

from word.models import ResourcePackage, ResourcePackageEntry, Word
from word.resource_packages import apply_package, validate_package
from word.test_resource_packages import fixture


class ImportMediaGateTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.media = self.root / 'data/media'
        self.media.mkdir(parents=True)
        self.private = self.root / 'data/private-imports'
        self.override = override_settings(DATA_DIR=self.root/'data', MEDIA_ROOT=str(self.media), PUBLIC_API_BASE='http://localhost:18080/api')
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.user = User.objects.create_user(username='synthetic-media-owner', password=None)
        self.package = self.root / 'package'
        fixture(self.package)

    def get(self, path):
        return self.client.get('/media/' + path)

    def test_orphan_legacy_public_file_denied_all_normalized_aliases(self):
        folder = self.media/'imports/orphan'
        folder.mkdir(parents=True)
        (folder/'sample.wav').write_bytes(b'synthetic-orphan')
        (self.media/'alias').symlink_to(self.media/'imports', target_is_directory=True)
        for path in ['imports/orphan/sample.wav', 'unused/../imports/orphan/sample.wav', 'imports/./orphan/sample.wav', 'alias/orphan/sample.wav']:
            self.assertEqual(self.get(path).status_code,404,path)
        self.assertTrue((folder/'sample.wav').exists())
        self.assertFalse(ResourcePackage.objects.exists())

    def test_committed_public_receipt_plays_private_storage_only_while_visible(self):
        receipt, _ = apply_package(validate_package(self.package, publish=True), self.user.username, publish=True)
        entry = receipt.entries.get()
        self.assertTrue(Path(receipt.storage_path).is_relative_to(self.private))
        self.assertFalse(list(self.media.rglob('*.wav')))
        path='imports/'+Path(receipt.storage_path).name+'/'+entry.audio_name
        response=self.get(path)
        self.assertEqual(response.status_code,200)
        self.assertEqual(b''.join(response.streaming_content),(self.package/'audio/0001synthetic.wav').read_bytes())
        self.assertEqual(response['Cache-Control'],'private, no-store')
        response.close()
        Word.objects.filter(pk=entry.word_id).update(visibility=False)
        self.assertEqual(self.get(path).status_code,404)
        Word.objects.filter(pk=entry.word_id).update(visibility=True)
        ResourcePackage.objects.filter(pk=receipt.pk).update(published=False)
        self.assertEqual(self.get(path).status_code,404)

    def test_interrupted_database_stage_with_residual_media_is_not_public(self):
        observed=[]
        def interruption(*args, **kwargs):
            directory=Path(kwargs['storage_path'])
            files=list(directory.glob('*.wav'))
            self.assertEqual(len(files),1)
            path='imports/'+directory.name+'/'+files[0].name
            self.assertEqual(self.get(path).status_code,404)
            observed.append(path)
            raise RuntimeError('synthetic interruption before receipt exists')
        # Simulate failed cleanup / process loss without killing any real process.
        with patch.object(ResourcePackage.objects,'create',side_effect=interruption), patch('word.resource_packages.shutil.rmtree'):
            with self.assertRaises(RuntimeError):
                apply_package(validate_package(self.package,publish=True),self.user.username,publish=True)
        self.assertFalse(ResourcePackage.objects.exists())
        self.assertFalse(Word.objects.exists())
        self.assertTrue(list(self.private.rglob('*.wav')))
        for path in observed:self.assertEqual(self.get(path).status_code,404)
        receipt,created=apply_package(validate_package(self.package,publish=True),self.user.username,publish=True)
        self.assertTrue(created)
        response=self.get(observed[0]);self.assertEqual(response.status_code,200);response.close()

    def test_ordinary_legacy_media_and_committed_import_location_remain_compatible(self):
        legacy=self.media/'files'
        legacy.mkdir();(legacy/'old.wav').write_bytes(b'legacy-media')
        response=self.get('files/old.wav');self.assertEqual(response.status_code,200);response.close()
        receipt,_=apply_package(validate_package(self.package,publish=True),self.user.username,publish=True)
        old_location=self.media/'imports'/Path(receipt.storage_path).name
        old_location.parent.mkdir(exist_ok=True)
        Path(receipt.storage_path).rename(old_location)
        ResourcePackage.objects.filter(pk=receipt.pk).update(storage_path=str(old_location))
        response=self.get('imports/'+old_location.name+'/'+receipt.entries.get().audio_name)
        self.assertEqual(response.status_code,200);response.close()


from django.db import close_old_connections
from django.test import TransactionTestCase
from threading import Thread


class CommittedReceiptVisibilityTests(TransactionTestCase):
    def test_separate_request_cannot_play_pending_entry_but_can_after_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            media=root/'data/media';media.mkdir(parents=True)
            package=root/'package';fixture(package,'synthetic-commit-boundary')
            user=User.objects.create_user(username='synthetic-commit-owner',password=None)
            with override_settings(DATA_DIR=root/'data',MEDIA_ROOT=str(media),PUBLIC_API_BASE='http://localhost:18080/api'):
                original=ResourcePackageEntry.objects.create
                observed=[]
                def stage_with_pending_entry(*args,**kwargs):
                    entry=original(*args,**kwargs)
                    target=Path(entry.package.storage_path)
                    self.assertTrue((target/entry.audio_name).is_file())
                    path='/media/imports/'+target.name+'/'+entry.audio_name
                    def independent_http_request():
                        close_old_connections()
                        try:
                            response=self.client_class().get(path)
                            observed.append(response.status_code)
                            response.close()
                        finally:
                            close_old_connections()
                    request=Thread(target=independent_http_request)
                    request.start();request.join(timeout=10)
                    self.assertFalse(request.is_alive())
                    self.assertTrue(observed)
                    # SQLite shared-memory tests may reject a concurrent read with
                    # a database lock; production readers can see the old snapshot.
                    # Either must fail closed, never stream the ready private file.
                    self.assertIn(observed[-1],(404,500,503))
                    return entry
                with patch.object(ResourcePackageEntry.objects,'create',side_effect=stage_with_pending_entry):
                    receipt,_=apply_package(validate_package(package,publish=True),user.username,publish=True)
                entry=receipt.entries.get()
                response=self.client.get('/media/imports/'+Path(receipt.storage_path).name+'/'+entry.audio_name)
                self.assertEqual(response.status_code,200)
                self.assertEqual(b''.join(response.streaming_content),(package/'audio/0001synthetic.wav').read_bytes())
