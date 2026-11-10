# crawlfq · 采集前沿调度与礼貌配额管制台

一款面向舆情/市场情报爬虫组的「采集塔台」：把 sitemap 种子 URL 做规范化去重后放进 URL 前沿，
按**域配额令牌桶**（qps / crawl-delay / 并发 / 优先级 / robots 规则）以虚拟时钟调度出队，
遇到 429 做指数退避，最后用**覆盖度审计**把「sitemap 声明 vs 实际已抓」对齐并导出缺口 CSV。

- 模拟客户：**澜舟情报**（舆情/市场情报公司，爬虫组 8 人维护 300 站点）
- 现有工作流：Scrapy 脚本 + 人工 delay；429/502 靠翻日志；sitemap 覆盖率无人计算
- 3 个痛点：① 同 URL 不同 query 顺序重复抓，浪费约 30% 配额；② 无 per-domain 配额，常被站方投诉；③ sitemap 声明 vs 实抓覆盖率不清、缺口无导出
- 上下游：上游=站点 sitemap / 种子 URL → 本系统（规范化去重 + 域配额调度 + 覆盖度审计）→ 下游=抽取管道、站方沟通

## 主要功能

| 页面 | 路由 | 说明 |
|---|---|---|
| 进近管制登录 | `/login` | 三账号登录，JWT + RBAC |
| 站点与配额 | `/sites` | 6 站点 robots/qps/crawl-delay/并发/优先级；管理员可改，只读角色 403 |
| URL 前沿 | `/frontier` | 300 raw → 260 唯一 → 折叠 40；规范化前后对比、布隆过滤器统计、规范化试算 |
| 采集任务 | `/tasks` | 任务列表 + 创建；只读角色创建 403 |
| 调度看板 | `/tasks/:id` | 域令牌桶余量、实发 qps、40 条调度序列、2 次 429 退避、1 次饥饿提升、信号带 |
| 抓取记录 | `/fetches` | 500 条 seed 记录 + 模拟记录；429 退避时间线、按域退避汇总 |
| 覆盖度审计 | `/audits` | 覆盖率 73.33%（88/120）与 88.00%（110/125）、缺口明细、缺口 CSV（合计 47 行） |

## 两个 Python 真算算法

### 算法 A：URL 规范化 + sha256 指纹 + 布隆去重（`backend/src/services/canonicalizer.py`）

- 规则（按序）：`scheme_defaulted` → scheme/host 小写 → 去默认端口 → 去 fragment →
  path percent 归一 → 连续斜杠折叠 → `/index.html|/index.htm|/index.php` 归一到目录 →
  非根路径去尾斜杠 → 剔除跟踪参数（`utm_*` / `spm` / `from` / `ref` / `sessionid` / `phpsessid` / `share_token` / `wxshare`）→
  query 按 (key, value) 字典序排序后重编码
- 输出：`canonical_url`、`fingerprint = sha256(canonical_url)`、`change_reasons[]`、`char_saved`
- 布隆过滤器（`backend/src/utils/bloom_filter.py`）：bit array `m = 2^20`（128 KiB）、`k = 5`，
  blake2b-128 派生双哈希 `h_i = (h1 + i*h2) mod m`；输出折叠统计与误判率估计 `p ≈ (1 - e^(-kn/m))^k`
  （seed 后插入 260 条时 p ≈ 3e-6 %）
- 失败态：空 URL / 超长 / 非法 scheme / 非法端口 → 422；seed 固定、插入顺序固定（canonical 字典序）→ 可复现

### 算法 B：域配额令牌桶调度 + aging 防饥饿 + 429 指数退避（`backend/src/services/scheduler.py`）

- 输入：`status=queued` 且非折叠的前沿 URL + 每域配置 + 令牌桶状态 + 确定性混沌注入脚本
- 出队分：`score = priority + min(2.0, wait_seconds/60*0.5) - 0.2*depth`；饥饿提升时 +3.0
- 令牌桶：`capacity = max(2, qps*3)`，虚拟时钟每 0.1s 按 `qps` 补充；`token >= 1` 才可出队；
  并发用 inflight 完成时刻控制；robots 禁止路径直接 blocked 记账不抓
- 429/503：该域退避窗口 `5s` 起翻倍（上限 300s），连续成功 5 次后减半衰减；429 URL 重新入队并累积 aging
- 饥饿提升：每出队 10 条检查一次「0 次出队的域」，取等待最久 URL 提升 +3.0（每个模拟最多 1 次）
- 混沌注入（确定性，无随机）：序列第 4 / 12 位强制探测 `www.36kr.com`，站方返回 429 → 2 次退避、窗口 5s → 可复现
- 输出：调度序列（≤40 条）、每域实发 qps / 令牌余量 / 信号灯、退避事件、饥饿提升记录、
  robots 阻塞清单、`digest = sha256(sequence)`（同 seed 逐字可复现）
- 失败态：任务站点下无排队 URL → 409；只读角色 → 403

## 快速启动（Docker Compose，5 服务）

```bash
cp .env.example .env
docker compose config --quiet
docker compose up -d --build          # 首次构建约 1.5-3 分钟
docker compose ps                     # 期望 5/5 healthy
# seed 在 backend 启动时自动执行（SEED_DEMO=true），日志里有一行：
# SEED_SUMMARY brand=crawlfq sites=6 urls=300 unique=260 tasks=3 fetches=500 audits=2 users=3
```

访问：

- 前端 <http://localhost:18238>（Nginx 托管 dist，`/api/` 反代到 backend:8000）
- 后端 API <http://localhost:19238/api/health>
- PostgreSQL <localhost:17738>

