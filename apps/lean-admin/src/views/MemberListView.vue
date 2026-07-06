<script setup>
// 會員列表（認識積木「表層」最單純的一頁）。規則見 intents/會員管理.md。
// 刻意做到最小：只有 讀清單 ＋ 搜尋 ＋ 分頁。新增、狀態、編輯、刪除、篩選都「留白」——
// 那些正是「你試」：學員看著缺口，指名讓 AI 補上（見 teaching/認識積木.md）。
import { computed, onMounted, ref } from 'vue'
import { Search } from '@lucide/vue'
import { listMembers } from '@/api/member'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import DataTable from '@/components/DataTable.vue'
import Pagination from '@/components/Pagination.vue'
import { TableCell } from '@/components/ui/table'

const members = ref([])
const q = ref('')
const loading = ref(false)
const errorMsg = ref('')

// 欄位定義（餵給 DataTable）。email 吃剩餘寬度。刻意沒有狀態欄、沒有操作欄——留給學員指名補。
const columns = [
  { label: '姓名', width: 'w-40' },
  { label: 'email' },
  { label: '電話', width: 'w-36' },
  { label: '註冊日期', width: 'w-32', align: 'center' },
]

// 分頁（客戶端；整包載入後切頁）。
const page = ref(1)
const pageSize = 10
const totalPages = computed(() => Math.max(1, Math.ceil(members.value.length / pageSize)))
const pagedMembers = computed(() => {
  const start = (page.value - 1) * pageSize
  return members.value.slice(start, start + pageSize)
})
function goPage(p) {
  page.value = Math.min(Math.max(1, p), totalPages.value)
}

async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    members.value = (await listMembers({ pageSize: 100, q: q.value })).items
    page.value = 1 // 每次搜尋後回第一頁
  } catch (e) {
    errorMsg.value = '載入失敗,請稍後再試'
    console.error(e)
  } finally {
    loading.value = false
  }
}
onMounted(load)
</script>

<template>
  <div class="flex h-full flex-col">
    <h1 class="shrink-0 text-lg font-semibold leading-none tracking-tight">會員列表</h1>

    <div class="mt-5 flex min-h-0 flex-1 flex-col rounded-lg border bg-card p-5 shadow-sm">
      <p v-if="errorMsg" class="text-destructive mb-3 shrink-0 text-sm">{{ errorMsg }}</p>

      <!-- 工具列：只有搜尋。新增/狀態/篩選都留白＝「你試」的缺口。 -->
      <div class="mb-4 flex shrink-0 items-center gap-2">
        <div class="flex w-56">
          <Input v-model="q" placeholder="搜尋會員姓名…" class="relative rounded-r-none focus-visible:z-10" @keyup.enter="load" />
          <Button variant="outline" size="icon" class="shrink-0 rounded-l-none border-l-0" title="搜尋" @click="load"><Search class="size-4" /></Button>
        </div>
      </div>

      <!-- 表格：最單純的讀清單（沒有狀態欄、沒有操作欄；那些是「你試」的缺口）。 -->
      <DataTable :items="pagedMembers" :columns="columns" :loading="loading">
        <template #row="{ item: m }">
          <TableCell class="font-medium">{{ m.name }}</TableCell>
          <TableCell>{{ m.email }}</TableCell>
          <TableCell>{{ m.phone || '—' }}</TableCell>
          <TableCell class="tabular-nums">{{ m.registered_at }}</TableCell>
        </template>
        <template #empty>還沒有會員資料</template>
      </DataTable>

      <!-- 分頁（釘在卡底）-->
      <div class="mt-4 shrink-0">
        <Pagination :page="page" :total-pages="totalPages" @update:page="goPage" />
      </div>
    </div>
  </div>
</template>
