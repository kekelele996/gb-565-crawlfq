import { createRouter, createWebHistory } from 'vue-router'
import { setupGuards } from './guards'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/sites' },
    {
      path: '/login',
      name: 'login',
      component: () => import('../pages/LoginPage.vue'),
      meta: { public: true },
    },
    { path: '/sites', name: 'sites', component: () => import('../pages/SitesPage.vue'), meta: { title: '站点与配额' } },
    {
      path: '/frontier',
      name: 'frontier',
      component: () => import('../pages/FrontierPage.vue'),
      meta: { title: 'URL 前沿' },
    },
    { path: '/tasks', name: 'tasks', component: () => import('../pages/TasksPage.vue'), meta: { title: '采集任务' } },
    {
      path: '/tasks/:id',
      name: 'task-board',
      component: () => import('../pages/TaskBoardPage.vue'),
      meta: { title: '调度看板' },
    },
    { path: '/fetches', name: 'fetches', component: () => import('../pages/FetchesPage.vue'), meta: { title: '抓取记录' } },
    { path: '/audits', name: 'audits', component: () => import('../pages/AuditsPage.vue'), meta: { title: '覆盖度审计' } },
    { path: '/:pathMatch(.*)*', redirect: '/sites' },
  ],
})

setupGuards(router)

export default router
