<script setup>
// 後台首頁 view：掛載時打後端 health 端點，把狀態交給 HealthBadge 元件顯示。
// 這頁能顯示「後端連線正常」就證明「後台 → 同一個後端」整條路通了
// （lean-admin 與 lean-web 共用 GET /api/v1/health 這個後端）。
import { ref, onMounted } from 'vue'
import { getHealth } from '@/api'
import HealthBadge from '@/components/HealthBadge.vue'

const status = ref('checking')

onMounted(async () => {
  try {
    const data = await getHealth()
    status.value = data.status === 'ok' ? 'ok' : 'error'
  } catch (e) {
    console.error('health check failed:', e)
    status.value = 'error'
  }
})
</script>

<template>
  <main style="font-family: system-ui, sans-serif; max-width: 480px; margin: 4rem auto; text-align: center;">
    <h1>lean-stack 管理後台</h1>
    <p style="color: #666;">後台 / Admin Console</p>
    <HealthBadge :status="status" />
    <!--
      之後加登入：後台是 auth 真正重要的地方。
      登入頁與權限守衛的接縫已留在 src/router/index.js（見該檔註解）。
    -->
  </main>
</template>
