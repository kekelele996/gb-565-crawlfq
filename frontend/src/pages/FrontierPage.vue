<template>
  <div class="page">
    <PageHeader
      kicker="TOWER / URL FRONTIER"
      title="URL 前沿与规范化折叠"
      sub="算法 A：raw URL 先按 9 条规则归一成 canonical，再取 sha256 指纹；同指纹变体折叠为一条主行。布隆过滤器 2^20 位 / k=5（blake2b 双哈希）实时判重并给出误判率估计。"
    >
      <template #actions>
        <button class="btn" type="button" :disabled="frontier.loading" @click="reload">刷新前沿</button>
      </template>
    </PageHeader>

    <div class="metric-row">
      <MetricBlock label="raw URL" :value="frontier.stats?.raw ?? 0" hint="原始条目（含重复变体）" />
      <MetricBlock label="唯一 canonical" :value="frontier.stats?.unique ?? 0" hint="sha256 指纹去重后" />
      <MetricBlock label="折叠重复" :value="frontier.stats?.folded ?? 0" hint="40 个重复变体（12.9%）" />
      <MetricBlock
        label="布隆误判率"
        :value="frontier.stats?.bloom.false_positive_pct ?? 0"
        unit="%"
        :hint="`m=${frontier.stats?.bloom.bits ?? 0} k=${frontier.stats?.bloom.k ?? 0}`"
      />
      <MetricBlock label="排队 / 已抓" :value="`${frontier.stats?.status_counts.queued ?? 0} / ${frontier.stats?.status_counts.done ?? 0}`" hint="queued / done" />
    </div>

    <div class="panel">
      <div class="panel-head">
        <h2>FILTER / 前沿筛选</h2>
        <span class="aside">共 {{ frontier.total }} 条 · 第 {{ frontier.page }} 页</span>
      </div>
      <div class="panel-body filter-bar">
        <select v-model="filters.state.domain" class="select" @change="filters.apply()">
          <option value="">全部域</option>
          <option v-for="row in frontier.stats?.by_domain ?? []" :key="row.domain" :value="row.domain">
            {{ row.name }} ({{ row.raw }})
          </option>
        </select>
        <select v-model="filters.state.status" class="select" @change="filters.apply()">
          <option value="">全部状态</option>
          <option value="queued">queued</option>
          <option value="done">done</option>
          <option value="blocked">blocked</option>
          <option value="folded">folded</option>
        </select>
        <select v-model="filters.state.duplicate" class="select" @change="filters.apply()">
          <option value="">全部条目</option>
          <option value="exclude">仅主行</option>
          <option value="only">仅折叠重复</option>
        </select>
        <input v-model="filters.state.q" class="input" placeholder="按 raw URL 搜索…" @keyup.enter="filters.apply()" />
        <button class="btn" type="button" @click="filters.apply()">筛选</button>
        <button class="btn" type="button" @click="filters.reset()">重置</button>
        <span class="tag muted">命中 {{ filters.activeCount.value }} 个条件</span>
      </div>
    </div>

    <div class="split">
      <section class="panel">
        <div class="panel-head">
          <h2>FRONTIER QUEUE / 前沿条目</h2>
          <span class="aside">{{ frontier.loading ? '加载中…' : '点击行查看规范化对比' }}</span>
        </div>
        <div v-if="frontier.error" class="banner" style="margin: 10px">{{ frontier.error }}</div>
        <div class="row-list">
          <button
            v-for="item in frontier.items"
            :key="item.id"
            class="row-item"
            :class="{ 'is-active': item.id === frontier.selected?.id }"
            type="button"
            @click="frontier.select(item.id)"
          >
            <StatusTag :value="item.status" kind="url" />
            <span class="main-line">
              <span class="name">{{ item.domain }} · depth {{ item.depth }}</span>
              <span class="meta" :title="item.raw_url">{{ item.raw_url }}</span>
            </span>
            <span class="tail">
              <template v-if="item.is_duplicate">折叠 → {{ item.fingerprint_short }}</template>
              <template v-else-if="item.change_reasons.length">归一 {{ item.change_reasons.length }} 条</template>
              <template v-else>canonical</template>
              <br />
              <span class="muted">{{ item.change_reasons.slice(0, 1).join('') }}</span>
            </span>
          </button>
          <div v-if="!frontier.items.length" class="empty">当前筛选下没有前沿条目，放宽条件或重置筛选。</div>
        </div>
        <div class="pagination">
          <button class="btn btn-small" type="button" :disabled="frontier.page <= 1" @click="changePage(-1)">上一页</button>
          <span>{{ frontier.page }} / {{ Math.max(1, Math.ceil(frontier.total / frontier.pageSize)) }}</span>
          <button
            class="btn btn-small"
            type="button"
            :disabled="frontier.page * frontier.pageSize >= frontier.total"
            @click="changePage(1)"
          >
            下一页
          </button>
        </div>
      </section>

      <div style="display: grid; gap: 16px">
        <section v-if="frontier.selected" class="panel">
          <div class="panel-head">
            <h2>CANONICAL DIFF / 规范化前后</h2>
            <span class="aside">{{ frontier.selected.domain }}</span>
          </div>
          <div class="panel-body" style="display: grid; gap: 12px">
            <CanonicalDiff
              :raw-url="frontier.selected.raw_url"
              :canonical-url="frontier.selected.canonical_url"
              :reasons="frontier.selected.change_reasons"
              :fingerprint="frontier.selected.fingerprint"
            />
            <dl class="kv">
              <dt>条目状态</dt>
              <dd><StatusTag :value="frontier.selected.status" kind="url" /></dd>
              <dt>发现来源</dt>
              <dd>{{ frontier.selected.source }} · depth {{ frontier.selected.depth }} · 优先级 {{ frontier.selected.priority_score }}</dd>
              <dt>折叠关系</dt>
              <dd>{{ frontier.selected.is_duplicate ? '重复变体，已折叠到主行' : '主行（唯一指纹）' }}</dd>
              <dt>等待 aging</dt>
              <dd>{{ frontier.selected.wait_seconds }} 秒 → aging 得分 {{ Math.min(2, (frontier.selected.wait_seconds / 60) * 0.5).toFixed(2) }}</dd>
              <dt>发现时间</dt>
              <dd>{{ formatTime(frontier.selected.discovered_at) }}</dd>
            </dl>
          </div>
        </section>

        <section class="panel">
          <div class="panel-head">
            <h2>CANONICALIZE / 规范化试算</h2>
            <span class="aside">后端 rules 真算</span>
          </div>
          <div class="panel-body" style="display: grid; gap: 10px">
            <div class="filter-bar">
              <input v-model="probeUrl" class="input" style="flex: 1; min-width: 220px" placeholder="粘贴 URL，如 https://WWW.TOUTIAO.COM:443//article/123/?utm_source=x&b=2&a=1" />
              <button class="btn" type="button" :disabled="previewing" @click="doPreview">试算</button>
            </div>
            <div v-if="frontier.error" class="banner">{{ frontier.error }}</div>
            <CanonicalDiff
              v-if="frontier.preview"
              :raw-url="frontier.preview.raw_url"
              :canonical-url="frontier.preview.canonical_url"
              :reasons="frontier.preview.change_reasons"
              :fingerprint="frontier.preview.fingerprint"
              :char-saved="frontier.preview.char_saved"
            />
            <div v-if="frontier.preview" class="gauge-meta">
              <span>布隆命中：{{ frontier.preview.bloom_hit ? '是（疑似重复）' : '否（新条目）' }}</span>
              <span>已存在：{{ frontier.preview.is_duplicate ? '是' : '否' }}</span>
            </div>
          </div>
        </section>

        <section class="panel">
          <div class="panel-head">
            <h2>SEED EXAMPLES / 3 条真实样例</h2>
            <span class="aside">query 排序 · utm 剔除 · index.html 归一</span>
          </div>
          <div class="panel-body" style="display: grid; gap: 9px">
            <button
              v-for="example in frontier.examples"
              :key="example.id"
              class="row-item"
              type="button"
              style="padding: 8px 0"
              @click="frontier.select(example.id)"
            >
              <span class="nav-index">{{ example.example_kind ?? 'sample' }}</span>
              <span class="main-line">
                <span class="name">{{ example.raw_url }}</span>
                <span class="meta">→ {{ example.canonical_url }}</span>
              </span>
              <span class="tail">{{ example.change_reasons.join(', ') }}</span>
            </button>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import PageHeader from '../components/common/PageHeader.vue'
