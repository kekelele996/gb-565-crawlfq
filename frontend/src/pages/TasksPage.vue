<template>
  <div class="page">
    <PageHeader
      kicker="TOWER / CRAWL TASKS"
      title="采集任务与调度入口"
      sub="任务 = 站点集合 + 调度窗口 + 序列上限。创建权限：调度主管 / 采集工程师；只读观察员 POST 会被后端 RBAC 拒绝（403）。"
    >
      <template #actions>
        <button class="btn" type="button" :disabled="tasks.loading" @click="tasks.load()">刷新任务</button>
      </template>
    </PageHeader>

    <div class="metric-row">
      <MetricBlock label="任务总数" :value="tasks.summary?.total ?? 0" hint="queued / finished 混合" />
      <MetricBlock label="待调度" :value="tasks.summary?.queued ?? 0" hint="主流程在此运行" />
      <MetricBlock label="已完成" :value="tasks.summary?.finished ?? 0" hint="含 seed 真算的模拟结果" />
      <MetricBlock label="累计调度序列" :value="tasks.summary?.scheduled_total ?? 0" hint="scheduled_count 求和" />
    </div>

    <div v-if="tasks.error" class="banner">{{ tasks.error }}</div>

    <div class="split">
      <section class="panel">
        <div class="panel-head">
          <h2>TASK BOARD / 任务列表</h2>
          <span class="aside">{{ tasks.loading ? '加载中…' : '点击进入调度看板' }}</span>
        </div>
        <table class="data-table">
          <thead>
            <tr>
              <th>任务</th>
              <th>站点</th>
              <th>状态</th>
              <th class="num">序列</th>
              <th class="num">429</th>
              <th class="num">饥饿提升</th>
              <th>创建人</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="task in tasks.items" :key="task.id">
              <td>
                <div>{{ task.name }}</div>
                <div class="muted" style="font-size: 10px">窗口 {{ task.window_s }}s · 序列上限 {{ task.max_sequence }}</div>
              </td>
              <td>{{ task.site_domains.length }} 域</td>
              <td><StatusTag :value="task.status" kind="task" /></td>
              <td class="num">{{ task.scheduled_count }}</td>
              <td class="num">{{ task.result_summary?.rate_limited_count ?? '—' }}</td>
              <td class="num">{{ task.result_summary?.starvation_count ?? '—' }}</td>
              <td class="muted">{{ task.created_by }}</td>
              <td>
                <div class="head-actions" style="justify-content: flex-end">
                  <RouterLink class="btn btn-small" :to="`/tasks/${task.id}`">看板</RouterLink>
                  <button
                    v-if="canSimulate"
                    class="btn btn-small"
                    type="button"
                    :disabled="tasks.simulating"
                    @click="runSimulation(task.id)"
                  >
                    运行
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="!tasks.items.length && !tasks.loading" class="empty">还没有任务，使用右侧表单创建第一条采集任务。</div>
      </section>

      <section class="panel">
        <div class="panel-head">
          <h2>NEW TASK / 创建任务</h2>
          <span class="aside">{{ canCreate ? 'POST /api/tasks' : '当前角色只读' }}</span>
        </div>
        <div class="panel-body" style="display: grid; gap: 12px">
          <div v-if="!canCreate" class="banner info">
            当前角色（{{ auth.roleLabel }}）没有 tasks:create 权限：提交创建会返回 403。如需创建请切换调度主管或采集工程师账号。
          </div>
          <div class="field">
            <label>任务名称</label>
            <input v-model="form.name" class="input" placeholder="如：财经站点 11 月增量采集" />
          </div>
          <div class="field">
            <label>站点集合（多选）</label>
            <div class="reason-chips">
              <label v-for="site in sites.items" :key="site.id" class="chip" style="cursor: pointer">
                <input v-model="form.site_domains" type="checkbox" :value="site.domain" style="margin-right: 5px" />
                {{ site.name }}
              </label>
            </div>
          </div>
          <div class="form-grid">
            <div class="field">
              <label>并发</label>
              <input v-model.number="form.concurrency" class="input" type="number" min="1" max="10" />
            </div>
            <div class="field">
              <label>窗口 s</label>
              <input v-model.number="form.window_s" class="input" type="number" min="1" max="120" />
            </div>
            <div class="field">
              <label>序列上限</label>
              <input v-model.number="form.max_sequence" class="input" type="number" min="1" max="200" />
            </div>
            <div class="field">
              <label>seed</label>
              <input v-model.number="form.seed" class="input" type="number" min="1" max="9999" />
            </div>
          </div>
          <button class="btn btn-primary" type="button" :disabled="creating" @click="submit">
            {{ creating ? '创建中…' : '创建采集任务' }}
          </button>
          <div v-if="error" class="banner">{{ error }}</div>
          <div v-if="created" class="banner success">
            已创建：{{ created.name }}（{{ created.site_domains.length }} 域）→ 进入
            <RouterLink :to="`/tasks/${created.id}`">调度看板</RouterLink>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import PageHeader from '../components/common/PageHeader.vue'
import MetricBlock from '../components/common/MetricBlock.vue'
import StatusTag from '../components/common/StatusTag.vue'
import { useTasksStore } from '../stores/tasksStore'
import { useSitesStore } from '../stores/sitesStore'
import { useAuthStore } from '../stores/authStore'
import type { CrawlTask } from '../types/task'
import type { ApiError } from '../types/api'

const tasks = useTasksStore()
const sites = useSitesStore()
const auth = useAuthStore()

const canCreate = computed(() => auth.can('tasks:create'))
const canSimulate = computed(() => auth.can('tasks:simulate'))
const creating = ref(false)
const error = ref('')
const created = ref<CrawlTask | null>(null)

const form = reactive({
  name: '',
  site_domains: [] as string[],
  concurrency: 3,
  window_s: 20,
  max_sequence: 40,
  seed: 7,
})

onMounted(() => {
  void tasks.load()
  void sites.load().then(() => {
    form.site_domains = sites.items.slice(0, 2).map((site) => site.domain)
    if (!form.name) form.name = `澜舟增量采集 ${new Date().toISOString().slice(0, 10)}`
  })
})

async function submit() {
  creating.value = true
  error.value = ''
  created.value = null
  try {
    created.value = await tasks.create({ ...form })
    form.name = ''
  } catch (err) {
    error.value = (err as ApiError).message ?? '创建失败'
  } finally {
    creating.value = false
  }
}

async function runSimulation(taskId: string) {
  try {
    await tasks.simulate(taskId)
    await tasks.load()
  } catch (error_) {
    tasks.error = (error_ as ApiError).message ?? '调度模拟失败'
  }
}
</script>
