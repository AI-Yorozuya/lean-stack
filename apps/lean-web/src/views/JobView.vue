<script setup>
// 非同步任務示範頁。
// 流程：按按鈕 → POST /progress/demo 派工 → 每秒輪詢 GET /progress/{id}
//        → 進度條 0→100，到 SUCCESS / FAILED 就停止輪詢。
// 這證明「前端 → 後端派工 → celery worker 背景跑 → 前端輪詢」整條 async 路通了。
import { ref, onUnmounted } from 'vue'
import { startDemoJob, getJob } from '@/api'

const job = ref(null)      // { id, name, status, progress, message }
const error = ref('')
let timer = null

function stopPolling() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

async function poll(id) {
  try {
    job.value = await getJob(id)
    // 終態就停止輪詢。
    if (job.value.status === 'SUCCESS' || job.value.status === 'FAILED') {
      stopPolling()
    }
  } catch (e) {
    console.error('poll failed:', e)
    error.value = '查詢進度失敗'
    stopPolling()
  }
}

async function run() {
  error.value = ''
  stopPolling()
  try {
    job.value = await startDemoJob()          // 立刻拿到 PENDING 的 job
    timer = setInterval(() => poll(job.value.id), 1000)  // 每秒輪詢
  } catch (e) {
    console.error('start failed:', e)
    error.value = '派工失敗（後端 / worker 沒起來？）'
  }
}

// 離開頁面時清掉 timer，避免背景一直打 API。
onUnmounted(stopPolling)
</script>

<template>
  <main style="font-family: system-ui, sans-serif; max-width: 480px; margin: 4rem auto;">
    <h1>非同步任務示範</h1>
    <p style="color: #666;">按下按鈕會派一個背景任務給 celery worker，前端每秒輪詢進度。</p>

    <button :disabled="!!timer" @click="run" style="padding: 0.5rem 1rem; font-size: 1rem;">
      {{ timer ? '執行中…' : '跑示範任務' }}
    </button>

    <div v-if="job" style="margin-top: 1.5rem;">
      <!-- 進度條：用一個外框 + 內部寬度隨 progress 變 -->
      <div style="background: #eee; border-radius: 6px; overflow: hidden; height: 22px;">
        <div
          :style="{
            width: job.progress + '%',
            height: '100%',
            background: job.status === 'FAILED' ? 'crimson' : '#2d8cff',
            transition: 'width .3s',
          }"
        ></div>
      </div>
      <p style="margin-top: .5rem;">
        狀態：<strong>{{ job.status }}</strong> — {{ job.progress }}%
      </p>
      <p v-if="job.message" style="color: #666;">{{ job.message }}</p>
    </div>

    <p v-if="error" style="color: crimson;">{{ error }}</p>

    <p style="margin-top: 2rem;"><router-link to="/">← 回首頁</router-link></p>
  </main>
</template>
