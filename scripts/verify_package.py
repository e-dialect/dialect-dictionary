"""Verify an extracted source delivery without Git or third-party dependencies."""
import hashlib
import json
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]


def verify(root):
    manifest = json.loads((root / "MANIFEST.json").read_text())
    paths = set()
    for item in manifest["files"]:
        relative = PurePosixPath(item["path"])
        if relative.is_absolute() or ".." in relative.parts or str(relative) != item["path"] or item["path"] in paths:
            raise ValueError("Invalid or duplicate inventory path")
        paths.add(item["path"])
        path = root / relative
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
            raise ValueError("Missing or linked file: " + str(relative))
        content = path.read_bytes()
        if len(content) != item["bytes"] or hashlib.sha256(content).hexdigest() != item["sha256"]:
            raise ValueError("Changed file: " + str(relative))
    release = json.loads((root / "RELEASE.json").read_text())
    print(json.dumps({"status": "ok", "version": release["version"], "sourceCommit": release["sourceCommit"], "filesVerified": len(paths)}, ensure_ascii=False))


if __name__ == "__main__":
    verify(ROOT)
