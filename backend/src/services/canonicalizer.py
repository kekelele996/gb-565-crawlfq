"""算法 A：URL 规范化 + sha256 去重指纹（输入 → 输出口径见 README §算法 A）。

规则（按顺序执行，每条变更记入 change_reasons）：
1. 去首尾空白；缺 scheme 补 https
2. scheme / host 小写；去掉默认端口 80/443
3. 去掉 fragment
4. path percent-decoding 归一后重新编码
5. path 连续斜杠折叠为单斜杠
6. 结尾 /index.html、/index.htm 归一到目录 /（站点根）
7. 非根路径去尾斜杠（根保留 /）
8. query 参数剔除跟踪参数（utm_* / spm / from / ref / sessionid / phpsessid）
9. query 参数按 (key, value) 字典序排序后重新编码

输出：canonical_url、sha256 指纹、变更原因列表、字符节省数。
失败态：空 URL / 解析异常 → CanonicalError（调用方返回 422）。
"""
from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlparse

TRACKING_PARAMS = {"spm", "from", "ref", "sessionid", "phpsessid", "share_token", "wxshare"}
TRACKING_PREFIXES = ("utm_",)
DEFAULT_PORTS = {"http": 80, "https": 443}
PATH_SAFE = "/:@!$&'()*+,;=-._~"


class CanonicalError(ValueError):
    pass


def _strip_tracking(query: str) -> tuple[list[tuple[str, str]], list[str]]:
    kept: list[tuple[str, str]] = []
    removed: list[str] = []
    for key, value in parse_qsl(query, keep_blank_values=True):
        lowered = key.lower()
        if lowered in TRACKING_PARAMS or lowered.startswith(TRACKING_PREFIXES):
            removed.append(key)
        else:
            kept.append((key, value))
    return kept, removed


def canonicalize(raw_url: str) -> dict:
    raw = (raw_url or "").strip()
    if not raw:
        raise CanonicalError("empty url")
    if len(raw) > 2048:
        raise CanonicalError("url too long (>2048)")

    reasons: list[str] = []
    candidate = raw
    if "://" not in candidate:
        candidate = "https://" + candidate
        reasons.append("scheme_defaulted")

    parsed = urlparse(candidate)
    if parsed.scheme not in ("http", "https"):
        raise CanonicalError(f"unsupported scheme: {parsed.scheme}")
    host = (parsed.hostname or "").lower()
    if not host:
        raise CanonicalError("missing host")

    scheme = parsed.scheme.lower()
    if scheme != parsed.scheme:
        reasons.append("lowercase_scheme")
    if host != (parsed.hostname or ""):
        reasons.append("lowercase_host")

    retyped_host = parsed.hostname or ""
    try:
        port = parsed.port
    except ValueError as exc:
        raise CanonicalError(f"invalid port: {exc}") from exc
    if port is not None and port != DEFAULT_PORTS.get(scheme):
        netloc = f"{host}:{port}"
    else:
        netloc = host
        if port is not None and port == DEFAULT_PORTS.get(scheme):
            reasons.append("default_port_removed")

    if parsed.fragment:
        reasons.append("fragment_removed")

    path = parsed.path or "/"
    decoded = unquote(path)
    requoted = quote(decoded, safe=PATH_SAFE + "%")
    if requoted != path:
        path = requoted
        reasons.append("percent_normalized")

    collapsed = re.sub(r"/{2,}", "/", path)
    if collapsed != path:
        path = collapsed
        reasons.append("duplicate_slash_removed")

    lowered_path = path
    for suffix in ("/index.html", "/index.htm", "/index.php"):
        if lowered_path.endswith(suffix):
            lowered_path = lowered_path[: -len(suffix)] or "/"
            reasons.append("index_page_to_root")
            break
    path = lowered_path or "/"

    if path != "/" and path.endswith("/"):
        path = path.rstrip("/") or "/"
        reasons.append("trailing_slash_removed")

    kept, removed = _strip_tracking(parsed.query)
    if removed:
        reasons.append("tracking_param_removed:" + ",".join(sorted(set(removed))))

    kept_norm = [(key, value) for key, value in kept]
    sorted_query = sorted(kept_norm, key=lambda pair: (pair[0], pair[1]))
    if sorted_query != kept_norm:
        reasons.append("query_sorted")
    query = urlencode(sorted_query, doseq=False, quote_via=quote)

    canonical_url = f"{scheme}://{netloc}{path}"
    if query:
        canonical_url += f"?{query}"

    if canonical_url != raw:
        # canonical_diff 是兜底原因，避免出现“有变化但没归因”的情况
        if not reasons:
            reasons.append("canonical_diff")
    fingerprint = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()

    return {
        "raw_url": raw,
        "canonical_url": canonical_url,
        "fingerprint": fingerprint,
        "change_reasons": reasons,
        "changed": canonical_url != raw,
        "char_saved": max(0, len(raw) - len(canonical_url)),
        "scheme": scheme,
        "host": netloc,
        "path": path,
        "query": query,
    }


def fold_urls(rows: list[dict]) -> dict:
    """对一批 {raw_url, site_id} 做规范化 + 指纹折叠统计。

    返回：items（含 canonical/fingerprint/reasons/is_duplicate/folded_index）、
    stats（raw / unique / folded / reason_histogram）。
    同指纹首次出现为主行，后续为重复变体。
    """
    first_seen: dict[str, int] = {}
    items: list[dict] = []
    reason_histogram: dict[str, int] = {}
    for index, row in enumerate(rows):
        result = canonicalize(row["raw_url"])
        fingerprint = result["fingerprint"]
        duplicate = fingerprint in first_seen
        for reason in result["change_reasons"]:
            reason_histogram[reason] = reason_histogram.get(reason, 0) + 1
        items.append(
            {
                "index": index,
                "site_id": row.get("site_id"),
                "raw_url": result["raw_url"],
                "canonical_url": result["canonical_url"],
                "fingerprint": fingerprint,
                "change_reasons": result["change_reasons"],
                "is_duplicate": duplicate,
                "folded_index": first_seen.get(fingerprint),
            }
        )
        if not duplicate:
            first_seen[fingerprint] = index
    unique = len(first_seen)
    return {
        "items": items,
        "stats": {
            "raw": len(rows),
            "unique": unique,
            "folded": len(rows) - unique,
            "reason_histogram": dict(sorted(reason_histogram.items(), key=lambda kv: (-kv[1], kv[0]))),
        },
    }
