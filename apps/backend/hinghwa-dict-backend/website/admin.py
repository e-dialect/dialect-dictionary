from django.contrib import admin
from django_apscheduler.apps import DjangoApschedulerConfig
from django_apscheduler.models import DjangoJob, DjangoJobExecution
from notifications.admin import NotificationAdmin
from notifications.models import Notification
from django import forms
from .models import Website, DailyExpression
from .announcement_admin import WebsiteAdminForm, article_choice, can_view_private_articles
from .announcement_config import article_ids
from article.models import Article
from django.http import JsonResponse, HttpResponseForbidden
from django.urls import path
from utils.admin.widgets import IPAKeyboardWidget


class WebsiteAdmin(admin.ModelAdmin):
    form = WebsiteAdminForm
    list_display = ["id", "announcement_summary", "word_of_the_day"]
    fieldsets = (
        ("公告管理", {"fields": ("announcements",), "description": "选择、排序后保存即可对新请求生效，无需重启；未公开文章仍不会对外显示。"}),
        ("其他首页内容（保留原有格式）", {"fields": ("hot_articles", "word_of_the_day", "carousel"), "classes": ("collapse",)}),
    )

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
        return [path('announcement-search/', self.admin_site.admin_view(self.announcement_search), name='website_announcement_search')] + super().get_urls()

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
