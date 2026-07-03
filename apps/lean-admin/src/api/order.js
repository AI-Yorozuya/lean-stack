// 訂單管理的 API 呼叫。教學重點：
// - 前端不算錢——小計/總額都是後端算好回來的（鐵則住在後端）。
//   前端表單裡的即時小計只是「顯示給人看」，送出後以後端回傳為準。
// - 每個函式對應後端 apps/order/apis.py 的一個端點，一眼對得上。
import http from './index'

// ── 客戶 ──────────────────────────────
export function listCustomers() {
  return http.get('/order/customers').then((res) => res.data)
}

export function createCustomer(payload) {
  // payload: { name, phone }
  return http.post('/order/customers', payload).then((res) => res.data)
}

// ── 訂單 ──────────────────────────────
export function listOrders({ page = 1, pageSize = 10, q = '', customerId = null } = {}) {
  const params = { page, page_size: pageSize }
  if (q) params.q = q
  if (customerId) params.customer_id = customerId
  return http.get('/order', { params }).then((res) => res.data) // → { items, count }
}

export function createOrder(payload) {
  // payload: { customer_id, items: [{ name, quantity, unit_price }] }
  return http.post('/order', payload).then((res) => res.data)
}

export function updateOrder(id, payload) {
  return http.put(`/order/${id}`, payload).then((res) => res.data)
}

export function deleteOrder(id) {
  return http.delete(`/order/${id}`).then((res) => res.data)
}
