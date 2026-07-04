<script setup>
// 訂單管理列表頁（Stage A：無狀態 CRUD）。
// 教學重點——這一頁就是「認識積木」上半的完整詞彙表：
//   看全部訂單   → table + pagination     （讀清單）
//   篩選         → input + select + button（讀清單·帶條件）
//   新增 / 編輯  → button → dialog + form （建立 / 修改）
//   刪除         → button → dialog 確認   （刪除）
// 七個元件、四個 API,每個都因為一個動作而存在。
// UI 積木一律用 @/components/ui 的 shadcn-vue 元件（樣式一致、無障礙內建）。
//
// 這一頁把三個 app 串起來：會員（下單的人）＋商品目錄（明細從這裡挑、抄快照）→ 訂單。
// 明細只送 product_id + 數量——品名/單價由後端從目錄抄，前端不傳價格（防亂塞、單一真相）。
//
// 鐵則的分工（重要）：表單裡的「小計/總計」是前端算給人看的即時回饋；
// 送出後一律以後端回傳為準——錢的真相在後端（見後端 models.py）。
import { computed, onMounted, reactive, ref } from 'vue'
import { Plus, X, Pencil, Trash2 } from '@lucide/vue'
import { createOrder, deleteOrder, listOrders, updateOrder, updateOrderNote } from '@/api/order'
import { createMember, listMembers } from '@/api/member'
import { listProducts } from '@/api/product'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import Pagination from '@/components/Pagination.vue'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import {
  Dialog,
  DialogContent,
  DialogScrollContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'

// ── 列表狀態 ────────────────────────────────────────────
const orders = ref([])
const count = ref(0)
const page = ref(1)
const pageSize = 30 // 每頁筆數（固定；資料量小，不放使用者可調的下拉）
const q = ref('')                  // input：模糊搜會員名
const filterMemberId = ref('all')  // Select：精準篩會員（'all' = 全部）
const members = ref([])
const products = ref([])           // 全部商品（含下架；價格 map 用）
const loading = ref(false)
const errorMsg = ref('')

// 表頭／表身是兩張表：垂直捲軸只長在表身（碰不到表頭）。橫捲時讓表頭跟著表身捲。
const headScroll = ref(null)
const bodyScroll = ref(null)
function syncHead() {
  if (headScroll.value && bodyScroll.value) headScroll.value.scrollLeft = bodyScroll.value.scrollLeft
}

const totalPages = computed(() => Math.max(1, Math.ceil(count.value / pageSize)))
// 只有上架商品能被挑進新明細（下架＝停售）。
const activeProducts = computed(() => products.value.filter((p) => p.is_active))
// product_id → 商品，算即時小計時查現價（顯示用）。
const productMap = computed(() => Object.fromEntries(products.value.map((p) => [String(p.id), p])))

async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    const data = await listOrders({
      page: page.value,
      pageSize,
      q: q.value,
      memberId: filterMemberId.value === 'all' ? null : Number(filterMemberId.value),
    })
    orders.value = data.items
    count.value = data.count
  } catch (e) {
    errorMsg.value = '載入失敗,請稍後再試'
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function loadMembers() {
  members.value = (await listMembers({ pageSize: 100 })).items
}

async function loadProducts() {
  products.value = (await listProducts({ pageSize: 100 })).items
}

function search() {
  page.value = 1
  load()
}

function goPage(p) {
  page.value = Math.min(Math.max(1, p), totalPages.value)
  load()
}

onMounted(() => {
  load()
  loadMembers()
  loadProducts()
})

// ── 新增 / 編輯 dialog ──────────────────────────────────
const showForm = ref(false)
const editingId = ref(null) // null = 新增；有值 = 編輯
const form = reactive({ member_id: '', items: [] })
const formError = ref('')

function blankItem() {
  return { product_id: '', quantity: 1 }
}

function openCreate() {
  editingId.value = null
  form.member_id = ''
  form.items = [blankItem()]
  formError.value = ''
  showForm.value = true
}

function openEdit(order) {
  editingId.value = order.id
  form.member_id = String(order.member.id)
  // 只取表單需要的欄位（品名/單價/小計是後端從目錄抄的，改單時重新挑）
  form.items = order.items.map((i) => ({
    product_id: String(i.product_id),
    quantity: i.quantity,
  }))
  formError.value = ''
  showForm.value = true
}

function addItem() {
  form.items.push(blankItem())
}

function removeItem(idx) {
  // 鐵則 {至少一筆明細}：前端先擋（體驗）,後端也會擋（真相）。
  if (form.items.length <= 1) {
    formError.value = '鐵則：一張訂單至少要有一筆明細'
    return
  }
  form.items.splice(idx, 1)
}

// 即時小計/總計——單價查目錄現價,只是顯示給人看；送出後以後端回傳為準。
const itemUnitPrice = (i) => Number(productMap.value[String(i.product_id)]?.unit_price ?? 0)
const itemSubtotal = (i) => (Number(i.quantity) || 0) * itemUnitPrice(i)
const formTotal = computed(() => form.items.reduce((sum, i) => sum + itemSubtotal(i), 0))

async function submitForm() {
  formError.value = ''
  if (!form.member_id) {
    formError.value = '請選擇會員'
    return
  }
  if (form.items.some((i) => !i.product_id)) {
    formError.value = '每一筆明細都要選一個商品'
    return
  }
  const payload = {
    member_id: Number(form.member_id),
    items: form.items.map((i) => ({
      product_id: Number(i.product_id),
      quantity: Number(i.quantity),
    })),
  }
  try {
    if (editingId.value) await updateOrder(editingId.value, payload)
    else await createOrder(payload)
    showForm.value = false
    load()
  } catch (e) {
    // 後端擋下的（422 = 鐵則/驗證不過）給人看得懂的訊息
    formError.value = e.response?.data?.detail || '儲存失敗,請稍後再試'
    console.error(e)
  }
}

// ── 快速新增會員（下單時會員還不存在的小門）─────────────
const showNewMember = ref(false)
const newMember = reactive({ name: '', email: '', phone: '' })
const newMemberError = ref('')

async function submitNewMember() {
  newMemberError.value = ''
  if (!newMember.name || !newMember.email) {
    newMemberError.value = '姓名與 email 必填'
    return
  }
  try {
    const m = await createMember({ ...newMember })
    await loadMembers()
    form.member_id = String(m.id) // 建完直接選上
    newMember.name = ''
    newMember.email = ''
    newMember.phone = ''
    showNewMember.value = false
  } catch (e) {
    newMemberError.value = e.response?.data?.detail || '建立失敗'
  }
}

// ── 刪除確認 dialog ─────────────────────────────────────
const deleting = ref(null) // 存要刪的 order 物件

async function confirmDelete() {
  await deleteOrder(deleting.value.id)
  deleting.value = null
  // 刪掉本頁最後一筆時退一頁,別停在空頁上
  if (orders.value.length === 1 && page.value > 1) page.value -= 1
  load()
}

// ── 備註 inline dialog（點備註欄的鉛筆 → 只改備註）──
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
  <!-- 整頁填滿可用高度：標題固定、卡片吃剩下的高，表格在卡內填滿並內捲、分頁釘在卡底 -->
  <div class="flex h-full flex-col">
    <h1 class="shrink-0 text-lg font-semibold leading-none tracking-tight">訂單列表</h1>

    <!-- 大卡片（學 top-admin：標題下一張白卡，搜尋列/表格/分頁全包在裡面；卡片用陰影、不用邊框）-->
    <div class="mt-5 flex min-h-0 flex-1 flex-col rounded-lg border bg-card p-5 shadow-sm">
      <p v-if="errorMsg" class="text-destructive mb-3 shrink-0 text-sm">{{ errorMsg }}</p>

      <!-- 工具列 -->
      <div class="mb-4 flex shrink-0 items-center justify-between gap-2">
        <div class="flex flex-wrap items-center gap-2">
          <Input v-model="q" placeholder="搜會員名…" class="w-40" @keyup.enter="search" />
          <Select v-model="filterMemberId" @update:model-value="search">
            <SelectTrigger class="w-40"><SelectValue placeholder="全部會員" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部會員</SelectItem>
              <SelectItem v-for="m in members" :key="m.id" :value="String(m.id)">{{ m.name }}</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" @click="search">搜尋</Button>
        </div>
        <Button @click="openCreate"><Plus class="size-4" /> 新增訂單</Button>
      </div>

      <!-- 表格：表頭／表身「兩張表、共用 colgroup」。垂直捲軸只長在表身 → 碰不到表頭；
           表頭右側也 overflow-y-scroll、掛同一個 .scroll-thin，預留跟表身捲軸同寬的空位 → 右緣對齊。
           水平方向表頭由 syncHead() 跟著表身左右捲。 -->
      <div class="flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border">
        <!-- 表頭（不參與垂直捲；右側預留捲軸槽）-->
        <div ref="headScroll" class="scroll-thin shrink-0 overflow-x-hidden overflow-y-scroll border-b bg-card">
          <!-- 底線整條只由外層 wrapper 的 border-b 畫（full-width、含右邊捲軸槽）；th 自己不畫，免得最右段變細。 -->
          <Table class="table-fixed [&_th]:border-b-0">
            <colgroup>
              <col class="w-28" /><col class="w-32" /><col class="w-28" /><col /><col class="w-32" /><col class="w-32" /><col class="w-28" />
            </colgroup>
            <TableHeader>
              <TableRow>
                <TableHead>單號</TableHead>
                <TableHead>會員</TableHead>
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
              <col class="w-28" /><col class="w-32" /><col class="w-28" /><col /><col class="w-32" /><col class="w-32" /><col class="w-28" />
            </colgroup>
            <TableBody>
            <TableRow v-for="o in orders" :key="o.id" class="group">
              <TableCell class="text-muted-foreground tabular-nums">{{ o.order_no }}</TableCell>
              <TableCell class="font-medium">{{ o.member.name }}</TableCell>
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
                  <Button variant="ghost" size="icon-sm" class="text-muted-foreground hover:text-foreground" title="編輯" @click="openEdit(o)">
                    <Pencil class="size-4" />
                  </Button>
                  <Button variant="ghost" size="icon-sm" class="text-destructive hover:text-destructive" title="刪除" @click="deleting = o">
                    <Trash2 class="size-4" />
                  </Button>
                </div>
              </TableCell>
            </TableRow>
            <TableRow v-if="!loading && orders.length === 0">
              <TableCell colspan="7" class="text-muted-foreground py-16 text-center">
                沒有訂單——按右上「＋ 新增訂單」開第一張
              </TableCell>
            </TableRow>
          </TableBody>
          </Table>
        </div>
      </div>

      <!-- 分頁（極簡：置中數字頁碼；釘在卡底）-->
      <div class="mt-4 shrink-0">
        <Pagination :page="page" :total-pages="totalPages" @update:page="goPage" />
      </div>
    </div>

    <!-- 新增/編輯 dialog + form -->
    <Dialog v-model:open="showForm">
      <DialogScrollContent class="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{{ editingId ? '編輯訂單' : '新增訂單' }}</DialogTitle>
          <DialogDescription>選會員、從商品目錄挑明細；小計/總計是顯示用,存檔後以後端計算為準。</DialogDescription>
        </DialogHeader>

        <div class="flex flex-col gap-4 py-2">
          <div class="flex flex-col gap-1.5">
            <Label>會員</Label>
            <div class="flex gap-2">
              <Select v-model="form.member_id">
                <SelectTrigger class="flex-1"><SelectValue placeholder="選擇會員" /></SelectTrigger>
                <SelectContent>
                  <SelectItem v-for="m in members" :key="m.id" :value="String(m.id)">{{ m.name }}</SelectItem>
                </SelectContent>
              </Select>
              <Button variant="outline" @click="showNewMember = !showNewMember">＋ 新會員</Button>
            </div>
            <div v-if="showNewMember" class="bg-muted flex flex-col gap-2 rounded-md p-2">
              <div class="flex gap-2">
                <Input v-model="newMember.name" placeholder="姓名" />
                <Input v-model="newMember.email" placeholder="email" />
                <Input v-model="newMember.phone" placeholder="電話（選填）" />
                <Button @click="submitNewMember">建立</Button>
              </div>
              <p v-if="newMemberError" class="text-destructive text-sm">{{ newMemberError }}</p>
            </div>
          </div>

          <div class="flex flex-col gap-2">
            <Label>明細（從商品目錄挑；小計 = 數量 × 牌價,自動算）</Label>
            <div v-for="(item, idx) in form.items" :key="idx" class="flex items-center gap-2">
              <Select v-model="item.product_id">
                <SelectTrigger class="flex-1"><SelectValue placeholder="選擇商品" /></SelectTrigger>
                <SelectContent>
                  <SelectItem v-for="p in activeProducts" :key="p.id" :value="String(p.id)">
                    {{ p.name }}（{{ p.unit_price.toLocaleString() }}）
                  </SelectItem>
                </SelectContent>
              </Select>
              <Input v-model.number="item.quantity" type="number" min="1" class="w-20" />
              <span class="text-muted-foreground w-28 text-right text-sm tabular-nums">= {{ itemSubtotal(item).toLocaleString() }}</span>
              <Button variant="ghost" size="icon-sm" class="text-destructive" @click="removeItem(idx)"><X class="size-4" /></Button>
            </div>
            <Button variant="outline" size="sm" class="w-fit" @click="addItem"><Plus class="size-4" /> 加一筆明細</Button>
          </div>

          <p class="font-semibold">
            總計：{{ formTotal.toLocaleString() }}
            <span class="text-muted-foreground ml-2 text-sm font-normal">（顯示用；存檔後以後端計算為準）</span>
          </p>
          <p v-if="formError" class="text-destructive text-sm">{{ formError }}</p>
        </div>

        <DialogFooter>
          <Button variant="outline" @click="showForm = false">取消</Button>
          <Button @click="submitForm">儲存</Button>
        </DialogFooter>
      </DialogScrollContent>
    </Dialog>

    <!-- 備註 inline dialog（只改備註）-->
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
