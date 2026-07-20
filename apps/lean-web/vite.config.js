import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 對外門市（storefront）的極簡前端。跟 lean-admin 同一套（Vue + Vite），
// 打同一個後端 API——所以「改後台的商品 → 這裡跟著變」。
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    port: Number(process.env.PORT) || 5175,
    // /api 一律 proxy 給後端；容器內由 VITE_API_PROXY_TARGET 指到 compose 內網 backend，
    // host 直跑則 fallback localhost（跟 admin 同慣例）。
    proxy: {
      '/api': {
        target: process.env.VITE_API_PROXY_TARGET || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
