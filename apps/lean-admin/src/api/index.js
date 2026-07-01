// 最小的 API 包裝：建一個 axios instance，baseURL 設成 /api/v1。
// 搭配 vite.config.js 的 proxy，/api 會被轉到後端 :8000。
import axios from 'axios'

const http = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
})

// 對應後端 GET /api/v1/health → { status: "ok" }
export function getHealth() {
  return http.get('/health').then((res) => res.data)
}

export default http
