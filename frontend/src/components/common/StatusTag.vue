<template>
  <span class="tag" :class="tone">{{ label }}</span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  ROBOTS_LABELS,
  TASK_STATUS_LABELS,
  URL_STATUS_LABELS,
  ROLE_LABELS,
  GAP_REASON_LABELS,
} from '../../constants/enums'

const props = defineProps<{ value: string; kind?: 'url' | 'task' | 'robots' | 'role' | 'signal' | 'gap' }>()

const labels: Record<string, Record<string, string>> = {
  url: URL_STATUS_LABELS,
  task: TASK_STATUS_LABELS,
  robots: ROBOTS_LABELS,
  role: ROLE_LABELS,
  gap: GAP_REASON_LABELS,
}

const label = computed(() => {
  if (props.kind === 'signal') {
    return props.value === 'green' ? '绿灯' : props.value === 'yellow' ? '黄灯' : '红灯'
  }
  const map = labels[props.kind ?? 'url'] ?? {}
  return map[props.value] ?? props.value
})

const tone = computed(() => {
  if (props.kind === 'signal') {
    return props.value === 'green' ? 'green' : props.value === 'yellow' ? 'amber' : 'red'
  }
  const value = props.value
  if (['done', 'finished', 'allow', 'green'].includes(value)) return 'green'
  if (['queued', 'running', 'partial', 'inflight', 'not_discovered'].includes(value)) return 'amber'
  if (['blocked', 'failed', 'folded', 'paused'].includes(value)) return 'red'
  return 'muted'
})
</script>
