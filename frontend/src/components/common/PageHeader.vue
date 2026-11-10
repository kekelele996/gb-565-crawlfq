<template>
  <header class="page-head">
    <div>
      <div class="kicker">{{ kicker }}</div>
      <h1>{{ title }}</h1>
      <p v-if="sub" class="sub">{{ sub }}</p>
    </div>
    <div class="head-actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<script setup lang="ts">
defineProps<{ kicker: string; title: string; sub?: string }>()
</script>
