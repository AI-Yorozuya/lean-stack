// 後台路由。
//
// 教學重點（怎麼加一頁）：
//   1) 在 src/views/ 新增一個 .vue（例如 UsersView.vue）。
//   2) 在下面 routes 陣列加一筆 { path: '/users', component: () => import('@/views/UsersView.vue') }。
//      用 () => import(...) 是 lazy load：進到該頁才下載，首頁更快。
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  // 進站預設導到會員（最單純的 CRUD 入門頁；沒有獨立首頁）
  { path: '/', redirect: '/members' },
  // 會員管理（最單純 CRUD；訂單的「下單的人」就是它）
  { path: '/members', name: 'members', component: () => import('@/views/MemberListView.vue') },
  // 商品管理（最單純 CRUD；訂單明細從這個目錄挑、抄快照）
  { path: '/products', name: 'products', component: () => import('@/views/ProductListView.vue') },
  // 訂單管理（有狀態：生命週期狀態機——本 repo 講「狀態與流程」的主場）
  { path: '/orders', name: 'orders', component: () => import('@/views/OrderListView.vue') },
  // 訂單新增/詳細/編輯共用一個 OrderDetailView（跟 ns/top 一樣不另開編輯檔）：
  //   name=order-new → 新增、order-detail → 檢視、order-edit → 編輯。
  //   /orders/new 要放在 /orders/:id 前面，不然 new 會被當成 id。
  { path: '/orders/new', name: 'order-new', component: () => import('@/views/OrderDetailView.vue') },
  { path: '/orders/:id', name: 'order-detail', component: () => import('@/views/OrderDetailView.vue') },
  { path: '/orders/:id/edit', name: 'order-edit', component: () => import('@/views/OrderDetailView.vue') },
  // 背景任務頁（celery 範例：任務清單 + 進度輪詢，lazy load）
  { path: '/job', name: 'job', component: () => import('@/views/BackgroundTaskView.vue') },
  // 新頁面路由加在這
  // 之後的登入頁也在這加：{ path: '/login', name: 'login', component: () => import('@/views/LoginView.vue') }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// ──────────────────────────────────────────────────────────────
// AUTH 接縫（目前刻意留空）
// 後台是最需要登入/權限的地方。之後在這裡加一個 beforeEach 守衛：
//   - 檢查登入狀態（token / session），未登入就 router.push('/login')
//   - 後端對應的 auth 接縫在 lean-backend 的 core/api.py（NinjaAPI auth=...）
// 例：
//   router.beforeEach((to) => {
//     const isLoggedIn = /* 讀 token */ false
//     if (!isLoggedIn && to.name !== 'login') return { name: 'login' }
//   })
// ──────────────────────────────────────────────────────────────

export default router
