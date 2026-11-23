from ..models import Word, Pronunciation


def word2pronunciation(word: Word, null=None):
    ipa = word.standard_ipa or ""
    recordings = (Pronunciation.objects.filter(visibility=True, ipa=ipa)
                  .exclude(source__in=["", "null"]).order_by("pk").values_list("source", flat=True))
    own = recordings.filter(word=word).first()
    if own or not ipa.strip():
        return own or null
    return recordings.filter(word__visibility=True).first() or null
