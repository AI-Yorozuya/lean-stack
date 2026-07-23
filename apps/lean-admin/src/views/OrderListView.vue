<script setup>
// 訂單管理頁：訂單清單（tab 依狀態篩、狀態欄顯示生命週期）。
// 操作：編輯 → 換頁（/orders/:id/edit，只有待付款可編輯）。訂單一成立就開帳，是財務單據——
// 不刪除；要取消進詳細頁「作廢」（狀態轉已取消並沖銷未收，帳務軌跡保留）。
// 備註 → inline 彈 dialog 快速改（只改備註、跟狀態無關，見後端 /order/{id}/note）。
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Search, Pencil } from '@lucide/vue'
import { listOrders, updateOrderNote } from '@/api/order'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import Pagination from '@/components/Pagination.vue'
import DataTable from '@/components/DataTable.vue'
import { TableCell } from '@/components/ui/table'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'

const router = useRouter()

// 欄位定義（餵給 DataTable：產生兩張表共用的 colgroup + 表頭）。備註省略 width = 吃剩餘寬度。
const columns = [
  { label: '單號', width: 'w-28' },
  { label: '客戶', width: 'w-32' },
  { label: '狀態', width: 'w-36', align: 'center' },
  { label: '總額', width: 'w-28', align: 'right' },
  { label: '備註' },
  { label: '下訂日期', width: 'w-32', align: 'center' },
  { label: '修改日期', width: 'w-32', align: 'center' },
]

// 狀態不用 tag，改文字樣式：進行中（待付款/待出貨）粗體黑字，終態（已出貨/已取消）灰字。
const statusClass = (s) => (s === 'PENDING' || s === 'AWAITING' ? 'font-medium text-foreground' : 'text-muted-foreground')
// 只有待付款（未收款）可編輯——收款後鎖定明細（帳已開，不讓總額脫鉤）。
const isEditable = (o) => o.status === 'PENDING'

const orders = ref([])
const loading = ref(false)
const errorMsg = ref('')

// ── 狀態篩選 tab（計數只在「待付款/待出貨」顯示，因為那才是要行動的）──
const statusTabs = [
  { key: 'all', label: '全部' },
  { key: 'PENDING', label: '待付款' },
  { key: 'AWAITING', label: '待出貨' },
  { key: 'SHIPPED', label: '已出貨' },
  { key: 'CANCELLED', label: '已取消' },
]
const activeStatus = ref('all')
const searchInput = ref('') // 搜尋輸入框
const keyword = ref('')     // 已按下搜尋、實際生效的關鍵字（送後端當 search）

// ── 後端完整篩選＋伺服器端分頁 ──
// 狀態頁籤、搜尋、分頁全部送後端；前端只顯示後端回來的那一頁（不抓全部再前端濾）。
const count = ref(0)            // 符合條件的總筆數（後端算）
const statusCounts = ref({})   // 各狀態筆數（後端回，給頁籤計數）
const pageSize = ref(20)
const page = ref(1)
const pagedOrders = computed(() => orders.value) // 後端已切好這一頁
const totalPages = computed(() => Math.max(1, Math.ceil(count.value / pageSize.value)))
const statusCount = (key) => statusCounts.value[key] ?? 0
const fmtCount = (n) => (n > 999 ? '999+' : n)

function selectStatus(key) { activeStatus.value = key; page.value = 1; load() } // 切狀態 → 回第一頁、重撈
function goPage(p) { page.value = Math.min(Math.max(1, p), totalPages.value); load() }
function setPageSize(n) { pageSize.value = n; page.value = 1; load() }
function search() { keyword.value = searchInput.value.trim(); page.value = 1; load() } // 按搜尋 / Enter → 套用、重撈

async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await listOrders({ page: page.value, pageSize: pageSize.value, search: keyword.value, status: activeStatus.value })
    orders.value = res.items
    count.value = res.count
    statusCounts.value = res.status_counts || {}
  } catch (e) {
    errorMsg.value = '載入失敗,請稍後再試'
    console.error(e)
  } finally {
    loading.value = false
  }
}
onMounted(load)

// 編輯 → 換頁
function goEdit(o) {
  router.push(`/orders/${o.id}/edit`)
}

// ── 備註 inline dialog（只改備註）──
const noteOrder = ref(null)
const noteText = ref('')
const noteSaving = ref(false)
function openNote(o) {
  noteOrder.value = o
  noteText.value = o.note || ''
}
async function saveNote() {
  noteSaving.value = true
  try {
    const updated = await updateOrderNote(noteOrder.value.id, noteText.value)
    const i = orders.value.findIndex((x) => x.id === updated.id)
    if (i > -1) orders.value[i] = updated
    noteOrder.value = null
  } catch (e) {
    console.error(e)
  } finally {
    noteSaving.value = false
  }
}
</script>

