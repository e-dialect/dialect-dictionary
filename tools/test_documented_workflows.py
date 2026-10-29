"""Check real documented CLI/Compose selections in temporary source/config trees.

Never starts services, registers certificates, creates users or reads live data.
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import unquote, urlsplit
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DOCS = ['README.md', 'docs/README.md', 'docs/directory.md', 'docs/install.md',
        'docs/packages/README.md', 'docs/traefik.md', 'docs/backup.md',
        'docs/troubleshooting.md', 'tools/frontend-config/README.md']


class DocumentedWorkflowTests(unittest.TestCase):
    def test_relative_links_and_shell_syntax(self):
        for name in DOCS:
            path = ROOT / name
            text = path.read_text()
            for link in re.findall(r'\[[^\]]*\]\(([^\s)]+)\)', text):
                url = urlsplit(link)
                if not url.scheme and url.path:
                    self.assertTrue((path.parent / unquote(url.path)).exists(), (name, link))
            for script in re.findall(r'```sh\n(.*?)\n```', text, re.S):
                result = subprocess.run(['bash', '-n'], input=script, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, (name, result.stderr))

    def fixture(self, root):
        for name in ['dictionary', 'VERSION', '.env.example', 'compose.yaml']:
            shutil.copyfile(ROOT / name, root / name)
        for name in ['config', 'ops/compose']:
            shutil.copytree(ROOT / name, root / name, ignore=shutil.ignore_patterns('site.json', 'version.json'))
        source = 'apps/backend/hinghwa-dict-backend'
        for name in ['HinghwaDict/site_config.py', 'word/resource_packages.py']:
            target = root / source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / source / name, target)
        subprocess.run([sys.executable, str(root / 'dictionary'), 'init'], cwd=root, check=True, capture_output=True)

    def test_quoted_directory_and_zip_preview(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.fixture(root)
            package = root / '我的 合成资料包'
            shutil.copytree(ROOT / 'packages/examples/synthetic-legacy-v1', package)
            archive = root / '我的 合成资料包.zip'
            with zipfile.ZipFile(archive, 'w') as target:
                for path in package.rglob('*'):
                    if path.is_file(): target.write(path, path.relative_to(package).as_posix())
            for path in [package, archive]:
                result = subprocess.run([sys.executable, str(root / 'dictionary'), 'preview', str(path), '--publish'], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)['errors'], [])

    @unittest.skipUnless(shutil.which('docker'), 'Docker Compose executable unavailable')
    def test_backup_mode_selects_actual_project_and_volume(self):
        text = (ROOT / 'docs/backup.md').read_text()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.fixture(root)
            for name in ['.env.traefik', '.env.traefik-standalone']:
                content = (ROOT / (name + '.example')).read_text().replace('ACME_EMAIL=', 'ACME_EMAIL=synthetic@example.test')
                (root / name).write_text(content)
            # No inherited deploy parameters, credentials or live Docker context needed.
            env = {k: v for k, v in os.environ.items() if k in ['PATH', 'TMPDIR', 'SYSTEMROOT']}
            for marker, project, proxy in [('compose-local', 'dictionary-demo', False),
                                           ('compose-existing-traefik', 'dictionary-demo', False),
                                           ('compose-standalone-traefik', 'dictionary-standalone', True)]:
                snippet = re.search(r'<!-- ' + marker + r' -->\n```sh\n(.*?)\n```', text, re.S).group(1)
                result = subprocess.run(['bash', '-c', snippet + '\n"${DC[@]}" config --format json'], cwd=root, env=env, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                config = json.loads(result.stdout)
                self.assertEqual(config['name'], project)
                self.assertEqual(config['volumes']['dictionary-data']['name'], project + '_dictionary-data')
                self.assertEqual('proxy' in config['services'], proxy)
                if marker != 'compose-local': self.assertFalse(config['services']['website'].get('ports'))


if __name__ == '__main__': unittest.main()
