"""Render the same public JSON for both frontends; contains no private settings."""
import json
import os
from pathlib import Path
from site_config import load_config

config = load_config(os.environ.get("DICTIONARY_CONFIG", "/config/site.json"))
for key in ("name", "shortName", "dialect", "apiBase", "features", "contentSource"):
    if key not in config:
        raise ValueError("missing public site field: " + key)
Path("/tmp/site-config.js").write_text(
    "window.__DICTIONARY_CONFIG__=" + json.dumps(config, ensure_ascii=True).replace("<", "\\u003c") + ";\n"
)
