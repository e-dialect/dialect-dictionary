"""Package reviewed source only. Never copies Git internals or runtime data."""
import argparse
import gzip
import hashlib
import io
import json
import re
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artifacts"
EXCLUDED_PARTS = {".git", "node_modules", ".venv", "__pycache__", "dist", "runtime", "backups", "artifacts", "logs", "media", "material", ".model_cache", "semantic_search_data"}
EVIDENCE = {"frontend-final.json", "compose-runtime.json", "validation-summary.json", "usage.json", "round2-summary.json", "round2-clean-build.json", "round2-recovery-runtime.json", "delivery-validation.json", "license-cleanup-validation.json"}
LICENSE_EXCLUSIONS = {"integrations/quick-start/sql.js", "integrations/quick-start/test_sql.py", "scripts/verify_synthetic_restore.py", "web/src/assets/IatRecorder.js", "web/src/assets/transcode.worker.js", "web/src/assets/rewards.svg", "web/src/assets/timg.gif", "web/public/certificate.png"}


def included(path):
    relative = path.relative_to(ROOT)
    if relative.as_posix() in LICENSE_EXCLUSIONS or relative.as_posix() in {"MANIFEST.json", "RELEASE.json"}:
        return False
    if set(relative.parts) & EXCLUDED_PARTS or path.is_symlink():
        return False
    if path.name.startswith(".env") and path.name != ".env.example":
        return False
    if path.suffix in {".sqlite3", ".sqlite", ".db", ".pem", ".key", ".p12"}:
        return False
    # Historical HTTP capture files may contain personal data or old tokens.
    if relative.parts[:2] == ("backend", "tests") and path.suffix == ".json":
        return False
    if relative.parts[0] == "evidence" and path.name not in EVIDENCE:
        return False
    return path.is_file()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-dirty", action="store_true", help="Draft acceptance only; marked in RELEASE.json")
    args = parser.parse_args()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT).strip())
    if dirty and not args.allow_dirty:
        raise SystemExit("Commit/review changes first, or explicitly create a marked --allow-dirty test draft")
    OUTPUT.mkdir(exist_ok=True)
    tracked = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT).decode().split("\0")
    paths = sorted({ROOT / name for name in tracked if name and included(ROOT / name)})
    forbidden = []
    excluded_hashes = {item["sha256"] for item in json.loads((ROOT / "provenance/excluded-materials.json").read_text())["files"]}
    for path in paths:
        if path.stat().st_size > 10 * 1024 * 1024:
            forbidden.append(str(path.relative_to(ROOT)))
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() in excluded_hashes:
            forbidden.append(str(path.relative_to(ROOT)))
        # Targeted known-token scan; source/dataset licensing is separately reviewed.
        if re.search(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|(?:AKIA|ASIA)[A-Z0-9]{16}|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|AKID[A-Za-z0-9]{28,}", content):
            forbidden.append(str(path.relative_to(ROOT)))
    if forbidden:
        raise SystemExit("Review required; no archive created for: " + ", ".join(forbidden))
    files = {path.relative_to(ROOT).as_posix(): path.read_bytes() for path in paths}
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    timestamp = int(subprocess.check_output(["git", "show", "-s", "--format=%ct", "HEAD"], cwd=ROOT))
    release = {"version": (ROOT / "VERSION").read_text().strip(), "sourceCommit": commit, "sourceDirty": dirty,
               "delivery": "source-only; online dependency/base-image fetch required for a new build",
               "excludedUnlicensedCode": sorted(LICENSE_EXCLUSIONS),
               "validatedLocalImages": json.loads((ROOT / "deploy/validated-images.json").read_text()),
               "upstreams": json.loads((ROOT / "provenance/sources.json").read_text()),
               "dependencyLocks": {name: hashlib.sha256(files[name]).hexdigest() for name in ["web/yarn.lock", "uni-app/yarn.lock", "deploy/requirements.dictionary.lock"]}}
    files["RELEASE.json"] = (json.dumps(release, ensure_ascii=False, indent=2) + "\n").encode()
    manifest = {"schemaVersion": 1, "files": [{"path": name, "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)} for name, content in sorted(files.items())]}
    files["MANIFEST.json"] = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    output = OUTPUT / "dialect-dictionary-kt2-source.tar.gz"
    with output.open("wb") as stream, gzip.GzipFile(filename="", mode="wb", fileobj=stream, mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode="w") as archive:
            for name, content in sorted(files.items()):
                info = tarfile.TarInfo("dialect-dictionary/" + name)
                info.size, info.mtime = len(content), timestamp
                original = ROOT / name
                info.mode = 0o755 if original.is_file() and original.stat().st_mode & 0o111 else 0o644
                archive.addfile(info, io.BytesIO(content))
    sha = hashlib.sha256(output.read_bytes()).hexdigest()
    (OUTPUT / "SHA256SUMS").write_text(sha + "  " + output.name + "\n")
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    (OUTPUT / "package-audit.json").write_text(json.dumps({"sourceCommit": commit, "sourceDirty": dirty, "files": len(files), "sha256": sha, "excludedUnlicensedCode": sorted(LICENSE_EXCLUSIONS), "targetedTokenMatches": 0, "noRuntimeOrDatabase": True}, indent=2) + "\n")
    print(json.dumps({"archive": output.name, "files": len(files), "sha256": sha, "dirtyDraft": dirty}))


if __name__ == "__main__":
    main()
