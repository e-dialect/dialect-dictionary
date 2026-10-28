"""Exercise the real novice preview entry point in a fresh tree, without Django."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class PreviewCliTests(unittest.TestCase):
    def test_preview_writes_nothing_and_zip_errors_have_no_trace(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            shutil.copyfile(ROOT / 'dictionary', target / 'dictionary')
            module = target / 'apps/backend/hinghwa-dict-backend/word/resource_packages.py'
            module.parent.mkdir(parents=True)
            shutil.copyfile(ROOT / 'apps/backend/hinghwa-dict-backend/word/resource_packages.py', module)
            package = target / 'package'
            shutil.copytree(ROOT / 'packages/examples/synthetic-legacy-v1', package)
            before = {p.relative_to(target): p.read_bytes() for p in target.rglob('*') if p.is_file()}
            env = dict(os.environ)
            env.pop('PYTHONDONTWRITEBYTECODE', None)
            result = subprocess.run([sys.executable, str(target/'dictionary'), 'preview', str(package)], env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['errors'], [])
            self.assertEqual(before, {p.relative_to(target): p.read_bytes() for p in target.rglob('*') if p.is_file()})
            (target/'broken.zip').write_bytes(b'PK\x03\x04truncated')
            result = subprocess.run([sys.executable, str(target/'dictionary'), 'preview', str(target/'broken.zip')], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn('Traceback', result.stderr)

class VersionCliTests(unittest.TestCase):
    def test_unpacked_source_never_inherits_parent_git_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            subprocess.run(['git', 'init', '--quiet', str(parent)], check=True)
            (parent / 'parent.txt').write_text('synthetic parent repository')
            subprocess.run(['git', '-C', str(parent), 'add', 'parent.txt'], check=True)
            subprocess.run(['git', '-C', str(parent), '-c', 'user.name=Synthetic Test', '-c', 'user.email=synthetic@example.test', 'commit', '--quiet', '-m', 'synthetic fixture'], check=True)
            target = parent / 'unpacked-release'
            target.mkdir()
            shutil.copyfile(ROOT / 'dictionary', target / 'dictionary')
            (target / 'VERSION').write_text('synthetic-version')
            def version():
                result = subprocess.run([sys.executable, str(target / 'dictionary'), 'version'], capture_output=True, text=True, check=True)
                return json.loads(result.stdout)
            record = version()
            self.assertEqual(record['sourceCommit'], 'unknown')
            self.assertIsNone(record['sourceDirty'])
            (target / 'RELEASE.json').write_text(json.dumps({'sourceCommit': 'synthetic-release-source'}))
            self.assertEqual(version()['sourceCommit'], 'synthetic-release-source')

if __name__ == '__main__': unittest.main()
