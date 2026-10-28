"""Offline trust-boundary regressions; no daemon, network, or credentials."""
import ast
import os
import re
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def proxy_settings(mode=None):
    """Evaluate the real standalone mode block without third-party imports."""
    tree = ast.parse((ROOT / 'apps/backend/hinghwa-dict-backend/HinghwaDict/standalone.py').read_text())
    begin = next(i for i, n in enumerate(tree.body) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'PROXY_MODE' for t in n.targets))
    end = next(i for i, n in enumerate(tree.body) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'DICTIONARY_CONFIG' for t in n.targets))
    values = {'os': os}
    with patch.dict(os.environ, {} if mode is None else {'PROXY_MODE': mode}, clear=True):
        exec(compile(ast.Module(body=tree.body[begin:end], type_ignores=[]), '<standalone proxy settings>', 'exec'), values)
    return values


class ProxyBoundaryTests(unittest.TestCase):
    def test_local_never_trusts_forwarded_proto(self):
        for mode in (None, 'local'):
            config = proxy_settings(mode)
            self.assertIsNone(config['SECURE_PROXY_SSL_HEADER'])
            self.assertFalse(config['CSRF_COOKIE_SECURE'])
            self.assertFalse(config['USE_X_FORWARDED_HOST'])

    def test_only_explicit_traefik_trusts_nginx(self):
        config = proxy_settings('traefik')
        self.assertEqual(config['SECURE_PROXY_SSL_HEADER'], ('HTTP_X_FORWARDED_PROTO', 'https'))
        self.assertTrue(config['SESSION_COOKIE_SECURE'])
        self.assertTrue(config['CSRF_COOKIE_SECURE'])
        for invalid in ('https', 'true', 'TRAEFIK', ''):
            with self.assertRaises(ValueError):
                proxy_settings(invalid)

    def test_startup_rejects_inconsistent_https_site(self):
        tree = ast.parse((ROOT / 'apps/backend/hinghwa-dict-backend/HinghwaDict/standalone.py').read_text())
        node = next(n for n in tree.body if isinstance(n, ast.If) and isinstance(n.test, ast.Compare) and isinstance(n.test.left, ast.Name) and n.test.left.id == 'PROXY_MODE' and isinstance(n.test.ops[0], ast.Eq))
        code = compile(ast.Module(body=[node], type_ignores=[]), '<standalone site boundary>', 'exec')
        site = {'webUrl': 'https://dictionary.example.test', 'mobileUrl': 'https://dictionary.example.test/mobile', 'apiBase': '/api'}
        for domain, changes, valid in [
            ('dictionary.example.test', {}, True),
            ('dictionary.example.test', {'webUrl': 'http://dictionary.example.test'}, False),
            ('dictionary.example.test', {'mobileUrl': 'https://evil.example.test/mobile'}, False),
            ('dictionary.example.test', {'apiBase': 'https://evil.example.test/api'}, False),
            ('dictionary.example.test`)', {}, False),
            ('*.example.test', {}, False),
            ('dictionary.example.test:443', {}, False),
        ]:
            with self.subTest(domain=domain, changes=changes), patch.dict(os.environ, {'DOMAIN': domain}):
                values = {'os': os, 're': re, 'PROXY_MODE': 'traefik', 'SITE_CONFIG': dict(site, **changes)}
                if valid:
                    exec(code, values)
                else:
                    with self.assertRaises(ValueError):
                        exec(code, values)

    def test_ingress_does_not_forward_client_scheme(self):
        local = (ROOT / 'ops/docker/nginx.conf').read_text()
        proxy = (ROOT / 'ops/docker/nginx.traefik.conf').read_text()
        self.assertIn('proxy_set_header X-Forwarded-Proto $scheme;', local)
        self.assertIn('proxy_set_header X-Forwarded-Proto https;', proxy)
        self.assertNotIn('$http_x_forwarded_proto', proxy)
        self.assertNotIn('$http_forwarded', proxy)
        self.assertNotIn('proxy_set_header X-Forwarded-Proto $scheme;', proxy)

    def test_overlay_has_no_new_proxy_or_host_ports(self):
        overlay = (ROOT / 'ops/compose/traefik.yaml').read_text()
        self.assertIn('ports: !override []', overlay)
        self.assertIn('external: true', overlay)
        self.assertIn('loadbalancer.server.port=8080', overlay)
        self.assertIn('.tls=true', overlay)
        self.assertIn('traefik.enable: "false"', overlay)
        self.assertNotIn('image:', overlay)
        self.assertNotIn('acme.json', overlay)
        self.assertNotIn('docker.sock', overlay)


if __name__ == '__main__':
    unittest.main()
