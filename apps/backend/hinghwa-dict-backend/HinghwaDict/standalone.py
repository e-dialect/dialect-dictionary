"""Independent dictionary deployment; retains the upstream application/model API."""

import os
import re
from pathlib import Path
from urllib.parse import urlparse

from .settings import *  # noqa: F401,F403
from .site_config import load_config

# Local HTTP never trusts caller-controlled scheme headers. Traefik mode is
# safe only with the overlay and the nginx template that overwrites this header.
PROXY_MODE = os.environ.get("PROXY_MODE", "local")
if PROXY_MODE not in {"local", "traefik"}:
    raise ValueError("PROXY_MODE must be local or traefik")
SECURE_PROXY_SSL_HEADER = (
    ("HTTP_X_FORWARDED_PROTO", "https") if PROXY_MODE == "traefik" else None
)
SESSION_COOKIE_SECURE = PROXY_MODE == "traefik"
CSRF_COOKIE_SECURE = PROXY_MODE == "traefik"
USE_X_FORWARDED_HOST = False

DICTIONARY_CONFIG = os.environ.get("DICTIONARY_CONFIG", "/config/site.json")
SITE_CONFIG = load_config(DICTIONARY_CONFIG)
if PROXY_MODE == "traefik":
    domain = os.environ.get("DOMAIN", "")
    dns_label = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
    if len(domain) > 253 or not re.fullmatch(dns_label + r"(?:\." + dns_label + r")+", domain):
        raise ValueError("DOMAIN must be one lowercase ASCII DNS FQDN")
    origin = "https://" + domain
    if SITE_CONFIG["webUrl"].rstrip("/") != origin:
        raise ValueError("Traefik webUrl must equal https://DOMAIN")
    if SITE_CONFIG["mobileUrl"].rstrip("/") != origin + "/mobile":
        raise ValueError("Traefik mobileUrl must equal https://DOMAIN/mobile")
    if SITE_CONFIG["apiBase"].rstrip("/") not in {"/api", origin + "/api"}:
        raise ValueError("Traefik apiBase must use the same HTTPS domain and /api")
SITE_NAME = SITE_CONFIG["name"]
PUBLIC_WEB_URL = SITE_CONFIG["webUrl"]
PUBLIC_API_BASE = (
    SITE_CONFIG["apiBase"]
    if SITE_CONFIG["apiBase"].startswith(("https://", "http://"))
    else PUBLIC_WEB_URL.rstrip("/") + "/" + SITE_CONFIG["apiBase"].lstrip("/")
)
DEFAULT_AVATAR_URL = (
    SITE_CONFIG["logo"]
    if SITE_CONFIG["logo"].startswith(("https://", "http://"))
    else PUBLIC_WEB_URL.rstrip("/") + "/" + SITE_CONFIG["logo"].lstrip("/")
)
TRUSTED_AVATAR_HOSTS = [urlparse(PUBLIC_WEB_URL).hostname]
DATA_DIR = Path(os.environ.get("DICTIONARY_DATA_DIR", "/data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DEBUG = False
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(DATA_DIR / "dictionary.sqlite3"),
    }
}
ROOT_URLCONF = "HinghwaDict.standalone_urls"
origins = list(
    dict.fromkeys(
        urlparse(SITE_CONFIG[key]).scheme + "://" + urlparse(SITE_CONFIG[key]).netloc
        for key in ("webUrl", "mobileUrl")
    )
)
ALLOWED_HOSTS = list(
    dict.fromkeys(
        ["localhost", "127.0.0.1", "backend"]
        + [urlparse(origin).hostname for origin in origins]
    )
)
CORS_ORIGIN_ALLOW_ALL = False
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = origins
CORS_ORIGIN_WHITELIST = origins
CSRF_TRUSTED_ORIGINS = origins
EMAIL_BACKEND = env.str(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)
DEFAULT_FROM_EMAIL = "dictionary@localhost"
FILE_STORAGE = env.str("FILE_STORAGE", default="local")
COS_PUBLIC_BASE_URL = env.str("COS_PUBLIC_BASE_URL", default="")
ENABLE_BACKGROUND_SCHEDULER = env.bool("ENABLE_BACKGROUND_SCHEDULER", default=False)
SIMPLEUI_LOGO = SITE_CONFIG["logo"]
MEDIA_ROOT = str(DATA_DIR / "media")
STATIC_ROOT = str(DATA_DIR / "static")
SAVED_PINYIN = str(DATA_DIR / "audio")
SEMANTIC_SEARCH_ENABLED = env.bool("SEMANTIC_SEARCH_ENABLED", default=False)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}

# Nginx strips /api before forwarding; reverse URLs retain the external prefix.
FORCE_SCRIPT_NAME = "/api"
STATIC_URL = "/api/static/"
