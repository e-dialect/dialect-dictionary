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
        'docs/troubleshooting.md', 'docs/ime-export.md', 'tools/frontend-config/README.md']


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

    def test_local_ports_and_successful_start_addresses(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.fixture(root)
            docker = root / 'docker'
            real_docker = shutil.which('docker')
            if not real_docker:
                self.skipTest('Docker Compose executable unavailable')
            docker.write_text(f'#!/bin/sh\ncase " $* " in\n'
                              f'  *" config --format json "*) exec "{real_docker}" "$@";;\n'
                              '  *" port website 8080 "*) echo 127.0.0.1:18081;;\nesac\n')
            docker.chmod(0o700)
            env = dict(os.environ, PATH=str(root) + os.pathsep + os.environ['PATH'], HTTP_PORT='18081')
            def invoke(*args):
                return subprocess.run([sys.executable, str(root / 'dictionary'), *args],
                                      cwd=root, env=env, text=True, capture_output=True, check=True)
            checked = invoke('check')
            for field in ['webUrl', 'mobileUrl', 'HTTP_PORT', '18080', '18081']:
                self.assertIn(field, checked.stderr)
            started = invoke('start', '--no-build')
            self.assertIn('电脑端：http://127.0.0.1:18081/', started.stdout)
            self.assertIn('手机端：http://127.0.0.1:18081/mobile/', started.stdout)
            site = root / 'config/site.json'
            site.write_text(site.read_text().replace('18080', '18081'))
            self.assertNotIn('HTTP_PORT', invoke('check').stderr)
            env_file = root / '.env.traefik'
            shutil.copyfile(ROOT / '.env.traefik.example', env_file)
            domain = re.search(r'^DOMAIN=(.+)$', env_file.read_text(), re.M)[1]
            site.write_text(site.read_text().replace('http://localhost:18081', 'https://' + domain))
            proxy = invoke('--traefik', 'start', '--no-build')
            self.assertIn('手机端：https://' + domain + '/mobile/', proxy.stdout)

    @unittest.skipUnless(shutil.which('docker'), 'Docker Compose executable unavailable')
    def test_proxy_checks_effective_mount_and_environment_override(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.fixture(root)
            base = root / 'config/site.json'
            site = root / 'config/proxy-site.json'
            site.write_text(base.read_text().replace('http://localhost:18080', 'https://dictionary.example.org'))
            for mode in ('traefik', 'traefik-standalone'):
                overlay = root / ('.env.' + mode)
                overlay.write_text((ROOT / (overlay.name + '.example')).read_text()
                                   .replace('./config/site.json', './config/proxy-site.json')
                                   .replace('ACME_EMAIL=', 'ACME_EMAIL=ops@example.test'))
                command = [sys.executable, 'dictionary', '--' + mode, 'check']
                valid = subprocess.run(command, cwd=root, capture_output=True, text=True)
                self.assertEqual(valid.returncode, 0, valid.stderr)
                invalid = subprocess.run(command, cwd=root, capture_output=True, text=True,
                                         env=dict(os.environ, SITE_CONFIG=str(base)))
                self.assertNotEqual(invalid.returncode, 0)
                self.assertIn(str(base), invalid.stderr)
            base.write_bytes(site.read_bytes())
            site.write_text('{"name":"incomplete"}')
            invalid = subprocess.run(command, cwd=root, capture_output=True, text=True)
            self.assertNotEqual(invalid.returncode, 0)
            self.assertIn(str(site), invalid.stderr)

    def test_init_isolates_new_directories_and_preserves_an_existing_project(self):
        with tempfile.TemporaryDirectory() as temporary:
            files = []
            for name in ('one', 'two'):
                root = Path(temporary) / name
                root.mkdir()
                self.fixture(root)
                files.append((root / '.env').read_text())
            self.assertNotEqual(files[0], files[1])
            legacy = (ROOT / '.env.example').read_bytes()
            (root / '.env').write_bytes(legacy)
            subprocess.run([sys.executable, 'dictionary', 'init'], cwd=root, check=True, capture_output=True)
            self.assertEqual((root / '.env').read_bytes(), legacy)

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
            project_name = re.search(r'^COMPOSE_PROJECT_NAME=(.+)$', (root / '.env').read_text(), re.M)[1]
            for marker, project, proxy in [('compose-local', project_name, False),
                                           ('compose-existing-traefik', project_name, False),
                                           ('compose-standalone-traefik', project_name + '-standalone', True)]:
                snippet = re.search(r'<!-- ' + marker + r' -->\n```sh\n(.*?)\n```', text, re.S).group(1)
                result = subprocess.run(['bash', '-c', snippet + '\n"${DC[@]}" config --format json'], cwd=root, env=env, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                config = json.loads(result.stdout)
                self.assertEqual(config['name'], project)
                self.assertEqual(config['volumes']['dictionary-data']['name'], project + '_dictionary-data')
                self.assertEqual('proxy' in config['services'], proxy)
                if marker != 'compose-local': self.assertFalse(config['services']['website'].get('ports'))


if __name__ == '__main__': unittest.main()
