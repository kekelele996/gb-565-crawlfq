"""robots 规则解析与路径判定（seed 预存文本，不真抓 robots.txt）。"""
from __future__ import annotations

import json
from urllib.parse import urlparse


def parse_rules(raw: str | None) -> dict:
    if not raw:
        return {"disallow": [], "allow": []}
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return {"disallow": [], "allow": []}
    if not isinstance(data, dict):
        return {"disallow": [], "allow": []}
    return {
        "disallow": [str(item) for item in data.get("disallow", []) if str(item).strip()],
        "allow": [str(item) for item in data.get("allow", []) if str(item).strip()],
    }


def path_blocked(rules: dict, path: str) -> bool:
    """最长匹配优先：allow 命中长度 >= disallow 命中长度则放行。"""
    best_allow = -1
    best_disallow = -1
    for pattern in rules.get("allow", []):
        if pattern and path.startswith(pattern):
            best_allow = max(best_allow, len(pattern))
    for pattern in rules.get("disallow", []):
        if pattern and path.startswith(pattern):
            best_disallow = max(best_disallow, len(pattern))
    return best_disallow > best_allow


def robots_blocks_url(robots_status: str, robots_rules: str | None, url: str) -> bool:
    if robots_status == "blocked":
        return True
    if robots_status != "partial":
        return False
    try:
        path = urlparse(url).path or "/"
    except ValueError:
        return False
    return path_blocked(parse_rules(robots_rules), path)
