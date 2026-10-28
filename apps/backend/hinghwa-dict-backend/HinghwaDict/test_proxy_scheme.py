"""Synthetic HTTP-only proxy/security checks, without a public endpoint or TLS."""
from django.contrib.auth.models import User
from django.test import Client, RequestFactory, TestCase, override_settings

PROXY_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


class ProxySchemeTests(TestCase):
    @override_settings(SECURE_PROXY_SSL_HEADER=None)
    def test_local_ignores_forged_scheme(self):
        for forged in ('https', 'https,http', 'https,https', 'http'):
            request = RequestFactory().get('/', HTTP_X_FORWARDED_PROTO=forged)
            self.assertFalse(request.is_secure())

    @override_settings(SECURE_PROXY_SSL_HEADER=PROXY_HEADER)
    def test_overwritten_proxy_header_marks_http_hop_secure(self):
        # nginx's literal https replaces incoming http/https/comma-list values.
        request = RequestFactory().get('/', HTTP_X_FORWARDED_PROTO='https')
        self.assertTrue(request.is_secure())
        request = RequestFactory().get('/', HTTP_X_FORWARDED_PROTO='http')
        self.assertFalse(request.is_secure())

    @override_settings(
        SECURE_PROXY_SSL_HEADER=PROXY_HEADER,
        SESSION_COOKIE_SECURE=True,
        CSRF_COOKIE_SECURE=True,
        ALLOWED_HOSTS=['dictionary.example.test'],
        CSRF_TRUSTED_ORIGINS=['https://dictionary.example.test'],
    )
    def test_https_admin_login_csrf_and_session(self):
        User.objects.create_superuser('synthetic-proxy-admin', 'synthetic@example.test', 'synthetic-only-password')
        client = Client(enforce_csrf_checks=True)
        headers = {'HTTP_HOST': 'dictionary.example.test', 'HTTP_X_FORWARDED_PROTO': 'https'}
        response = client.get('/admin/login/', **headers)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.wsgi_request.is_secure())
        self.assertTrue(client.cookies['csrftoken']['secure'])
        credentials = {'username': 'synthetic-proxy-admin', 'password': 'synthetic-only-password', 'next': '/admin/'}
        self.assertEqual(client.post('/admin/login/', credentials, HTTP_ORIGIN='https://dictionary.example.test', **headers).status_code, 403)
        credentials['csrfmiddlewaretoken'] = client.cookies['csrftoken'].value
        self.assertEqual(client.post('/admin/login/', credentials, HTTP_ORIGIN='https://attacker.example.test', **headers).status_code, 403)
        response = client.post('/admin/login/', credentials, HTTP_ORIGIN='https://dictionary.example.test', **headers)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(client.cookies['sessionid']['secure'])
        response = client.get('/admin/', **headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(client.get('/admin/', HTTP_HOST='attacker.example.test', HTTP_X_FORWARDED_PROTO='https').status_code, 400)
