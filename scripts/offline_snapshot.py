"""Offline SQLite/local-media backup and new-directory restore; stop writers first.

No import, production connection, credential generation, or permission grants.
Snapshots contain private data and keys; never upload them as source deliveries.
"""
import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import sqlite3
import tarfile
import tempfile


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def check_db(path):
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        if db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise ValueError("SQLite integrity check failed")
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("SQLite foreign key check failed")


def private_file(path):
    return os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb")


def backup(data, config, release, output):
    for directory in (data, config):
        if not directory.is_dir() or directory.is_symlink():
            raise ValueError("Expected real data/config directory")
        if output.resolve().is_relative_to(directory.resolve()):
            raise ValueError("Backup output must be outside data/config")
    if not release.is_file() or release.is_symlink():
        raise ValueError("Missing regular RELEASE.json")
    database = data / "dictionary.sqlite3"
    check_db(database)
    with tempfile.TemporaryDirectory() as temporary:
        snapshot = Path(temporary) / "dictionary.sqlite3"
        with closing(sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)) as source:
            with closing(sqlite3.connect(snapshot)) as target:
                source.backup(target)
        entries = {"data/dictionary.sqlite3": snapshot, "RELEASE.json": release}
        for prefix, directory in (("data", data), ("config", config)):
            for path in sorted(directory.rglob("*")):
                if path.is_symlink():
                    raise ValueError("Symlinks require an explicit external-storage backup: " + str(path))
                if path.is_file():
                    relative = path.relative_to(directory).as_posix()
                    if prefix == "data" and relative in {"dictionary.sqlite3", "dictionary.sqlite3-wal", "dictionary.sqlite3-shm", "dictionary.sqlite3-journal"}:
                        continue
                    entries[prefix + "/" + relative] = path
                elif not path.is_dir():
                    raise ValueError("Unsupported data file")
        inventory = {name: {"sha256": file_hash(path), "bytes": path.stat().st_size} for name, path in entries.items()}
        manifest = Path(temporary) / "SNAPSHOT.json"
        manifest.write_text(json.dumps({"schemaVersion": 1, "privateData": True, "files": inventory}, indent=2) + "\n")
        with private_file(output) as stream:
            with tarfile.open(fileobj=stream, mode="w:gz") as archive:
                for name, path in entries.items():
                    archive.add(path, arcname=name, recursive=False)
                archive.add(manifest, arcname="SNAPSHOT.json", recursive=False)
    print(json.dumps({"backup": output.name, "sha256": file_hash(output), "files": len(entries)}))


def restore(archive_path, target):
    if target.exists() or target.is_symlink():
        raise ValueError("Restore target must not exist; existing data is never overwritten")
    with tarfile.open(archive_path, "r:gz") as archive:
        by_name = {}
        for member in archive.getmembers():
            path = PurePosixPath(member.name)
            if not member.isfile() or path.is_absolute() or ".." in path.parts or member.name in by_name or str(path) != member.name:
                raise ValueError("Unsafe/duplicate snapshot member")
            if not (member.name in {"SNAPSHOT.json", "RELEASE.json"} or member.name.startswith(("data/", "config/"))):
                raise ValueError("Unexpected snapshot path")
            by_name[member.name] = member
        metadata = by_name.get("SNAPSHOT.json")
        if metadata is None or metadata.size > 8 * 1024 * 1024:
            raise ValueError("Missing or oversized snapshot inventory")
        manifest = json.load(archive.extractfile(metadata))
        if manifest.get("schemaVersion") != 1 or not isinstance(manifest.get("files"), dict):
            raise ValueError("Unsupported snapshot schema")
        if set(by_name) != set(manifest["files"]) | {"SNAPSHOT.json"}:
            raise ValueError("Snapshot inventory mismatch")
        if not {"data/dictionary.sqlite3", "RELEASE.json"}.issubset(manifest["files"]):
            raise ValueError("Incomplete snapshot")
        for name, expected in manifest["files"].items():
            member = by_name[name]
            digest = hashlib.sha256()
            with archive.extractfile(member) as source:
                for block in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(block)
            if member.size != expected["bytes"] or digest.hexdigest() != expected["sha256"]:
                raise ValueError("Snapshot checksum mismatch: " + name)
        target.mkdir(parents=True, mode=0o700)
        for name, member in by_name.items():
            path = target / name
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with private_file(path) as stream, archive.extractfile(member) as source:
                for block in iter(lambda: source.read(1024 * 1024), b""):
                    stream.write(block)
    check_db(target / "data/dictionary.sqlite3")
    print(json.dumps({"restored": str(target), "files": len(manifest["files"]), "integrity": "ok", "foreignKeys": "ok"}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    make = sub.add_parser("backup")
    for key in ("data", "config", "release", "output"):
        make.add_argument("--" + key, type=Path, required=True)
    recover = sub.add_parser("restore")
    recover.add_argument("--archive", type=Path, required=True)
    recover.add_argument("--target", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "backup":
        backup(args.data, args.config, args.release, args.output)
    else:
        restore(args.archive, args.target)
