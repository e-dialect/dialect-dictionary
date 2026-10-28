"""Public deployment configuration. Software and content grants remain separate."""

import json
from pathlib import Path
from urllib.parse import urlparse

FIELDS = {
    "name",
    "shortName",
    "dialect",
    "logo",
    "apiBase",
    "webUrl",
    "mobileUrl",
    "contentSource",
    "features",
}
OPTIONAL_FIELDS = {"phonologyAudioBase", "feedback"}


def load_config(path):
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(config, dict) or set(config) - FIELDS - OPTIONAL_FIELDS:
        raise ValueError("site configuration accepts public fields only")
    for field in FIELDS:
        if field not in config:
            raise ValueError("missing site field: " + field)
    for field in ("name", "shortName", "logo", "apiBase", "webUrl", "mobileUrl"):
        if not isinstance(config[field], str) or not config[field].strip():
            raise ValueError("site field must be nonempty text: " + field)
    for field in ("webUrl", "mobileUrl"):
        parsed = urlparse(config[field])
        if (
            parsed.scheme not in ("http", "https")
            or not parsed.hostname
            or parsed.username
            or parsed.password
        ):
            raise ValueError(
                "site URL must be an HTTP(S) origin/path without credentials"
            )
    if not isinstance(config["dialect"], dict) or set(config["dialect"]) != {
        "name",
        "code",
    }:
        raise ValueError("dialect requires name and code")
    if not all(
        isinstance(value, str) and value.strip() for value in config["dialect"].values()
    ):
        raise ValueError("dialect name and code must be nonempty")
    if not isinstance(config["features"], dict) or not all(
        isinstance(value, bool) for value in config["features"].values()
    ):
        raise ValueError("features must be boolean flags")
    if not isinstance(config["contentSource"], dict) or set(
        config["contentSource"]
    ) != {"name", "url", "notice"}:
        raise ValueError("contentSource requires name, url and notice")
    if not all(isinstance(value, str) for value in config["contentSource"].values()):
        raise ValueError("contentSource must contain public text only")
    if "phonologyAudioBase" in config and not isinstance(
        config["phonologyAudioBase"], str
    ):
        raise ValueError("phonologyAudioBase must be public text")
    feedback = config.get("feedback")
    if feedback is not None:
        if not isinstance(feedback, dict) or set(feedback) - {
            "webUrl",
            "miniProgramAppId",
            "productId",
        }:
            raise ValueError("feedback accepts public routing fields only")
        if not all(isinstance(value, str) for value in feedback.values()):
            raise ValueError("feedback fields must be text")
    return config
