"""Create one explicitly synthetic record only in an empty independent database."""

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from user.models import UserInfo
from word.models import Word
from website.models import Website


class Command(BaseCommand):
    help = "Seed a synthetic smoke-test entry in an empty dictionary; never imports production content."

    @transaction.atomic
    def handle(self, *args, **kwargs):
        if Word.objects.exists():
            self.stdout.write("Dictionary is nonempty; demo seed skipped.")
            return
        author, created = User.objects.get_or_create(username="dictionary-demo")
        if created:
            author.set_unusable_password()
            author.save()
        UserInfo.objects.get_or_create(
            user=author, defaults={"nickname": "演示内容维护者"}
        )
        word = Word.objects.create(
            contributor=author,
            visibility=True,
            word="示例词条",
            definition="【技术演示】此条仅用于验证独立词典查词流程，不代表真实方言释义。",
            annotation=settings.SITE_CONFIG["contentSource"]["notice"],
            mandarin="[]",
            tags="[]",
            standard_pinyin="",
            standard_ipa="",
        )
        Website.objects.get_or_create(pk=1, defaults={"word_of_the_day": str(word.id)})
        self.stdout.write(
            "Created one synthetic entry; no language dataset or recording was imported."
        )
