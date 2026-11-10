<template>
  <div class="page">
    <PageHeader
      kicker="TOWER / APPROACH SEQUENCE"
      title="调度看板 · 令牌桶与退避"
      :sub="task?.name ?? '加载调度结果…'"
    >
      <template #actions>
        <RouterLink class="btn" to="/tasks">← 任务列表</RouterLink>
        <button v-if="canSimulate" class="btn btn-primary" type="button" :disabled="tasks.simulating" @click="rerun">
          {{ tasks.simulating ? '模拟中…' : '运行调度模拟' }}
        </button>
      </template>
    </PageHeader>

    <div v-if="tasks.error" class="banner">{{ tasks.error }}</div>

    <template v-if="result">
      <div class="metric-row">
        <MetricBlock label="调度序列长度" :value="result.sequence_length" hint="上限 40 条（窗口内出队）" />
        <MetricBlock label="429 退避事件" :value="result.rate_limited_count" hint="base 5s 起、上限 300s" />
        <MetricBlock label="饥饿提升" :value="result.starvation_boosts.length" hint="aging 触顶后 +3.0" />
        <MetricBlock label="虚拟耗时" :value="result.elapsed_s" unit="s" hint="虚拟时钟，非真实网络" />
        <MetricBlock label="robots 阻塞" :value="result.blocked_count" hint="禁止路径不计入调度" />
        <MetricBlock label="结果摘要" :value="result.digest.slice(0, 10)" hint="sha256(sequence) 可复现" />
      </div>

      <section class="panel">
        <div class="panel-head">
          <h2>APPROACH STRIP / 进近信号带</h2>
          <span class="aside">每格 = 一次调度（绿=2xx 红=429）· 第 4/12 位为确定性 429 探测</span>
        </div>
        <div class="panel-body" style="display: grid; gap: 10px">
          <div class="approach-strip">
            <span
              v-for="item in result.sequence"
              :key="item.seq"
              class="signal-block"
              :class="item.rate_limited ? 'red' : item.seq === selectedSeq?.seq ? 'amber' : 'green'"
              :title="`#${item.seq} ${item.domain} t=${item.virtual_time_s}s ${item.status_code}`"
            >
              {{ String(item.seq).padStart(2, '0') }}
            </span>
          </div>
          <div class="gauge-meta">
            <span>公式：{{ result.formula }}</span>
            <span>blocked {{ result.blocked_count }} · 折叠变体不参与调度</span>
          </div>
        </div>
      </section>

      <div class="split">
        <section class="panel">
          <div class="panel-head">
            <h2>SCHEDULE SEQUENCE / 调度序列（{{ result.sequence.length }}）</h2>
            <span class="aside">点击行查看规范化对比</span>
          </div>
          <div class="scroll-thin" style="max-height: 470px; overflow: auto">
            <table class="data-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th class="num">t(s)</th>
                  <th>域</th>
                  <th>canonical URL</th>
                  <th class="num">score</th>
                  <th class="num">token</th>
                  <th class="num">状态</th>
                  <th>标记</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="item in result.sequence"
                  :key="item.seq"
                  :class="{ 'is-selected': item.seq === selectedSeq?.seq, 'is-rate-limited': item.rate_limited }"
                  style="cursor: pointer"
                  @click="selectedSeq = item"
                >
                  <td>{{ String(item.seq).padStart(2, '0') }}</td>
                  <td class="num seq-time">{{ item.virtual_time_s.toFixed(1) }}</td>
                  <td>{{ item.domain }}</td>
                  <td class="url-cell canonical" :title="item.canonical_url">{{ truncate(item.canonical_url, 62) }}</td>
                  <td class="num">{{ item.score.toFixed(2) }}</td>
                  <td class="num">{{ item.token_before.toFixed(1) }}→{{ item.token_after.toFixed(1) }}</td>
                  <td class="num">
                    <span :class="item.rate_limited ? 'sig-red' : 'sig-green'">{{ item.status_code }}</span>
                  </td>
                  <td>
                    <span v-if="item.forced_probe" class="tag red">429 探测</span>
                    <span v-if="item.starvation_boosted" class="tag lamp">饥饿提升</span>
                    <span v-if="!item.forced_probe && !item.starvation_boosted" class="tag muted">normal</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <div style="display: grid; gap: 16px">
          <section class="panel">
            <div class="panel-head">
              <h2>DOMAIN TOKEN BUCKETS</h2>
              <span class="aside">令牌余量 / 实发 qps</span>
            </div>
            <div class="panel-body" style="display: grid; gap: 9px">
              <QuotaGauge
                v-for="stat in result.domain_stats"
                :key="stat.domain"
                :domain="stat.domain"
                :site-name="stat.site_name"
                :qps="stat.qps_quota"
                :tokens="stat.tokens_remaining"
                :capacity="stat.capacity"
                :signal="stat.signal"
                :effective-qps="stat.effective_qps"
                :backoff-window="stat.backoff_window_s"
                :issued="stat.issued"
                :concurrency="stat.max_concurrency"
              />
            </div>
          </section>

          <section class="panel">
            <div class="panel-head">
              <h2>BACKOFF / 429 退避</h2>
              <span class="aside">{{ result.backoff_events.length }} 次</span>
            </div>
            <div class="panel-body" style="display: grid; gap: 8px">
              <div v-for="event in result.backoff_events" :key="event.seq" class="gauge backoff">
                <div class="gauge-head">
                  <span class="domain">#{{ event.seq }} {{ event.site_name }} · {{ event.domain }}</span>
                  <span class="qps sig-red">{{ event.status_code }}</span>
                </div>
                <div class="gauge-meta">
                  <span>t={{ event.virtual_time_s.toFixed(1) }}s 第 {{ event.consecutive_429 }} 次 429</span>
                  <span>窗口 {{ event.window_before_s.toFixed(0) }}s → {{ event.window_after_s.toFixed(0) }}s</span>
                </div>
                <div class="gauge-meta">
                  <span>URL {{ truncate(event.raw_url, 48) }}</span>
                  <span>退避至 {{ event.backoff_until_s.toFixed(1) }}s</span>
                </div>
              </div>
              <div v-if="!result.backoff_events.length" class="empty">本次模拟没有 429 退避事件。</div>
            </div>
          </section>

          <section class="panel">
            <div class="panel-head">
              <h2>STARVATION / 饥饿提升</h2>
              <span class="aside">{{ result.starvation_boosts.length }} 次</span>
            </div>
            <div class="panel-body" style="display: grid; gap: 8px">
              <div v-for="boost in result.starvation_boosts" :key="boost.url_id" class="gauge">
                <div class="gauge-head">
                  <span class="domain">{{ boost.site_name }} · {{ boost.domain }}</span>
                  <span class="qps lamp-text">{{ boost.score_before }} → {{ boost.score_after }}</span>
                </div>
                <div class="gauge-meta">
                  <span>等待 {{ boost.wait_seconds }}s · 第 {{ boost.seq_at }} 位出队</span>
                  <span>aging 达上限仍排不上 → +3.0</span>
                </div>
                <div class="gauge-meta"><span>{{ boost.reason }}</span></div>
              </div>
              <div v-if="!result.starvation_boosts.length" class="empty">本次模拟没有触发饥饿提升。</div>
            </div>
          </section>

          <section v-if="selectedSeq" class="panel">
            <div class="panel-head">
              <h2>SEQUENCE #{{ selectedSeq.seq }} 明细</h2>
              <span class="aside">{{ selectedSeq.site_name }}</span>
            </div>
            <div class="panel-body" style="display: grid; gap: 10px">
              <CanonicalDiff
                :raw-url="selectedSeq.raw_url"
                :canonical-url="selectedSeq.canonical_url"
                :reasons="selectedSeq.forced_probe ? ['429 探测（混沌注入）'] : []"
              />
              <dl class="kv">
                <dt>出队得分</dt>
                <dd>
                  priority {{ selectedSeq.priority }} + aging {{ selectedSeq.aging }} + depth
                  {{ selectedSeq.depth_penalty }} + 饥饿 {{ selectedSeq.starvation_boosted ? 3 : 0 }} =
                  {{ selectedSeq.score }}
                </dd>
                <dt>虚拟时刻</dt>
                <dd>t={{ selectedSeq.virtual_time_s }}s · 延迟 {{ selectedSeq.latency_ms }}ms</dd>
                <dt>令牌</dt>
                <dd>{{ selectedSeq.token_before }} → {{ selectedSeq.token_after }}</dd>
              </dl>
            </div>
          </section>
        </div>
      </div>
    </template>

    <div v-else class="panel">
      <div class="panel-body">
        <EmptyState
          title="任务还没有调度结果"
          hint="点击右上角「运行调度模拟」：虚拟时钟按域令牌桶出队，固定注入 2 次 429 探测并在第 10 位检查饥饿提升，全程不发真实网络请求。"
        >
          <template #action>
            <button v-if="canSimulate" class="btn btn-primary" type="button" :disabled="tasks.simulating" @click="rerun">
              运行调度模拟
            </button>
          </template>
        </EmptyState>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import PageHeader from '../components/common/PageHeader.vue'
