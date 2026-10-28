from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django import forms
from django.conf import settings

from .models import UserInfo
from utils.admin.widgets import ImagePreviewWidget


class UserInfoAdminForm(forms.ModelForm):
    """Custom form for UserInfo admin with image preview for avatar."""

    class Meta:
        model = UserInfo
        fields = "__all__"
        widgets = {
            "avatar": ImagePreviewWidget(max_width=200, max_height=200),
        }


class UserInfoAdmin(admin.ModelAdmin):
    form = UserInfoAdminForm
    list_display = ["ID", "user", "nickname", "telephone"]
    search_fields = ["user__username", "nickname", "telephone", "user__email", "id"]
    ordering = ["user__id"]
    list_per_page = 50


admin.site.register(UserInfo, UserInfoAdmin)
admin.site.unregister(Group)
admin.site.site_url = getattr(settings, "PUBLIC_WEB_URL", "/")
admin.site.site_header = getattr(settings, "SITE_NAME", "在线词典") + "后台管理"
admin.site.site_title = getattr(settings, "SITE_NAME", "在线词典") + "后台管理"
UserAdmin.list_display = ("id", "username", "email", "is_staff", "is_superuser")
UserAdmin.ordering = ("id",)
