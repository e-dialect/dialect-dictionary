"""Bounded data-only parsing for the existing article-ID storage format."""
import ast
import json


def article_ids(value):
    if value in (None, ''):
        return []
    if isinstance(value, str):
        if len(value) > 32000:
            raise ValueError('公告配置过长。')
        try:
            value = json.loads(value)
        except (ValueError, TypeError):
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
        number = int(item)
        if number <= 0 or number > 9223372036854775807:
            raise ValueError('公告编号超出范围。')
        if number not in result:
            result.append(number)
    return result
