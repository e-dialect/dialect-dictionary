import json
from django.contrib.auth.models import User
from django.test import TestCase
from word.models import Word
from user.models import UserInfo

class PrivateBulkReadTests(TestCase):
    def test_anonymous_bulk_cannot_read_private_imports(self):
        author = User.objects.create_user(username='synthetic-private-owner', password=None)
        UserInfo.objects.create(user=author, nickname='合成维护者')
        private = Word.objects.create(word='私有测试', contributor=author, definition='不能匿名获取', visibility=False, mandarin='[]', tags='[]')
        public = Word.objects.create(word='公开测试', contributor=author, definition='可公开', visibility=True, mandarin='[]', tags='[]')
        response = self.client.put('/words', json.dumps({'words':[private.pk, public.pk]}), content_type='application/json')
        self.assertEqual(response.status_code,200)
        words = response.json()['words']
        self.assertEqual([item['word']['id'] for item in words], [public.pk])
        self.assertEqual(words[0]['word']['word'], '公开测试')
        self.assertNotIn(private.pk, [item['word']['id'] for item in words])
        self.assertEqual(self.client.get('/words/'+str(private.pk)).status_code,403)
