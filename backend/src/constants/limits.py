"""算法与调度常量（口径见 README §算法）。"""

# 算法 A：布隆过滤器（2^20 位 = 128KiB，k=5，blake2b 派生双哈希）
BLOOM_BITS = 1 << 20
BLOOM_K = 5

# 算法 B：令牌桶 + aging + 429 退避
BACKOFF_BASE_S = 5.0
BACKOFF_CAP_S = 300.0
BACKOFF_DECAY_AFTER_SUCCESS = 5
AGING_PER_MINUTE = 0.5
AGING_CAP = 2.0
DEPTH_PENALTY = 0.2
STARVATION_BOOST = 3.0
STARVATION_CHECK_EVERY = 10
TOKEN_BUCKET_CAPACITY_FACTOR = 3.0
TOKEN_BUCKET_MIN_CAPACITY = 2.0
RATE_LIMIT_WRITE_PER_MINUTE = 240
DEFAULT_SIM_WINDOW_S = 20.0
DEFAULT_SIM_MAX_SEQUENCE = 40
DEFAULT_SIM_SEED = 7

# 429 混沌注入脚本（确定性，无随机）：序列第 N 次调度强制探测该域
CHAOS_PROBES: tuple[dict, ...] = (
    {"seq": 4, "domain": "www.36kr.com", "remark": "站方返回 429（确定性探测）"},
    {"seq": 12, "domain": "finance.sina.com.cn", "remark": "第二域 429，退避窗口独立计算"},
)

# 覆盖度审计口径：coverage_ratio = fetched / sitemap_declared（四舍五入 4 位）
COVERAGE_SCALE = 4
