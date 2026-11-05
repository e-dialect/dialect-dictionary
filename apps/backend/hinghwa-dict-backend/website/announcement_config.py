"""Bounded, data-only parsing for the existing active-homepage storage."""
import ast
import hashlib
import json

ACTIVE_WEBSITE_ID = 1
MAX_CONFIG_CHARS = 32000


def revision(value):
    return hashlib.sha256(str(value).encode('utf-8')).hexdigest()


def article_ids(value):
    if value in (None, ''):
        return []
    if isinstance(value, str):
        if len(value) > MAX_CONFIG_CHARS:
            raise ValueError('公告配置过长。')
        value = value.strip()
        if not value or value[0] not in '[(' or value[-1] not in '])':
            raise ValueError('公告配置必须是文章编号列表。')
        # Valid IDs never contain brackets. Reject nested structures before
        # invoking either parser, including deeply nested JSON/Python literals.
        if any(c in '[]{}()' for c in value[1:-1]):
            raise ValueError('公告只接受一层文章编号列表，不接受嵌套结构。')
        try:
            value = json.loads(value)
        except (ValueError, TypeError, RecursionError):
            try:
                value = ast.literal_eval(value)
            except (ValueError, SyntaxError, RecursionError) as exc:
                raise ValueError('公告配置必须是文章编号列表。') from exc
    if not isinstance(value, (list, tuple)) or len(value) > 500:
        raise ValueError('公告配置须为不超过500篇文章的列表。')
    result = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, str)):
            raise ValueError('公告编号必须是正整数。')
        if isinstance(item, str) and (not item.isascii() or not item.isdecimal()):
            raise ValueError('公告编号必须是正整数。')
        try:
            number = int(item)
        except ValueError as exc:
            raise ValueError('公告编号过长或无效。') from exc
        if number <= 0 or number > 9223372036854775807:
            raise ValueError('公告编号超出范围。')
        if number not in result:
            result.append(number)
    return result


def payload_ids(raw):
    if len(raw) > MAX_CONFIG_CHARS:
        raise ValueError('公告请求过长。')
    try:
        body = json.loads(raw)
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise ValueError('公告请求必须是有效JSON。') from exc
    if not isinstance(body, dict) or not isinstance(body.get('announcements'), list):
        raise ValueError('公告须为文章编号列表。')
    return article_ids(body['announcements'])
