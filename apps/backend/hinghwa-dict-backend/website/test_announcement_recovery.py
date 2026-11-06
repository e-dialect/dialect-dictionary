"""Synthetic recovery, concurrency and active-homepage regression cases.

This file does not import/inherit the earlier announcement regression class.
"""
import json
from unittest.mock import patch
from django.contrib.auth.models import User, Permission
from django.test import TestCase, SimpleTestCase, Client
from django.utils import timezone
from article.models import Article
from website.models import Website
from website.announcement_config import article_ids, payload_ids, revision


class BoundedAnnouncementDataTests(SimpleTestCase):
    def test_nested_and_oversized_inputs_have_friendly_failures(self):
        for value in ['[' * 1200 + '1' + ']' * 1200, '{"not":"a list"}', '(' * 1200 + '1' + ')' * 1200, '[' + '1,' * 20000 + '1]']:
            with self.subTest(value_length=len(value)), self.assertRaises(ValueError):
                article_ids(value)
        with self.assertRaises(ValueError): payload_ids(b'{"announcements":' + b'['*1200 + b'1' + b']'*1200 + b'}')

    def test_existing_flat_literal_formats_keep_effective_order(self):
        self.assertEqual(article_ids("('2', 1, 2)"),[2,1])
        self.assertEqual(article_ids('[2,1]'),[2,1])
        with self.assertRaises(ValueError): payload_ids(b'[]')


class AnnouncementRecoveryFlowTests(TestCase):
    def setUp(self):
        self.operator=User.objects.create_superuser('synthetic-recovery',password=None)
        self.client.force_login(self.operator)
        self.article=Article.objects.create(author=self.operator,title='合成修复示例',description='',content='合成正文',cover='https://example.invalid/x.png',update_time=timezone.now(),visibility=False)
        self.original='[invalid, configuration]'
        self.site=Website.objects.create(pk=1,announcements=self.original,hot_articles='[77]')
        self.change='/admin/website/website/1/change/'
        self.undo='/admin/website/website/1/undo-announcement-repair/'

    def post(self, **extra):
        data={'announcements':json.dumps([self.article.pk]),'hot_articles':'[77]','carousel':'[]','word_of_the_day':'1','_save':'保存'}
        data.update(extra)
        return self.client.post(self.change,data)

    def test_invalid_storage_cannot_be_overwritten_without_explicit_repair(self):
        response=self.post()
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'明确勾选')
        self.site.refresh_from_db()
        self.assertEqual(self.site.announcements,self.original)
        self.assertEqual(self.site.announcements_repair_backup,{})

    def test_explicit_repair_preserves_raw_backup_and_can_be_undone(self):
        response=self.post(announcement_rebuild='yes',announcement_revision=revision(self.original))
        self.assertEqual(response.status_code,302)
        self.site.refresh_from_db();self.article.refresh_from_db()
        self.assertEqual(self.site.announcements_repair_backup['original'],self.original)
        self.assertEqual(article_ids(self.site.announcements),[self.article.pk])
        self.assertFalse(self.article.visibility)
        self.assertEqual(self.client.post(self.undo).status_code,302)
        self.site.refresh_from_db()
        self.assertEqual(self.site.announcements,self.original)
        self.assertEqual(self.site.hot_articles,'[77]')
        self.assertEqual(self.site.announcements_repair_backup['original'],self.original)

    def test_stale_repair_and_stale_undo_never_overwrite_new_content(self):
        self.assertEqual(self.post(announcement_rebuild='yes',announcement_revision='old-revision').status_code,200)
        self.site.refresh_from_db();self.assertEqual(self.site.announcements,self.original)
        self.post(announcement_rebuild='yes',announcement_revision=revision(self.original))
        Website.objects.filter(pk=1).update(announcements='[]')
        self.assertEqual(self.client.post(self.undo).status_code,409)
        self.site.refresh_from_db();self.assertEqual(self.site.announcements,'[]')

    def test_concurrent_repair_with_same_result_rejects_stale_undo(self):
        from django.contrib import admin
        self.post(announcement_rebuild='yes', announcement_revision=revision(self.original))
        self.site.refresh_from_db()
        current = self.site.announcements
        newer_backup = {'original': '[another invalid original]', 'repaired': current}
        model_admin = admin.site._registry[Website]
        get_object = model_admin.get_object

        def interleave_new_repair(*args, **kwargs):
            stale_object = get_object(*args, **kwargs)
            Website.objects.filter(pk=1).update(announcements_repair_backup=newer_backup)
            return stale_object

        with patch.object(model_admin, 'get_object', side_effect=interleave_new_repair):
            self.assertEqual(self.client.post(self.undo).status_code, 409)
        self.site.refresh_from_db()
        self.assertEqual(self.site.announcements, current)
        self.assertEqual(self.site.announcements_repair_backup, newer_backup)

    def test_undo_is_post_only_csrf_protected_and_permission_checked(self):
        self.assertEqual(self.client.get(self.undo).status_code,405)
        viewer=User.objects.create_user('synthetic-read-only',password=None,is_staff=True)
        viewer.user_permissions.add(Permission.objects.get(codename='view_website'))
        self.client.force_login(viewer)
        self.assertEqual(self.client.post(self.undo).status_code,403)
        strict=Client(enforce_csrf_checks=True);strict.force_login(self.operator)
        self.assertEqual(strict.post(self.undo).status_code,403)

    def test_missing_active_row_is_explicitly_created_without_touching_other_rows(self):
        self.site.delete()
        other=Website.objects.create(pk=2,announcements='[99]')
        url='/admin/website/website/'
        self.assertEqual(self.client.get(url).status_code,200)
        self.assertFalse(Website.objects.filter(pk=1).exists())
        self.assertEqual(self.client.post(url+'create-homepage/').status_code,302)
        other.refresh_from_db();self.assertEqual(other.announcements,'[99]')
        self.assertTrue(Website.objects.filter(pk=1).exists())
        response=self.client.get(url)
        self.assertEqual(response.status_code,302)
        self.assertIn('/website/website/1/change/',response['Location'])
        self.assertContains(self.client.get(url+'?all=1'),'其他/历史配置')

    @patch('website.views.token_check',return_value=True)
    def test_api_rejects_malformed_deep_or_oversized_json(self, token):
        url='/website/announcements'
        for body in [b'not json',b'{"announcements":'+b'['*1200+b'1'+b']'*1200+b'}']:
            self.assertEqual(self.client.put(url,data=body,content_type='application/json',HTTP_TOKEN='synthetic').status_code,400)
        self.assertEqual(self.client.put(url,data=b' '*32001,content_type='application/json',HTTP_TOKEN='synthetic').status_code,413)
        self.site.refresh_from_db();self.assertEqual(self.site.announcements,self.original)
