"""Our legacy-tsv-v1 adapter, not an official language-resource standard.

Validation reads bounded files into memory and has no database/filesystem writes.
Only apply_package touches the ORM or creates isolated, exclusively owned directories.
"""
import csv
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tempfile
import wave
import zipfile


MAX_FILES = 5000
MAX_FILE = 32 * 1024 * 1024
MAX_TOTAL = 128 * 1024 * 1024
HEADER = ["编号", "普通话", "方言", "发音", "注释"]


class PackageError(ValueError):
    pass


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate metadata key: " + key)
        result[key] = value
    return result


def read_bounded(path):
    with open(path, "rb") as stream:
        return stream.read(MAX_FILE + 1)


def read_zip(archive, entry):
    with archive.open(entry) as stream:
        return stream.read(MAX_FILE + 1)


def preview_summary(plan):
    return {key: value for key, value in plan.items() if key != "files"}


def safe_name(name):
    path = PurePosixPath(name)
    if not name or ":" in name.split("/")[0] or "\\" in name or path.is_absolute() or any(p in (".", "..", "") for p in name.split("/")):
        raise PackageError(f"Unsafe package path: {name!r}")
    return name


def read_package(path):
    try:
        return _read_package(path)
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, EOFError) as exc:
        raise PackageError("Invalid or unsupported ZIP package: " + str(exc)) from exc


def _read_package(path):
    """Do not extract ZIP files; reject links, traversal, excess size, and duplicates."""
    path = Path(path)
    if path.is_symlink():
        raise PackageError("Package root must not be a symlink")
    files = {}
    total = 0

    def add(name, size, reader):
        nonlocal total
        safe_name(name)
        if name in files:
            raise PackageError(f"Duplicate package path: {name}")
        total += size
        if size > MAX_FILE or total > MAX_TOTAL or len(files) >= MAX_FILES:
            raise PackageError("Package exceeds limits: 5000 files, 32 MiB/file, 128 MiB total")
        data = reader()
        if len(data) != size:
            raise PackageError(f"File changed while reading: {name}")
        files[name] = data

    if path.is_dir():
        node_count = 0
        for root, directories, names in os.walk(path, followlinks=False):
            node_count += len(directories) + len(names)
            if node_count > MAX_FILES:
                raise PackageError("Directory exceeds 5000 entries")
            for name in directories + names:
                item = Path(root) / name
                if item.is_symlink():
                    raise PackageError(f"Symlink forbidden: {item.relative_to(path)}")
            for name in names:
                item = Path(root) / name
                if not item.is_file():
                    raise PackageError(f"Not a regular file: {item}")
                add(item.relative_to(path).as_posix(), item.stat().st_size, lambda p=item: read_bounded(p))
    elif path.is_file() and zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            if len(archive.infolist()) > MAX_FILES:
                raise PackageError("ZIP exceeds 5000 members")
            for entry in archive.infolist():
                safe_name(entry.filename.rstrip("/") if entry.is_dir() else entry.filename)
                mode = entry.external_attr >> 16
                if stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR)):
                    raise PackageError(f"ZIP link/special file forbidden: {entry.filename}")
                if entry.flag_bits & 1:
                    raise PackageError("Encrypted ZIP is unsupported")
                if not entry.is_dir():
                    add(entry.filename, entry.file_size, lambda e=entry: read_zip(archive, e))
    else:
        raise PackageError("Expected a directory or ZIP package")
    return files