停止：`docker compose down -v --remove-orphans`

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3.5 + TypeScript 5.6 + Vite 5 + Pinia 2 + Vue Router 4 + Axios（无 UI 框架，自研塔台设计系统） |
| 后端 | Python 3.11 + FastAPI 0.115 + SQLAlchemy 2.0 + Pydantic 2 + PyJWT + PBKDF2 |
| Worker | Celery 5.4 + Redis（心跳任务写 `crawlfq:worker:heartbeat`，healthcheck 兜底 celery ping） |
| 数据库 | PostgreSQL 16（命名卷持久化） |
| 缓存/队列 | Redis 7（写接口限流滑动窗口 + worker 心跳） |
| 反向代理 | Nginx 1.27（`/api/` 反代 + SPA 回落 + `/healthz`） |

## Docker 服务

| 服务 | 端口 | healthcheck |
|---|---|---|
| frontend | `${FRONTEND_PORT:-18238}:80` | `wget --spider http://127.0.0.1/` |
| backend | `${BACKEND_PORT:-19238}:8000` | `curl -fsS http://127.0.0.1:8000/api/health` |
| worker | 无对外端口 | Redis 心跳键 / `celery inspect ping` |
| db | `${DB_PORT:-17738}:5432` | `pg_isready` |
| redis | 内部 6379 | `redis-cli ping` |

命名卷：`db_data` / `redis_data` / `artifacts`。`backend`、`worker` 依赖 `db`/`redis` 的 `service_healthy`；
`frontend` 依赖 `backend` healthy。全部 `container_name: ${COMPOSE_PROJECT_NAME:-crawlfq}-<role>`。

## 目录结构

```
gb-565/
├── docker-compose.yml / .env / .env.example / README.md
├── backend/
│   ├── Dockerfile / requirements.txt / migrations/0001_initial.sql
│   ├── scripts/seed_demo.py          # 幂等 seed + SEED_SUMMARY
│   └── src/{config,constants,models,schemas,services,controllers,routes,middlewares,utils}/ + main.py
├── worker/
│   ├── Dockerfile / healthcheck.sh
│   └── src/{config/celery_app.py,tasks.py}
└── frontend/
    ├── Dockerfile / nginx.conf / vite.config.ts / package.json
    └── src/{api,stores,types,components/common,hooks,pages,router,utils,constants,styles}/
```

后端分层：`routes`（HTTP 声明 + 鉴权依赖）→ `controllers`（薄编排）→ `services`（业务/算法）→
`models`（SQLAlchemy）→ `schemas`（Pydantic 入参）；`middlewares`（trace/审计上下文、写接口限流、RBAC）；
`utils`（JWT/PBKDF2/布隆过滤器/robots/分页/时间）。

## 演示账号（密码统一 `Demo@2026`）

| 账号 | 角色 | 权限 |
|---|---|---|
| `admin@crawlfq.io` | 调度主管 admin | 全部：改站点配额、建任务、跑调度、跑审计、导出缺口、看审计日志 |
| `engineer@crawlfq.io` | 采集工程师 engineer | 读全部 + 建任务 / 跑调度模拟 / 跑审计与导出缺口；**不能**改站点配额（403） |
| `viewer@crawlfq.io` | 只读观察员 viewer | 只读看板/前沿/记录/审计；**创建任务 403**、跑模拟 403、改配额 403、导出缺口 403 |

## 环境变量

见 `.env.example`：`DB_*`、`JWT_SECRET`、`ACCESS_TOKEN_MINUTES`、`FRONTEND_PORT/BACKEND_PORT/DB_PORT`、
`REDIS_URL`、`SEED_DEMO`、`RATE_LIMIT_WRITE_PER_MINUTE`、`BLOOM_BITS=1048576`、`BLOOM_K=5`、
`SIM_WINDOW_S=20`、`SIM_MAX_SEQUENCE=40`、`SIM_SEED=7`、`ARTIFACT_DIR`。

## 共享枚举出现位置（前后端各一份，字面量一致）

| 枚举 | 后端 | 前端 |
|---|---|---|
| `RobotsStatus` / `UrlStatus` / `UrlSource` / `TaskStatus` / `FetchOrigin` / `GapReason` / `SignalLevel` / `UserRole` | `backend/src/constants/enums.py` | `frontend/src/constants/enums.ts` |
| 权限点 `sites:update` / `tasks:create` / `tasks:simulate` / `audits:run` / `audits:export` | `backend/src/constants/roles.py` | `frontend/src/constants/enums.ts`（经 `auth.can()` 使用） |
| 错误码 `CRF-4xxx` | `backend/src/constants/error_codes.py` | `frontend/src/constants/messages.ts` |

## 本地开发（可选）

```bash
# backend
cd backend && python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
DB_HOST=localhost DB_PORT=17738 uvicorn src.main:app --reload --port 8000
# frontend（代理 /api → localhost:19238）
cd frontend && npm install --registry=https://registry.npmjs.org && npm run dev
```

## 设计说明

「机场塔台进近图」视觉方向：深藏蓝夜空 + 荧光黄信号灯 + 信号白；标题 `Oswald` 窄体、
数据 `Space Mono`；左侧站点轨道 + 右侧宽调度区的非对称布局；域 = 进近区段，调度格 = 信号块；
动效为令牌桶条形 `transform` 填充与 backoff 状态一次性脉冲。Google Fonts CDN 不可达时回退系统
sans/monospace（见 TESTING.md 已知差异）。

## License

MIT（演示项目，seed 中的域名/数值均为模拟数据，不发起真实抓取）。