import MetricBlock from '../components/common/MetricBlock.vue'
import StatusTag from '../components/common/StatusTag.vue'
import CanonicalDiff from '../components/common/CanonicalDiff.vue'
import { useFrontierStore } from '../stores/frontierStore'
import { useTableFilters } from '../hooks/useTableFilters'
import { formatTime } from '../utils/format'
import type { ApiError } from '../types/api'

const frontier = useFrontierStore()
const probeUrl = ref('https://WWW.TOUTIAO.COM:443//article/7300000000000000001/?utm_source=wechat&b=2&a=1#comments')
const previewing = ref(false)

const fields = [
  { key: 'domain', label: '域', options: [] },
  { key: 'status', label: '状态', options: [] },
  { key: 'duplicate', label: '重复', options: [] },
  { key: 'q', label: '搜索', options: [] },
]

const filters = useTableFilters(
  { domain: '', status: '', duplicate: '', q: '' },
  fields,
  () => {
    frontier.filters = {
      domain: filters.state.domain,
      status: filters.state.status,
      duplicate: filters.state.duplicate,
      q: filters.state.q,
    }
    void frontier.load(true)
  },
)

function reload() {
  void frontier.loadStats()
  void frontier.loadExamples()
  void frontier.load()
}

function changePage(delta: number) {
  frontier.page = Math.max(1, frontier.page + delta)
  void frontier.load()
}

async function doPreview() {
  previewing.value = true
  try {
    await frontier.runPreview(probeUrl.value)
  } catch (error) {
    frontier.error = (error as ApiError).message ?? '规范化失败'
  } finally {
    previewing.value = false
  }
}

onMounted(() => {
  void frontier.loadStats()
  void frontier.loadExamples()
  void frontier.load()
})
</script>
