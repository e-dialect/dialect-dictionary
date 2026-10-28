"""Check the identified restricted files, runtime imports, built output and source archive."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tarfile

ROOT = Path(__file__).resolve().parents[1]
RECORDS = json.loads((ROOT / "docs/attribution/sources/excluded-materials.json").read_text())["files"]
HASHES = {item["sha256"] for item in RECORDS}
PATTERN = re.compile(rb"IatRecorder|transcode\.worker|iat-api\.xfyun\.cn|(?:[/'\"])certificate\.png|(?:[/'\"])rewards\.svg|(?:[/'\"])timg\.gif")


def check_content(name, content):
    if hashlib.sha256(content).hexdigest() in HASHES:
        raise AssertionError("Restricted file bytes: " + name)
    if name.endswith((".js", ".vue", ".html", ".css")) and PATTERN.search(content):
        raise AssertionError("Restricted runtime reference: " + name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--web-dist", action="store_true")
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    for item in RECORDS:
        assert not (ROOT / item["path"]).exists(), item["path"]
    checked = 0
    for path in (ROOT / "apps/web/src").rglob("*"):
        if path.is_file():
            check_content(path.name, path.read_bytes())
            checked += 1
    if args.web_dist:
        directory = ROOT / "apps/web/dist"
        assert (directory / "index.html").is_file(), "Build Web first"
        for path in directory.rglob("*"):
            if path.is_file():
                check_content(path.name, path.read_bytes())
                checked += 1
    members = 0
    if args.archive:
        with tarfile.open(args.archive) as archive:
            for member in archive.getmembers():
                assert member.isfile(), member.name
                relative = member.name.removeprefix("dialect-dictionary/")
                assert relative not in {item["path"] for item in RECORDS}, relative
                content = archive.extractfile(member).read()
                if relative.startswith(("apps/web/src/", "apps/web/public/")):
                    check_content(relative, content)
                assert hashlib.sha256(content).hexdigest() not in HASHES, relative
                members += 1
    print(json.dumps({"identifiedRestrictedPathsAbsent": len(RECORDS), "runtimeFilesChecked": checked, "archiveFilesChecked": members}))


if __name__ == "__main__":
    main()