def validate_package(path, publish=False):
    files = read_package(path)
    errors = []
    digest = hashlib.sha256()
    for name, data in sorted(files.items()):
        encoded = name.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big") + encoded + len(data).to_bytes(8, "big") + data)
    metadata = {}
    try:
        metadata = json.loads(files["metadata.json"].decode("utf-8-sig"), object_pairs_hook=unique_object)
        if not isinstance(metadata, dict):
            raise ValueError("must be an object")
    except (KeyError, ValueError, UnicodeError) as exc:
        errors.append(f"metadata.json: missing/invalid UTF-8 JSON ({exc})")
        metadata = {}
    if metadata.get("profile") != "legacy-tsv-v1":
        errors.append("metadata.profile must be legacy-tsv-v1 (our adapter profile)")
    package_id = metadata.get("package_id", "")
    if not isinstance(package_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,119}", package_id):
        errors.append("metadata.package_id requires 1–120 ASCII letters/digits/dot/underscore/hyphen")
    for key in ("source", "license"):
        if not isinstance(metadata.get(key), str) or not metadata[key].strip():
            errors.append(f"metadata.{key}: explicit source/license statement required; do not guess")
    dialect = metadata.get("dialect", {})
    if not isinstance(dialect, dict):
        dialect = {}
    for key in ("county", "town", "mapping_note"):
        if not isinstance(dialect.get(key), str) or not dialect[key].strip():
            errors.append(f"metadata.dialect.{key}: explicit dialect mapping required")
    if any(len(dialect.get(k, "")) > 100 for k in ("county", "town") if isinstance(dialect.get(k, ""), str)):
        errors.append("metadata.dialect county/town exceed 100 characters")
    publication = metadata.get("publication", {})
    if publish and (not isinstance(publication, dict) or publication.get("authorized") is not True or not isinstance(publication.get("statement"), str) or not publication["statement"].strip()):
        errors.append("--publish requires publication.authorized=true and publication.statement declaring package-specific public authorization")
    raw = files.get("words.tsv", b"")
    encoding = "utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
    rows = []
    try:
        text = raw.decode(encoding)
        if "\x00" in text:
            raise ValueError("NUL bytes: UTF-16 requires a BOM")
        reader = csv.reader(io.StringIO(text), delimiter="\t", strict=True)
        header = next(reader, None)
        if header != HEADER:
            errors.append(f"words.tsv line 1 ({encoding}): expected five-column header {HEADER}")
        ids = set()
        for row in reader:
            line = reader.line_num
            if len(rows) >= MAX_FILES:
                errors.append("words.tsv exceeds 5000 rows")
                break
            if len(row) != 5:
                errors.append(f"words.tsv line {line}: expected 5 columns, got {len(row)}")
                continue
            external_id, mandarin, word, ipa, note = [s.strip() for s in row]
            audio_key = external_id.zfill(4)
            if not re.fullmatch(r"[0-9]{1,4}", external_id) or int(external_id) == 0 or audio_key in ids:
                errors.append(f"words.tsv line {line}: ID must be unique 1–4 decimal digits (audio uses four-digit zero padding): {external_id!r}")
            ids.add(audio_key)
            if any("\n" in cell or "\r" in cell for cell in row):
                errors.append(f"words.tsv line {line}: multiline fields unsupported")
            if not word or len(word) > 60 or len(ipa) > 50 or not mandarin or not ipa:
                errors.append(f"words.tsv line {line}: nonempty 普通话/方言/IPA required; 方言 <=60, IPA <=50 characters")
            # IPA stays IPA. Never transliterate or invent pinyin.
            rows.append(dict(external_id=external_id, audio_key=audio_key, mandarin=mandarin, word=word, ipa=ipa, note=note, line=line))
    except (UnicodeError, ValueError, csv.Error) as exc:
        errors.append(f"words.tsv ({encoding}): decode/parse failed: {exc}")
    if not rows:
        errors.append("words.tsv: no data rows")
    audio_by_id = {}
    for name, data in files.items():
        if name in ("metadata.json", "words.tsv"):
            continue
        match = re.fullmatch(r"audio/([0-9]{4})(?![0-9])[^/]*\.(wav|mp3)", name, re.IGNORECASE)
        if not match:
            errors.append(f"Unsupported/extra file: {name}; only audio/NNNN*.wav|mp3 allowed. FLV must be transcoded before packaging")
            continue
        external_id, extension = match.groups()
        if len(name.split("/", 1)[1]) > 200:
            errors.append(f"Audio filename exceeds 200 characters: {name}")
        if external_id in audio_by_id:
            errors.append(f"Duplicate audio for source ID {external_id}: {name}")
        audio_by_id[external_id] = name
        try:
            if extension.lower() == "wav":
                with wave.open(io.BytesIO(data)) as recording:
                    if recording.getnframes() <= 0 or recording.getnchannels() not in (1, 2) or not recording.readframes(1):
                        raise ValueError("empty/unsupported WAV")
            elif not (data.startswith(b"ID3") or (len(data) >= 4 and data[0] == 255 and data[1] & 224 == 224)):
                raise ValueError("missing MP3 header")
        except (wave.Error, EOFError, ValueError) as exc:
            errors.append(f"Invalid media {name}: {exc}")
    row_ids = {row["audio_key"] for row in rows}
    for row in rows:
        row["audio"] = audio_by_id.get(row["audio_key"])
        if not row["audio"]:
            errors.append(f"words.tsv line {row['line']}: missing audio for {row['external_id']}")
    for extra in sorted(set(audio_by_id) - row_ids):
        errors.append(f"Extra audio without TSV row: {audio_by_id[extra]}")
    return dict(metadata=metadata, digest=digest.hexdigest(), rows=rows, files=files, errors=errors, encoding=encoding)