<template>
  <div class="flex h-full flex-col">
    <h1 class="shrink-0 text-lg font-semibold leading-none tracking-tight">訂單列表</h1>

    <!-- 大卡片：頂部狀態 tab（全寬）+ 內容（含表格）-->
    <div class="mt-5 flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border bg-card shadow-sm">
      <!-- 狀態篩選 tab（底線式）-->
      <div class="flex shrink-0 border-b">
        <button
          v-for="tab in statusTabs"
          :key="tab.key"
          type="button"
          :class="[
            'flex cursor-pointer items-center gap-1.5 whitespace-nowrap border-b-2 px-4 py-3 text-sm transition-colors -mb-px',
            activeStatus === tab.key ? 'border-primary font-medium text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground',
          ]"
          @click="selectStatus(tab.key)"
        >
          {{ tab.label }}
          <span
            v-if="tab.key === 'PENDING' || tab.key === 'AWAITING'"
            :class="[
              'inline-flex min-w-[1.25rem] items-center justify-center rounded-full px-1.5 py-0.5 text-xs tabular-nums',
              activeStatus === tab.key ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground',
            ]"
          >{{ fmtCount(statusCount(tab.key)) }}</span>
        </button>
      </div>

      <!-- 內容 -->
      <div class="flex min-h-0 flex-1 flex-col p-5">
        <p v-if="errorMsg" class="text-destructive mb-3 shrink-0 text-sm">{{ errorMsg }}</p>

        <!-- 工具列：搜尋（左）＋ 新增訂單（右）。狀態篩選交給上方 tab，這裡只做關鍵字搜尋。 -->
        <div class="mb-4 flex shrink-0 items-center justify-between gap-2">
          <!-- 搜尋框：input + 搜尋 icon 鈕接在一起（input 右角磨平、鈕左角磨平且去左框，共用一條分隔線）-->
          <div class="flex w-64">
            <Input
              v-model="searchInput"
              placeholder="搜尋客戶姓名或單號…"
              class="relative rounded-r-none focus-visible:z-10"
              @keyup.enter="search"
            />
            <Button variant="outline" size="icon" class="shrink-0 rounded-l-none border-l-0" title="搜尋" @click="search">
              <Search class="size-4" />
            </Button>
          </div>
          <Button @click="router.push('/orders/new')"><Plus class="size-4" /> 新增訂單</Button>
        </div>

        <!-- 表格：水電（捲軸分家/對齊/底線/空狀態）全包在 DataTable；這裡只宣告欄位＋一列怎麼畫 -->
        <DataTable :items="pagedOrders" :columns="columns" :loading="loading">
          <template #row="{ item: o }">
            <TableCell class="tabular-nums">
              <button type="button" class="hover:text-primary hover:underline" @click="router.push(`/orders/${o.id}`)">{{ o.order_no }}</button>
            </TableCell>
            <TableCell class="font-medium">{{ o.member.name }}</TableCell>
            <TableCell class="text-center">
              <span :class="statusClass(o.status)">{{ o.status_display }}</span>
            </TableCell>
            <TableCell class="text-right tabular-nums">{{ o.total.toLocaleString() }}</TableCell>
            <TableCell>
              <div class="flex items-center gap-1.5">
                <span class="min-w-0 truncate">{{ o.note }}</span>
                <button
                  type="button"
                  class="text-muted-foreground/60 hover:text-foreground shrink-0"
                  title="改備註"
                  @click="openNote(o)"
                ><Pencil class="size-3.5" /></button>
              </div>
            </TableCell>
            <TableCell class="tabular-nums">{{ o.order_date }}</TableCell>
            <TableCell class="tabular-nums">{{ o.updated_at }}</TableCell>
          </template>
          <template #actions="{ item: o }">
            <Button variant="ghost" size="icon-sm" class="text-muted-foreground hover:text-foreground" :disabled="!isEditable(o)" :title="isEditable(o) ? '編輯' : '收款後不可編輯（進詳細頁可作廢）'" @click="goEdit(o)">
              <Pencil class="size-4" />
            </Button>
          </template>
          <template #empty>
            {{ keyword ? '找不到符合的訂單' : (activeStatus === 'all' ? '還沒有訂單——按上方「＋ 新增訂單」開第一張' : '此狀態目前沒有訂單') }}
          </template>
        </DataTable>

        <!-- 分頁 -->
        <div class="mt-4 shrink-0">
          <Pagination :page="page" :total-pages="totalPages" :page-size="pageSize" @update:page="goPage" @update:page-size="setPageSize" />
        </div>
      </div>
    </div>

    <!-- 備註 inline dialog -->
    <Dialog :open="!!noteOrder" @update:open="(v) => { if (!v) noteOrder = null }">
      <DialogContent class="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>備註 · {{ noteOrder?.order_no }}</DialogTitle>
          <DialogDescription>自由文字，跟訂單狀態無關、隨時可改。</DialogDescription>
        </DialogHeader>
        <div class="py-2">
          <Input v-model="noteText" placeholder="輸入備註…" maxlength="200" @keyup.enter="saveNote" />
        </div>
        <DialogFooter>
          <Button variant="outline" @click="noteOrder = null">取消</Button>
          <Button :disabled="noteSaving" @click="saveNote">儲存</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
