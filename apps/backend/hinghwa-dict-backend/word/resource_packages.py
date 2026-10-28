"""Our legacy-tsv-v1 adapter, not an official language-resource standard.

Validation reads bounded files into memory and has no database/filesystem writes.
Only apply_package touches the ORM or creates isolated, exclusively owned directories.
"""
import csv
from contextlib import contextmanager
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


@contextmanager
def package_lock(private_root, package_id):
    """Apply-only, nonblocking process lock. OS releases it after crash/close."""
    import fcntl
    lock_root = private_root / ".locks"
    if lock_root.is_symlink():
        raise PackageError("Import lock directory must not be a symlink")
    lock_root.mkdir(mode=0o700, exist_ok=True)
    lock_path = lock_root / (hashlib.sha256(package_id.encode()).hexdigest() + ".lock")
    flags = os.O_WRONLY | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(lock_path, flags, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise PackageError("Import busy for this package ID; retry after the other import finishes") from exc
        yield
    finally:
        # Closing also releases the flock; never unlink a lock inode while others may use it.
        os.close(descriptor)


def verify_resumable_directory(destination, expected):
    """Inspect all existing bytes before adding anything; never overwrite alien data."""
    if destination.is_symlink() or not destination.is_dir():
        raise PackageError("Residual import destination must be a regular directory")
    for item in destination.iterdir():
        if item.is_symlink() or not item.is_file() or item.name not in expected:
            raise PackageError("Residual import contains unknown or linked data; inspect it before retrying")
        if item.stat().st_size != len(expected[item.name]) or read_bounded(item) != expected[item.name]:
            raise PackageError("Residual import bytes differ from this exact package; nothing was overwritten")


def sync_directory(path):
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


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
    data_root = Path(getattr(settings, "DATA_DIR", os.environ.get("DATA_DIR", str(Path(settings.BASE_DIR) / "data")))).resolve()
    private_root = data_root / "private-imports"
    media_root = Path(settings.MEDIA_ROOT).resolve()
    if private_root.is_symlink() or private_root.resolve().is_relative_to(media_root):
        raise PackageError("DATA_DIR/private-imports must be outside publicly served MEDIA_ROOT")
    private_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    sync_directory(data_root)
    with package_lock(private_root, package_id):
        # A competing importer may have completed while this invocation was starting.
        previous = ResourcePackage.objects.filter(package_id=package_id).first()
        if previous:
            if previous.digest != plan["digest"]:
                raise PackageError(f"Package ID {package_id} already exists with a different digest; choose a new version ID")
            if previous.published != publish:
                raise PackageError("Package already imported with different publication state; no implicit publication change")
            return previous, False
        staging = Path(tempfile.mkdtemp(prefix=".stage-", dir=private_root))
        destination = None
        created_destination = False
        try:
            expected = {Path(row["audio"]).name: plan["files"][row["audio"]] for row in plan["rows"]}
            for name, content in expected.items():
                with (staging / name).open("wb") as stream:
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
            folder = hashlib.sha256(package_id.encode()).hexdigest()[:24] + "-" + plan["digest"][:16]
            root = private_root  # Even published imports are served only through the receipt/entry gate.
            if root.is_symlink():
                raise PackageError("Import storage root must not be a symlink")
            root.mkdir(parents=True, exist_ok=True)
            destination = root / folder
            if destination.exists() or destination.is_symlink():
                verify_resumable_directory(destination, expected)
            else:
                destination.mkdir(mode=0o700)
                created_destination = True
            for item in staging.iterdir():
                target = destination / item.name
                if target.exists():
                    continue  # Validated byte-for-byte above under this package's lock.
                if created_destination:
                    item.rename(target)
                else:
                    # Resume only missing files, exclusively; preserve all adopted bytes on failure.
                    # Link a fully written/fsynced private staged file atomically. A
                    # crash during resume must not create a truncated target file.
                    os.link(item, target, follow_symlinks=False)
            sync_directory(destination)
            sync_directory(private_root)
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
            if created_destination:
                # Do not delete media if commit succeeded or its state cannot safely be established.
                try:
                    committed = ResourcePackage.objects.filter(package_id=package_id, digest=plan["digest"]).exists()
                except Exception:
                    committed = True
                if not committed:
                    shutil.rmtree(destination, ignore_errors=True)
            raise
        finally:
            shutil.rmtree(staging, ignore_errors=True)
