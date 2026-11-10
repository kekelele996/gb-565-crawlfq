<template>
  <div class="shell">
    <aside class="rail">
      <div class="rail-brand">
        <div class="callsign">CRAWLFQ</div>
        <div class="sub">APPROACH CONTROL · 塔台</div>
      </div>

      <div class="rail-meta">
        <div>席位 <b>{{ auth.roleLabel || '—' }}</b></div>
        <div>呼号 <b>{{ auth.displayName || '—' }}</b></div>
        <div>频段 <b>18238 / 19238 / 17738</b></div>
      </div>

      <nav class="rail-nav">
        <RouterLink v-for="(item, index) in navItems" :key="item.to" :to="item.to" class="nav-item">
          <span class="nav-index">{{ String(index + 1).padStart(2, '0') }}</span>
          <span class="nav-label">{{ item.label }}</span>
        </RouterLink>
      </nav>

      <div class="rail-foot">
        <div class="rail-user">
          <span class="who">{{ auth.user?.email }}</span>
          <span class="role">{{ auth.roleLabel }} · {{ auth.role }}</span>
        </div>
        <button class="btn btn-small" type="button" @click="logout">退出席位</button>
      </div>
    </aside>

    <main class="main">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/authStore'

const auth = useAuthStore()
const router = useRouter()

const navItems = [
  { to: '/sites', label: '站点与配额' },
  { to: '/frontier', label: 'URL 前沿' },
  { to: '/tasks', label: '采集任务' },
  { to: '/fetches', label: '抓取记录' },
  { to: '/audits', label: '覆盖度审计' },
]

function logout() {
  auth.logout()
  void router.push('/login')
}
</script>