import MetricBlock from '../components/common/MetricBlock.vue'
import QuotaGauge from '../components/common/QuotaGauge.vue'
import CanonicalDiff from '../components/common/CanonicalDiff.vue'
import EmptyState from '../components/common/EmptyState.vue'
import { useTasksStore } from '../stores/tasksStore'
import { useAuthStore } from '../stores/authStore'
import { truncate } from '../utils/format'
import type { SequenceItem } from '../types/task'
import type { ApiError } from '../types/api'

const route = useRoute()
const tasks = useTasksStore()
const auth = useAuthStore()
const selectedSeq = ref<SequenceItem | null>(null)

const canSimulate = computed(() => auth.can('tasks:simulate'))
const task = computed(() => tasks.current)
const result = computed(() => tasks.current?.scheduler_result ?? null)

onMounted(async () => {
  const taskId = String(route.params.id)
  await tasks.loadDetail(taskId)
  if (result.value?.sequence?.length) selectedSeq.value = result.value.sequence[0]
})

async function rerun() {
  const taskId = String(route.params.id)
  try {
    await tasks.simulate(taskId)
    if (result.value?.sequence?.length) selectedSeq.value = result.value.sequence[0]
  } catch (error) {
    tasks.error = (error as ApiError).message ?? '调度模拟失败'
  }
}
</script>
