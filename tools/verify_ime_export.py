#!/usr/bin/env python3
"""Read-only verification of locally exported Pouleng addon archives."""
import importlib.util
from pathlib import Path
import json
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ime_export', ROOT / 'apps/backend/hinghwa-dict-backend/word/ime_export.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
if __name__ == '__main__':
    try:
        if len(sys.argv) != 2: raise ValueError('Usage: python3 tools/verify_ime_export.py exports/file.zip')
        print(json.dumps(module.verify_archive(sys.argv[1]), ensure_ascii=False))
    except Exception as error:
        raise SystemExit('校验失败：' + str(error))
