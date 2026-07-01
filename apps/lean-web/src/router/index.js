// 前端路由（目前只有一條）。
//
// 教學重點（怎麼加一頁）：
//   1) 在 src/views/ 新增一個 .vue（例如 LedgerView.vue）。
//   2) 在下面 routes 陣列加一筆 { path: '/ledger', component: () => import('@/views/LedgerView.vue') }。
//      用 () => import(...) 是 lazy load：進到該頁才下載，首頁更快。
import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'

const routes = [
  { path: '/', name: 'home', component: HomeView },
  // 非同步任務示範頁（lazy load）。
  { path: '/job', name: 'job', component: () => import('@/views/JobView.vue') },
  // 新頁面路由加在這
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
