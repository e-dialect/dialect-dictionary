from django.contrib import admin
from django_apscheduler.apps import DjangoApschedulerConfig
from django_apscheduler.models import DjangoJob, DjangoJobExecution
from notifications.admin import NotificationAdmin
from notifications.models import Notification
from django import forms
from .models import Website, DailyExpression
from .announcement_admin import WebsiteAdminForm, article_choice, can_view_private_articles
from .announcement_config import article_ids, ACTIVE_WEBSITE_ID
from article.models import Article
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseNotAllowed, HttpResponseNotFound, HttpResponseRedirect
from django.urls import path, reverse
from django.template.response import TemplateResponse
from django.contrib import messages
from utils.admin.widgets import IPAKeyboardWidget


class WebsiteAdmin(admin.ModelAdmin):
    form = WebsiteAdminForm
    change_form_template = "admin/website/website/change_form.html"
    ordering = ("id",)
    list_display = ["id", "configuration_role", "announcement_summary", "word_of_the_day"]
    fieldsets = (
        ("公告管理", {"fields": ("announcements",), "description": "选择、排序后保存即可对新请求生效，无需重启；未公开文章仍不会对外显示。"}),
        ("其他首页内容（保留原有格式）", {"fields": ("hot_articles", "word_of_the_day", "carousel"), "classes": ("collapse",)}),
    )

    @admin.display(description="用途")
    def configuration_role(self, obj):
        return "当前网站首页（生效）" if obj.pk == ACTIVE_WEBSITE_ID else "其他/历史配置（不影响首页）"

    def changelist_view(self, request, extra_context=None):
        if not self.has_view_or_change_permission(request):
            return HttpResponseForbidden()
        if request.method == 'GET' and not request.GET.get('all'):
            if Website.objects.filter(pk=ACTIVE_WEBSITE_ID).exists():
                return HttpResponseRedirect(reverse('admin:website_website_change', args=[ACTIVE_WEBSITE_ID]))
            return TemplateResponse(request, 'admin/website/website/empty_homepage.html', {
                **self.admin_site.each_context(request), 'opts': self.model._meta,
                'title': '还没有首页配置', 'can_create': self.has_add_permission(request),
                'create_url': reverse('admin:website_create_homepage'),
                'all_url': reverse('admin:website_website_changelist') + '?all=1',
            })
        return super().changelist_view(request, extra_context)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        context = dict(extra_context or {})
        context.update(is_active_homepage=str(object_id) == str(ACTIVE_WEBSITE_ID),
                       active_homepage_url=reverse('admin:website_website_changelist'),
                       all_configurations_url=reverse('admin:website_website_changelist') + '?all=1')
        return super().change_view(request, object_id, form_url, context)

    def add_view(self, request, form_url='', extra_context=None):
        context = dict(extra_context or {})
        context.update(is_add_configuration=True,
                       active_homepage_url=reverse('admin:website_website_changelist'),
                       all_configurations_url=reverse('admin:website_website_changelist') + '?all=1')
        return super().add_view(request, form_url, context)

    def repair_conflict(self, request, message):
        return TemplateResponse(request, 'admin/website/website/repair_conflict.html', {
            **self.admin_site.each_context(request), 'opts': self.model._meta,
            'title': '没有覆盖公告配置', 'message': message,
            'back_url': reverse('admin:website_website_changelist'),
        }, status=409)

    def save_model(self, request, obj, form, change):
        if form.repair_requested:
            obj.announcements_repair_backup = {'original': form.original_announcements, 'repaired': obj.announcements}
        super().save_model(request, obj, form, change)

    def create_homepage(self, request):
        if request.method != 'POST':
            return HttpResponseNotAllowed(['POST'])
        if not self.has_add_permission(request):
            return HttpResponseForbidden()
        obj, created = Website.objects.get_or_create(pk=ACTIVE_WEBSITE_ID)
        if created:
            self.log_addition(request, obj, '按用户确认创建当前首页配置；不修改其他配置行。')
        return HttpResponseRedirect(reverse('admin:website_website_change', args=[obj.pk]))

    def undo_announcement_repair(self, request, object_id):
        if request.method != 'POST':
            return HttpResponseNotAllowed(['POST'])
        obj = self.get_object(request, object_id)
        if obj is None:
            return HttpResponseNotFound()
        if not self.has_change_permission(request, obj):
            return HttpResponseForbidden()
        backup = obj.announcements_repair_backup
        if not isinstance(backup, dict) or not isinstance(backup.get('original'), str) or not isinstance(backup.get('repaired'), str):
            return self.repair_conflict(request, '没有可撤销的修复备份；原配置没有改变。')
        updated = Website.objects.filter(pk=obj.pk, announcements=backup['repaired']).update(announcements=backup['original'])
        if not updated:
            return self.repair_conflict(request, '配置已被再次修改，未覆盖任何内容。请重新打开核对；修复前原值仍保留。')
        self.log_change(request, obj, '撤销公告修复，恢复原始配置；未修改文章公开状态或其他字段。')
        self.message_user(request, '已恢复修复前原值；若仍有格式错误，可重新确认修复。', messages.SUCCESS)
        return HttpResponseRedirect(reverse('admin:website_website_change', args=[obj.pk]))

    @admin.display(description="本站公告")
    def announcement_summary(self, obj):
        try:
            return f"已选{len(article_ids(obj.announcements))}篇，按手动顺序显示"
        except ValueError:
            return "配置格式待核对（原值保留）"

    def get_form(self, request, obj=None, **kwargs):
        form_class = super().get_form(request, obj, **kwargs)
        class RequestForm(form_class):
            def __init__(self, *args, **kw):
                super().__init__(*args, request=request, **kw)
        return RequestForm

    def get_urls(self):
        return [
            path('announcement-search/', self.admin_site.admin_view(self.announcement_search), name='website_announcement_search'),
            path('create-homepage/', self.admin_site.admin_view(self.create_homepage), name='website_create_homepage'),
            path('<path:object_id>/undo-announcement-repair/', self.admin_site.admin_view(self.undo_announcement_repair), name='website_announcement_undo'),
        ] + super().get_urls()

    def announcement_search(self, request):
        if not self.has_change_permission(request) or request.method != 'GET':
            return HttpResponseForbidden()
        articles = Article.objects.filter(title__icontains=request.GET.get('q', '')[:100])
        if not can_view_private_articles(request):
            articles = articles.filter(visibility=True)
        rows = list(articles.order_by('-publish_time', '-id')[:21])
        return JsonResponse({'articles': [article_choice(a) for a in rows[:20]], 'has_more': len(rows) > 20})


