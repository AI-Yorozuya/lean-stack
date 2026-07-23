<script setup>
// 訂單頁（一個檔吃三模式，跟 ns/top 一樣不另開編輯檔）：
//   /orders/:id 檢視、/orders/:id/edit 編輯（未出貨可改）、/orders/new 新增。
// 檢視/新增/編輯共用同一套骨架（框線描述格 + 明細表 + 收款三欄），只有「該編輯的格子」在編輯時換成輸入/挑選。
// 會員、商品都用「彈出對話框搜尋分頁挑選」；狀態機動作照後端 available_actions 顯示（非法後端擋 422）。
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Pencil, Printer, Plus, X, Search } from '@lucide/vue'
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
import PillButton from '@/components/PillButton.vue'
import CustomerSelectDialog from '@/components/CustomerSelectDialog.vue'
import ProductSelectDialog from '@/components/ProductSelectDialog.vue'
import logoUrl from '@/assets/yorozuya-logo.png' // AI 萬事屋 logo（列印單據抬頭用）

const route = useRoute()
const router = useRouter()

const mode = computed(() => {
  if (route.name === 'order-new') return 'create'
  if (route.name === 'order-edit') return 'edit'
  return 'view'
})
const isCreate = computed(() => mode.value === 'create')
const editing = computed(() => mode.value !== 'view')
const orderId = computed(() => (route.params.id ? Number(route.params.id) : null))

const order = ref(null)
const loading = ref(true)
const errorMsg = ref('')
const acting = ref(false)

const form = reactive({ member_id: '', items: [] })
const formError = ref('')
const saving = ref(false)
const selectedMember = ref(null)
const showCustomerDialog = ref(false)
const showProductDialog = ref(false)

const money = (n) => Number(n).toLocaleString()
const itemSubtotal = (i) => (Number(i.quantity) || 0) * Number(i.unit_price)
const formTotal = computed(() => form.items.reduce((s, i) => s + itemSubtotal(i), 0))

// 合法動作由後端回（available_actions）：有 pay/ship 才顯示推進鈕、有 cancel 才顯示取消。
const has = (a) => order.value?.available_actions?.includes(a) ?? false
// 未出貨/未取消可編輯（跟後端 update_order 的 is_editable 一致）。
const isEditable = computed(() => !!order.value && order.value.status !== 'SHIPPED' && order.value.status !== 'CANCELLED')

