<template>
  <div class="empty">
    <p>{{ title }}</p>
    <p v-if="hint" class="muted" style="margin-top: 4px">{{ hint }}</p>
    <div v-if="$slots.action" style="margin-top: 10px">
      <slot name="action" />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ title: string; hint?: string }>()
</script>
