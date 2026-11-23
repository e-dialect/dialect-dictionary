from django.contrib.auth.models import User
from django.test import TestCase

from word.models import Pronunciation, Word
from word.word.word2pronunciation import word2pronunciation


class RecordingMatchTests(TestCase):
    def test_only_nonempty_ipa_can_match_another_public_word(self):
        author = User.objects.create_user(username="recording-fixture")
        first, second = [Word.objects.create(word=text, contributor=author, visibility=True)
                         for text in ("合成甲", "合成乙")]
        recording = Pronunciation.objects.create(word=first, contributor=author, visibility=True,
                                                 source="https://example.invalid/one.wav", ipa="")
        self.assertEqual(word2pronunciation(first), recording.source)
        self.assertIsNone(word2pronunciation(second))
        second.standard_ipa = recording.ipa = "ka"
        recording.save()
        self.assertEqual(word2pronunciation(second), recording.source)
        second.standard_ipa = 'KA'
        self.assertIsNone(word2pronunciation(second))
        second.standard_ipa = 'ka'
        recording.visibility = False
        recording.save()
        self.assertEqual(word2pronunciation(second, "null"), "null")
