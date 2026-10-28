"""Only a committed, publicly visible import receipt grants media access.

All new imports stay outside MEDIA_ROOT. Existing ordinary local media and old
committed imported-media locations retain their URLs; imports is a reserved URL
namespace and never falls through to the unrestricted legacy static handler.
"""
import posixpath
from pathlib import Path

from django.conf import settings
from django.db.models import Q
from django.http import Http404
from django.views.decorators.http import require_safe
from django.views.static import serve
from django.utils.http import content_disposition_header


@require_safe
def dictionary_media(request, path):
    base = Path(settings.MEDIA_ROOT).resolve()
    normalized = posixpath.normpath(path).lstrip('/')
    target = (base / normalized).resolve()
    if not target.is_relative_to(base):
        raise Http404
    parts = normalized.split('/')
    if parts[0] != 'imports':
        if target.is_relative_to(base / 'imports'):
            raise Http404
        return serve(request, normalized, document_root=str(base))
    if len(parts) != 3 or parts[1] in ('', '.', '..') or parts[2] in ('', '.', '..'):
        raise Http404
    folder, filename = parts[1:]
    data = Path(settings.DATA_DIR).resolve()
    allowed = [data / 'private-imports' / folder, base / 'imports' / folder]
    from word.models import ResourcePackageEntry
    # A separate HTTP request observes committed state, never an importer's pending
    # transaction. No on_commit file publication or filesystem existence fallback.
    entry = ResourcePackageEntry.objects.select_related('package').filter(
        Q(package__storage_path=str(allowed[0])) | Q(package__storage_path=str(allowed[1])),
        package__published=True, word__visibility=True,
        pronunciation__visibility=True, audio_name=filename,
    ).first()
    if entry is None:
        raise Http404
    directory = Path(entry.package.storage_path)
    if directory.is_symlink() or directory.resolve() not in allowed:
        raise Http404
    media = directory / filename
    if media.is_symlink() or media.resolve().parent != directory.resolve():
        raise Http404
    response = serve(request, filename, document_root=str(directory))
    response['Cache-Control'] = 'private, no-store'
    return response


@require_safe
def dictionary_legacy_file(request, type, id, Y, M, D, X):
    """Standalone legacy alias shares the same namespace and receipt checks.

    The original non-standalone website.openUrl is deliberately unchanged.
    Preserve successful legacy downloads' bytes, MIME type and attachment name.
    """
    response = dictionary_media(request, f"{type}/{id}/{Y}_{M}_{D}_{X}")
    response['Content-Type'] = 'application/octet-stream'
    response['Content-Disposition'] = content_disposition_header(True, X)
    return response
