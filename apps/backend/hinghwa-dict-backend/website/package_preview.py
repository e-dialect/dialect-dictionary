"""Admin-only ZIP preview; shares the CLI validator and never calls apply_package."""
from pathlib import Path
import tempfile
import zipfile

from django import forms
from django.conf import settings
from django.core.exceptions import SuspiciousOperation, ValidationError
from django.http import HttpResponseForbidden, HttpResponseNotAllowed
from django.template.response import TemplateResponse
from django.urls import reverse
from word.resource_packages import PackageError, validate_package, preview_summary


MAX_WEB_ZIP_BYTES = 19 * 1024 * 1024
MAX_WEB_REQUEST_BYTES = 20 * 1024 * 1024


class PackagePreviewForm(forms.Form):
    package = forms.FileField(
        label='选择一份 ZIP 资料包',
        widget=forms.ClearableFileInput(attrs={'accept': '.zip'}),
        help_text='最多19 MiB；只检查，不导入、不公开。ZIP内根目录应有 metadata.json、words.tsv 和 audio/。',
    )

    def clean_package(self):
        upload = self.cleaned_data['package']
        if not upload.name.lower().endswith('.zip'):
            raise ValidationError('请选择 ZIP 文件。文件夹请先按资料包说明压缩，不能只修改扩展名。')
        if upload.size > MAX_WEB_ZIP_BYTES:
            raise ValidationError('ZIP 超过19 MiB网页预览限制；请使用资料包指南中的本地命令预览。')
        return upload


def preview_upload(upload):
    """Private temporary copy, bounded streaming, cleanup even on parse failure.

    The shared validator reads ZIP members without extracting them. Its independent
    limits are 5000 entries, 32 MiB/member and 128 MiB expanded data.
    """
    with tempfile.TemporaryDirectory(prefix='dictionary-preview-') as temporary:
        root = Path(temporary).resolve()
        media = Path(settings.MEDIA_ROOT).resolve()
        if root == media or media in root.parents:
            raise OSError('Preview temporary storage must be outside public media')
        target = root / 'package.zip'  # Never use the client's filename as a path.
        size = 0
        with target.open('xb') as destination:
            for chunk in upload.chunks(chunk_size=64 * 1024):
                size += len(chunk)
                if size > MAX_WEB_ZIP_BYTES:
                    raise PackageError('ZIP exceeds the 19 MiB web upload limit')
                destination.write(chunk)
        return preview_summary(validate_package(target, publish=False))


def clipped(value, maximum):
    if not isinstance(value, str):
        return '（未填写或格式错误）'
    return value[:maximum] + ('…（显示已截短，原包未修改）' if len(value) > maximum else '')


def display_summary(plan):
    metadata = plan['metadata']
    dialect = metadata.get('dialect', {})
    if not isinstance(dialect, dict):
        dialect = {}
    return {
        'package_id': clipped(metadata.get('package_id'), 120),
        'source': clipped(metadata.get('source'), 4096),
        'license': clipped(metadata.get('license'), 4096),
        'county': clipped(dialect.get('county'), 100),
        'town': clipped(dialect.get('town'), 100),
        'mapping_note': clipped(dialect.get('mapping_note'), 4096),
        'digest': plan['digest'], 'encoding': plan['encoding'],
        'row_count': len(plan['rows']), 'error_count': len(plan['errors']),
        'errors': [clipped(error, 1000) for error in plan['errors'][:100]],
        'rows': [{key: value if key == 'line' else clipped(value, 500)
                  for key, value in row.items()} for row in plan['rows'][:50]],
        'rows_truncated': len(plan['rows']) > 50,
        'errors_truncated': len(plan['errors']) > 100,
    }


def package_preview(request, admin_site):
    if not request.user.has_perm('word.view_resourcepackage'):
        return HttpResponseForbidden('当前账号没有资料包查看权限；请联系站点管理员。')
    if request.method not in ('GET', 'POST'):
        return HttpResponseNotAllowed(['GET', 'POST'])
    context = {
        **admin_site.each_context(request), 'title': '资料包只读预览',
        'back_url': reverse('admin:index'), 'result': None, 'failure': '',
    }
    status = 200
    form = PackagePreviewForm()
    if request.method == 'POST':
        try:
            length = int(request.META.get('CONTENT_LENGTH') or 0)
            if length < 0:
                raise ValueError('negative request size')
            if length > MAX_WEB_REQUEST_BYTES:
                context['failure'] = '整个上传请求超过20 MiB。请改用本地命令预览；没有导入或公开任何内容。'
                status = 413
            else:
                form = PackagePreviewForm(request.POST, request.FILES)
                if form.is_valid():
                    try:
                        context['result'] = display_summary(preview_upload(form.cleaned_data['package']))
                    except (PackageError, zipfile.BadZipFile, UnicodeError, RecursionError) as exc:
                        form.add_error('package', '无法校验资料包，请按规范修正后重新选择。详情：' + clipped(str(exc), 1000))
                    except OSError:
                        # Do not expose server paths or uploaded content in errors/logs.
                        form.add_error('package', '临时读取失败，请稍后重试或联系管理员检查临时存储空间。')
        except (ValueError, SuspiciousOperation):
            context['failure'] = '上传请求格式不正确或超出处理限制，请重新选择一个 ZIP；没有导入或公开任何内容。'
            status = 400
    context['form'] = form
    response = TemplateResponse(request, 'admin/website/package_preview.html', context, status=status)
    response['Cache-Control'] = 'private, no-store'
    return response
