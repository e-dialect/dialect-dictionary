import json
import re
from unittest.mock import patch
from django.contrib.auth.models import User, Permission
from django.test import TestCase, SimpleTestCase
from django.utils import timezone
from article.models import Article
from user.models import UserInfo
from website.models import Website
from website.announcement_config import article_ids


class AnnouncementParsingTests(SimpleTestCase):
    def test_data_only_legacy_formats_and_order(self):
        for value in ['[2, 1, 2]', "['2', '1']", '(2, 1)', [2, 1]]:
            self.assertEqual(article_ids(value), [2, 1])
        self.assertEqual(article_ids(''), [])

    def test_code_and_invalid_values_are_not_executed(self):
        for value in ["__import__('os').system('bad')", '[True]', '[0]', '[-1]', '[1.2]', '{}', '["not-an-id"]', '["9" * 99999]']:
            with self.subTest(value=value), self.assertRaises(ValueError): article_ids(value)


class AnnouncementAdminTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('synthetic-owner', password=None)
        UserInfo.objects.create(user=self.owner, nickname='合成作者')
        self.operator = User.objects.create_superuser('synthetic-admin', password=None)
        self.editor = User.objects.create_user('synthetic-editor', password=None, is_staff=True)
        self.editor.user_permissions.add(Permission.objects.get(codename='change_website'))
        self.viewer = User.objects.create_user('synthetic-viewer', password=None, is_staff=True)
        self.viewer.user_permissions.add(Permission.objects.get(codename='view_website'))
        def article(title, public=True, **values):
            return Article.objects.create(author=self.owner, title=title, description='合成简介 <b>仅文字</b>', content='合成正文', cover='https://example.invalid/synthetic.png', update_time=timezone.now(), visibility=public, **values)
        self.first = article('合成资料征集')
        self.second = article('合成活动通知')
        self.private = article('不可泄露的合成草稿标题', False)
        self.site = Website.objects.create(pk=1, announcements=json.dumps([self.second.pk,self.private.pk,self.first.pk]))
        self.search = '/admin/website/website/announcement-search/'
        self.change = '/admin/website/website/1/change/'

    def form_data(self, ids):
        return {'announcements':json.dumps(ids), 'hot_articles':'[]','word_of_the_day':'1','carousel':'[]','_save':'保存'}

    def test_public_api_filters_private_preserves_order_and_next_request_updates(self):
        response = self.client.get('/website/announcements')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual([x['article']['id'] for x in response.json()['announcements']], [self.second.pk,self.first.pk])
        self.site.announcements=json.dumps([self.first.pk]);self.site.save()
        self.assertEqual([x['article']['id'] for x in self.client.get('/website/announcements').json()['announcements']], [self.first.pk])

    def test_stored_code_denied_without_execution_or_rewrite(self):
        self.site.announcements="__import__('os').system('bad')";self.site.save()
        with patch('os.system') as execute:
            self.assertEqual(self.client.get('/website/announcements').status_code,400)
        execute.assert_not_called();self.site.refresh_from_db()
        self.assertIn('__import__',self.site.announcements)

    def test_admin_search_auth_and_existing_permissions(self):
        self.assertEqual(self.client.get(self.search).status_code,302)
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.get(self.search).status_code,403)
        self.client.force_login(self.editor)
        response=self.client.get(self.search,{'q':'合成'})
        self.assertEqual(response.status_code,200)
        self.assertNotIn(self.private.pk,[a['id'] for a in response.json()['articles']])
        page=self.client.get(self.change)
        self.assertNotContains(page,self.private.title)
        # json_script correctly escapes non-ASCII text. Assert decoded data,
        # not a literal substring that is absent from the safe HTML payload.
        match = re.search(
            r'<script[^>]*id="id_announcements_choices"[^>]*>(.*?)</script>',
            page.content.decode(), re.DOTALL,
        )
        self.assertIsNotNone(match)
        choices = json.loads(match.group(1))
        hidden = next(item for item in choices if item['id'] == self.private.pk)
        self.assertEqual(hidden['title'], f'文章 #{self.private.pk}（已删除或无查看权限）')
        self.assertEqual(hidden['preview'], '')
        self.assertIsNone(hidden['public'])

    def test_view_only_admin_can_open_without_edit_controls(self):
        self.client.force_login(self.viewer)
        response = self.client.get(self.change)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertNotContains(response, 'class="announcement-search"')
        self.assertNotContains(response, self.private.title)
        self.assertEqual(self.client.get('/admin/website/website/').status_code, 302)

    def test_superuser_search_status_date_plaintext_and_title_filter(self):
        self.client.force_login(self.operator)
        response=self.client.get(self.search,{'q':'草稿'})
        item=response.json()['articles'][0]
        self.assertEqual(item['id'],self.private.pk);self.assertFalse(item['public'])
        self.assertTrue(item['date']);self.assertNotIn('<b>',item['preview'])
        self.assertEqual(self.client.get(self.search,{'q':'不存在的关键词'}).json()['articles'],[])

    def test_save_keeps_order_does_not_publish_and_reopen_keeps_choices(self):
        self.client.force_login(self.operator)
        order=[self.first.pk,self.private.pk,self.second.pk]
        response=self.client.post(self.change,self.form_data(order))
        self.assertEqual(response.status_code,302,response.content)
        self.site.refresh_from_db();self.private.refresh_from_db()
        self.assertEqual(article_ids(self.site.announcements),order);self.assertFalse(self.private.visibility)
        page=self.client.get(self.change)
        choices=page.context['adminform'].form.fields['announcements'].widget.get_context('announcements',self.site.announcements,{'id':'id_announcements'})['widget']['choices']
        self.assertEqual([x['id'] for x in choices],order)
        self.assertContains(page,'取消并返回')

    def test_repeat_selection_deduplicates_and_other_fields_unchanged(self):
        self.client.force_login(self.operator)
        self.client.post(self.change,self.form_data([self.first.pk,self.first.pk,self.second.pk]))
        self.site.refresh_from_db()
        self.assertEqual(article_ids(self.site.announcements),[self.first.pk,self.second.pk])
        self.assertEqual(self.site.hot_articles,'[]')

    def test_editor_cannot_add_new_private_article_but_can_keep_existing(self):
        self.client.force_login(self.editor)
        self.site.announcements=json.dumps([self.first.pk]);self.site.save()
        self.assertEqual(self.client.post(self.change,self.form_data([self.private.pk])).status_code,200)
        self.site.refresh_from_db();self.assertEqual(article_ids(self.site.announcements),[self.first.pk])
        self.site.announcements=json.dumps([self.private.pk,self.first.pk]);self.site.save()
        self.assertEqual(self.client.post(self.change,self.form_data([self.first.pk,self.private.pk])).status_code,302)
        self.private.refresh_from_db();self.assertFalse(self.private.visibility)

    def test_safe_json_script_and_cancel_get_does_not_save(self):
        self.first.title='</script><img src=x onerror="window.syntheticDanger=1">';self.first.save()
        self.client.force_login(self.operator)
        before=self.site.announcements
        page=self.client.get(self.change)
        self.assertContains(page,'\\u003C/script\\u003E')
        self.assertNotContains(page,'</script><img')
        self.client.get('/admin/website/website/')
        self.site.refresh_from_db();self.assertEqual(self.site.announcements,before)

    @patch('website.views.token_check')
    def test_api_put_keeps_existing_admin_gate_and_validates_ids(self, token):
        token.return_value=False
        self.assertEqual(self.client.put('/website/announcements',data=json.dumps({'announcements':[self.first.pk]}),content_type='application/json').status_code,401)
        token.return_value=True
        self.assertEqual(self.client.put('/website/announcements',data=json.dumps({'announcements':[True]}),content_type='application/json').status_code,400)
        self.assertEqual(self.client.put('/website/announcements',data=json.dumps({'announcements':[self.first.pk]}),content_type='application/json',HTTP_TOKEN='synthetic').status_code,200)
        self.assertEqual(token.call_args.args[-1],-1)
