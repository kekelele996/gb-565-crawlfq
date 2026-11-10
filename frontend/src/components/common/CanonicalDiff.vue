<template>
  <div class="diff">
    <div class="diff-line before">
      <span class="marker">RAW</span>
      <span class="value">{{ rawUrl }}</span>
    </div>
    <div class="diff-line after">
      <span class="marker">CANON</span>
      <span class="value">{{ canonicalUrl }}</span>
    </div>
    <div class="reason-chips">
      <span v-for="reason in reasons" :key="reason" class="chip">{{ reason }}</span>
      <span v-if="!reasons.length" class="chip">无归一变更（已是规范形式）</span>
    </div>
    <div v-if="fingerprint" class="gauge-meta">
      <span>sha256</span>
      <span>{{ fingerprint }}</span>
    </div>
    <div v-if="charSaved !== undefined" class="gauge-meta">
      <span>规则命中 {{ reasons.length }} 条</span>
      <span>字符节省 {{ charSaved }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    rawUrl: string
    canonicalUrl: string
    reasons: string[]
    fingerprint?: string
    charSaved?: number
  }>(),
  { fingerprint: '', charSaved: undefined },
)
</script>
