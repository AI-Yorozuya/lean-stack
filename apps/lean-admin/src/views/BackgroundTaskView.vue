<script setup>
// 背景任務（原「非同步示範」）——搬 top-admin 批次任務頁的做法：
//   一張「所有背景任務」清單（名稱/狀態/進度/開始/花費/訊息），
//   有任務在跑（RUNNING/PENDING）就每 2 秒輪詢刷新，跑完自動停。
// 教學重點：worker 在背景跑、前端只是「輪詢同一張 Job 表」看進度——
//   最白話的 async 進度做法（不用 websocket）。真相在後端（見 apps/progress）。
import { ref, onMounted, onUnmounted } from 'vue'
import { RefreshCw, Play } from '@lucide/vue'
import { listJobs, startDemoJob } from '@/api'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'

// 狀態 → badge 樣式（黑白語彙；失敗用紅）
const STATUS = { PENDING: 'outline', RUNNING: 'secondary', SUCCESS: 'default', FAILED: 'destructive' }

const jobs = ref([])
const loading = ref(false)
const running = ref(false) // 派工中（按鈕 disabled 用）
let pollTimer = null

async function load() {
  loading.value = true
  try {
    jobs.value = await listJobs()
    // 只要還有沒跑完的，就每 2 秒輪詢；全跑完就停（省得一直打 API）。
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
    if (jobs.value.some((j) => j.status === 'RUNNING' || j.status === 'PENDING')) {
      pollTimer = setInterval(load, 2000)
    }
  } catch (e) {
    console.error('load jobs failed:', e)
  } finally {
    loading.value = false
  }
}

async function runDemo() {
  running.value = true
  try {
    await startDemoJob() // 派工，後端立刻回（實際由 worker 背景跑）
    await load() // 刷新清單（會帶起輪詢看它 0→100）
  } catch (e) {
    console.error('run demo failed:', e)
  } finally {
    running.value = false
  }
}

const fmtTime = (iso) => (iso ? new Date(iso).toLocaleTimeString('zh-TW', { hour12: false }) : '-')
const fmtElapsed = (s) => (s == null ? '-' : `${s} 秒`)

onMounted(load)
onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <div class="flex h-full flex-col">
    <div class="flex shrink-0 items-center justify-between gap-2">
      <h1 class="text-2xl font-semibold tracking-tight">背景任務</h1>
      <div class="flex items-center gap-2">
        <Button variant="outline" :disabled="loading" @click="load"><RefreshCw class="size-4" /> 重新整理</Button>
        <Button :disabled="running" @click="runDemo"><Play class="size-4" /> 跑一個示範任務</Button>
      </div>
    </div>

    <!-- 大卡片 -->
    <div class="mt-4 flex min-h-0 flex-1 flex-col rounded-lg bg-white p-6 shadow-sm">
      <!-- 表格：表頭固定（捲軸不碰它）＋ 表身內捲；同一組 colgroup 對齊 -->
      <div class="flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border">
        <div class="scroll-thin bg-muted shrink-0 overflow-y-auto [scrollbar-gutter:stable]">
          <Table class="table-fixed">
            <colgroup>
              <col class="w-14" /><col class="w-40" /><col class="w-24" /><col class="w-48" /><col class="w-28" /><col class="w-24" /><col />
            </colgroup>
            <TableHeader>
              <TableRow>
                <TableHead>#</TableHead>
                <TableHead>名稱</TableHead>
                <TableHead>狀態</TableHead>
                <TableHead>進度</TableHead>
                <TableHead>開始</TableHead>
                <TableHead>花費</TableHead>
                <TableHead>訊息</TableHead>
              </TableRow>
            </TableHeader>
          </Table>
        </div>
        <div class="scroll-thin min-h-0 flex-1 overflow-y-auto [scrollbar-gutter:stable]">
          <Table class="table-fixed">
            <colgroup>
              <col class="w-14" /><col class="w-40" /><col class="w-24" /><col class="w-48" /><col class="w-28" /><col class="w-24" /><col />
            </colgroup>
            <TableBody>
              <TableRow v-for="j in jobs" :key="j.id">
                <TableCell class="text-muted-foreground">{{ j.id }}</TableCell>
                <TableCell class="font-medium">{{ j.name }}</TableCell>
                <TableCell><Badge :variant="STATUS[j.status]">{{ j.status_display }}</Badge></TableCell>
                <TableCell>
                  <div class="bg-secondary h-2 w-full overflow-hidden rounded-full">
                    <div
                      class="h-full rounded-full transition-all duration-300"
                      :class="j.status === 'FAILED' ? 'bg-destructive' : 'bg-primary'"
                      :style="{ width: j.progress + '%' }"
                    />
                  </div>
                </TableCell>
                <TableCell class="text-muted-foreground tabular-nums">{{ fmtTime(j.started_at) }}</TableCell>
                <TableCell class="text-muted-foreground tabular-nums">{{ fmtElapsed(j.elapsed_seconds) }}</TableCell>
                <TableCell class="text-muted-foreground truncate">{{ j.message || '-' }}</TableCell>
              </TableRow>
              <TableRow v-if="!loading && jobs.length === 0">
                <TableCell colspan="7" class="text-muted-foreground py-16 text-center">
                  還沒有背景任務——按右上「跑一個示範任務」開始
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  </div>
</template>
