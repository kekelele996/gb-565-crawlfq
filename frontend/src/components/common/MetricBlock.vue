<template>
  <div class="metric">
    <span class="label">{{ label }}</span>
    <span class="value">
      {{ value }}<small v-if="unit">{{ unit }}</small>
    </span>
    <span v-if="hint" class="hint">{{ hint }}</span>
  </div>
</template>

<script setup lang="ts">
defineProps<{ label: string; value: string | number; unit?: string; hint?: string }>()
</script>
