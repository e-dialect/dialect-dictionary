import json
from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags
from article.models import Article
from .announcement_config import article_ids, revision, MAX_CONFIG_CHARS
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

    def __init__(self, request=None, original='', backup=None, object_id=None, attrs=None):
        super().__init__(attrs)
        self.request, self.original = request, original
        self.backup, self.object_id = backup or {}, object_id

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
        try:
            article_ids(self.original)
            original_error = ''
        except ValueError as exc:
            original_error = str(exc)
        safe_attrs = attrs or {}
        undo_available = (isinstance(self.backup, dict) and
                          isinstance(self.backup.get('original'), str) and
                          self.backup.get('repaired') == self.original)
        context['widget'].update(
            choices=[records.get(i, {'id': i, 'title': f'文章 #{i}（已删除或无查看权限）', 'public': None, 'date': '', 'preview': ''}) for i in ids],
            data_id=safe_attrs.get('id', name) + '_choices', error=error, search_url=reverse('admin:website_announcement_search'),
            cancel_url=reverse('admin:website_website_changelist') + '?all=1',
            original_error=original_error, revision=revision(self.original),
            original_preview=self.original[:2000], original_truncated=len(self.original) > 2000,
            repairing=bool(self.request and self.request.method == 'POST' and self.request.POST.get('announcement_rebuild') == 'yes'),
            undo_url=reverse('admin:website_announcement_undo', args=[self.object_id]) if self.object_id and undo_available else '',
            # Invalid old data must not be silently replaced by an empty list.
            value=(value if len(str(value)) <= MAX_CONFIG_CHARS else '__invalid_stored_config__') if error else json.dumps(ids),
        )
        return context


class WebsiteAdminForm(forms.ModelForm):
    class Meta:
        model = Website
        fields = '__all__'

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.original_announcements = self.instance.announcements or ''
        try:
            article_ids(self.original_announcements)
            self.original_error = False
        except ValueError:
            self.original_error = True
        self.repair_requested = self.is_bound and self.data.get('announcement_rebuild') == 'yes'
        self.fields['announcements'].widget = AnnouncementWidget(
            request, self.original_announcements, self.instance.announcements_repair_backup, self.instance.pk)
        self.fields['announcements'].required = False
        self.fields['announcements'].help_text = '按标题搜索并加入；上移/下移调整顺序。加入未公开文章不会替它通过审核。最后点击页面底部保存。'

    def clean(self):
        cleaned = super().clean()
        if self.original_error:
            if not self.repair_requested:
                self.add_error('announcements', '原配置有误，须明确勾选重新选择后才能替换；取消会保留原值。')
            elif self.data.get('announcement_revision') != revision(self.original_announcements):
                self.add_error('announcements', '配置已被其他人修改，请重新打开后再修复。')
        elif self.repair_requested:
            self.add_error('announcements', '配置状态已变化，请重新打开页面，不能覆盖其他人的修改。')
        return cleaned

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
