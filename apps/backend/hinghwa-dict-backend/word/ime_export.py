"""Independent Pouleng/Rime addon exporter; no upstream schema/data copied.

Local administrative CLI only. No download URL, engine install, IPA conversion or
implicit private-data selection. Generated archives are private by default.
"""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import tempfile
import unicodedata
import zipfile

PROFILE = 'pouleng-rime-v1'
UPSTREAM = 'https://github.com/e-dialect/hinghwa-ime'
UPSTREAM_COMMIT = 'e3b392032dd3dff586948553f944ca628e4cbd33'
MAX_BYTES = 32 * 1024 * 1024


class ExportError(ValueError):
    pass


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode('utf-8')


def mapping_codes(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ExportError('Mapping must be a regular UTF-8 TSV file, not a link')
    with path.open('rb') as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ExportError('Mapping exceeds 32 MiB')
    try:
        rows = csv.reader(io.StringIO(raw.decode('utf-8-sig')), delimiter='\t', strict=True)
        if next(rows, None) != ['external_id', 'code']:
            raise ExportError('Mapping header must be external_id<TAB>code')
        codes = {}
        for row in rows:
            if len(codes) >= 5000 or len(row) != 2:
                raise ExportError(f'Mapping line {rows.line_num}: expected two columns, maximum 5000 entries')
            key, code = row
            if not re.fullmatch(r'[0-9]{1,4}', key) or key in codes:
                raise ExportError(f'Mapping line {rows.line_num}: invalid or duplicate original ID')
            if len(code) > 200 or not re.fullmatch(r'[a-z]+[1-8]?(?: [a-z]+[1-8]?)*', code):
                raise ExportError(f'Mapping line {rows.line_num}: unsupported Pouleng code; no automatic conversion')
            codes[key] = code
        return codes, hashlib.sha256(raw).hexdigest()
    except (UnicodeError, csv.Error) as exc:
        raise ExportError('Mapping must be valid UTF-8 TSV') from exc


def prepare_export(package_id, requester, mapping, version, include_private=False):
    from django.contrib.auth.models import User
    from django.db import transaction
    from word.models import ResourcePackage
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}', version):
        raise ExportError('An explicit safe --version is required (1-64 ASCII letters/digits/dot/underscore/hyphen)')
    # One consistent DB read transaction; perform no model save/counter updates.
    with transaction.atomic():
        actor = User.objects.filter(username=requester, is_active=True).first()
        if actor is None:
            raise ExportError('Requester must be an existing active user; no account is created')
        package = ResourcePackage.objects.filter(package_id=package_id).first()
        if package is None:
            raise ExportError('Package not found')
        if include_private and not (actor.is_superuser or package.importer_id == actor.id):
            raise ExportError('Private export requires the package importer or a superuser')
        entries = list(package.entries.select_related('word', 'pronunciation').order_by('source_line', 'external_id')[:5001])
        if len(entries) > 5000:
            raise ExportError('Package exceeds 5000 export entries')
        if not entries:
            raise ExportError('Package has no entries')
        if not include_private and (not package.published or any(not e.word.visibility or not e.pronunciation.visibility for e in entries)):
            raise ExportError('Package is not fully public; no private rows exported or silently skipped')
        codes, mapping_hash = mapping_codes(mapping)
        ids = {entry.external_id for entry in entries}
        if set(codes) != ids:
            raise ExportError('Mapping must cover exactly every original package ID; missing or extra IDs found')
        rows = []
        seen = set()
        for entry in entries:
            word = entry.word.word
            if not word or word != word.strip() or word.startswith('#') or any(unicodedata.category(c) in ('Cc', 'Cf', 'Cs') for c in word):
                raise ExportError(f'Unsupported Rime text at original ID {entry.external_id}; no text was rewritten')
            code = codes[entry.external_id]
            if (word, code) in seen:
                raise ExportError('Duplicate text/code pair; no silent deduplication')
            seen.add((word, code))
            rows.append({'external_id': entry.external_id, 'text': word, 'code': code,
                         'standard_ipa': entry.word.standard_ipa, 'standard_pinyin': entry.word.standard_pinyin,
                         'pronunciation_ipa': entry.pronunciation.ipa, 'pronunciation_pinyin': entry.pronunciation.pinyin})
        if not isinstance(package.metadata.get('source'), str) or not package.metadata['source'].strip() or not isinstance(package.metadata.get('license'), str) or not package.metadata['license'].strip():
            raise ExportError('Explicit package source and license are required')
        return {'profile': PROFILE, 'version': version, 'package_id': package.package_id,
                'package_sha256': package.digest, 'metadata': package.metadata, 'mapping_sha256': mapping_hash,
                'requester': actor.username, 'includes_private': include_private,
                'target': {'repository': UPSTREAM, 'commit': UPSTREAM_COMMIT, 'schema_id': 'Pouleng'},
                'rows': rows,
                'omitted_fields': ['audio bytes/URLs', 'definitions', 'annotations', 'account credentials'],
                'notes': ['IPA and original pinyin are retained in source.json, not converted to input codes.',
                          'Codes and tone digits are preserved; upstream Pouleng speller ignores tone during typing.',
                          'Weight 100 is a fixed export default, not measured corpus frequency.']}


