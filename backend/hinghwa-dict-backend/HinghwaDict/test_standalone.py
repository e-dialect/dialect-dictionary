"""Synthetic integration tests; no production account, dataset, or external API."""

import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from user.models import UserInfo
from utils.token import generate_token
from website.storage import upload_file, _local_path
from word.models import Application, Word
from word.forms import PronunciationForm


class StandaloneIntegrationTests(TestCase):
    def setUp(self):
        policy_directory = tempfile.TemporaryDirectory()
        self.addCleanup(policy_directory.cleanup)
        policy_path = Path(policy_directory.name) / "policy.json"
        now = datetime.now(timezone.utc)
        policy_path.write_text(json.dumps({
            "version": 1,
            "issuedAt": (now - timedelta(seconds=1)).isoformat().replace("+00:00", "Z"),
            "expiresAt": (now + timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
            "features": {"wordApplications": {"enabled": True, "roles": ["authenticated"]}},
        }))
        policy_override = override_settings(FEATURE_POLICY_PATH=str(policy_path))
        policy_override.enable()
        self.addCleanup(policy_override.disable)
        self.user = User.objects.create_user(
            username="synthetic-contributor", password="temporary-test-password"
        )
        UserInfo.objects.create(user=self.user, nickname="合成测试用户")
        self.word = Word.objects.create(
            word="合成测试词",
            definition="只用于自动测试",
            contributor=self.user,
            visibility=True,
        )
        self.token = generate_token(self.user)

    def payload(self, word_id):
        return {
            "word": word_id,
            "reason": "合成测试纠错",
            "content": {
                "word": "建议内容",
                "definition": "待审核内容",
                "annotation": "",
                "mandarin": ["测试"],
                "standard_pinyin": "",
                "standard_ipa": "",
                "tags": [],
                "related_words": [],
                "related_articles": [],
            },
        }

    def test_health_and_keyword_search_without_model(self):
        response = self.client.get("/healthz", HTTP_HOST="localhost")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        response = self.client.get(
            "/words", {"search": "合成测试词"}, HTTP_HOST="localhost"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.word.id, response.json()["words"])

    def test_correction_remains_pending_and_does_not_publish(self):
        response = self.client.post(
            "/words/applications",
            json.dumps(self.payload(self.word.id)),
            content_type="application/json",
            HTTP_TOKEN=self.token,
            HTTP_HOST="localhost",
        )
        self.assertEqual(response.status_code, 200, response.content)
        application = Application.objects.get(pk=response.json()["id"])
        self.assertEqual(application.word_id, self.word.id)
        self.assertEqual(application.contributor, self.user)
        self.assertIsNone(application.verifier)
        self.assertIsNone(application.approved)
        self.word.refresh_from_db()
        self.assertEqual(self.word.word, "合成测试词")

    def test_new_word_is_only_an_application(self):
        response = self.client.post(
            "/words/applications",
            json.dumps(self.payload(0)),
            content_type="application/json",
            HTTP_TOKEN=self.token,
            HTTP_HOST="localhost",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIsNone(Application.objects.get(pk=response.json()["id"]).word_id)
        self.assertEqual(Word.objects.count(), 1)

    def test_unauthenticated_cannot_apply(self):
        response = self.client.post(
            "/words/applications",
            json.dumps(self.payload(self.word.id)),
            content_type="application/json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(response.status_code, 401, response.content)
        self.assertEqual(Application.objects.count(), 0)

    def test_contributor_policy_does_not_grant_review_permission(self):
        application = Application.objects.create(
            contributor=self.user, word=self.word, content_word="合成申请"
        )
        response = self.client.put(
            f"/words/applications/{application.id}",
            json.dumps({"result": True, "reason": "不可提升权限"}),
            content_type="application/json",
            HTTP_TOKEN=self.token,
            HTTP_HOST="localhost",
        )
        self.assertEqual(response.status_code, 403, response.content)
        application.refresh_from_db()
        self.assertIsNone(application.verifier)

    def test_closed_policy_preserves_own_history_but_denies_write(self):
        application = Application.objects.create(
            contributor=self.user, word=self.word, content_word="历史合成申请"
        )
        with override_settings(FEATURE_POLICY_PATH="/nonexistent/synthetic-policy.json"):
            response = self.client.get(
                f"/words/applications/{application.id}",
                HTTP_TOKEN=self.token, HTTP_HOST="localhost",
            )
            self.assertEqual(response.status_code, 200, response.content)
            response = self.client.post(
                "/words/applications",
                json.dumps(self.payload(self.word.id)),
                content_type="application/json",
                HTTP_TOKEN=self.token, HTTP_HOST="localhost",
            )
            self.assertEqual(response.status_code, 403, response.content)
        self.assertEqual(Application.objects.count(), 1)

    def test_local_storage_and_path_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.txt"
            source.write_text("synthetic-media")
            media = Path(directory) / "media"
            with override_settings(
                FILE_STORAGE="local",
                MEDIA_ROOT=str(media),
                PUBLIC_API_BASE="http://localhost:18080/api",
            ):
                url = upload_file(str(source), "files/synthetic/audio.txt")
                self.assertEqual(
                    url, "http://localhost:18080/api/media/files/synthetic/audio.txt"
                )
                self.assertEqual(
                    (media / "files/synthetic/audio.txt").read_text(), "synthetic-media"
                )
                for key in ("../escape", "/outside", ""):
                    with self.assertRaises(ValueError):
                        _local_path(key)

    def test_geography_disabled_accepts_recording_without_fake_area(self):
        data = {
            "source": "https://example.test/recording.wav",
            "pinyin": "test",
            "ipa": "test",
            "county": "",
            "town": "",
        }
        with override_settings(SITE_CONFIG={"features": {"geography": False}}):
            self.assertTrue(PronunciationForm(data).is_valid())
        with override_settings(SITE_CONFIG={"features": {"geography": True}}):
            self.assertFalse(PronunciationForm(data).is_valid())

    def test_local_media_delete_uses_own_storage_path(self):
        with tempfile.TemporaryDirectory() as directory:
            key = f"files/recording/{self.user.id}/2026/10/25/synthetic.wav"
            path = Path(directory) / key
            path.parent.mkdir(parents=True)
            path.write_bytes(b"synthetic")
            with override_settings(
                FILE_STORAGE="local",
                MEDIA_ROOT=directory,
                PUBLIC_API_BASE="http://localhost:18080/api",
            ):
                response = self.client.delete(
                    "/website/files",
                    json.dumps({"url": "http://localhost:18080/api/media/" + key}),
                    content_type="application/json",
                    HTTP_TOKEN=self.token,
                    HTTP_HOST="localhost",
                )
                self.assertEqual(response.status_code, 200, response.content)
                self.assertFalse(path.exists())