class DailyExpressionAdminForm(forms.ModelForm):
    """Custom form for DailyExpression admin with IPA keyboard for pinyin."""

    class Meta:
        model = DailyExpression
        fields = "__all__"
        widgets = {
            "pinyin": IPAKeyboardWidget(),
        }


class DailyExpressionAdmin(admin.ModelAdmin):
    form = DailyExpressionAdminForm
    list_display = ["id", "english", "mandarin", "character", "pinyin"]
    list_per_page = 50
    search_fields = ["id", "english", "mandarin", "character", "pinyin"]
    ordering = ("id",)


admin.site.register(Website, WebsiteAdmin)
admin.site.register(DailyExpression, DailyExpressionAdmin)

DjangoApschedulerConfig.verbose_name = "定时任务"
DjangoApschedulerConfig.verbose_name_plural = "定时任务"
DjangoJobExecution._meta.verbose_name_plural = "任务执行情况"
DjangoJobExecution._meta.verbose_name = "任务执行情况"
DjangoJob._meta.verbose_name_plural = "任务"
DjangoJob._meta.verbose_name = "任务"
# 好像没用
Notification._meta.verbose_name_plural = "站内通知"
NotificationAdmin.search_fields = ["recipient__username", "actor__username"]
NotificationAdmin.list_display = list_display = (
    "id",
    "recipient",
    "actor",
    "level",
    "verb",
    "timestamp",
    "unread",
    "public",
)
NotificationAdmin.date_hierarchy = "timestamp"
