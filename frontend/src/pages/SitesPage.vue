<template>
  <div class="page">
    <PageHeader
      kicker="TOWER / SITE REGISTRY"
      title="站点清单与礼貌配额"
      sub="域 = 进近区段。qps / crawl-delay / 并发 / 优先级决定令牌桶补充与出队顺序；robots partial 域的禁止路径直接 blocked 记账，不进入调度。"
    >
      <template #actions>
        <button class="btn" type="button" :disabled="sites.loading" @click="sites.load()">刷新站点</button>
        <span class="tag lamp">5/5 healthy</span>
      </template>
    </PageHeader>

    <div class="metric-row">
      <MetricBlock label="注册站点" :value="sites.items.length" hint="1 个 robots partial" />
      <MetricBlock label="启用配额合计" :value="sites.summary?.total_qps ?? 0" unit="qps" hint="跨域礼貌上限" />
      <MetricBlock label="robots allow" :value="sites.summary?.allow ?? 0" hint="全站允许" />
      <MetricBlock label="robots partial" :value="sites.summary?.partial ?? 0" hint="按路径最长匹配放行" />
    </div>

    <div v-if="sites.error" class="banner">{{ sites.error }}</div>

    <div class="split-narrow">
      <section class="panel">
        <div class="panel-head">
          <h2>进近区段 / DOMAINS</h2>
          <span class="aside">{{ sites.items.length }} 域</span>
        </div>
        <div class="row-list">
          <button
            v-for="site in sites.items"
            :key="site.id"
            class="row-item"
            :class="{ 'is-active': site.id === sites.selected?.id }"
            type="button"
            @click="sites.select(site.id)"
          >
            <span class="lamp" :class="site.enabled ? 'green' : 'red'" />
            <span class="main-line">
              <span class="name">{{ site.name }}</span>
              <span class="meta">{{ site.domain }}</span>
            </span>
            <span class="tail">
              {{ site.qps_quota.toFixed(1) }} qps<br />
              <StatusTag :value="site.robots_status" kind="robots" />
            </span>
          </button>
        </div>
      </section>

      <section v-if="sites.selected" class="panel">
        <div class="panel-head">
          <h2>{{ sites.selected.name }} / {{ sites.selected.domain }}</h2>
          <span class="aside">
            priority P{{ sites.selected.priority }} · sitemap {{ sites.selected.sitemap_declared }} 条
          </span>
        </div>
        <div class="panel-body" style="display: grid; gap: 13px">
          <QuotaGauge
            :domain="sites.selected.domain"
            :site-name="sites.selected.name"
            :qps="sites.selected.qps_quota"
            :tokens="sites.selected.qps_quota * 3"
            :capacity="sites.selected.qps_quota * 3"
            :signal="sites.selected.enabled ? 'green' : 'red'"
            :effective-qps="sites.selected.qps_quota"
            :concurrency="sites.selected.max_concurrency"
          />

          <div v-if="!canEdit" class="banner info">
            当前角色（{{ auth.roleLabel }}）只读：修改配额需调度主管权限，PATCH 会返回 403。下方字段仅供核对。
          </div>

          <div class="form-grid">
            <div class="field">
              <label>qps_quota</label>
              <input v-model.number="form.qps_quota" class="input" type="number" step="0.5" min="0.1" max="20" :disabled="!canEdit" />
            </div>
            <div class="field">
              <label>crawl_delay_s</label>
              <input v-model.number="form.crawl_delay_s" class="input" type="number" step="0.5" min="0" max="60" :disabled="!canEdit" />
            </div>
            <div class="field">
              <label>max_concurrency</label>
              <input v-model.number="form.max_concurrency" class="input" type="number" step="1" min="1" max="16" :disabled="!canEdit" />
            </div>
            <div class="field">
              <label>priority（1-5）</label>
              <input v-model.number="form.priority" class="input" type="number" step="1" min="1" max="5" :disabled="!canEdit" />
            </div>
            <div class="field">
              <label>enabled</label>
              <select v-model="form.enabled" class="select" :disabled="!canEdit">
                <option :value="true">启用</option>
                <option :value="false">停用</option>
              </select>
            </div>
            <div class="field">
              <label>robots_status</label>
              <select v-model="form.robots_status" class="select" :disabled="!canEdit">
                <option value="allow">allow</option>
                <option value="partial">partial</option>
                <option value="blocked">blocked</option>
              </select>
            </div>
          </div>

          <div class="grid-2">
            <div>
              <div class="kicker muted" style="font-size: 10px; letter-spacing: 0.14em">ROBOTS DISALLOW</div>
              <div class="reason-chips" style="margin-top: 6px">
                <span v-for="path in sites.selected.robots_disallow" :key="path" class="chip">{{ path }}</span>
                <span v-if="!sites.selected.robots_disallow.length" class="chip">无</span>
              </div>
            </div>
            <div>
              <div class="kicker muted" style="font-size: 10px; letter-spacing: 0.14em">LAST AUDIT</div>
              <div style="margin-top: 6px">{{ formatTime(sites.selected.last_audited_at) }}</div>
            </div>
          </div>

          <div class="head-actions">
            <button v-if="canEdit" class="btn btn-primary" type="button" :disabled="sites.saving" @click="save">
              {{ sites.saving ? '写入配置…' : '保存配额配置' }}
            </button>
            <span v-if="sites.lastChange" class="tag green">已落库 {{ sites.lastChange.slice(0, 90) }}</span>
          </div>
          <p class="muted" style="font-size: 10.5px">
            修改「今日头条」qps 3 → 1 后回到任务看板重新运行调度模拟，序列长度会变短（令牌预算减少，可复现）。
          </p>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, watch } from 'vue'
import PageHeader from '../components/common/PageHeader.vue'
import MetricBlock from '../components/common/MetricBlock.vue'
import StatusTag from '../components/common/StatusTag.vue'
import QuotaGauge from '../components/common/QuotaGauge.vue'
import { useSitesStore } from '../stores/sitesStore'
import { useAuthStore } from '../stores/authStore'
import { formatTime } from '../utils/format'
import type { ApiError } from '../types/api'
import type { RobotsStatus } from '../constants/enums'

const sites = useSitesStore()
const auth = useAuthStore()
const canEdit = computed(() => auth.can('sites:update'))

const form = reactive({
  qps_quota: 1,
  crawl_delay_s: 1,
  max_concurrency: 1,
  priority: 3,
  enabled: true as boolean,
  robots_status: 'allow' as RobotsStatus,
})

watch(
  () => sites.selected,
  (site) => {
    if (!site) return
    form.qps_quota = site.qps_quota
    form.crawl_delay_s = site.crawl_delay_s
    form.max_concurrency = site.max_concurrency
    form.priority = site.priority
    form.enabled = site.enabled
    form.robots_status = site.robots_status
  },
  { immediate: true },
)

onMounted(() => {
  void sites.load()
})

async function save() {
  if (!sites.selected) return
  try {
    await sites.save(sites.selected.id, {
      qps_quota: form.qps_quota,
      crawl_delay_s: form.crawl_delay_s,
      max_concurrency: form.max_concurrency,
      priority: form.priority,
      enabled: form.enabled,
      robots_status: form.robots_status,
    })
  } catch (error) {
    sites.error = (error as ApiError).message ?? '保存失败'
  }
}
</script>
