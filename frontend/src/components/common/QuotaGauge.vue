<template>
  <div class="gauge" :class="{ backoff: backoffWindow > 0 }">
    <div class="gauge-head">
      <span class="domain" :title="domain">{{ siteName }} · {{ domain }}</span>
      <span class="qps">qps {{ qps.toFixed(1) }}</span>
    </div>
    <div class="gauge-track">
      <div class="gauge-fill" :class="tone" :style="{ transform: `scaleX(${ratio})` }" />
    </div>
    <div class="gauge-meta">
      <span>
        <span class="lamp" :class="tone" /> 令牌 {{ tokens.toFixed(1) }}/{{ capacity.toFixed(1) }}
      </span>
      <span v-if="backoffWindow > 0" class="sig-red">退避 {{ backoffWindow.toFixed(0) }}s</span>
      <span v-else>实发 {{ effectiveQps.toFixed(2) }} qps · 出队 {{ issued }}</span>
    </div>
    <div class="gauge-meta">
      <span>并发 {{ concurrency }}</span>
      <span :class="signal === 'green' ? 'sig-green' : signal === 'yellow' ? 'sig-amber' : 'sig-red'">
        信号 {{ signal === 'green' ? 'GREEN' : signal === 'yellow' ? 'AMBER' : 'RED' }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    domain: string
    siteName: string
    qps: number
    tokens: number
    capacity: number
    signal: string
    effectiveQps?: number
    backoffWindow?: number
    issued?: number
    concurrency?: number
  }>(),
  { effectiveQps: 0, backoffWindow: 0, issued: 0, concurrency: 1 },
)

const ratio = computed(() => {
  if (!props.capacity) return 0
  return Math.max(0, Math.min(1, props.tokens / props.capacity))
})

const tone = computed(() =>
  props.signal === 'green' ? 'green' : props.signal === 'yellow' ? 'amber' : 'red',
)
</script>
