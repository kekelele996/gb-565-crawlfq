<template>
  <div class="page">
    <PageHeader
      kicker="TOWER / COVERAGE AUDIT"
      title="覆盖度审计与缺口导出"
      sub="覆盖率口径：fetched / sitemap_declared（4 位小数）。缺口 csv 逐行列出未抓 URL 与原因（robots 禁止 / 抓取失败 / 配额耗尽 / sitemap 未发现），两次审计合计 47 行。"
    >
      <template #actions>
        <button class="btn" type="button" :disabled="audits.loading" @click="audits.load()">刷新审计</button>
        <button class="btn btn-primary" type="button" :disabled="audits.exporting" @click="exportAll">
          {{ audits.exporting ? '导出中…' : '导出全部缺口 CSV' }}
        </button>
      </template>
    </PageHeader>

    <div class="metric-row">
      <MetricBlock label="审计批次" :value="audits.summary?.total ?? 0" hint="今日头条 / 澎湃" />
      <MetricBlock label="sitemap 声明" :value="audits.summary?.declared_total ?? 0" hint="120 + 125" />
      <MetricBlock label="已抓合计" :value="audits.summary?.fetched_total ?? 0" hint="88 + 110" />
      <MetricBlock label="缺口合计" :value="audits.summary?.gap_total ?? 0" hint="32 + 15 = 47 行 CSV" />
      <MetricBlock
        label="平均覆盖率"
        :value="formatPercent(audits.summary?.avg_coverage ?? 0)"
        hint="73.33% 与 88.00%"
      />
    </div>

    <div v-if="audits.error" class="banner">{{ audits.error }}</div>
    <div v-if="audits.lastExport" class="banner success">
      CSV 已生成：{{ audits.lastExport.rows }} 行数据（含表头 {{ audits.lastExport.rows + 1 }} 行）· {{ formatTime(audits.lastExport.at) }}
    </div>

    <div class="split">
      <div style="display: grid; gap: 16px">
        <section
          v-for="audit in audits.items"
          :key="audit.id"
          class="panel"
          :style="selectedAudit?.id === audit.id ? 'border-color: var(--lamp-dim)' : ''"
        >
          <div class="panel-head">
            <h2>{{ audit.site_domain }}</h2>
            <span class="aside">{{ audit.batch_label }}</span>
          </div>
          <div class="panel-body" style="display: grid; gap: 10px">
            <div class="gauge-meta">
              <span>覆盖率 {{ formatPercent(audit.coverage_ratio, 2) }}</span>
              <span>{{ audit.fetched }} / {{ audit.sitemap_declared }} · 缺口 {{ audit.gap_count }}</span>
            </div>
            <div class="progress-track">
              <div class="progress-fill" :style="{ transform: `scaleX(${audit.coverage_ratio})` }" />
            </div>
            <div class="gauge-meta">
              <span>已发现 {{ audit.discovered }} 条（≤ 声明数）</span>
              <span>created {{ formatTime(audit.created_at) }}</span>
            </div>
            <div class="head-actions">
              <button class="btn btn-small" type="button" @click="selectedAudit = audit">查看缺口</button>
              <button
                class="btn btn-small"
                type="button"
                :disabled="audits.exporting || !canExport"
                @click="exportOne(audit.id)"
              >
                导出本批 CSV（{{ audit.gap_count }} 行）
              </button>
            </div>
          </div>
        </section>

        <section class="panel">
          <div class="panel-head">
            <h2>RUN AUDIT / 重跑审计</h2>
            <span class="aside">{{ canRun ? 'POST /api/audits/run' : '只读角色 403' }}</span>
          </div>
          <div class="panel-body" style="display: grid; gap: 10px">
            <div class="filter-bar">
              <select v-model="runDomain" class="select">
                <option v-for="site in sites.items" :key="site.id" :value="site.domain">{{ site.name }}</option>
              </select>
              <button class="btn" type="button" :disabled="audits.running || !canRun" @click="runAudit">
                {{ audits.running ? '审计中…' : '按当前抓取状态重算' }}
              </button>
            </div>
            <p class="muted" style="font-size: 10.5px">
              重算规则：declared 取站点 sitemap 声明数，fetched = frontier 中 status=done 的唯一 URL 数，缺口优先填 robots 禁止 / 失败 / 排队 URL，不足补 sitemap 未发现占位条目。
            </p>
          </div>
        </section>
      </div>

      <section class="panel">
        <div class="panel-head">
          <h2>GAPS / 缺口明细</h2>
          <span class="aside">{{ selectedAudit ? `${selectedAudit.site_domain} · 前 ${selectedAudit.gaps?.length ?? 0} 行` : '—' }}</span>
        </div>
        <div v-if="selectedAudit" class="scroll-thin" style="max-height: 560px; overflow: auto">
          <table class="data-table">
            <thead>
              <tr>
                <th>#</th>
                <th>缺口 URL</th>
                <th>原因</th>
                <th class="num">depth</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(gap, index) in selectedAudit.gaps ?? []" :key="`${gap.url}-${index}`">
                <td>{{ index + 1 }}</td>
                <td class="url-cell" :title="gap.url">{{ truncate(gap.url, 70) }}</td>
                <td><StatusTag :value="gap.reason" kind="gap" /></td>
                <td class="num">{{ gap.depth }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="empty">左侧选择一条审计批次查看缺口明细。</div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import PageHeader from '../components/common/PageHeader.vue'
import MetricBlock from '../components/common/MetricBlock.vue'
import StatusTag from '../components/common/StatusTag.vue'
import { useAuditsStore } from '../stores/auditsStore'
import { useSitesStore } from '../stores/sitesStore'
import { useAuthStore } from '../stores/authStore'
import { formatPercent, formatTime, truncate } from '../utils/format'
import type { CoverageAudit } from '../types/audit'
import type { ApiError } from '../types/api'

const audits = useAuditsStore()
const sites = useSitesStore()
const auth = useAuthStore()

const selectedAudit = ref<CoverageAudit | null>(null)
const runDomain = ref('www.toutiao.com')
const canRun = computed(() => auth.can('audits:run'))
const canExport = computed(() => auth.can('audits:export'))

watch(
  () => audits.items,
  (items) => {
    if (!selectedAudit.value && items.length) selectedAudit.value = items[0]
    else if (selectedAudit.value) {
      selectedAudit.value = items.find((item) => item.id === selectedAudit.value?.id) ?? items[0] ?? null
    }
  },
  { immediate: true, deep: false },
)

onMounted(async () => {
  await sites.load()
  await audits.load()
})

async function exportAll() {
  try {
    await audits.exportGaps()
  } catch (error) {
    audits.error = (error as ApiError).message ?? '导出失败'
  }
}

async function exportOne(auditId: string) {
  try {
    await audits.exportGaps(auditId)
  } catch (error) {
    audits.error = (error as ApiError).message ?? '导出失败'
  }
}

async function runAudit() {
  try {
    await audits.run(runDomain.value)
    await audits.load()
  } catch (error) {
    audits.error = (error as ApiError).message ?? '审计失败'
  }
}
</script>