// 檢視／編輯共用的顯示值分流：會員（檢視看 order.member、新增/編輯看 selectedMember）、明細列、金額。
const mem = computed(() => (mode.value === 'view' ? order.value?.member : selectedMember.value))
const displayItems = computed(() =>
  editing.value ? form.items.map((i) => ({ ...i, subtotal: itemSubtotal(i) })) : order.value?.items || [],
)
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
}
function syncFormFromOrder(o) {
  selectedMember.value = o.member
  form.member_id = String(o.member.id)
  form.items = o.items.map((i) => ({ product_id: i.product_id, name: i.name, unit_price: i.unit_price, quantity: i.quantity }))
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

async function doAction(action) {
  acting.value = true
  errorMsg.value = ''
  try {
    order.value = await transitionOrder(orderId.value, action)
    if (mode.value === 'edit') router.push(`/orders/${orderId.value}`) // 從編輯頁推狀態後導回詳細頁看結果
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || '操作失敗,請稍後再試'
    console.error(e)
  } finally {
    acting.value = false
  }
}
function printOrder() {
  window.print()
}
const showCancel = ref(false)
async function confirmCancel() {
  showCancel.value = false
  await doAction('cancel')
}

function removeItem(idx) {
  form.items.splice(idx, 1)
}
function onSelectCustomer(m) {
  selectedMember.value = m
  form.member_id = String(m.id)
}
function onSelectProduct(p) {
  const exist = form.items.find((i) => String(i.product_id) === String(p.id))
  if (exist) exist.quantity += 1
  else form.items.push({ product_id: p.id, name: p.name, unit_price: p.unit_price, quantity: 1 })
}
async function submitForm() {
  formError.value = ''
  if (!form.member_id) {
    formError.value = '請選擇會員'
    return
  }
  if (!form.items.length) {
    formError.value = '請至少加一項商品'
    return
  }
  saving.value = true
  const payload = {
    member_id: Number(form.member_id),
    items: form.items.map((i) => ({ product_id: Number(i.product_id), quantity: Number(i.quantity) })),
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
    <!-- header：返回 ｜垂直分隔線｜ 標題（狀態） ｜ 訂單操作 label+膠囊鈕 ｜ 列印(方形,最右) -->
    <div class="flex shrink-0 flex-wrap items-center gap-2">
      <Button variant="outline" size="sm" class="no-print min-w-28 rounded-full" @click="goBack"><ArrowLeft class="size-4" /> 回上一頁</Button>
      <div class="bg-border mx-1 h-6 w-px shrink-0"></div>
      <h1 class="text-lg font-semibold leading-none tracking-tight">
        {{ headerTitle }}<span v-if="order">（{{ order.status_display }}）</span>
      </h1>

      <div v-if="order" class="no-print ml-10 flex flex-wrap items-center gap-2">
        <span class="text-muted-foreground text-sm">訂單操作：</span>
        <PillButton v-if="has('pay')" :disabled="acting" @click="doAction('pay')">收款</PillButton>
        <PillButton v-if="has('ship')" :disabled="acting" @click="doAction('ship')">出貨</PillButton>
        <PillButton v-if="isEditable && mode === 'view'" variant="outline" :disabled="acting" @click="goEdit"><Pencil class="size-4" /> 編輯</PillButton>
        <PillButton v-if="has('cancel')" variant="outline" class="text-destructive hover:text-destructive" :disabled="acting" @click="showCancel = true">取消</PillButton>
      </div>
      <Button v-if="order" variant="outline" size="sm" class="no-print ml-auto" @click="printOrder"><Printer class="size-4" /> 列印訂單</Button>
    </div>

    <p v-if="errorMsg" class="text-destructive mt-4 shrink-0 text-sm">{{ errorMsg }}</p>
    <LoadingState v-if="loading" class="mt-5" />

    <template v-else-if="order || isCreate">
      <div class="mt-5 flex min-h-0 flex-1 flex-col gap-4">
        <!-- 會員卡（框線 descriptions；只有會員名稱在編輯時可挑，其餘唯讀）-->
        <div class="shrink-0 overflow-hidden rounded-lg border bg-card shadow-sm">
          <div class="border-b px-4 py-2.5 text-sm font-semibold">會員</div>
          <dl class="grid grid-cols-1 text-sm sm:grid-cols-2">
            <div class="flex border-b sm:col-span-2">
              <dt class="text-muted-foreground w-24 shrink-0 border-r bg-muted/40 px-3 py-2">會員名稱</dt>
              <dd class="flex-1">
                <span v-if="mode === 'view'" class="block px-3 py-2 font-medium">{{ order.member.name }}</span>
                <button v-else type="button" class="hover:bg-muted/30 flex h-9 w-full cursor-pointer items-center justify-between px-3 text-sm transition-colors" @click="showCustomerDialog = true">
                  <span :class="mem ? 'font-medium' : 'text-muted-foreground'">{{ mem ? mem.name : '搜尋 / 選擇會員…' }}</span>
                  <Search class="text-muted-foreground size-4" />
                </button>
              </dd>
            </div>
            <div class="flex border-b">
              <dt class="text-muted-foreground w-24 shrink-0 border-r bg-muted/40 px-3 py-2">會員電話</dt>
              <dd class="flex-1 px-3 py-2 tabular-nums">{{ mem?.phone || '—' }}</dd>
            </div>
            <div class="flex border-b sm:border-l">
              <dt class="text-muted-foreground w-24 shrink-0 border-r bg-muted/40 px-3 py-2">下訂日期</dt>
              <dd class="flex-1 px-3 py-2 tabular-nums">{{ order?.order_date || '—' }}</dd>
            </div>
            <div class="flex sm:col-span-2">
              <dt class="text-muted-foreground w-24 shrink-0 border-r bg-muted/40 px-3 py-2">備註</dt>
              <dd class="flex-1 px-3 py-2">{{ order?.note || '—' }}</dd>
            </div>
          </dl>
        </div>

        <!-- 明細卡：檢視／編輯共用 3-table（撐滿剩餘高度、保底 min-h-64，視窗太矮改整頁捲動）-->
        <div class="flex min-h-64 flex-1 flex-col overflow-hidden rounded-lg border bg-card shadow-sm">
          <div class="flex shrink-0 items-center justify-between border-b px-4 py-2.5">
            <span class="text-sm font-semibold">明細</span>
            <Button v-if="editing" variant="outline" size="sm" @click="showProductDialog = true"><Plus class="size-4" /> 新增商品</Button>
          </div>
          <div class="scroll-thin shrink-0 overflow-x-hidden overflow-y-scroll border-b bg-card">
            <Table class="table-fixed [&_th]:border-b-0">
              <colgroup><col /><col class="w-28" /><col class="w-24" /><col class="w-32" /><col class="w-12" /></colgroup>
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
          <div class="scroll-thin min-h-0 flex-1 overflow-y-scroll">
            <Table class="table-fixed [&_thead]:hidden">
              <colgroup><col /><col class="w-28" /><col class="w-24" /><col class="w-32" /><col class="w-12" /></colgroup>
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
                  <TableCell colspan="5" class="text-muted-foreground py-10 text-center">{{ editing ? '還沒有商品——按右上「＋ 新增商品」挑一項' : '沒有商品' }}</TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </div>
          <div class="scroll-thin shrink-0 overflow-x-hidden overflow-y-scroll border-t bg-card">
            <Table class="table-fixed [&_td]:border-b-0">
              <colgroup><col /><col class="w-28" /><col class="w-24" /><col class="w-32" /><col class="w-12" /></colgroup>
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

        <!-- 收款卡 -->
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

      <p v-if="editing && formError" class="text-destructive mt-3 shrink-0 text-sm">{{ formError }}</p>
      <div v-if="editing" class="mt-3 flex shrink-0 justify-end gap-2">
        <Button variant="outline" size="sm" class="min-w-24" @click="goBack">取消</Button>
        <Button :disabled="saving" size="sm" class="min-w-24" @click="submitForm">儲存</Button>
      </div>
    </template>

    <!-- 選會員 / 選商品對話框（編輯模式用）-->
    <CustomerSelectDialog v-model:open="showCustomerDialog" @select="onSelectCustomer" />
    <ProductSelectDialog v-model:open="showProductDialog" @select="onSelectProduct" />

    <!-- 取消確認 -->
    <Dialog :open="showCancel" @update:open="(v) => { if (!v) showCancel = false }">
      <DialogContent class="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>取消訂單 {{ order?.order_no }}？</DialogTitle>
          <DialogDescription>取消後進入「已取消」終態、不可再改（出貨前才可取消）。</DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" @click="showCancel = false">不取消</Button>
          <Button variant="destructive" :disabled="acting" @click="confirmCancel">確定取消訂單</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- 列印單據：teleport 到 body，螢幕上隱藏、只有列印時整頁顯示（抬頭用 AI 萬事屋）-->
    <Teleport to="body">
      <div v-if="order" class="print-doc">
        <div class="pd-head">
          <img :src="logoUrl" alt="AI 萬事屋" class="pd-logo" />
          <div class="pd-company">AI 萬事屋</div>
          <div class="pd-sub">報價・訂單・收款一條龍　｜　service@ai-yorozuya.com</div>
        </div>
        <h2 class="pd-title">訂單 {{ order.order_no }}</h2>
        <table class="pd-info">
          <tbody>
            <tr><th>會員名稱</th><td>{{ order.member.name }}</td><th>下訂日期</th><td>{{ order.order_date }}</td></tr>
            <tr><th>會員電話</th><td>{{ order.member.phone || '—' }}</td><th>訂單狀態</th><td>{{ order.status_display }}</td></tr>
            <tr><th>備註</th><td colspan="3">{{ order.note || '—' }}</td></tr>
          </tbody>
        </table>
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
