// 商品管理的 API 呼叫。對應後端 apps/product/apis.py。
// 教學重點：{一 sku 一商品}（撞了後端回 422）、{下架不刪}（沒有 delete，只有下架/上架）。
import http from './index'

export function listProducts({ page = 1, pageSize = 100, q = '', activeOnly = false } = {}) {
  const params = { page, page_size: pageSize }
  if (q) params.q = q
  if (activeOnly) params.active_only = true
  return http.get('/product', { params }).then((res) => res.data) // → { items, count }
}

export function createProduct(payload) {
  // payload: { sku, name, unit_price }
  return http.post('/product', payload).then((res) => res.data)
}

export function updateProduct(id, payload) {
  // payload: { name, unit_price }（sku 建立後不給改）
  return http.put(`/product/${id}`, payload).then((res) => res.data)
}

export function deactivateProduct(id) {
  return http.post(`/product/${id}/deactivate`).then((res) => res.data)
}

export function reactivateProduct(id) {
  return http.post(`/product/${id}/reactivate`).then((res) => res.data)
}
