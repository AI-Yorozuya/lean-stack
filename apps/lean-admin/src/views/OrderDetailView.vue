<script setup>
// 訂單詳細頁（唯讀檢視 + 狀態機動作）。版面參考 top-erp / ns-erp 的訂單詳細：
//   header（單號 + 彩色狀態徽章 + 動作鈕）→ 金額摘要 band（總額/已收/未收，先講錢）
//   → 基本資料（框線 descriptions 格）→ 明細表。客戶名連到「客戶帳款」（會計連結）。
// 狀態機動作照後端回的 available_actions 長——合法才顯示按鈕，非法後端擋（422）。
// 編輯走另一頁（只有待付款可編輯）；這裡只做「看 + 推狀態」。
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Pencil, ArrowUpRight } from '@lucide/vue'
import { getOrder, transitionOrder } from '@/api/order'
import { Button } from '@/components/ui/button'
import LoadingState from '@/components/LoadingState.vue'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'

const route = useRoute()
const router = useRouter()
const orderId = Number(route.params.id)

const order = ref(null)
const loading = ref(true)
const errorMsg = ref('')
const acting = ref(false)

const money = (n) => Number(n).toLocaleString()
// 狀態徽章：進行中的兩狀態各給一個語意色，終態走灰——一眼看出這單走到哪。
const STATUS_BADGE = {
  PENDING: 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300',
  AWAITING: 'bg-blue-100 text-blue-800 dark:bg-blue-950/60 dark:text-blue-300',
  SHIPPED: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300',
  CANCELLED: 'bg-muted text-muted-foreground',
}
const badgeClass = (s) => STATUS_BADGE[s] || 'bg-muted text-muted-foreground'
// 合法動作由後端回（available_actions）：有 pay/ship 才顯示推進鈕、有 cancel 才顯示取消。
const has = (a) => order.value?.available_actions?.includes(a) ?? false
// 只有待付款（未收款）可編輯——收款後鎖定明細（跟後端 EDITABLE_STATUSES 一致）。
const isEditable = computed(() => order.value?.status === 'PENDING')
// 這張訂單的未收餘額 = 總額 − 已收（帳款那邊是客戶層級總帳，這裡看單筆）。
const outstanding = computed(() => (order.value ? order.value.total - order.value.paid_amount : 0))

async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    order.value = await getOrder(orderId)
  } catch (e) {
    errorMsg.value = '載入失敗,請稍後再試'
    console.error(e)
  } finally {
    loading.value = false
  }
}
onMounted(load)

async function doAction(action) {
  acting.value = true
  errorMsg.value = ''
  try {
    order.value = await transitionOrder(orderId, action) // 回傳更新後的訂單（含新的 available_actions）
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || '操作失敗,請稍後再試'
    console.error(e)
  } finally {
    acting.value = false
  }
}

// 取消是終態、不可逆 → 先確認
const showCancel = ref(false)
async function confirmCancel() {
  showCancel.value = false
  await doAction('cancel')
}
</script>

