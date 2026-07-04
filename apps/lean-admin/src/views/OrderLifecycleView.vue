<script setup>
// 訂單管理 Stage B 頁：訂單清單（tab 依狀態篩、狀態欄顯示生命週期）。
// 操作：編輯 → 換頁（/orders/:id/edit）；刪除 → 確認 dialog。
// 備註 → inline 彈 dialog 快速改（只改備註、跟狀態無關，見後端 /order/{id}/note）。
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Pencil, Trash2 } from '@lucide/vue'
import { listOrders, deleteOrder, updateOrderNote } from '@/api/order'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import Pagination from '@/components/Pagination.vue'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'

const router = useRouter()

// 狀態不用 tag，改文字樣式：進行中（待付款/待出貨）粗體黑字，終態（已出貨/已取消）灰字。
const statusClass = (s) => (s === 'PENDING' || s === 'AWAITING' ? 'font-medium text-foreground' : 'text-muted-foreground')
// 出貨前（待付款/待出貨）才可編輯。
const isEditable = (o) => o.status === 'PENDING' || o.status === 'AWAITING'

const orders = ref([])
const loading = ref(false)
const errorMsg = ref('')

// 表頭／表身是兩張表：垂直捲軸只長在表身（碰不到表頭）。
// 欄多到要橫捲時，讓表頭跟著表身左右捲，兩張表才對得齊。
const headScroll = ref(null)
const bodyScroll = ref(null)
function syncHead() {
  if (headScroll.value && bodyScroll.value) headScroll.value.scrollLeft = bodyScroll.value.scrollLeft
}

// ── 狀態篩選 tab（計數只在「待付款/待出貨」顯示，因為那才是要行動的）──
const statusTabs = [
  { key: 'all', label: '全部' },
  { key: 'PENDING', label: '待付款' },
  { key: 'AWAITING', label: '待出貨' },
  { key: 'SHIPPED', label: '已出貨' },
  { key: 'CANCELLED', label: '已取消' },
]
const activeStatus = ref('all')
const filteredOrders = computed(() =>
  activeStatus.value === 'all' ? orders.value : orders.value.filter((o) => o.status === activeStatus.value),
)
const statusCount = (key) =>
  key === 'all' ? orders.value.length : orders.value.filter((o) => o.status === key).length
const fmtCount = (n) => (n > 999 ? '999+' : n)

// ── 分頁（客戶端）──
const page = ref(1)
const pageSize = 15
const totalPages = computed(() => Math.max(1, Math.ceil(filteredOrders.value.length / pageSize)))
const pagedOrders = computed(() => {
  const start = (page.value - 1) * pageSize
  return filteredOrders.value.slice(start, start + pageSize)
})
function selectStatus(key) {
  activeStatus.value = key
  page.value = 1
}
function goPage(p) {
  page.value = Math.min(Math.max(1, p), totalPages.value)
}

async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    orders.value = (await listOrders({ pageSize: 100 })).items
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

// ── 刪除確認 dialog ──
const deleting = ref(null)
async function confirmDelete() {
  await deleteOrder(deleting.value.id)
  deleting.value = null
  load()
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

        <!-- 表格：表頭／表身「兩張表、共用 colgroup」。
             垂直捲軸只長在表身 → 碰不到表頭；表頭右側也 overflow-y-scroll、掛「同一個 .scroll-thin」，
             預留跟表身捲軸一模一樣寬的空位 → 兩邊右緣停在同一條線、欄位與隔線完全對齊（不用硬寫 px）。
             水平方向表頭不自己捲，由 syncHead() 跟著表身左右捲（欄多到要橫捲時才用得到）。 -->
        <div class="flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border">
          <!-- 表頭（不參與垂直捲；右側 overflow-y-scroll 預留捲軸槽，空槽透明看不見）-->
          <div ref="headScroll" class="scroll-thin shrink-0 overflow-x-hidden overflow-y-scroll border-b bg-card">
            <!-- 底線整條只由外層 wrapper 的 border-b 畫（full-width、含右邊捲軸槽）；
                 th 自己不再畫線，免得兩條略微錯開、最右段看起來變細。 -->
            <Table class="table-fixed [&_th]:border-b-0">
              <colgroup>
                <col class="w-28" /><col class="w-32" /><col class="w-36" /><col class="w-28" /><col /><col class="w-32" /><col class="w-32" /><col class="w-28" />
              </colgroup>
              <TableHeader>
                <TableRow>
                  <TableHead>單號</TableHead>
                  <TableHead>會員</TableHead>
                  <TableHead class="text-center">狀態</TableHead>
                  <TableHead class="text-right">總額</TableHead>
                  <TableHead>備註</TableHead>
                  <TableHead>下訂日期</TableHead>
                  <TableHead>修改日期</TableHead>
                  <TableHead class="bg-card sticky right-0 z-20 border-l text-center">操作</TableHead>
                </TableRow>
              </TableHeader>
            </Table>
          </div>
          <!-- 表身（垂直捲軸只在這裡；橫捲時同步表頭）-->
          <div ref="bodyScroll" class="scroll-thin min-h-0 flex-1 overflow-x-auto overflow-y-scroll" @scroll="syncHead">
            <Table class="table-fixed">
              <colgroup>
                <col class="w-28" /><col class="w-32" /><col class="w-36" /><col class="w-28" /><col /><col class="w-32" /><col class="w-32" /><col class="w-28" />
              </colgroup>
              <TableBody>
              <TableRow v-for="o in pagedOrders" :key="o.id" class="group">
                <TableCell class="text-muted-foreground tabular-nums">{{ o.order_no }}</TableCell>
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
                <TableCell class="bg-card group-hover:bg-muted/50 sticky right-0 z-10 border-l">
                  <div class="flex items-center justify-center gap-1">
                    <Button variant="ghost" size="icon-sm" class="text-muted-foreground hover:text-foreground" :disabled="!isEditable(o)" :title="isEditable(o) ? '編輯' : '已出貨/已取消不可編輯'" @click="goEdit(o)">
                      <Pencil class="size-4" />
                    </Button>
                    <Button variant="ghost" size="icon-sm" class="text-destructive hover:text-destructive" title="刪除" @click="deleting = o">
                      <Trash2 class="size-4" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
              <TableRow v-if="!loading && filteredOrders.length === 0">
                <TableCell colspan="8" class="text-muted-foreground py-10 text-center">
                  {{ activeStatus === 'all' ? '還沒有訂單——先到「訂單(無狀態)」開一張' : '此狀態目前沒有訂單' }}
                </TableCell>
              </TableRow>
            </TableBody>
            </Table>
          </div>
        </div>

        <!-- 分頁 -->
        <div class="mt-4 shrink-0">
          <Pagination :page="page" :total-pages="totalPages" @update:page="goPage" />
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

    <!-- 刪除確認 dialog -->
    <Dialog :open="!!deleting" @update:open="(v) => { if (!v) deleting = null }">
      <DialogContent class="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>刪除訂單 {{ deleting?.order_no }}？</DialogTitle>
          <DialogDescription>
            會員 {{ deleting?.member.name }}、總額 {{ deleting?.total.toLocaleString() }}。刪了就沒了（明細一起刪）。
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
