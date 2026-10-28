"""Strict read-only deployment policy. No Django, network, cache or client identity."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

VERSION = 1
CAPABILITY_TTL = 15
FEATURE = "wordApplications"
ROLES = frozenset(("authenticated", "staff", "superuser"))
MAX_POLICY_LIFETIME = timedelta(days=30)


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate policy key")
        result[key] = value
    return result


def _keys(value, expected):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError("unknown or missing policy fields")


def _timestamp(value):
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("UTC timestamp required")
    return datetime.fromisoformat(value[:-1] + "+00:00")


def read_policy(path, now=None):
    """Return an effective allow rule, or None on any invalid/unreadable policy."""
    now = now or datetime.now(timezone.utc)
    try:
        with Path(path).open("rb") as stream:
            raw = stream.read(16385)
        if len(raw) > 16384:
            return None
        data = json.loads(raw, object_pairs_hook=_object)
        _keys(data, ("version", "issuedAt", "expiresAt", "features"))
        if type(data["version"]) is not int or data["version"] != VERSION:
            return None
        issued = _timestamp(data["issuedAt"])
        expires = _timestamp(data["expiresAt"])
        if not issued <= now < expires or not timedelta(0) < expires - issued <= MAX_POLICY_LIFETIME:
            return None
        _keys(data["features"], (FEATURE,))
        rule = data["features"][FEATURE]
        _keys(rule, ("enabled", "roles"))
        if type(rule["enabled"]) is not bool or not isinstance(rule["roles"], list):
            return None
        if any(not isinstance(role, str) or role not in ROLES for role in rule["roles"]):
            return None
        if len(set(rule["roles"])) != len(rule["roles"]):
            return None
        return {"enabled": rule["enabled"], "roles": frozenset(rule["roles"]), "expiresAt": expires}
    except (OSError, ValueError, TypeError, OverflowError, UnicodeError, RecursionError):
        return None


def permits(rule, user):
    if not rule or not rule["enabled"] or not getattr(user, "is_active", False):
        return False
    if not getattr(user, "is_authenticated", False):
        return False
    actual = {"authenticated"}
    if getattr(user, "is_staff", False):
        actual.add("staff")
    if getattr(user, "is_superuser", False):
        actual.add("superuser")
    return bool(actual.intersection(rule["roles"]))


def capabilities(path, now=None):
    now = now or datetime.now(timezone.utc)
    rule = read_policy(path, now)
    # Never advertise beyond policy expiry; re-read on each authorization regardless.
    expires = now + timedelta(seconds=CAPABILITY_TTL)
    if rule and rule["enabled"] and rule["roles"]:
        expires = min(expires, rule["expiresAt"])
        enabled = True
    else:
        enabled = False
    return {
        "version": VERSION,
        "generatedAt": now.isoformat().replace("+00:00", "Z"),
        "expiresAt": expires.isoformat().replace("+00:00", "Z"),
        "ttlSeconds": CAPABILITY_TTL,
        "features": {FEATURE: {"enabled": enabled}},
    }
