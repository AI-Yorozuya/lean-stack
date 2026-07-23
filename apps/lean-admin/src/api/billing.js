// 帳款（收費）的 API 呼叫。帳款頁是唯讀投影——分錄由訂單生命週期產生，這裡只讀不寫。
// 教學重點：餘額不是存的欄位，是後端把 append-only 分錄「算出來」回給前端（見後端 apps/billing）。
import http from './index'

// 客戶應收總覽（一列一客戶，欠最多的在前）。onlyOutstanding=true 只回還有欠款的。
export function listReceivables({ onlyOutstanding = false } = {}) {
  const params = {}
  if (onlyOutstanding) params.only_outstanding = true
  return http.get('/billing/receivables', { params }).then((res) => res.data) // → { items, count, total_balance }
}

// 單一客戶的分錄流（含每筆的跑動餘額）。
export function getCustomerLedger(customerId) {
  return http.get(`/billing/customers/${customerId}/ledger`).then((res) => res.data)
}
