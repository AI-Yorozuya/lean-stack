// 會員管理的 API 呼叫。對應後端 apps/member/apis.py。
// 教學重點：{一 email 一會員}（撞了後端回 422）、{停用不刪}（沒有 delete，只有停用/啟用）。
import http from './index'

export function listMembers({ page = 1, pageSize = 100, search = '', status = '' } = {}) {
  const params = { page, page_size: pageSize }
  if (search) params.search = search
  if (status) params.status = status
  return http.get('/members', { params }).then((res) => res.data) // → { items, count }
}

export function createMember(payload) {
  // payload: { name, email, phone }
  return http.post('/members', payload).then((res) => res.data)
}

export function updateMember(id, payload) {
  // payload: { name, phone }（email 建立後不給改）
  return http.put(`/members/${id}`, payload).then((res) => res.data)
}

export function deactivateMember(id) {
  return http.post(`/members/${id}/deactivate`).then((res) => res.data)
}

export function reactivateMember(id) {
  return http.post(`/members/${id}/reactivate`).then((res) => res.data)
}
