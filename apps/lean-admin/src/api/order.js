// 訂單管理的 API 呼叫。教學重點：
// - 前端不算錢——小計/總額都是後端算好回來的（鐵則住在後端）。
//   前端表單裡的即時小計只是「顯示給人看」，送出後以後端回傳為準。
// - 明細只送 product_id + quantity——品名/單價由後端從目錄抄快照，前端不傳價格。
// - 會員從 @/api/member、商品從 @/api/product 各自取（訂單只管訂單）。
// - 每個函式對應後端 apps/order/apis.py 的一個端點，一眼對得上。
import http from './index'

// ── 訂單 ──────────────────────────────
export function listOrders({ page = 1, pageSize = 10, q = '', memberId = null } = {}) {
  const params = { page, page_size: pageSize }
  if (q) params.q = q
  if (memberId) params.member_id = memberId
  return http.get('/orders', { params }).then((res) => res.data) // → { items, count }
}

export function getOrder(id) {
  return http.get(`/orders/${id}`).then((res) => res.data)
}

export function createOrder(payload) {
  // payload: { member_id, items: [{ product_id, quantity }] }
  return http.post('/orders', payload).then((res) => res.data)
}

export function updateOrderNote(id, note) {
  // 只改備註（inline dialog 用）
  return http.post(`/orders/${id}/note`, { note }).then((res) => res.data)
}

export function updateOrder(id, payload) {
  return http.put(`/orders/${id}`, payload).then((res) => res.data)
}

export function deleteOrder(id) {
  return http.delete(`/orders/${id}`).then((res) => res.data)
}

// ── 訂單狀態機 ──────────────────
// 每個函式對應一條「合法轉移」。非法轉移後端會回 422（狀態機擋下來），
// 前端把 detail 訊息顯示給人看即可（真相/守門在後端）。
// action ∈ pay | ship | cancel
export function transitionOrder(id, action) {
  return http.post(`/orders/${id}/${action}`).then((res) => res.data)
}
