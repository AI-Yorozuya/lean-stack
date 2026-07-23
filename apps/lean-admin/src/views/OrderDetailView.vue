<script setup>
// 訂單頁（一個檔吃三模式，跟 ns/top 一樣不另開編輯檔）：
//   /orders/:id       檢視 —— 唯讀
//   /orders/:id/edit  編輯 —— 只有待付款可改（後端 update_order 擋非法回 422）
//   /orders/new       新增 —— 空表單
// 關鍵：檢視／新增／編輯共用「同一套版面骨架」（框線描述格 + 3-table 品項 + 收款三欄），
//   只有「該編輯的格子」在編輯時換成嵌在格子裡的輸入框——所以三個模式長得一模一樣。
// 檢視↔編輯共用同一份已載入的 order：切換不重抓、不閃 loading。
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, ArrowUpRight, Pencil, Printer, Plus, X, Search } from '@lucide/vue'
import { getOrder, transitionOrder, createOrder, updateOrder } from '@/api/order'
import { Button } from '@/components/ui/button'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import LoadingState from '@/components/LoadingState.vue'
import NumberInput from '@/components/NumberInput.vue'
import DatePicker from '@/components/DatePicker.vue'
import PillButton from '@/components/PillButton.vue'
import CustomerSelectDialog from '@/components/CustomerSelectDialog.vue'
import ProductSelectDialog from '@/components/ProductSelectDialog.vue'
import logoUrl from '@/assets/yorozuya-logo.png' // AI 萬事屋 logo（列印單據抬頭用）

const route = useRoute()
const router = useRouter()

// 模式看 route name（三條路由都指到本檔）
const mode = computed(() => {
  if (route.name === 'order-new') return 'create'
  if (route.name === 'order-edit') return 'edit'
  return 'view'
})
const isCreate = computed(() => mode.value === 'create')
const editing = computed(() => mode.value !== 'view')
const orderId = computed(() => (route.params.id ? Number(route.params.id) : null))

const order = ref(null) // 已載入的訂單（檢視顯示 + 編輯預填 + 抬頭單號共用）
const loading = ref(true)
const errorMsg = ref('')
const acting = ref(false) // 檢視：推狀態中

// 編輯表單。明細品項自帶 name/unit_price 快照（挑選當下抄一份），顯示與算小計都不靠外部產品清單。
const form = reactive({ member_id: '', items: [], contact_name: '', contact_phone: '', shipping_address: '', expected_ship_date: '' })
const formError = ref('')
const saving = ref(false)
const selectedMember = ref(null)
const showCustomerDialog = ref(false)
const showProductDialog = ref(false)

const money = (n) => Number(n).toLocaleString()
const itemSubtotal = (i) => (Number(i.quantity) || 0) * Number(i.unit_price)
const formTotal = computed(() => form.items.reduce((sum, i) => sum + itemSubtotal(i), 0))

// 合法動作由後端回（available_actions）：有 pay/ship 才顯示推進鈕、有 cancel 才顯示取消。
const has = (a) => order.value?.available_actions?.includes(a) ?? false
// 只有待付款（未收款）可編輯——收款後鎖定明細（跟後端 EDITABLE_STATUSES 一致）。
const isEditable = computed(() => order.value?.status === 'PENDING')

// ── 檢視／編輯共用的顯示值（同一套骨架就靠這幾個 computed 分流）──
// 客戶：檢視看 order.member，新增/編輯看 selectedMember（載入時抄自 order.member）。
const cust = computed(() => (mode.value === 'view' ? order.value?.member : selectedMember.value))
// 明細列：編輯用 form.items（小計前端即時算），檢視用 order.items（小計後端算好）。
const displayItems = computed(() =>
  editing.value ? form.items.map((i) => ({ ...i, subtotal: itemSubtotal(i) })) : order.value?.items || [],
)
// 金額：編輯用即時 formTotal，檢視用後端 total。
const orderTotal = computed(() => (editing.value ? formTotal.value : order.value?.total || 0))
const paidAmount = computed(() => order.value?.paid_amount || 0)
const outstandingAmount = computed(() => orderTotal.value - paidAmount.value)