def apply_package(plan, importer, publish=False):
    from django.conf import settings
    from django.contrib.auth.models import User
    from django.db import transaction
    from user.models import UserInfo
    from word.models import Pronunciation, ResourcePackage, ResourcePackageEntry, Word
    from urllib.parse import quote

    if plan["errors"]:
        raise PackageError("\n".join(plan["errors"]))
    if publish:
        publication = plan["metadata"].get("publication", {})
        if publication.get("authorized") is not True or not publication.get("statement", "").strip():
            raise PackageError("Package lacks explicit public authorization")
    try:
        author = User.objects.get(username=importer)
    except User.DoesNotExist:
        raise PackageError(f"Importer {importer!r} does not exist; use an existing username")
    package_id = plan["metadata"]["package_id"]
    previous = ResourcePackage.objects.filter(package_id=package_id).first()
    if previous:
        if previous.digest != plan["digest"]:
            raise PackageError(f"Package ID {package_id} already exists with a different digest; choose a new version ID")
        if previous.published != publish:
            raise PackageError("Package already imported with different publication state; no implicit publication change")
        return previous, False
    data_root = Path(getattr(settings, "DATA_DIR", os.environ.get("DATA_DIR", str(Path(settings.BASE_DIR) / "data")))).resolve()
    private_root = data_root / "private-imports"
    media_root = Path(settings.MEDIA_ROOT).resolve()
    if private_root.is_symlink() or private_root.resolve().is_relative_to(media_root):
        raise PackageError("DATA_DIR/private-imports must be outside publicly served MEDIA_ROOT")
    private_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    staging = Path(tempfile.mkdtemp(prefix=".stage-", dir=private_root))
    destination = None
    moved = False
    try:
        for row in plan["rows"]:
            (staging / Path(row["audio"]).name).write_bytes(plan["files"][row["audio"]])
        folder = hashlib.sha256(package_id.encode()).hexdigest()[:24] + "-" + plan["digest"][:16]
        root = media_root / "imports" if publish else private_root
        if root.is_symlink():
            raise PackageError("Import storage root must not be a symlink")
        root.mkdir(parents=True, exist_ok=True)
        destination = root / folder
        # mkdir is exclusive: existing/orphan files are never overwritten or removed.
        destination.mkdir(mode=0o755 if publish else 0o700)
        moved = True
        for item in staging.iterdir():
            item.rename(destination / item.name)
        with transaction.atomic():
            UserInfo.objects.get_or_create(user=author, defaults={"nickname": "资料维护者"})
            receipt = ResourcePackage.objects.create(package_id=package_id, digest=plan["digest"], profile="legacy-tsv-v1", metadata=plan["metadata"], importer=author, published=publish, storage_path=str(destination))
            dialect = plan["metadata"]["dialect"]
            for row in plan["rows"]:
                word = Word.objects.bulk_create([Word(word=row["word"], definition=row["note"], annotation=f"Resource package: {package_id}; external ID: {row['external_id']}\nSource: {plan['metadata']['source']}\nLicense: {plan['metadata']['license']}", mandarin=json.dumps([row["mandarin"]], ensure_ascii=False), standard_ipa=row["ipa"], standard_pinyin="", contributor=author, visibility=publish)])[0]
                source = getattr(settings, "PUBLIC_API_BASE", "").rstrip("/") + "/media/imports/" + folder + "/" + quote(Path(row["audio"]).name) if publish else ""
                pronunciation = Pronunciation.objects.bulk_create([Pronunciation(word=word, source=source, ipa=row["ipa"], pinyin="", county=dialect["county"], town=dialect["town"], contributor=author, visibility=publish)])[0]
                ResourcePackageEntry.objects.create(package=receipt, external_id=row["external_id"], source_line=row["line"], word=word, pronunciation=pronunciation, audio_name=Path(row["audio"]).name)
        return receipt, True
    except BaseException:
        if moved:
            shutil.rmtree(destination, ignore_errors=True)
        raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)
