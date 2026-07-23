// 報價單的 API 呼叫。刻意跟 order.js 同形（報價單與訂單同承重牆家族）。
// 教學重點：
// - 前端不算錢——小計/總額都是後端算好回來的（鐵則住在後端）。表單即時小計只是顯示。
// - 明細只送 product_id + quantity——品名/單價由後端從目錄抄快照，前端不傳價格。
// - 客戶從 @/api/member 取（報價單的「客戶」就是會員）；商品從 @/api/product 取。
// - 每個函式對應後端 apps/quotation/apis.py 的一個端點，一眼對得上。
import http from './index'

// ── 報價單 ──────────────────────────────
export function listQuotations({ page = 1, pageSize = 10, search = '', status = '', customerId = null } = {}) {
  const params = { page, page_size: pageSize }
  if (search) params.search = search
  if (status && status !== 'all') params.status = status
  if (customerId) params.customer_id = customerId
  return http.get('/quotations', { params }).then((res) => res.data) // → { items, count, status_counts }
}

export function getQuotation(id) {
  return http.get(`/quotations/${id}`).then((res) => res.data)
}

export function createQuotation(payload) {
  // payload: { customer_id, items: [{ product_id, quantity }], note }
  return http.post('/quotations', payload).then((res) => res.data)
}

export function updateQuotationNote(id, note) {
  // 只改備註（inline dialog 用）
  return http.post(`/quotations/${id}/note`, { note }).then((res) => res.data)
}

export function updateQuotation(id, payload) {
  return http.put(`/quotations/${id}`, payload).then((res) => res.data)
}

export function deleteQuotation(id) {
  return http.delete(`/quotations/${id}`).then((res) => res.data)
}

// ── 報價單狀態機 ──────────────────
// 每個函式對應一條「合法轉移」。非法轉移後端會回 422（狀態機擋下來），
// 前端把 detail 訊息顯示給人看即可（真相/守門在後端）。
// action ∈ send | win | void；win（成交）會在後端生一張訂單。
export function transitionQuotation(id, action) {
  return http.post(`/quotations/${id}/${action}`).then((res) => res.data)
}
