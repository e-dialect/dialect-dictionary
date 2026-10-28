"""Stdlib-only policy tests: python3 -m unittest HinghwaDict.test_feature_policy."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from HinghwaDict.feature_policy import read_policy, permits, capabilities


class FeaturePolicyTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "policy.json"
        self.now = datetime(2026, 10, 25, 7, 0, tzinfo=timezone.utc)
        self.data = {
            "version": 1, "issuedAt": "2026-10-25T00:00:00Z",
            "expiresAt": "2026-10-26T00:00:00Z",
            "features": {"wordApplications": {"enabled": True, "roles": ["staff"]}},
        }
        self.write()

    def write(self):
        self.path.write_text(json.dumps(self.data))

    def test_roles_are_server_attributes_and_active_required(self):
        rule = read_policy(self.path, self.now)
        user = SimpleNamespace(is_active=True, is_authenticated=True, is_staff=False, is_superuser=False)
        self.assertFalse(permits(rule, user))
        user.is_staff = True
        self.assertTrue(permits(rule, user))
        user.is_active = False
        self.assertFalse(permits(rule, user))

    def test_authenticated_rule_does_not_grant_admin_role(self):
        self.data["features"]["wordApplications"]["roles"] = ["authenticated"]
        self.write()
        user = SimpleNamespace(is_active=True, is_authenticated=True, is_staff=False, is_superuser=False)
        self.assertTrue(permits(read_policy(self.path, self.now), user))
        self.assertFalse(user.is_superuser)

    def test_file_is_rechecked_and_failures_close(self):
        self.assertTrue(capabilities(self.path, self.now)["features"]["wordApplications"]["enabled"])
        self.data["features"]["wordApplications"]["enabled"] = False
        self.write()
        self.assertFalse(capabilities(self.path, self.now)["features"]["wordApplications"]["enabled"])
        self.path.unlink()
        self.assertIsNone(read_policy(self.path, self.now))

    def test_invalid_policies_fail_closed(self):
        variants = [
            {"version": 0}, {"version": True}, {"unknown": True},
            {"issuedAt": "2099-01-01T00:00:00Z"},
            {"expiresAt": "2026-10-25T06:59:59Z"},
            {"expiresAt": "2099-01-01T00:00:00Z"},
            {"features": {"wordApplications": {"enabled": "true", "roles": ["staff"]}}},
            {"features": {"wordApplications": {"enabled": True, "roles": ["reviewer"]}}},
            {"features": {"wordApplications": {"enabled": True, "roles": ["staff"], "platform": "review"}}},
            {"features": {"wordApplications": {"enabled": True, "roles": ["staff", "staff"]}}},
            {"features": {"other": {"enabled": True, "roles": ["staff"]}}},
        ]
        for change in variants:
            with self.subTest(change=change):
                invalid = dict(self.data)
                invalid.update(change)
                self.path.write_text(json.dumps(invalid))
                self.assertIsNone(read_policy(self.path, self.now))
        for raw in ('{', '[]', '{"version":1,"version":1}', 'x' * 16385):
            self.path.write_text(raw)
            self.assertIsNone(read_policy(self.path, self.now))

    def test_public_contract_never_exposes_roles(self):
        result = capabilities(self.path, self.now)
        self.assertEqual(result["version"], 1)
        self.assertEqual(result["ttlSeconds"], 15)
        self.assertEqual(result["features"], {"wordApplications": {"enabled": True}})
        self.assertNotIn("staff", json.dumps(result))
        self.assertLessEqual(
            datetime.fromisoformat(result["expiresAt"].replace("Z", "+00:00")),
            self.now + timedelta(seconds=15),
        )

    def test_public_expiry_cannot_outlive_policy(self):
        self.data["expiresAt"] = "2026-10-25T07:00:02Z"
        self.write()
        result = capabilities(self.path, self.now)
        self.assertEqual(result["expiresAt"], self.data["expiresAt"])
        self.assertFalse(capabilities(
            self.path, self.now + timedelta(seconds=2)
        )["features"]["wordApplications"]["enabled"])

    def test_duplicate_nested_keys_are_rejected(self):
        raw = json.dumps(self.data).replace(
            '"enabled": true', '"enabled": false, "enabled": true'
        )
        self.path.write_text(raw)
        self.assertIsNone(read_policy(self.path, self.now))
