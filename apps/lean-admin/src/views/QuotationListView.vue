<script setup>
// 報價單管理頁：報價清單（tab 依狀態篩、狀態欄顯示生命週期）。刻意跟 OrderListView 同形。
// 操作：編輯 → 換頁（/quotations/:id/edit，只有草稿能改）；刪除 → 確認 dialog；備註 → inline dialog。
// 狀態機動作（送出/成交/作廢）在詳細頁做——這裡點單號進去。
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Search, Pencil, Trash2 } from '@lucide/vue'
import { listQuotations, deleteQuotation, updateQuotationNote } from '@/api/quotation'
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

// 欄位定義（餵給 DataTable）。備註省略 width = 吃剩餘寬度。
const columns = [
  { label: '單號', width: 'w-28' },
  { label: '客戶', width: 'w-32' },
  { label: '狀態', width: 'w-36', align: 'center' },
  { label: '總額', width: 'w-28', align: 'right' },
  { label: '備註' },
  { label: '建立日期', width: 'w-32', align: 'center' },
  { label: '修改日期', width: 'w-32', align: 'center' },
]

// 狀態文字樣式：進行中（草稿/已送出）粗體黑字，終態（已成交/已作廢）灰字。
const statusClass = (s) => (s === 'DRAFT' || s === 'SENT' ? 'font-medium text-foreground' : 'text-muted-foreground')
// 只有草稿能編輯明細（送出後鎖定，後端 update 也會擋）。
const isEditable = (q) => q.status === 'DRAFT'

const quotations = ref([])
const loading = ref(false)
const errorMsg = ref('')

// ── 狀態篩選 tab（計數只在「草稿/已送出」顯示，因為那才是要行動的）──
const statusTabs = [
  { key: 'all', label: '全部' },
  { key: 'DRAFT', label: '草稿' },
  { key: 'SENT', label: '已送出' },
  { key: 'WON', label: '已成交' },
  { key: 'VOID', label: '已作廢' },
]
const activeStatus = ref('all')
const searchInput = ref('')
const keyword = ref('')

// ── 後端完整篩選＋伺服器端分頁 ──
const count = ref(0)
const statusCounts = ref({})
const pageSize = ref(20)
const page = ref(1)
const pagedQuotations = computed(() => quotations.value)
const totalPages = computed(() => Math.max(1, Math.ceil(count.value / pageSize.value)))
const statusCount = (key) => statusCounts.value[key] ?? 0
const fmtCount = (n) => (n > 999 ? '999+' : n)

function selectStatus(key) { activeStatus.value = key; page.value = 1; load() }
function goPage(p) { page.value = Math.min(Math.max(1, p), totalPages.value); load() }
function setPageSize(n) { pageSize.value = n; page.value = 1; load() }
function search() { keyword.value = searchInput.value.trim(); page.value = 1; load() }

async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await listQuotations({ page: page.value, pageSize: pageSize.value, search: keyword.value, status: activeStatus.value })
    quotations.value = res.items
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

function goEdit(q) {
  router.push(`/quotations/${q.id}/edit`)
}

// ── 備註 inline dialog（只改備註）──
const noteQuotation = ref(null)
const noteText = ref('')
const noteSaving = ref(false)
function openNote(q) {
  noteQuotation.value = q
  noteText.value = q.note || ''
}
async function saveNote() {
  noteSaving.value = true
  try {
    const updated = await updateQuotationNote(noteQuotation.value.id, noteText.value)
    const i = quotations.value.findIndex((x) => x.id === updated.id)
    if (i > -1) quotations.value[i] = updated
    noteQuotation.value = null
  } catch (e) {
    console.error(e)
  } finally {
    noteSaving.value = false
  }
}

// ── 刪除確認 dialog ──
const deleting = ref(null)
async function confirmDelete() {
  await deleteQuotation(deleting.value.id)
  deleting.value = null
  load()
}
</script>