const headerTitle = computed(() => {
  if (isCreate.value) return '新增訂單'
  if (mode.value === 'edit') return `編輯訂單 ${order.value?.order_no || ''}`
  return `訂單 ${order.value?.order_no || ''}`
})

function resetForm() {
  form.member_id = ''
  form.items = []
  form.contact_name = ''
  form.contact_phone = ''
  form.shipping_address = ''
  form.expected_ship_date = ''
}
function syncFormFromOrder(o) {
  selectedMember.value = o.member
  form.member_id = String(o.member.id)
  form.items = o.items.map((i) => ({ product_id: i.product_id, name: i.name, unit_price: i.unit_price, quantity: i.quantity }))
  form.contact_name = o.contact_name || ''
  form.contact_phone = o.contact_phone || ''
  form.shipping_address = o.shipping_address || ''
  form.expected_ship_date = o.expected_ship_date || ''
}

// 進頁/切模式時初始化。新增 → 空表單不打 API；已載入同一張 → 只同步表單不重抓（view↔edit 不閃 loading）。
async function init() {
  errorMsg.value = ''
  formError.value = ''
  if (isCreate.value) {
    order.value = null
    selectedMember.value = null
    resetForm()
    loading.value = false
    return
  }
  const id = orderId.value
  if (order.value && order.value.id === id) {
    syncFormFromOrder(order.value)
    loading.value = false
    return
  }
  loading.value = true
  try {
    const o = await getOrder(id)
    order.value = o
    syncFormFromOrder(o)
  } catch (e) {
    errorMsg.value = '載入失敗,請稍後再試'
    console.error(e)
  } finally {
    loading.value = false
  }
}
watch(() => [route.name, route.params.id], init, { immediate: true })

function goBack() {
  router.push('/orders')
}
function goEdit() {
  router.push(`/orders/${order.value.id}/edit`)
}

// ── 狀態機動作（收款/出貨/作廢）──
async function doAction(action) {
  acting.value = true
  errorMsg.value = ''
  try {
    order.value = await transitionOrder(orderId.value, action) // 回傳更新後的訂單（含新的 available_actions）
    // 從編輯頁推狀態後，導回詳細頁看結果（避免停在一個已不可編輯的表單上）。
    if (mode.value === 'edit') router.push(`/orders/${orderId.value}`)
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || '操作失敗,請稍後再試'
    console.error(e)
  } finally {
    acting.value = false
  }
}
// 列印訂單：叫瀏覽器列印（配 @media print 樣式，只印訂單內容、藏側欄/按鈕）。
function printOrder() {
  window.print()
}
// 取消是終態、不可逆 → 先確認
const showCancel = ref(false)
async function confirmCancel() {
  showCancel.value = false
  await doAction('cancel')
}

