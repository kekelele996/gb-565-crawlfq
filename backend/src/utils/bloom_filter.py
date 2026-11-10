"""算法 A 组件：确定性布隆过滤器（2^20 位，k=5，blake2b 派生双哈希）。

- 位数组用 bytearray 存 m 位；不依赖 third-party。
- 两条 64bit blake2b 摘要派生 k 个位置：h_i = (h1 + i*h2) mod m。
- 误判率估计：p ≈ (1 - e^(-kn/m))^k（n=插入量，m=位数，k=哈希函数数）。
- 可复现：同一 URL 集合插入顺序固定 → 位图与统计完全一致。
"""
from __future__ import annotations

import hashlib
import math


class BloomFilter:
    def __init__(self, bits: int = 1 << 20, k: int = 5, key: bytes = b"crawlfq-bloom-v1") -> None:
        if bits <= 0 or k <= 0:
            raise ValueError("bits/k must be positive")
        self.bits = int(bits)
        self.k = int(k)
        self._key = key
        self._bytes = bytearray((self.bits + 7) // 8)
        self.inserted = 0
        self.hits = 0

    # ---- 哈希 ----
    def _digest(self, item: str) -> tuple[int, int]:
        raw = hashlib.blake2b(item.encode("utf-8"), digest_size=16, key=self._key).digest()
        h1 = int.from_bytes(raw[:8], "big")
        h2 = int.from_bytes(raw[8:], "big") | 1
        return h1, h2

    def _positions(self, item: str) -> list[int]:
        h1, h2 = self._digest(item)
        return [(h1 + i * h2) % self.bits for i in range(self.k)]

    # ---- 位操作 ----
    def _set(self, pos: int) -> None:
        self._bytes[pos >> 3] |= 1 << (pos & 7)

    def _get(self, pos: int) -> bool:
        return bool(self._bytes[pos >> 3] & (1 << (pos & 7)))

    def add(self, item: str) -> None:
        for pos in self._positions(item):
            self._set(pos)
        self.inserted += 1

    def might_contain(self, item: str) -> bool:
        for pos in self._positions(item):
            if not self._get(pos):
                return False
        self.hits += 1
        return True

    def add_if_absent(self, item: str) -> bool:
        """返回 True 表示新条目（未被折叠），False 表示疑似重复。"""
        if self.might_contain(item):
            return False
        self.add(item)
        return True

    # ---- 统计 ----
    @property
    def set_bits(self) -> int:
        return sum(bin(byte).count("1") for byte in self._bytes)

    def estimated_false_positive_rate(self) -> float:
        if self.inserted == 0:
            return 0.0
        return (1.0 - math.exp(-self.k * self.inserted / self.bits)) ** self.k

    def stats(self) -> dict:
        fp = self.estimated_false_positive_rate()
        return {
            "bits": self.bits,
            "k": self.k,
            "inserted": self.inserted,
            "set_bits": self.set_bits,
            "load": round(self.set_bits / self.bits, 6),
            "false_positive_rate": round(fp, 8),
            "false_positive_pct": round(fp * 100, 6),
            "hit_checks": self.hits,
            "algorithm": "blake2b-128 -> double hashing, bit array",
        }
