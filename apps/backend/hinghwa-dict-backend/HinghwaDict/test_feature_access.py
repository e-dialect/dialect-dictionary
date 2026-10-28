"""Request-level gates; no external services or production data."""
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from django.http import JsonResponse
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.views import View
from HinghwaDict.feature_access import WordApplicationPolicyMixin
from word.application.views import MultiApplication, SingleApplication


class Probe(WordApplicationPolicyMixin, View):
    def get(self, request):
        return JsonResponse({"read": True})
    def post(self, request):
        return JsonResponse({"written": True})
    put = post
    patch = post
    delete = post


class FeatureAccessTests(SimpleTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "policy.json"
        self.override = override_settings(FEATURE_POLICY_PATH=str(self.path))
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.factory = RequestFactory()

    def policy(self, enabled, roles=None):
        now = datetime.now(timezone.utc)
        self.path.write_text(json.dumps({
            "version": 1,
            "issuedAt": (now - timedelta(seconds=1)).isoformat().replace("+00:00", "Z"),
            "expiresAt": (now + timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
            "features": {"wordApplications": {"enabled": enabled, "roles": roles or ["staff"]}},
        }))

    def test_disabled_blocks_every_write_even_spoofed_headers(self):
        for enabled in (None, False):
            if enabled is not None:
                self.policy(enabled)
            for method in ("post", "put", "patch", "delete"):
                request = getattr(self.factory, method)("/", HTTP_PLATFORM="review", HTTP_ROLE="superuser")
                self.assertEqual(Probe.as_view()(request).status_code, 403)

    def test_original_read_path_remains_available(self):
        self.assertEqual(Probe.as_view()(self.factory.get("/")).status_code, 200)

    @patch("HinghwaDict.feature_access.token_user")
    @patch("HinghwaDict.feature_access.token_pass", return_value="verified")
    def test_server_role_required(self, verify, get_user):
        self.policy(True)
        user = SimpleNamespace(is_active=True, is_authenticated=True, is_staff=False, is_superuser=False)
        get_user.return_value = user
        request = self.factory.post("/", HTTP_ROLE="staff")
        self.assertEqual(Probe.as_view()(request).status_code, 403)
        user.is_staff = True
        self.assertEqual(Probe.as_view()(request).status_code, 200)
        verify.assert_called()

    def test_actual_application_classes_have_gate(self):
        self.assertTrue(issubclass(MultiApplication, WordApplicationPolicyMixin))
        self.assertTrue(issubclass(SingleApplication, WordApplicationPolicyMixin))
        self.assertEqual(MultiApplication.as_view()(self.factory.post("/")).status_code, 403)
        self.assertEqual(SingleApplication.as_view()(self.factory.put("/"), id=1).status_code, 403)

    def test_public_endpoint_is_no_store_and_read_only(self):
        response = self.client.get("/capabilities", HTTP_HOST="localhost")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["features"]["wordApplications"]["enabled"])
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(self.client.post("/capabilities", HTTP_HOST="localhost").status_code, 405)