// ── 編輯：表單 ──
function removeItem(idx) {
  form.items.splice(idx, 1)
}
function onSelectCustomer(m) {
  selectedMember.value = m
  form.member_id = String(m.id)
}
// 挑到產品：已在明細就數量 +1，否則新增一列（抄品名/單價快照）。
function onSelectProduct(p) {
  const exist = form.items.find((i) => String(i.product_id) === String(p.id))
  if (exist) exist.quantity += 1
  else form.items.push({ product_id: p.id, name: p.name, unit_price: p.unit_price, quantity: 1 })
}
async function submitForm() {
  formError.value = ''
  if (!form.member_id) {
    formError.value = '請選擇客戶'
    return
  }
  if (!form.items.length) {
    formError.value = '請至少加一項產品'
    return
  }
  saving.value = true
  const payload = {
    member_id: Number(form.member_id),
    items: form.items.map((i) => ({ product_id: Number(i.product_id), quantity: Number(i.quantity) })),
    contact_name: form.contact_name,
    contact_phone: form.contact_phone,
    shipping_address: form.shipping_address,
    expected_ship_date: form.expected_ship_date || null,
  }
  try {
    if (isCreate.value) await createOrder(payload)
    else await updateOrder(orderId.value, payload)
    goBack()
  } catch (e) {
    formError.value = e.response?.data?.detail || '儲存失敗,請稍後再試'
    console.error(e)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="flex min-h-full flex-col">
    <!-- header（參考 ns-admin 訂單詳細）：返回 ｜垂直分隔線｜ 標題（狀態） ｜ 訂單操作 label+膠囊鈕 ｜ 列印(方形,最右) -->
    <div class="flex shrink-0 flex-wrap items-center gap-2">
      <Button variant="outline" size="sm" class="no-print min-w-28 rounded-full" @click="goBack"><ArrowLeft class="size-4" /> 回上一頁</Button>
      <!-- 垂直分隔線：隔開返回鈕與標題（同 ns el-page-header）-->
      <div class="bg-border mx-1 h-6 w-px shrink-0"></div>
      <!-- 狀態緊接編號後、字體大小顏色跟編號一致（同一個 h1 樣式，不縮小不變灰）-->
      <h1 class="text-lg font-semibold leading-none tracking-tight">
        {{ headerTitle }}<span v-if="order">（{{ order.status_display }}）</span>
      </h1>

      <!-- 訂單操作：label(冒號) + 膠囊鈕（整體往右；收款/出貨/編輯/作廢共用 PillButton、寬度一致可容五字）-->
      <div v-if="order" class="no-print ml-10 flex flex-wrap items-center gap-2">
        <span class="text-muted-foreground text-sm">訂單操作：</span>
        <PillButton v-if="has('pay')" :disabled="acting" @click="doAction('pay')">收款</PillButton>
        <PillButton v-if="has('ship')" :disabled="acting" @click="doAction('ship')">出貨</PillButton>
        <!-- 編輯鈕只在檢視模式出現（已在編輯頁再按編輯沒意義）-->
        <PillButton v-if="isEditable && mode === 'view'" variant="outline" :disabled="acting" @click="goEdit"><Pencil class="size-4" /> 編輯</PillButton>
        <PillButton v-if="has('cancel')" variant="outline" class="text-destructive hover:text-destructive" :disabled="acting" @click="showCancel = true">作廢</PillButton>
      </div>
      <!-- 列印：方形、推到最右邊；size sm 高度跟其它 header 鈕一致（32px），只用形狀區分 -->
      <Button v-if="order" variant="outline" size="sm" class="no-print ml-auto" @click="printOrder"><Printer class="size-4" /> 列印訂單</Button>
    </div>

    <p v-if="errorMsg" class="text-destructive mt-4 shrink-0 text-sm">{{ errorMsg }}</p>
    <LoadingState v-if="loading" class="mt-5" />

    <!-- ══ 內容：檢視／新增／編輯共用同一套骨架，只有「該編輯的格子」換成輸入 ══ -->
    <template v-else-if="order || isCreate">
      <div class="mt-5 flex min-h-0 flex-1 flex-col gap-4">
        <!-- 上排兩張卡：客戶 ｜ 收貨（框線 descriptions，label 淡底）-->
        <div class="grid shrink-0 gap-4 lg:grid-cols-2">
          <!-- 客戶卡 -->
          <div class="overflow-hidden rounded-lg border bg-card shadow-sm">
            <div class="border-b px-4 py-2.5 text-sm font-semibold">客戶</div>
            <dl class="grid grid-cols-1 text-sm sm:grid-cols-2">
              <!-- 客戶名稱（跨兩欄）：檢視=連到帳款；新增=可搜尋；編輯=顯示但 disable（成立後不可換客戶）-->
              <div class="flex border-b sm:col-span-2">
                <dt class="text-muted-foreground w-24 shrink-0 border-r bg-muted/40 px-3 py-2">客戶名稱</dt>
                <dd class="flex-1">
                  <button v-if="mode === 'view'" type="button" class="hover:text-primary flex w-full cursor-pointer items-center gap-1 px-3 py-2 font-medium hover:underline" @click="router.push(`/billing/customers/${order.member.id}`)">
                    {{ order.member.name }} <ArrowUpRight class="size-3.5 opacity-60" />
                  </button>
                  <button v-else type="button" :disabled="!isCreate" class="hover:bg-muted/30 disabled:hover:bg-transparent flex h-9 w-full cursor-pointer items-center justify-between px-3 text-sm transition-colors disabled:cursor-not-allowed disabled:opacity-60" @click="showCustomerDialog = true">
                    <span :class="cust ? 'font-medium' : 'text-muted-foreground'">{{ cust ? cust.name : '搜尋 / 選擇客戶…' }}</span>
                    <Search class="text-muted-foreground size-4" />
                  </button>
                </dd>
              </div>
              <!-- 客戶電話（唯讀，取自客戶檔）-->
              <div class="flex border-b">
                <dt class="text-muted-foreground w-24 shrink-0 border-r bg-muted/40 px-3 py-2">客戶電話</dt>
                <dd class="flex-1 px-3 py-2 tabular-nums">{{ cust?.phone || '—' }}</dd>
              </div>
              <!-- 下訂日期（唯讀）-->
              <div class="flex border-b sm:border-l">
                <dt class="text-muted-foreground w-24 shrink-0 border-r bg-muted/40 px-3 py-2">下訂日期</dt>
                <dd class="flex-1 px-3 py-2 tabular-nums">{{ order?.order_date || '—' }}</dd>
              </div>
              <!-- 聯絡人（可編輯：格子內無邊框輸入）-->
              <div class="flex">
                <dt class="text-muted-foreground w-24 shrink-0 border-r bg-muted/40 px-3 py-2">聯絡人</dt>
                <dd class="flex-1">
                  <input v-if="editing" v-model="form.contact_name" class="focus:bg-muted/30 h-9 w-full bg-transparent px-3 text-sm outline-none transition-colors" />
                  <span v-else class="block px-3 py-2">{{ order.contact_name || '—' }}</span>
                </dd>
              </div>
              <!-- 聯絡人電話（可編輯）-->
              <div class="flex border-t sm:border-t-0 sm:border-l">
                <dt class="text-muted-foreground w-24 shrink-0 border-r bg-muted/40 px-3 py-2">聯絡人電話</dt>
                <dd class="flex-1">
                  <input v-if="editing" v-model="form.contact_phone" class="focus:bg-muted/30 h-9 w-full bg-transparent px-3 text-sm tabular-nums outline-none transition-colors" />
                  <span v-else class="block px-3 py-2 tabular-nums">{{ order.contact_phone || '—' }}</span>
                </dd>
              </div>
            </dl>
          </div>

          <!-- 收貨卡 -->
          <div class="overflow-hidden rounded-lg border bg-card shadow-sm">
            <div class="border-b px-4 py-2.5 text-sm font-semibold">收貨</div>
            <dl class="text-sm">
              <!-- 收貨地址（可編輯）-->
              <div class="flex border-b">
                <dt class="text-muted-foreground w-24 shrink-0 border-r bg-muted/40 px-3 py-2">收貨地址</dt>
                <dd class="flex-1">
                  <input v-if="editing" v-model="form.shipping_address" maxlength="200" class="focus:bg-muted/30 h-9 w-full bg-transparent px-3 text-sm outline-none transition-colors" />
                  <span v-else class="block px-3 py-2">{{ order.shipping_address || '—' }}</span>
                </dd>
              </div>
              <!-- 預計出貨日（可編輯：bare DatePicker 無縫嵌入格子）-->
              <div class="flex border-b">
                <dt class="text-muted-foreground w-24 shrink-0 border-r bg-muted/40 px-3 py-2">預計出貨日</dt>
                <dd class="flex-1">
                  <DatePicker v-if="editing" v-model="form.expected_ship_date" bare />
                  <span v-else class="block px-3 py-2 tabular-nums">{{ order.expected_ship_date || '—' }}</span>
                </dd>
              </div>
              <!-- 備註（唯讀顯示；本表單不改備註）-->
              <div class="flex">
                <dt class="text-muted-foreground w-24 shrink-0 border-r bg-muted/40 px-3 py-2">備註</dt>
                <dd class="flex-1 px-3 py-2">{{ order?.note || '—' }}</dd>
              </div>
            </dl>
          </div>
        </div>

        <!-- 品項卡：檢視／編輯共用 3-table；撐滿剩餘高度、但保底 min-h-64（視窗太矮不壓扁，改由整頁捲動）-->
        <div class="flex min-h-64 flex-1 flex-col overflow-hidden rounded-lg border bg-card shadow-sm">
          <div class="flex shrink-0 items-center justify-between border-b px-4 py-2.5">
            <span class="text-sm font-semibold">品項</span>
            <Button v-if="editing" variant="outline" size="sm" @click="showProductDialog = true"><Plus class="size-4" /> 新增品項</Button>
          </div>
          <!-- 表頭 -->
          <div class="scroll-thin shrink-0 overflow-x-hidden overflow-y-scroll border-b bg-card">
            <Table class="table-fixed [&_th]:border-b-0">
              <colgroup>
                <col /><col class="w-28" /><col class="w-24" /><col class="w-32" /><col class="w-12" />
              </colgroup>
              <TableHeader>
                <TableRow>
                  <TableHead>品名</TableHead>
                  <TableHead class="text-right">單價</TableHead>
                  <TableHead :class="editing ? 'text-center' : 'text-right'">數量</TableHead>
                  <TableHead class="text-right">小計</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
            </Table>
          </div>
          <!-- 表身 -->
          <div class="scroll-thin min-h-0 flex-1 overflow-y-scroll">
            <Table class="table-fixed [&_thead]:hidden">
              <colgroup>
                <col /><col class="w-28" /><col class="w-24" /><col class="w-32" /><col class="w-12" />
              </colgroup>
              <TableBody>
                <TableRow v-for="(item, idx) in displayItems" :key="item.product_id ?? item.id">
                  <TableCell class="font-medium">{{ item.name }}</TableCell>
                  <TableCell class="text-right tabular-nums">{{ money(item.unit_price) }}</TableCell>
                  <TableCell :class="editing ? 'text-center' : 'text-right tabular-nums'">
                    <NumberInput v-if="editing" v-model="form.items[idx].quantity" :min="1" />
                    <template v-else>{{ item.quantity }}</template>
                  </TableCell>
                  <TableCell class="text-right tabular-nums">{{ money(item.subtotal) }}</TableCell>
                  <TableCell class="text-center">
                    <Button v-if="editing" variant="ghost" size="icon-sm" class="text-destructive" @click="removeItem(idx)"><X class="size-4" /></Button>
                  </TableCell>
                </TableRow>
                <TableRow v-if="!displayItems.length" class="hover:bg-transparent">
                  <TableCell colspan="5" class="text-muted-foreground py-10 text-center">{{ editing ? '還沒有品項——按右上「＋ 新增品項」挑一項' : '沒有品項' }}</TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </div>
          <!-- 表尾：總計永遠釘底，同 colgroup + 預留捲軸槽對齊上表 -->
          <div class="scroll-thin shrink-0 overflow-x-hidden overflow-y-scroll border-t bg-card">
            <Table class="table-fixed [&_td]:border-b-0">
              <colgroup>
                <col /><col class="w-28" /><col class="w-24" /><col class="w-32" /><col class="w-12" />
              </colgroup>
              <TableBody>
                <TableRow class="hover:bg-transparent">
                  <TableCell></TableCell>
                  <TableCell></TableCell>
                  <TableCell class="text-right font-semibold">總計</TableCell>
                  <TableCell class="text-right font-semibold tabular-nums">{{ money(orderTotal) }}</TableCell>
                  <TableCell></TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </div>
        </div>

        <!-- 收款卡（金額）：檢視用後端數字、編輯用即時總額 -->
        <div class="shrink-0 overflow-hidden rounded-lg border bg-card shadow-sm">
          <div class="border-b px-5 py-3 text-sm font-medium">收款</div>
          <div class="grid grid-cols-3 divide-x">
            <div class="px-5 py-4">
              <div class="text-muted-foreground text-xs">訂單總額</div>
              <div class="mt-1 text-lg font-semibold tabular-nums">{{ money(orderTotal) }}</div>
            </div>
            <div class="px-5 py-4">
              <div class="text-muted-foreground text-xs">已收</div>
              <div class="mt-1 text-lg font-semibold tabular-nums">{{ money(paidAmount) }}</div>
            </div>
            <div class="px-5 py-4">
              <div class="text-muted-foreground text-xs">未收餘額</div>
              <div class="mt-1 text-lg font-semibold tabular-nums" :class="outstandingAmount > 0 ? 'text-foreground' : 'text-muted-foreground'">{{ money(outstandingAmount) }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 編輯：錯誤 + 取消/儲存（釘在內容下方，不隨內容捲動）-->
      <p v-if="editing && formError" class="text-destructive mt-3 shrink-0 text-sm">{{ formError }}</p>
      <!-- 取消/儲存：方形（rounded-md）、size sm(32px)、共用五字寬（min-w-24），跟頭部膠囊鈕區隔開 -->
      <div v-if="editing" class="mt-3 flex shrink-0 justify-end gap-2">
        <Button variant="outline" size="sm" class="min-w-24" @click="goBack">取消</Button>
        <Button :disabled="saving" size="sm" class="min-w-24" @click="submitForm">儲存</Button>
      </div>
    </template>

    <!-- 選客戶 / 選產品對話框（編輯模式用）-->
    <CustomerSelectDialog v-model:open="showCustomerDialog" @select="onSelectCustomer" />
    <ProductSelectDialog v-model:open="showProductDialog" @select="onSelectProduct" />

    <!-- 作廢確認 -->
    <Dialog :open="showCancel" @update:open="(v) => { if (!v) showCancel = false }">
      <DialogContent class="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>作廢訂單 {{ order?.order_no }}？</DialogTitle>
          <DialogDescription>作廢後進入「已取消」終態、不可再改,並沖銷這張訂單還沒收的應收(帳務軌跡保留)。</DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" @click="showCancel = false">不作廢</Button>
          <Button variant="destructive" :disabled="acting" @click="confirmCancel">確定作廢</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- 列印單據：teleport 到 body，螢幕上隱藏、只有列印時整頁顯示（參考 ns-admin 報價單，抬頭用 AI 萬事屋）-->
    <Teleport to="body">
      <div v-if="order" class="print-doc">
        <!-- 公司抬頭 -->
        <div class="pd-head">
          <img :src="logoUrl" alt="AI 萬事屋" class="pd-logo" />
          <div class="pd-company">AI 萬事屋</div>
          <div class="pd-sub">報價・訂單・收款一條龍　｜　service@ai-yorozuya.com</div>
        </div>
        <h2 class="pd-title">訂單 {{ order.order_no }}</h2>

        <!-- 客戶 / 訂單資訊 -->
        <table class="pd-info">
          <tbody>
            <tr>
              <th>客戶名稱</th><td>{{ order.member.name }}</td>
              <th>下訂日期</th><td>{{ order.order_date }}</td>
            </tr>
            <tr>
              <th>客戶電話</th><td>{{ order.member.phone || '—' }}</td>
              <th>預計出貨日</th><td>{{ order.expected_ship_date || '—' }}</td>
            </tr>
            <tr>
              <th>聯絡人</th><td>{{ order.contact_name || '—' }}</td>
              <th>聯絡人電話</th><td>{{ order.contact_phone || '—' }}</td>
            </tr>
            <tr>
              <th>收貨地址</th><td colspan="3">{{ order.shipping_address || '—' }}</td>
            </tr>
          </tbody>
        </table>

        <!-- 明細 -->
        <table class="pd-items">
          <thead>
            <tr><th class="l">品名</th><th class="r">單價</th><th class="r">數量</th><th class="r">小計</th></tr>
          </thead>
          <tbody>
            <tr v-for="it in order.items" :key="it.id">
              <td class="l">{{ it.name }}</td>
              <td class="r">{{ money(it.unit_price) }}</td>
              <td class="r">{{ it.quantity }}</td>
              <td class="r">{{ money(it.subtotal) }}</td>
            </tr>
          </tbody>
          <tfoot>
            <tr><td class="r" colspan="3">總計</td><td class="r">{{ money(order.total) }}</td></tr>
            <tr><td class="r" colspan="3">已收</td><td class="r">{{ money(order.paid_amount) }}</td></tr>
            <tr><td class="r" colspan="3">未收餘額</td><td class="r">{{ money(order.total - order.paid_amount) }}</td></tr>
          </tfoot>
        </table>

        <div class="pd-foot">本單據由 AI 萬事屋 ERP 系統開立　·　感謝您的惠顧</div>
      </div>
    </Teleport>
  </div>
</template>
