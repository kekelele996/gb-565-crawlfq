<template>
  <div class="login-shell">
    <section class="login-visual">
      <div class="radar" />
      <div>
        <div class="brand">CRAWLFQ</div>
        <p class="tagline" style="margin-top: 16px">
          澜舟情报 · 采集塔台。<br />
          把 sitemap 前沿、域配额与 429 退避收敛进一条进近序列：<br />
          先规范化去重，再按令牌桶放行，最后用覆盖度审计对齐站方声明。
        </p>
      </div>
      <div>
        <div class="stripes" style="margin-bottom: 18px">
          <span /><span /><span /><span /><span />
        </div>
        <div class="rail-meta" style="position: relative; z-index: 1; max-width: 360px">
          <div>席位频段 <b>FRONT 18238 · API 19238 · DB 17738</b></div>
          <div>演示账号密码 <b>Demo@2026</b></div>
          <div>调度模拟 <b>虚拟时钟 · 不真发网络请求</b></div>
        </div>
      </div>
    </section>

    <section class="login-form-side">
      <form class="login-card" @submit.prevent="submit">
        <div class="kicker">TOWER ACCESS / 席位登录</div>
        <h1>进近管制登录</h1>

        <div class="field">
          <label for="email">邮箱</label>
          <input id="email" v-model="email" class="input" type="email" autocomplete="username" placeholder="admin@crawlfq.io" />
        </div>
        <div class="field">
          <label for="password">口令</label>
          <input
            id="password"
            v-model="password"
            class="input"
            type="password"
            autocomplete="current-password"
            placeholder="Demo@2026"
          />
        </div>

        <div class="preset-row">
          <button
            v-for="preset in presets"
            :key="preset.email"
            class="preset"
            type="button"
            @click="fill(preset.email)"
          >
            {{ preset.label }}
          </button>
        </div>

        <div v-if="error" class="banner">{{ error }}</div>

        <button class="btn btn-primary" type="submit" :disabled="auth.loading">
          {{ auth.loading ? '校准席位…' : '进入塔台' }}
        </button>

        <p class="muted" style="font-size: 10.5px">
          三个演示账号：admin@crawlfq.io（调度主管）/ engineer@crawlfq.io（采集工程师）/ viewer@crawlfq.io（只读）。
          角色差异由后端 RBAC 判定，只读角色创建任务返回 403。
        </p>
      </form>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import type { ApiError } from '../types/api'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const email = ref('admin@crawlfq.io')
const password = ref('Demo@2026')
const error = ref('')

const presets = [
  { label: '调度主管', email: 'admin@crawlfq.io' },
  { label: '采集工程师', email: 'engineer@crawlfq.io' },
  { label: '只读', email: 'viewer@crawlfq.io' },
]

function fill(value: string) {
  email.value = value
  password.value = 'Demo@2026'
}

async function submit() {
  error.value = ''
  try {
    await auth.login(email.value.trim(), password.value)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/sites'
    await router.push(redirect)
  } catch (err) {
    error.value = (err as ApiError).message ?? '登录失败'
  }
}
</script>