<template>
  <div class="flex h-full flex-col">
    <h1 class="shrink-0 text-lg font-semibold leading-none tracking-tight">報價單列表</h1>

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
            v-if="tab.key === 'DRAFT' || tab.key === 'SENT'"
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

        <!-- 工具列：搜尋（左）＋ 新增報價（右）。 -->
        <div class="mb-4 flex shrink-0 items-center justify-between gap-2">
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
          <Button @click="router.push('/quotations/new')"><Plus class="size-4" /> 新增報價</Button>
        </div>

        <!-- 表格：水電（捲軸/對齊/空狀態）全包在 DataTable；這裡只宣告欄位＋一列怎麼畫 -->
        <DataTable :items="pagedQuotations" :columns="columns" :loading="loading">
          <template #row="{ item: q }">
            <TableCell class="tabular-nums">
              <button type="button" class="hover:text-primary hover:underline" @click="router.push(`/quotations/${q.id}`)">{{ q.quote_no }}</button>
            </TableCell>
            <TableCell class="font-medium">{{ q.customer.name }}</TableCell>
            <TableCell class="text-center">
              <span :class="statusClass(q.status)">{{ q.status_display }}</span>
            </TableCell>
            <TableCell class="text-right tabular-nums">{{ q.total.toLocaleString() }}</TableCell>
            <TableCell>
              <div class="flex items-center gap-1.5">
                <span class="min-w-0 truncate">{{ q.note }}</span>
                <button
                  type="button"
                  class="text-muted-foreground/60 hover:text-foreground shrink-0"
                  title="改備註"
                  @click="openNote(q)"
                ><Pencil class="size-3.5" /></button>
              </div>
            </TableCell>
            <TableCell class="tabular-nums">{{ q.created_at }}</TableCell>
            <TableCell class="tabular-nums">{{ q.updated_at }}</TableCell>
          </template>
          <template #actions="{ item: q }">
            <Button variant="ghost" size="icon-sm" class="text-muted-foreground hover:text-foreground" :disabled="!isEditable(q)" :title="isEditable(q) ? '編輯' : '送出後不可編輯'" @click="goEdit(q)">
              <Pencil class="size-4" />
            </Button>
            <Button variant="ghost" size="icon-sm" class="text-destructive hover:text-destructive" title="刪除" @click="deleting = q">
              <Trash2 class="size-4" />
            </Button>
          </template>
          <template #empty>
            {{ keyword ? '找不到符合的報價單' : (activeStatus === 'all' ? '還沒有報價單——按上方「＋ 新增報價」開第一張' : '此狀態目前沒有報價單') }}
          </template>
        </DataTable>

        <!-- 分頁 -->
        <div class="mt-4 shrink-0">
          <Pagination :page="page" :total-pages="totalPages" :page-size="pageSize" @update:page="goPage" @update:page-size="setPageSize" />
        </div>
      </div>
    </div>

    <!-- 備註 inline dialog -->
    <Dialog :open="!!noteQuotation" @update:open="(v) => { if (!v) noteQuotation = null }">
      <DialogContent class="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>備註 · {{ noteQuotation?.quote_no }}</DialogTitle>
          <DialogDescription>自由文字，跟報價狀態無關、隨時可改。</DialogDescription>
        </DialogHeader>
        <div class="py-2">
          <Input v-model="noteText" placeholder="輸入備註…" maxlength="200" @keyup.enter="saveNote" />
        </div>
        <DialogFooter>
          <Button variant="outline" @click="noteQuotation = null">取消</Button>
          <Button :disabled="noteSaving" @click="saveNote">儲存</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- 刪除確認 dialog -->
    <Dialog :open="!!deleting" @update:open="(v) => { if (!v) deleting = null }">
      <DialogContent class="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>刪除報價單 {{ deleting?.quote_no }}？</DialogTitle>
          <DialogDescription>
            客戶 {{ deleting?.customer.name }}、總額 {{ deleting?.total.toLocaleString() }}。刪了就沒了（明細一起刪）。
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" @click="deleting = null">取消</Button>
          <Button variant="destructive" @click="confirmDelete">確定刪除</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
