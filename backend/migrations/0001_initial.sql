-- crawlfq 初始 schema（等价 DDL 留档；运行期由 src/config/database.init_db 使用
-- SQLAlchemy metadata.create_all 幂等建表，保证冷启动无需迁移工具）。
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY,
  email VARCHAR(200) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  display_name VARCHAR(120) NOT NULL DEFAULT '',
  role VARCHAR(20) NOT NULL DEFAULT 'viewer',
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  last_login_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS seed_sites (
  id UUID PRIMARY KEY,
  domain VARCHAR(160) NOT NULL UNIQUE,
  name VARCHAR(120) NOT NULL,
  robots_status VARCHAR(16) NOT NULL DEFAULT 'allow',
  robots_rules TEXT NOT NULL DEFAULT '{"disallow": [], "allow": []}',
  crawl_delay_s DOUBLE PRECISION NOT NULL DEFAULT 1.0,
  qps_quota DOUBLE PRECISION NOT NULL DEFAULT 1.0,
  max_concurrency INTEGER NOT NULL DEFAULT 2,
  priority INTEGER NOT NULL DEFAULT 3,
  sitemap_declared INTEGER NOT NULL DEFAULT 0,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  last_audited_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS frontier_urls (
  id UUID PRIMARY KEY,
  site_id UUID NOT NULL REFERENCES seed_sites(id),
  raw_url TEXT NOT NULL UNIQUE,
  canonical_url TEXT NOT NULL,
  fingerprint CHAR(64) NOT NULL,
  source VARCHAR(16) NOT NULL DEFAULT 'sitemap',
  depth INTEGER NOT NULL DEFAULT 0,
  priority_score DOUBLE PRECISION NOT NULL DEFAULT 0,
  status VARCHAR(16) NOT NULL DEFAULT 'queued',
  wait_seconds DOUBLE PRECISION NOT NULL DEFAULT 0,
  is_duplicate BOOLEAN NOT NULL DEFAULT FALSE,
  folded_into_id UUID,
  change_reasons TEXT NOT NULL DEFAULT '[]',
  discovered_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_frontier_urls_fingerprint ON frontier_urls(fingerprint);
CREATE INDEX IF NOT EXISTS ix_frontier_urls_status ON frontier_urls(status);

CREATE TABLE IF NOT EXISTS crawl_tasks (
  id UUID PRIMARY KEY,
  name VARCHAR(160) NOT NULL UNIQUE,
  site_ids TEXT NOT NULL DEFAULT '[]',
  concurrency INTEGER NOT NULL DEFAULT 3,
  quota_snapshot TEXT NOT NULL DEFAULT '{}',
  status VARCHAR(16) NOT NULL DEFAULT 'queued',
  seed INTEGER NOT NULL DEFAULT 7,
  window_s DOUBLE PRECISION NOT NULL DEFAULT 20,
  max_sequence INTEGER NOT NULL DEFAULT 40,
  scheduled_count INTEGER NOT NULL DEFAULT 0,
  scheduler_result TEXT,
  created_by VARCHAR(120) NOT NULL DEFAULT '',
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS fetch_records (
  id UUID PRIMARY KEY,
  task_id UUID,
  url_id UUID,
  domain VARCHAR(160) NOT NULL,
  status_code INTEGER NOT NULL,
  latency_ms INTEGER NOT NULL DEFAULT 0,
  bytes INTEGER NOT NULL DEFAULT 0,
  was_duplicate BOOLEAN NOT NULL DEFAULT FALSE,
  rate_limited BOOLEAN NOT NULL DEFAULT FALSE,
  backoff_applied_s DOUBLE PRECISION NOT NULL DEFAULT 0,
  origin VARCHAR(16) NOT NULL DEFAULT 'seed',
  fetched_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_fetch_records_domain ON fetch_records(domain);
CREATE INDEX IF NOT EXISTS ix_fetch_records_fetched_at ON fetch_records(fetched_at);

CREATE TABLE IF NOT EXISTS coverage_audits (
  id UUID PRIMARY KEY,
  site_id UUID NOT NULL REFERENCES seed_sites(id),
  site_domain VARCHAR(160) NOT NULL,
  batch_label VARCHAR(64) NOT NULL,
  sitemap_declared INTEGER NOT NULL,
  discovered INTEGER NOT NULL,
  fetched INTEGER NOT NULL,
  coverage_ratio DOUBLE PRECISION NOT NULL,
  gap_count INTEGER NOT NULL,
  gaps TEXT NOT NULL DEFAULT '[]',
  created_at TIMESTAMPTZ NOT NULL,
  UNIQUE (site_domain, batch_label)
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id UUID PRIMARY KEY,
  action VARCHAR(64) NOT NULL,
  entity_type VARCHAR(64) NOT NULL,
  entity_id VARCHAR(80) NOT NULL DEFAULT '',
  actor_email VARCHAR(200) NOT NULL DEFAULT '',
  actor_role VARCHAR(20) NOT NULL DEFAULT '',
  payload TEXT NOT NULL DEFAULT '{}',
  ip VARCHAR(64) NOT NULL DEFAULT '',
  trace_id VARCHAR(64) NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL
);
