<script setup>
// 首頁 view：掛載時打後端 health 端點，把狀態交給 HealthBadge 元件顯示。
// 這頁能顯示「後端連線正常」就證明 Vue → ninja → Django → Postgres 整條路通了。
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
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
    <h1>lean-fullstack</h1>
    <HealthBadge :status="status" />
    <p style="margin-top: 1.5rem;"><RouterLink to="/job">非同步任務示範 →</RouterLink></p>
  </main>
</template>
