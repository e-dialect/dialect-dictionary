"""Meaningful offline snapshot failure/success checks with synthetic-only data."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import tarfile
import tempfile
import unittest

from offline_snapshot import backup, restore, file_hash
from verify_package import verify


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.data = self.root / "data"
        self.config = self.root / "config"
        self.data.mkdir()
        self.config.mkdir()
        with contextlib.closing(sqlite3.connect(self.data / "dictionary.sqlite3")) as db, db:
            db.executescript("CREATE TABLE words(id INTEGER PRIMARY KEY, text TEXT); CREATE TABLE audio(word_id INTEGER REFERENCES words(id), source TEXT); INSERT INTO words VALUES(7,'合成词'); INSERT INTO audio VALUES(7,'/api/media/synthetic.wav');")
        (self.data / "media").mkdir()
        (self.data / "media/synthetic.wav").write_bytes(b"synthetic-unit-test-media")
        (self.config / "site.json").write_text(json.dumps({"name": "合成词典", "contentSource": {"license": "CC0-1.0"}}))
        (self.config / "feature-policy.example.json").write_text('{"enabled":false}')
        self.release = self.root / "RELEASE.json"
        self.release.write_text('{"version":"synthetic-only"}')
        self.archive = self.root / "snapshot.tar.gz"
        self.output = contextlib.redirect_stdout(io.StringIO())
        self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)

    def make(self):
        backup(self.data, self.config, self.release, self.archive)

    def test_roundtrip_content_media_config_and_version(self):
        self.make()
        target = self.root / "restored"
        restore(self.archive, target)
        for name in ["data/media/synthetic.wav", "config/site.json", "config/feature-policy.example.json", "RELEASE.json"]:
            self.assertEqual(file_hash(target / name), file_hash(self.root / name))
        with contextlib.closing(sqlite3.connect(target / "data/dictionary.sqlite3")) as db:
            self.assertEqual(db.execute("SELECT text FROM words WHERE id=7").fetchone(), ("合成词",))
        self.assertEqual(self.archive.stat().st_mode & 0o777, 0o600)

    def test_no_backup_or_restore_overwrite(self):
        self.make()
        before = self.archive.read_bytes()
        with self.assertRaises(FileExistsError):
            self.make()
        self.assertEqual(self.archive.read_bytes(), before)
        with self.assertRaises(ValueError):
            restore(self.archive, self.data)

    def rewrite(self, transform):
        self.make()
        altered = self.root / "altered.tar.gz"
        with tarfile.open(self.archive) as source, tarfile.open(altered, "w:gz") as output:
            for member in source.getmembers():
                content = source.extractfile(member).read()
                member, content = transform(member, content)
                member.size = len(content)
                output.addfile(member, io.BytesIO(content))
        return altered

    def test_tamper_detected_before_target_created(self):
        changed = self.rewrite(lambda member, content: (member, b"changed" if member.name == "config/site.json" else content))
        target = self.root / "restored"
        with self.assertRaisesRegex(ValueError, "checksum"):
            restore(changed, target)
        self.assertFalse(target.exists())

    def test_traversal_and_links_rejected(self):
        def unsafe(member, content):
            if member.name == "config/site.json":
                member.name = "../escape.json"
            return member, content
        changed = self.rewrite(unsafe)
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            restore(changed, self.root / "restored")
        self.assertFalse((self.root / "restored").exists())
        (self.data / "linked").symlink_to(self.config / "site.json")
        with self.assertRaisesRegex(ValueError, "Symlinks"):
            backup(self.data, self.config, self.release, self.root / "linked.tar.gz")

    def test_foreign_key_damage_rejected(self):
        with contextlib.closing(sqlite3.connect(self.data / "dictionary.sqlite3")) as db, db:
            db.execute("INSERT INTO audio VALUES(99,'missing')")
        with self.assertRaisesRegex(ValueError, "foreign key"):
            self.make()
        self.assertFalse(self.archive.exists())

    def package_manifest(self):
        (self.root / "MANIFEST.json").write_text(json.dumps({"files": [{"path": "RELEASE.json", "bytes": self.release.stat().st_size, "sha256": file_hash(self.release)}]}))

    def test_changed_delivery_source_detected(self):
        self.package_manifest()
        self.release.write_text('{"version":"changed"}')
        with self.assertRaisesRegex(ValueError, "Changed"):
            verify(self.root)

    def test_delivery_path_traversal_rejected(self):
        (self.root / "MANIFEST.json").write_text(json.dumps({"files": [{"path": "../outside", "bytes": 0, "sha256": hashlib.sha256(b'').hexdigest()}]}))
        with self.assertRaisesRegex(ValueError, "Invalid"):
            verify(self.root)


if __name__ == "__main__":
    unittest.main()
