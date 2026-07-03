<script setup>
// 非同步任務示範頁。
// 流程：按按鈕 → POST /progress/demo 派工 → 每秒輪詢 GET /progress/{id}
//        → 進度條 0→100，到 SUCCESS / FAILED 就停止輪詢。
// 這證明「前端 → 後端派工 → celery worker 背景跑 → 前端輪詢」整條 async 路通了。
import { ref, onUnmounted } from 'vue'
import { startDemoJob, getJob } from '@/api'
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'

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
  <div class="mx-auto max-w-lg">
    <h1 class="text-2xl font-semibold tracking-tight">非同步任務示範</h1>
    <p class="text-muted-foreground mt-1 text-sm">按下按鈕會派一個背景任務給 celery worker，前端每秒輪詢進度。</p>

    <Card class="mt-5">
      <CardHeader>
        <CardTitle>示範任務</CardTitle>
        <CardDescription>派工 → 背景執行 → 輪詢進度 0→100</CardDescription>
      </CardHeader>
      <CardContent class="flex flex-col gap-4">
        <Button :disabled="!!timer" class="w-fit" @click="run">
          {{ timer ? '執行中…' : '跑示範任務' }}
        </Button>

        <div v-if="job" class="flex flex-col gap-2">
          <!-- 進度條：外框 + 內部寬度隨 progress 變 -->
          <div class="bg-secondary h-2.5 w-full overflow-hidden rounded-full">
            <div
              class="h-full rounded-full transition-all duration-300"
              :class="job.status === 'FAILED' ? 'bg-destructive' : 'bg-primary'"
              :style="{ width: job.progress + '%' }"
            />
          </div>
          <p class="text-sm">
            狀態：<span class="font-medium">{{ job.status }}</span> — {{ job.progress }}%
          </p>
          <p v-if="job.message" class="text-muted-foreground text-sm">{{ job.message }}</p>
        </div>

        <p v-if="error" class="text-destructive text-sm">{{ error }}</p>
      </CardContent>
    </Card>
  </div>
</template>
