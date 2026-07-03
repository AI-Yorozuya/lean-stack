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
// 鐵則的分工（重要）：表單裡的「小計/總計」是前端算給人看的即時回饋；
// 送出後一律以後端回傳為準——錢的真相在後端（見後端 models.py）。
import { computed, onMounted, reactive, ref } from 'vue'
import { Plus, X } from '@lucide/vue'
import {
  createCustomer,
  createOrder,
  deleteOrder,
  listCustomers,
  listOrders,
  updateOrder,
} from '@/api/order'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
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

// 沒有專用的 shadcn Select 元件時,原生 <select> 套這個 class 對齊 Input 外觀。
const selectClass =
  'border-input h-9 rounded-md border bg-transparent px-3 py-1 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-3'

// ── 列表狀態 ────────────────────────────────────────────
const orders = ref([])
const count = ref(0)
const page = ref(1)
const pageSize = 10
const q = ref('')                 // input：模糊搜客戶名
const filterCustomerId = ref('')  // select：精準篩客戶
const customers = ref([])
const loading = ref(false)
const errorMsg = ref('')

const totalPages = computed(() => Math.max(1, Math.ceil(count.value / pageSize)))

async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    const data = await listOrders({
      page: page.value,
      pageSize,
      q: q.value,
      customerId: filterCustomerId.value || null,
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

async function loadCustomers() {
  customers.value = await listCustomers()
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
  loadCustomers()
})

// ── 新增 / 編輯 dialog ──────────────────────────────────
const showForm = ref(false)
const editingId = ref(null) // null = 新增；有值 = 編輯
const form = reactive({ customer_id: '', items: [] })
const formError = ref('')

function blankItem() {
  return { name: '', quantity: 1, unit_price: 0 }
}

function openCreate() {
  editingId.value = null
  form.customer_id = ''
  form.items = [blankItem()]
  formError.value = ''
  showForm.value = true
}

function openEdit(order) {
  editingId.value = order.id
  form.customer_id = order.customer.id
  // 只取表單需要的欄位（id/subtotal 是後端的事）
  form.items = order.items.map((i) => ({
    name: i.name,
    quantity: i.quantity,
    unit_price: i.unit_price,
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

// 即時小計/總計——只是顯示給人看；送出後以後端回傳為準。
const itemSubtotal = (i) => (Number(i.quantity) || 0) * (Number(i.unit_price) || 0)
const formTotal = computed(() => form.items.reduce((sum, i) => sum + itemSubtotal(i), 0))

async function submitForm() {
  formError.value = ''
  if (!form.customer_id) {
    formError.value = '請選擇客戶'
    return
  }
  const payload = {
    customer_id: Number(form.customer_id),
    items: form.items.map((i) => ({
      name: i.name,
      quantity: Number(i.quantity),
      unit_price: Number(i.unit_price),
    })),
  }
  try {
    if (editingId.value) await updateOrder(editingId.value, payload)
    else await createOrder(payload)
    showForm.value = false
    load()
  } catch (e) {
    // 後端擋下的（422 = 鐵則/驗證不過）給人看得懂的訊息
    formError.value = e.response?.status === 422 ? '資料不合規則：請檢查明細（數量要 > 0、至少一筆）' : '儲存失敗,請稍後再試'
    console.error(e)
  }
}

// ── 快速新增客戶（下單時客戶還不存在的小門）─────────────
const showNewCustomer = ref(false)
const newCustomer = reactive({ name: '', phone: '' })

async function submitNewCustomer() {
  if (!newCustomer.name) return
  const c = await createCustomer({ ...newCustomer })
  await loadCustomers()
  form.customer_id = c.id // 建完直接選上
  newCustomer.name = ''
  newCustomer.phone = ''
  showNewCustomer.value = false
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
</script>

<template>
  <div>
    <h1 class="text-2xl font-semibold tracking-tight">訂單管理</h1>

    <!-- 大卡片（學 top-admin：標題下一張白卡，搜尋列/表格/分頁全包在裡面；卡片用陰影、不用邊框）-->
    <div class="mt-4 rounded-lg bg-white p-5 shadow-sm">
      <p v-if="errorMsg" class="text-destructive mb-3 text-sm">{{ errorMsg }}</p>

      <!-- 工具列 -->
      <div class="mb-4 flex items-center justify-between gap-2">
        <div class="flex flex-wrap items-center gap-2">
          <Input v-model="q" placeholder="搜客戶名…" class="w-40" @keyup.enter="search" />
          <select v-model="filterCustomerId" :class="selectClass" @change="search">
            <option value="">全部客戶</option>
            <option v-for="c in customers" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
          <Button variant="outline" @click="search">搜尋</Button>
        </div>
        <Button @click="openCreate"><Plus class="size-4" /> 新增訂單</Button>
      </div>

      <!-- 表格：自己一張帶邊框的框，嵌在白卡裡（密度/表頭底色由 ui/table 統一）-->
      <div class="overflow-hidden rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead class="w-16">#</TableHead>
            <TableHead>客戶</TableHead>
            <TableHead>日期</TableHead>
            <TableHead>明細</TableHead>
            <TableHead class="text-right">總額</TableHead>
            <TableHead class="w-32"></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="o in orders" :key="o.id">
            <TableCell class="text-muted-foreground">{{ o.id }}</TableCell>
            <TableCell class="font-medium">{{ o.customer.name }}</TableCell>
            <TableCell class="text-muted-foreground">{{ o.order_date }}</TableCell>
            <TableCell class="text-muted-foreground">{{ o.items.length }} 筆</TableCell>
            <TableCell class="text-right tabular-nums">{{ o.total.toLocaleString() }}</TableCell>
            <TableCell class="text-right whitespace-nowrap">
              <Button variant="ghost" size="sm" @click="openEdit(o)">編輯</Button>
              <Button variant="ghost" size="sm" class="text-destructive hover:text-destructive" @click="deleting = o">刪除</Button>
            </TableCell>
          </TableRow>
          <TableRow v-if="!loading && orders.length === 0">
            <TableCell colspan="6" class="text-muted-foreground py-16 text-center">
              沒有訂單——按右上「＋ 新增訂單」開第一張
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
      </div>

      <!-- 分頁 -->
      <div class="mt-4 flex items-center justify-between gap-4 text-sm">
        <span class="text-muted-foreground">共 {{ count }} 筆</span>
        <div class="flex items-center gap-3">
          <Button variant="outline" size="sm" :disabled="page <= 1" @click="goPage(page - 1)">上一頁</Button>
          <span class="text-muted-foreground tabular-nums">{{ page }} / {{ totalPages }}</span>
          <Button variant="outline" size="sm" :disabled="page >= totalPages" @click="goPage(page + 1)">下一頁</Button>
        </div>
      </div>
    </div>

    <!-- 新增/編輯 dialog + form -->
    <Dialog v-model:open="showForm">
      <DialogScrollContent class="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{{ editingId ? `編輯訂單 #${editingId}` : '新增訂單' }}</DialogTitle>
          <DialogDescription>選客戶、填明細；小計/總計是顯示用,存檔後以後端計算為準。</DialogDescription>
        </DialogHeader>

        <div class="flex flex-col gap-4 py-2">
          <div class="flex flex-col gap-1.5">
            <Label>客戶</Label>
            <div class="flex gap-2">
              <select v-model="form.customer_id" :class="[selectClass, 'flex-1']">
                <option value="" disabled>選擇客戶</option>
                <option v-for="c in customers" :key="c.id" :value="c.id">{{ c.name }}</option>
              </select>
              <Button variant="outline" @click="showNewCustomer = !showNewCustomer">＋ 新客戶</Button>
            </div>
            <div v-if="showNewCustomer" class="bg-muted flex gap-2 rounded-md p-2">
              <Input v-model="newCustomer.name" placeholder="客戶姓名" />
              <Input v-model="newCustomer.phone" placeholder="電話（選填）" />
              <Button @click="submitNewCustomer">建立</Button>
            </div>
          </div>

          <div class="flex flex-col gap-2">
            <Label>明細（小計 = 數量 × 單價,自動算）</Label>
            <div v-for="(item, idx) in form.items" :key="idx" class="flex items-center gap-2">
              <Input v-model="item.name" placeholder="品項名" class="flex-1" />
              <Input v-model.number="item.quantity" type="number" min="1" class="w-20" />
              <span class="text-muted-foreground">×</span>
              <Input v-model.number="item.unit_price" type="number" min="0" class="w-28" />
              <span class="text-muted-foreground w-24 text-right text-sm tabular-nums">= {{ itemSubtotal(item).toLocaleString() }}</span>
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

    <!-- 刪除確認 dialog -->
    <Dialog :open="!!deleting" @update:open="(v) => { if (!v) deleting = null }">
      <DialogContent class="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>刪除訂單 #{{ deleting?.id }}？</DialogTitle>
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