<template>
  <div class="flex h-full flex-col">
    <!-- 回上頁 header：返回 + 單號 + 彩色狀態徽章 + 動作區（靠右）-->
    <div class="flex shrink-0 items-center gap-3">
      <Button variant="ghost" size="icon-sm" title="返回訂單列表" @click="router.push('/orders')">
        <ArrowLeft class="size-4" />
      </Button>
      <h1 class="text-lg font-semibold leading-none tracking-tight">訂單 {{ order?.order_no || '' }}</h1>
      <span
        v-if="order"
        :class="['inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium', badgeClass(order.status)]"
      >{{ order.status_display }}</span>

      <div v-if="order" class="ml-auto flex items-center gap-2">
        <Button v-if="has('pay')" :disabled="acting" @click="doAction('pay')">收款</Button>
        <Button v-if="has('ship')" :disabled="acting" @click="doAction('ship')">出貨</Button>
        <Button v-if="isEditable" variant="outline" :disabled="acting" @click="router.push(`/orders/${order.id}/edit`)">
          <Pencil class="size-4" /> 編輯
        </Button>
        <Button v-if="has('cancel')" variant="outline" class="text-destructive hover:text-destructive" :disabled="acting" @click="showCancel = true">
          作廢
        </Button>
      </div>
    </div>

    <p v-if="errorMsg" class="text-destructive mt-4 shrink-0 text-sm">{{ errorMsg }}</p>

    <!-- 載入中：有質感的品牌 loading -->
    <LoadingState v-if="loading" class="mt-5" />

    <!-- 內容 -->
    <div v-else-if="order" class="mt-5 flex min-h-0 flex-1 flex-col gap-4 overflow-auto">
      <!-- 上排兩張卡：客戶 ｜ 收貨 -->
      <div class="grid shrink-0 gap-4 lg:grid-cols-2">
        <!-- 客戶卡 -->
        <div class="rounded-lg border bg-card shadow-sm">
          <div class="border-b px-5 py-3 text-sm font-medium">客戶</div>
          <dl class="grid grid-cols-2 gap-x-6 gap-y-4 p-5 text-sm">
            <div class="col-span-2">
              <dt class="text-muted-foreground text-xs">客戶名稱</dt>
              <dd class="mt-1">
                <button type="button" class="hover:text-primary inline-flex items-center gap-1 font-medium hover:underline" @click="router.push(`/billing/customers/${order.member.id}`)">
                  {{ order.member.name }} <ArrowUpRight class="size-3.5 opacity-60" />
                </button>
              </dd>
            </div>
            <div><dt class="text-muted-foreground text-xs">客戶電話</dt><dd class="mt-1 tabular-nums">{{ order.member.phone || '—' }}</dd></div>
            <div><dt class="text-muted-foreground text-xs">下訂日期</dt><dd class="mt-1 tabular-nums">{{ order.order_date }}</dd></div>
            <div><dt class="text-muted-foreground text-xs">聯絡人</dt><dd class="mt-1">{{ order.contact_name || '—' }}</dd></div>
            <div><dt class="text-muted-foreground text-xs">聯絡人電話</dt><dd class="mt-1 tabular-nums">{{ order.contact_phone || '—' }}</dd></div>
          </dl>
        </div>

        <!-- 收貨卡 -->
        <div class="rounded-lg border bg-card shadow-sm">
          <div class="border-b px-5 py-3 text-sm font-medium">收貨</div>
          <dl class="grid grid-cols-1 gap-y-4 p-5 text-sm">
            <div><dt class="text-muted-foreground text-xs">收貨地址</dt><dd class="mt-1">{{ order.shipping_address || '—' }}</dd></div>
            <div><dt class="text-muted-foreground text-xs">預計出貨日</dt><dd class="mt-1 tabular-nums">{{ order.expected_ship_date || '—' }}</dd></div>
            <div><dt class="text-muted-foreground text-xs">備註</dt><dd class="mt-1">{{ order.note || '—' }}</dd></div>
          </dl>
        </div>
      </div>

      <!-- 品項卡（bordered table，隨內容展開；整頁捲動）-->
      <div class="shrink-0 overflow-hidden rounded-lg border bg-card shadow-sm">
        <div class="border-b px-5 py-3 text-sm font-medium">品項</div>
        <div class="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>品名</TableHead>
                <TableHead class="text-right">單價</TableHead>
                <TableHead class="text-right">數量</TableHead>
                <TableHead class="text-right">小計</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="it in order.items" :key="it.id">
                <TableCell class="font-medium">{{ it.name }}</TableCell>
                <TableCell class="text-right tabular-nums">{{ money(it.unit_price) }}</TableCell>
                <TableCell class="text-right tabular-nums">{{ it.quantity }}</TableCell>
                <TableCell class="text-right tabular-nums">{{ money(it.subtotal) }}</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
        <div class="flex items-center justify-end border-t px-5 py-3 text-sm">
          <span class="font-semibold">總計 <span class="tabular-nums">{{ money(order.total) }}</span></span>
        </div>
      </div>

      <!-- 收款卡（金額）-->
      <div class="shrink-0 overflow-hidden rounded-lg border bg-card shadow-sm">
        <div class="border-b px-5 py-3 text-sm font-medium">收款</div>
        <div class="grid grid-cols-3 divide-x">
          <div class="px-5 py-4">
            <div class="text-muted-foreground text-xs">訂單總額</div>
            <div class="mt-1 text-lg font-semibold tabular-nums">{{ money(order.total) }}</div>
          </div>
          <div class="px-5 py-4">
            <div class="text-muted-foreground text-xs">已收</div>
            <div class="mt-1 text-lg font-semibold tabular-nums">{{ money(order.paid_amount) }}</div>
          </div>
          <div class="px-5 py-4">
            <div class="text-muted-foreground text-xs">未收餘額</div>
            <div class="mt-1 text-lg font-semibold tabular-nums" :class="outstanding > 0 ? 'text-foreground' : 'text-muted-foreground'">{{ money(outstanding) }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 作廢確認 -->
    <Dialog :open="showCancel" @update:open="(v) => { if (!v) showCancel = false }">
      <DialogContent class="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>作廢訂單 {{ order?.order_no }}？</DialogTitle>
          <DialogDescription>作廢後進入「已取消」終態、不可再改，並沖銷這張訂單還沒收的應收（帳務軌跡保留）。</DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" @click="showCancel = false">不作廢</Button>
          <Button variant="destructive" :disabled="acting" @click="confirmCancel">確定作廢</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
