"""算法 B：域配额令牌桶调度模拟器（虚拟时钟，不真发网络请求）。

输入：排队中的前沿 URL（已去重）+ 每域配置（qps / crawl-delay / 并发 / 优先级 /
robots 规则）+ 令牌桶初始状态 + 确定性混沌注入脚本（2 次 429 探测）。

出队分数：score = priority + min(2.0, wait_seconds/60*0.5) - 0.2*depth
          （饥饿提升时额外 +3.0）
令牌桶：capacity = max(2, qps*3)，按虚拟时钟 refill；token>=1 才可出队；
        并发上限用 inflight 完成时刻控制；robots 禁止路径直接 blocked 记账不抓。
429/503：该域退避窗口 base 5s 起翻倍（上限 300s），连续成功 5 次后衰减减半。
输出：调度序列（前 N）、每域实际 qps / 令牌余量 / 信号灯、限速事件、
      饥饿提升记录、被阻塞 URL、确定性摘要（同 seed 可复现）。
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime

from src.constants.enums import SignalLevel
from src.constants.limits import (
    AGING_CAP,
    AGING_PER_MINUTE,
    BACKOFF_BASE_S,
    BACKOFF_CAP_S,
    BACKOFF_DECAY_AFTER_SUCCESS,
    CHAOS_PROBES,
    DEPTH_PENALTY,
    STARVATION_BOOST,
    STARVATION_CHECK_EVERY,
    TOKEN_BUCKET_CAPACITY_FACTOR,
    TOKEN_BUCKET_MIN_CAPACITY,
)
from src.utils.robots import robots_blocks_url
from src.utils.timeutil import to_iso, utcnow

DT = 0.1


@dataclass(frozen=True)
class SiteConfig:
    domain: str
    name: str
    qps_quota: float
    crawl_delay_s: float
    max_concurrency: int
    priority: int
    robots_status: str = "allow"
    robots_rules: str = '{"disallow": [], "allow": []}'
    enabled: bool = True


@dataclass
class UrlItem:
    url_id: str
    domain: str
    raw_url: str
    canonical_url: str
    depth: int = 0
    priority_score: float = 0.0
    wait_seconds: float = 0.0


@dataclass
class DomainState:
    config: SiteConfig
    tokens: float
    capacity: float
    rate: float
    inflight: list[float] = field(default_factory=list)
    issued: int = 0
    succeeded: int = 0
    rate_limited: int = 0
    consecutive_429: int = 0
    success_streak: int = 0
    backoff_window_s: float = 0.0
    backoff_until: float = 0.0

    @property
    def domain(self) -> str:
        return self.config.domain


class DomainTokenBucket:
    """令牌桶（虚拟时钟）：capacity = max(2, qps*3)，每秒补 qps 个令牌。"""

    @staticmethod
    def build(site: SiteConfig) -> DomainState:
        qps = max(0.1, float(site.qps_quota))
        capacity = max(TOKEN_BUCKET_MIN_CAPACITY, round(qps * TOKEN_BUCKET_CAPACITY_FACTOR, 2))
        # 令牌桶预充满（burst = capacity），窗口开头允许一次小突发；
        # 因此短窗口（20s）的 issued/elapsed 会略高于 qps 配额，属令牌桶正常 burst 语义。
        return DomainState(config=site, tokens=capacity, capacity=capacity, rate=qps)

    @staticmethod
    def refill(state: DomainState, dt: float) -> None:
        state.tokens = min(state.capacity, state.tokens + state.rate * dt)


def _hash_int(*parts: object) -> int:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def _latency_ms(seed: int, url_id: str, t: float) -> int:
    return 80 + _hash_int(seed, url_id, round(t, 2)) % 420


def _score(state: DomainState, url: UrlItem, promoted_id: str | None) -> dict:
    aging = min(AGING_CAP, url.wait_seconds / 60.0 * AGING_PER_MINUTE)
    depth_penalty = -DEPTH_PENALTY * max(0, int(url.depth))
    base = float(url.priority_score) if url.priority_score else float(state.config.priority)
    total = base + aging + depth_penalty
    boosted = url.url_id == promoted_id
    if boosted:
        total += STARVATION_BOOST
    return {
        "priority": round(base, 3),
        "aging": round(aging, 3),
        "depth_penalty": round(depth_penalty, 3),
        "starvation_boost": STARVATION_BOOST if boosted else 0.0,
        "total": round(total, 3),
        "starvation_boosted": boosted,
    }


def _signal(state: DomainState, elapsed: float) -> str:
    """信号灯：红=仍在退避窗口 / 黄=本轮被 429 限速过 / 绿=正常。"""
    if state.backoff_until > elapsed:
        return SignalLevel.RED.value
    if state.rate_limited > 0:
        return SignalLevel.YELLOW.value
    return SignalLevel.GREEN.value


def simulate(
    sites: list[SiteConfig],
    urls: list[UrlItem],
    *,
    task_name: str = "调度模拟",
    window_s: float = 20.0,
    max_sequence: int = 40,
    seed: int = 7,
    chaos_probes: tuple[dict, ...] | None = None,
    now: datetime | None = None,
) -> dict:
    window_s = max(1.0, float(window_s))
    max_sequence = max(1, int(max_sequence))
    probes = tuple(chaos_probes if chaos_probes is not None else CHAOS_PROBES)

    states: dict[str, DomainState] = {}
    for site in sites:
        if site.enabled:
            states[site.domain] = DomainTokenBucket.build(site)

    queues: dict[str, list[UrlItem]] = {domain: [] for domain in states}
    blocked: list[dict] = []
    for url in urls:
        state = states.get(url.domain)
        if state is None:
            continue
        if robots_blocks_url(state.config.robots_status, state.config.robots_rules, url.raw_url):
            blocked.append(
                {
                    "url_id": url.url_id,
                    "domain": url.domain,
                    "raw_url": url.raw_url,
                    "reason": "robots_disallow",
                    "robots_status": state.config.robots_status,
                }
            )
            continue
        queues[url.domain].append(url)
    for domain in queues:
        queues[domain].sort(key=lambda item: (-item.priority_score, item.url_id))

    sequence: list[dict] = []
    backoff_events: list[dict] = []
    backoff_decays: list[dict] = []
    starvation_boosts: list[dict] = []
    promoted_id: str | None = None
    starvation_done = False

    t = 0.0
    while len(sequence) < max_sequence and t < window_s:
        t = round(t + DT, 4)
        for state in states.values():
            DomainTokenBucket.refill(state, DT)
            state.inflight = [done_at for done_at in state.inflight if done_at > t]

        # 1) 确定性混沌注入：第 N 次调度强制探测某域，站方返回 429
        target: UrlItem | None = None
        forced_probe = False
        next_seq = len(sequence) + 1
        for probe in probes:
            if probe.get("seq") != next_seq:
                continue
            state = states.get(str(probe.get("domain")))
            if state is None or not queues.get(state.domain):
                continue
            if state.tokens < 1 or t < state.backoff_until:
                continue
            if len(state.inflight) >= max(1, state.config.max_concurrency):
                continue
            target = queues[state.domain][0]
            forced_probe = True
            break

        # 2) 饥饿提升：每出队 STARVATION_CHECK_EVERY 条检查一次，全程只提升 1 次
        if target is None and not starvation_done and len(sequence) >= STARVATION_CHECK_EVERY:
            if len(sequence) % STARVATION_CHECK_EVERY == 0:
                starved: list[tuple[float, str, UrlItem, dict]] = []
                for domain, queue in queues.items():
                    state = states[domain]
                    if state.issued > 0 or not queue:
                        continue
                    if state.tokens < 1 or t < state.backoff_until:
                        continue
                    if len(state.inflight) >= max(1, state.config.max_concurrency):
                        continue
                    for url in queue:
                        stats = _score(state, url, None)
                        starved.append((url.wait_seconds, domain, url, stats))
                if starved:
                    # 等待最久者优先；同等待时长按域名/URL 字典序，确定性
                    starved.sort(key=lambda row: (-row[0], row[1], row[2].url_id))
                    wait_s, domain, url, stats = starved[0]
                    promoted_id = url.url_id
                    starvation_done = True
                    starvation_boosts.append(
                        {
                            "seq_at": len(sequence) + 1,
                            "domain": domain,
                            "site_name": states[domain].config.name,
                            "url_id": url.url_id,
                            "raw_url": url.raw_url,
                            "wait_seconds": round(wait_s, 1),
                            "score_before": stats["total"],
                            "score_after": round(stats["total"] + STARVATION_BOOST, 3),
                            "virtual_time_s": t,
                            "reason": "域连续 0 次出队，aging 达上限仍排不上，按公平性提升",
                        }
                    )

        # 3) 正常出队：score 最高者，token/退避/并发全部满足才可出队
        target_score: dict | None = None
        if target is None:
            best_key: tuple | None = None
            for domain, queue in queues.items():
                state = states[domain]
                if not queue or state.tokens < 1 or t < state.backoff_until:
                    continue
                if len(state.inflight) >= max(1, state.config.max_concurrency):
                    continue
                for url in queue:
                    stats = _score(state, url, promoted_id)
                    key = (-stats["total"], domain, url.url_id)
                    if best_key is None or key < best_key:
                        best_key = key
                        target = url
                        target_score = stats
            if target is None:
                continue
        else:
            target_score = _score(states[target.domain], target, promoted_id)

        state = states[target.domain]
        assert target_score is not None
        token_before = round(state.tokens, 2)
        state.tokens = max(0.0, state.tokens - 1.0)
        state.issued += 1
        latency = _latency_ms(seed, target.url_id, t)
        state.inflight.append(round(t + latency / 1000.0, 3))

        status_code = 200
        rate_limited = False
        backoff_applied = 0.0
        challenge = _hash_int(seed, target.url_id, "challenge")
        if forced_probe:
            status_code = 429
            rate_limited = True
        elif challenge % 23 == 0:
            status_code = 304

        # 出队：命中则从队列移除（429 会重新入队）
        if target in queues[target.domain]:
            queues[target.domain].remove(target)

        if rate_limited:
            state.rate_limited += 1
            state.consecutive_429 += 1
            window = min(BACKOFF_CAP_S, BACKOFF_BASE_S * (2 ** (state.consecutive_429 - 1)))
            state.backoff_window_s = window
            state.backoff_until = round(t + window, 3)
            backoff_applied = window
            # 429 后重新入队，等待时间 + 退避窗口（aging 继续累积）
            target.wait_seconds = round(target.wait_seconds + window, 1)
            queues[target.domain].append(target)
            queues[target.domain].sort(key=lambda item: (-item.priority_score, item.url_id))
            backoff_events.append(
                {
                    "seq": len(sequence) + 1,
                    "domain": target.domain,
                    "site_name": state.config.name,
                    "url_id": target.url_id,
                    "raw_url": target.raw_url,
                    "status_code": 429,
                    "window_before_s": round(state.backoff_window_s / 2, 2) if state.consecutive_429 > 1 else 0.0,
                    "window_after_s": window,
                    "backoff_until_s": state.backoff_until,
                    "consecutive_429": state.consecutive_429,
                    "virtual_time_s": t,
                }
            )
        else:
            state.succeeded += 1
            state.success_streak += 1
            if state.success_streak >= BACKOFF_DECAY_AFTER_SUCCESS and state.backoff_window_s > BACKOFF_BASE_S:
                before = state.backoff_window_s
                state.backoff_window_s = max(BACKOFF_BASE_S, round(before / 2, 2))
                state.success_streak = 0
                backoff_decays.append(
                    {
                        "seq": len(sequence) + 1,
                        "domain": target.domain,
                        "window_before_s": before,
                        "window_after_s": state.backoff_window_s,
                        "virtual_time_s": t,
                    }
                )

        sequence.append(
            {
                "seq": len(sequence) + 1,
                "url_id": target.url_id,
                "domain": target.domain,
                "site_name": state.config.name,
                "raw_url": target.raw_url,
                "canonical_url": target.canonical_url,
                "depth": target.depth,
                "priority": target_score["priority"],
                "wait_seconds": round(target.wait_seconds, 1),
                "aging": target_score["aging"],
                "depth_penalty": target_score["depth_penalty"],
                "score": target_score["total"],
                "starvation_boosted": target_score["starvation_boosted"],
                "forced_probe": forced_probe,
                "status_code": status_code,
                "rate_limited": rate_limited,
                "backoff_applied_s": round(backoff_applied, 2),
                "latency_ms": latency,
                "token_before": token_before,
                "token_after": round(state.tokens, 2),
                "virtual_time_s": t,
            }
        )

    succeeded = sum(1 for item in sequence if not item["rate_limited"])
    elapsed = round(max(t, 0.1), 2)
    domain_stats: list[dict] = []
    for domain, state in states.items():
        domain_stats.append(
            {
                "domain": domain,
                "site_name": state.config.name,
                "qps_quota": state.config.qps_quota,
                "crawl_delay_s": state.config.crawl_delay_s,
                "max_concurrency": state.config.max_concurrency,
                "priority": state.config.priority,
                "capacity": state.capacity,
                "tokens_remaining": round(state.tokens, 2),
                "token_ratio": round(state.tokens / state.capacity, 4) if state.capacity else 0.0,
                "issued": state.issued,
                "succeeded": state.succeeded,
                "rate_limited": state.rate_limited,
                "effective_qps": round(state.issued / elapsed, 2) if elapsed else 0.0,
                "backoff_window_s": state.backoff_window_s,
                "backoff_until_s": state.backoff_until,
                "signal": _signal(state, elapsed),
            }
        )
    domain_stats.sort(key=lambda row: (-row["qps_quota"], row["domain"]))

    digest_source = [
        [item["seq"], item["url_id"], item["status_code"], item["virtual_time_s"]] for item in sequence
    ]
    digest = hashlib.sha256(
        json.dumps(digest_source, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()

    return {
        "task_name": task_name,
        "seed": seed,
        "window_s": window_s,
        "max_sequence": max_sequence,
        "sequence_length": len(sequence),
        "issued": len(sequence),
        "succeeded": succeeded,
        "rate_limited_count": sum(1 for item in sequence if item["rate_limited"]),
        "elapsed_s": elapsed,
        "sequence": sequence,
        "backoff_events": backoff_events,
        "backoff_decays": backoff_decays,
        "starvation_boosts": starvation_boosts,
        "blocked_count": len(blocked),
        "blocked": blocked[:20],
        "domain_stats": domain_stats,
        "chaos_plan": list(probes),
        "formula": "score = priority + min(2.0, wait_s/60*0.5) - 0.2*depth（饥饿提升 +3.0）；"
        "token 桶 capacity=max(2, qps*3)，token>=1 才出队；429 退避 base5s 翻倍上限 300s",
        "digest": digest,
        "generated_at": to_iso(now or utcnow()),
    }
