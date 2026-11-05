import json
from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags
from article.models import Article
from .announcement_config import article_ids
from .models import Website


def can_view_private_articles(request):
    model_admin = admin.site._registry.get(Article)
    return bool(request and model_admin and model_admin.has_view_permission(request))


def article_choice(article):
    published = article.publish_time
    if timezone.is_aware(published):
        published = timezone.localtime(published)
    return {'id': article.id, 'title': article.title, 'public': article.visibility,
            'date': published.strftime('%Y-%m-%d %H:%M'),
            # This is plain text, never HTML/Markdown; JS also uses textContent.
            'preview': strip_tags(article.description or article.content)[:500]}


class AnnouncementWidget(forms.Widget):
    template_name = 'website/widgets/announcements.html'

    class Media:
        css = {'all': ('website/announcements.css',)}
        js = ('website/announcements.js',)

    def __init__(self, request=None, attrs=None):
        super().__init__(attrs)
        self.request = request

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        try:
            ids = article_ids(value)
            error = ''
        except ValueError as exc:
            ids, error = [], str(exc)
        queryset = Article.objects.filter(id__in=ids)
        if not can_view_private_articles(self.request):
            queryset = queryset.filter(visibility=True)
        records = {a.id: article_choice(a) for a in queryset}
        context['widget'].update(
            choices=[records.get(i, {'id': i, 'title': f'文章 #{i}（已删除或无查看权限）', 'public': None, 'date': '', 'preview': ''}) for i in ids],
            data_id=attrs.get('id', name) + '_choices', error=error, search_url=reverse('admin:website_announcement_search'),
            cancel_url=reverse('admin:website_website_changelist'),
            # Invalid old data must not be silently replaced by an empty list.
            value=value if error else json.dumps(ids),
        )
        return context


class WebsiteAdminForm(forms.ModelForm):
    class Meta:
        model = Website
        fields = '__all__'

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.fields['announcements'].widget = AnnouncementWidget(request)
        self.fields['announcements'].required = False
        self.fields['announcements'].help_text = '按标题搜索并加入；上移/下移调整顺序。加入未公开文章不会替它通过审核。最后点击页面底部保存。'

    def clean_announcements(self):
        try:
            selected = article_ids(self.cleaned_data.get('announcements'))
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        try:
            previous = set(article_ids(self.instance.announcements))
        except ValueError:
            previous = set()
        new_ids = set(selected) - previous
        allowed = Article.objects.filter(id__in=new_ids)
        if not can_view_private_articles(self.request):
            allowed = allowed.filter(visibility=True)
        if set(allowed.values_list('id', flat=True)) != new_ids:
            raise ValidationError('新增选择含不存在或无权查看的文章，请重新搜索选择。')
        return json.dumps(selected)
