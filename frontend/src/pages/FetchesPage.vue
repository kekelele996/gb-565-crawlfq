<template>
  <div class="page">
    <PageHeader
      kicker="TOWER / FETCH TIMELINE"
      title="抓取记录与限速事件时间线"
      sub="抓取记录区分 seed 演示与调度模拟两种来源；429 记录携带实际退避秒数（5s 起翻倍，上限 300s），时间线按抓取时间倒序。"
    >
      <template #actions>
        <button class="btn" type="button" @click="reloadAll">刷新记录</button>
      </template>
    </PageHeader>

    <div class="metric-row">
      <MetricBlock label="抓取记录总数" :value="fetches.summary?.total ?? 0" hint="seed 500 + 模拟 40" />
      <MetricBlock label="429 限速" :value="fetches.summary?.rate_limited ?? 0" hint="退避生效" />
      <MetricBlock label="重复折叠命中" :value="fetches.summary?.duplicates ?? 0" hint="was_duplicate" />
      <MetricBlock label="来源" :value="originLabel" hint="seed / simulation" />
    </div>

    <div class="panel">
      <div class="panel-head">
        <h2>FILTER / 抓取筛选</h2>
        <span class="aside">共 {{ fetches.total }} 条 · 第 {{ fetches.page }} 页</span>
      </div>
      <div class="panel-body filter-bar">
        <select v-model="filters.state.domain" class="select" @change="applyFilters">
          <option value="">全部域</option>
          <option v-for="site in sites.items" :key="site.id" :value="site.domain">{{ site.name }}</option>
        </select>
        <select v-model="filters.state.code" class="select" @change="applyFilters">
          <option value="">全部状态码</option>
          <option value="200">200</option>
          <option value="304">304</option>
          <option value="429">429</option>
          <option value="404">404</option>
          <option value="500">500</option>
        </select>
        <select v-model="filters.state.origin" class="select" @change="applyFilters">
          <option value="">全部来源</option>
          <option value="seed">seed</option>
          <option value="simulation">simulation</option>
        </select>
        <select v-model="filters.state.rateLimited" class="select" @change="applyFilters">
          <option value="">限速不限</option>
          <option value="yes">仅 429</option>
          <option value="no">仅非 429</option>
        </select>
        <button class="btn" type="button" @click="filters.reset()">重置</button>
      </div>
    </div>

    <div class="split">
      <section class="panel">
        <div class="panel-head">
          <h2>FETCH RECORDS / 抓取记录</h2>
          <span class="aside">{{ fetches.loading ? '加载中…' : '429 行高亮' }}</span>
        </div>
        <div v-if="fetches.error" class="banner" style="margin: 10px">{{ fetches.error }}</div>
        <div class="scroll-thin" style="max-height: 520px; overflow: auto">
          <table class="data-table">
            <thead>
              <tr>
                <th>抓取时间</th>
                <th>域</th>
                <th class="num">状态</th>
                <th class="num">延迟</th>
                <th class="num">字节</th>
                <th class="num">退避</th>
                <th>来源</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="record in fetches.items"
                :key="record.id"
                :class="{ 'is-rate-limited': record.rate_limited }"
              >
                <td class="seq-time">{{ formatTime(record.fetched_at) }}</td>
                <td>{{ record.domain }}</td>
                <td class="num">
                  <span :class="record.rate_limited ? 'sig-red' : record.status_code >= 400 ? 'sig-amber' : 'sig-green'">
                    {{ record.status_code }}
                  </span>
                </td>
                <td class="num">{{ record.latency_ms }}ms</td>
                <td class="num">{{ record.bytes }}</td>
                <td class="num">{{ record.backoff_applied_s ? `${record.backoff_applied_s}s` : '—' }}</td>
                <td>
                  <span
                    class="tag"
                    :class="record.origin === 'simulation' ? 'lamp' : 'muted'"
                    :title="record.origin"
                  >{{ record.origin === 'simulation' ? 'sim' : 'seed' }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="pagination">
          <button class="btn btn-small" type="button" :disabled="fetches.page <= 1" @click="changePage(-1)">上一页</button>
          <span>{{ fetches.page }} / {{ Math.max(1, Math.ceil(fetches.total / fetches.pageSize)) }}</span>
          <button
            class="btn btn-small"
            type="button"
            :disabled="fetches.page * fetches.pageSize >= fetches.total"
            @click="changePage(1)"
          >
            下一页
          </button>
        </div>
      </section>

      <div style="display: grid; gap: 16px">
        <section class="panel">
          <div class="panel-head">
            <h2>RATE LIMIT TIMELINE</h2>
            <span class="aside">{{ fetches.timeline?.window }}</span>
          </div>
          <div class="panel-body" style="display: grid; gap: 8px">
            <div
              v-for="event in fetches.timeline?.rate_limited_events ?? []"
              :key="event.id"
              class="gauge backoff"
            >
              <div class="gauge-head">
                <span class="domain">{{ event.domain }}</span>
                <span class="qps sig-red">429</span>
              </div>
              <div class="gauge-meta">
                <span>{{ formatTime(event.fetched_at) }}</span>
                <span>退避 {{ event.backoff_applied_s }}s · 延迟 {{ event.latency_ms }}ms</span>
              </div>
            </div>
            <div v-if="!(fetches.timeline?.rate_limited_events ?? []).length" class="empty">时间线里还没有 429 事件。</div>
          </div>
        </section>

        <section class="panel">
          <div class="panel-head">
            <h2>BACKOFF BY DOMAIN</h2>
            <span class="aside">按限速次数排序</span>
          </div>
          <div class="panel-body" style="display: grid; gap: 8px">
            <div v-for="row in fetches.timeline?.backoff_domains ?? []" :key="row.domain" class="gauge">
              <div class="gauge-head">
                <span class="domain">{{ row.domain }}</span>
                <span class="qps sig-red">{{ row.rate_limited }} 次</span>
              </div>
              <div class="gauge-meta">
                <span>最大退避 {{ row.max_backoff_s }}s</span>
                <span>最近 {{ formatTime(row.last_at) }}</span>
              </div>
            </div>
            <div v-if="!(fetches.timeline?.backoff_domains ?? []).length" class="empty">暂无域名触达限速。</div>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import PageHeader from '../components/common/PageHeader.vue'
import MetricBlock from '../components/common/MetricBlock.vue'
import { useFetchesStore } from '../stores/fetchesStore'
import { useSitesStore } from '../stores/sitesStore'
import { useTableFilters } from '../hooks/useTableFilters'
import { usePolling } from '../hooks/usePolling'
import { formatTime } from '../utils/format'

const fetches = useFetchesStore()
const sites = useSitesStore()

const fields = [
  { key: 'domain', label: '域', options: [] },
  { key: 'code', label: '状态码', options: [] },
  { key: 'origin', label: '来源', options: [] },
  { key: 'rateLimited', label: '限速', options: [] },
]

const filters = useTableFilters({ domain: '', code: '', origin: '', rateLimited: '' }, fields, () =>
  applyFilters(),
)

const originLabel = computed(() => {
  const origins = fetches.summary?.by_origin ?? {}
  return Object.entries(origins)
    .map(([key, value]) => `${key} ${value}`)
    .join(' / ')
})

function applyFilters() {
  fetches.filters = {
    domain: filters.state.domain,
    code: filters.state.code,
    origin: filters.state.origin,
    rateLimited: filters.state.rateLimited,
  }
  void fetches.load(true)
}

function changePage(delta: number) {
  fetches.page = Math.max(1, fetches.page + delta)
  void fetches.load()
}

function reloadAll() {
  void fetches.load()
  void fetches.loadTimeline()
}

onMounted(() => {
  void sites.load()
  void fetches.load()
})

usePolling(async () => {
  await fetches.loadTimeline()
}, 12000)
</script>
