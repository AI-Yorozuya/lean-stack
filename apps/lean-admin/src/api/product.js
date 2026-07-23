// 產品管理的 API 呼叫。對應後端 apps/product/apis.py。
// 教學重點：{一 sku 一產品}（撞了後端回 422）、{停售不刪}（沒有 delete，只有停售/建立）。
import http from './index'

export function listProducts({ page = 1, pageSize = 100, search = '', activeOnly = false } = {}) {
  const params = { page, page_size: pageSize }
  if (search) params.search = search
  if (activeOnly) params.active_only = true
  return http.get('/products', { params }).then((res) => res.data) // → { items, count }
}

export function createProduct(payload) {
  // payload: { sku, name, unit_price }
  return http.post('/products', payload).then((res) => res.data)
}

export function updateProduct(id, payload) {
  // payload: { name, unit_price }（sku 建立後不給改）
  return http.put(`/products/${id}`, payload).then((res) => res.data)
}

export function deactivateProduct(id) {
  return http.post(`/products/${id}/deactivate`).then((res) => res.data)
}

export function reactivateProduct(id) {
  return http.post(`/products/${id}/reactivate`).then((res) => res.data)
}
