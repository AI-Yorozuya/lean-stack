import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],

  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },

  server: {
    // 後台用 5174，跟前台 lean-web(5173) 區隔，兩者可同時開。
    port: 5174,
    // 把打到 /api 的請求，dev 時轉給後端的 :8000（與 lean-web 同一個後端）。
    // 好處：前端程式碼一律用相對路徑 /api/...，不用管 CORS、也不用寫死後端網址。
    proxy: {
      '/api': {
        // 容器內跑（docker compose）時由 VITE_API_PROXY_TARGET 指到 compose 內網的 backend；
        // host 上直接跑則 fallback localhost。兩種起法共用同一份 config。
        target: process.env.VITE_API_PROXY_TARGET || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