def archive_bytes(plan, authorization_statement):
    if not authorization_statement or not authorization_statement.strip():
        raise ExportError('Export requires an explicit --authorization-statement for text, codes and intended local use')
    name = 'dictionary_local_' + hashlib.sha256(plan['package_id'].encode()).hexdigest()[:12]
    header = '# Rime dictionary\n# encoding: utf-8\n---\n'
    header += f'name: {name}\nversion: "{plan["version"]}"\nsort: by_weight\nuse_preset_vocabulary: false\nimport_tables:\n  - Pouleng\n...\n'
    dictionary = header + ''.join(f'{r["text"]}\t{r["code"]}\t100\n' for r in plan['rows'])
    source = dict(plan, dictionary_name=name, authorization_statement=authorization_statement.strip())
    files = {name + '.dict.yaml': dictionary.encode('utf-8'), 'source.json': json_bytes(source),
             'Pouleng.custom.example.yaml': f'# Merge into your existing custom file; never overwrite it blindly.\npatch:\n  "translator/dictionary": {name}\n'.encode(),
             'INSTALL.txt': ('这是附加词库，不是输入法本体。先安装固定来源的Pouleng方案及其依赖。\n'
                             '备份Rime用户目录，将.dict.yaml放入用户目录，按.example.yaml合并自定义配置。\n'
                             '不要覆盖已有Pouleng.custom.yaml；重新部署后自行验证候选字与声调提示。\n'
                             '私有资料不得上传公共同步库；完整中文步骤见词典仓库docs/ime-export.md。\n').encode('utf-8')}
    manifest = {'schemaVersion': 1, 'profile': PROFILE, 'version': plan['version'],
                'files': {k: {'sha256': hashlib.sha256(v).hexdigest(), 'bytes': len(v)} for k, v in files.items()}}
    if any(len(value) > MAX_BYTES for value in files.values()):
        raise ExportError('Export member exceeds 32 MiB; nothing written')
    files['MANIFEST.json'] = json_bytes(manifest)
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for path, data in sorted(files.items()):
            info = zipfile.ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100600 << 16
            archive.writestr(info, data)
    return output.getvalue()


def write_export(plan, output, authorization_statement):
    from django.conf import settings
    path = Path(output)
    if path.resolve().is_relative_to(Path(settings.MEDIA_ROOT).resolve()):
        raise ExportError('Export must stay outside public MEDIA_ROOT')
    data = archive_bytes(plan, authorization_statement)
    # A complete private temp file becomes visible atomically, never overwriting.
    descriptor, temporary = tempfile.mkstemp(prefix='.ime-export-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        os.link(temporary, path, follow_symlinks=False)
    finally:
        os.unlink(temporary)
    return {'file': path.name, 'sha256': hashlib.sha256(data).hexdigest(), 'entries': len(plan['rows']),
            'profile': PROFILE, 'version': plan['version']}


def verify_archive(path):
    """Inspect without extraction. Hashes detect corruption, not authenticity."""
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        names = [i.filename for i in infos]
        if len(infos) != 5 or len(set(names)) != 5 or any('/' in n or '\\' in n or n in ('.', '..') for n in names):
            raise ExportError('Unexpected archive members')
        fixed = {'source.json', 'MANIFEST.json', 'INSTALL.txt', 'Pouleng.custom.example.yaml'}
        dictionaries = set(names) - fixed
        if not fixed.issubset(names) or len(dictionaries) != 1 or not re.fullmatch(r'dictionary_local_[0-9a-f]{12}\.dict\.yaml', next(iter(dictionaries))):
            raise ExportError('Unexpected export filenames')
        if sum(i.file_size for i in infos) > 128 * 1024 * 1024:
            raise ExportError('Archive exceeds 128 MiB')
        if any(i.file_size > MAX_BYTES or i.flag_bits & 1 or ((i.external_attr >> 16) & 0o170000) not in (0, 0o100000) or (i.external_attr >> 16) & 0o111 for i in infos):
            raise ExportError('Unsafe or oversized archive member')
        contents = {}
        for info in infos:
            with archive.open(info) as stream:
                data = stream.read(MAX_BYTES + 1)
            if len(data) != info.file_size or len(data) > MAX_BYTES:
                raise ExportError('Invalid archive member size')
            contents[info.filename] = data
    manifest = json.loads(contents.pop('MANIFEST.json'))
    if manifest.get('profile') != PROFILE or manifest.get('schemaVersion') != 1 or set(manifest.get('files', {})) != set(contents):
        raise ExportError('Invalid manifest')
    for name, data in contents.items():
        if manifest['files'][name] != {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}:
            raise ExportError('Archive checksum mismatch: ' + name)
    return {'valid': True, 'profile': PROFILE, 'version': manifest['version'], 'files': len(contents)}
