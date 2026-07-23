<script setup>
// 訂單詳細頁（唯讀檢視 + 狀態機動作）。參考 top-admin 的 OrderDetailView 骨架、精簡版：
//   回上頁 header ＋「下一步」推進鈕（收款/出貨）＋ 取消；下面兩張卡（摘要 / 明細）。
// 狀態機動作直接照後端回的 available_actions 長——合法才顯示按鈕，非法後端擋（422）。
// 編輯走另一頁（/orders/:id/edit）；這裡只做「看 + 推狀態」。
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Pencil } from '@lucide/vue'
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

// 狀態文字樣式：進行中粗體黑、終態灰（跟清單一致）。
const statusClass = (s) => (s === 'PENDING' || s === 'AWAITING' ? 'font-medium text-foreground' : 'text-muted-foreground')
// 合法動作由後端回（available_actions）：有 pay/ship 才顯示推進鈕、有 cancel 才顯示取消。
const has = (a) => order.value?.available_actions?.includes(a) ?? false
// 非終態（還有動作可做）＝可編輯。
const isEditable = computed(() => (order.value?.available_actions?.length ?? 0) > 0)

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
    <!-- 回上頁 header：返回 + 單號 + 狀態 + 動作區（靠右）-->
    <div class="flex shrink-0 items-center gap-3">
      <Button variant="ghost" size="icon-sm" title="返回訂單列表" @click="router.push('/orders')">
        <ArrowLeft class="size-4" />
      </Button>
      <h1 class="text-lg font-semibold leading-none tracking-tight">訂單 {{ order?.order_no || '' }}</h1>
      <span v-if="order" :class="statusClass(order.status)" class="text-sm">· {{ order.status_display }}</span>

      <div v-if="order" class="ml-auto flex items-center gap-2">
        <Button v-if="has('pay')" :disabled="acting" @click="doAction('pay')">收款</Button>
        <Button v-if="has('ship')" :disabled="acting" @click="doAction('ship')">出貨</Button>
        <Button v-if="isEditable" variant="outline" :disabled="acting" @click="router.push(`/orders/${order.id}/edit`)">
          <Pencil class="size-4" /> 編輯
        </Button>
        <Button v-if="has('cancel')" variant="outline" class="text-destructive hover:text-destructive" :disabled="acting" @click="showCancel = true">
          取消訂單
        </Button>
      </div>
    </div>

    <p v-if="errorMsg" class="text-destructive mt-4 shrink-0 text-sm">{{ errorMsg }}</p>

    <!-- 載入中：有質感的品牌 loading -->
    <LoadingState v-if="loading" class="mt-5" />

    <!-- 內容 -->
    <div v-else-if="order" class="mt-5 flex min-h-0 flex-1 flex-col gap-4 overflow-auto">
      <!-- 摘要卡 -->
      <div class="shrink-0 rounded-lg border bg-card p-5 shadow-sm">
        <dl class="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-4">
          <div><dt class="text-muted-foreground text-xs">客戶</dt><dd class="mt-1 font-medium">{{ order.member.name }}</dd></div>
          <div><dt class="text-muted-foreground text-xs">電話</dt><dd class="mt-1 tabular-nums">{{ order.member.phone || '—' }}</dd></div>
          <div><dt class="text-muted-foreground text-xs">下訂日期</dt><dd class="mt-1 tabular-nums">{{ order.order_date }}</dd></div>
          <div><dt class="text-muted-foreground text-xs">修改日期</dt><dd class="mt-1 tabular-nums">{{ order.updated_at }}</dd></div>
          <div class="col-span-2 sm:col-span-4"><dt class="text-muted-foreground text-xs">備註</dt><dd class="mt-1">{{ order.note || '—' }}</dd></div>
        </dl>
      </div>

      <!-- 明細卡 -->
      <div class="flex min-h-0 flex-col overflow-hidden rounded-lg border bg-card shadow-sm">
        <div class="shrink-0 border-b px-5 py-3 text-sm font-medium">明細</div>
        <div class="scroll-thin min-h-0 flex-1 overflow-auto">
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
                <TableCell class="text-right tabular-nums">{{ it.unit_price.toLocaleString() }}</TableCell>
                <TableCell class="text-right tabular-nums">{{ it.quantity }}</TableCell>
                <TableCell class="text-right tabular-nums">{{ it.subtotal.toLocaleString() }}</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
        <!-- 總計列（已收 / 總計）-->
        <div class="flex shrink-0 items-center justify-end gap-8 border-t px-5 py-3 text-sm">
          <span class="text-muted-foreground">已收 <span class="text-foreground tabular-nums">{{ order.paid_amount.toLocaleString() }}</span></span>
          <span class="font-semibold">總計 <span class="tabular-nums">{{ order.total.toLocaleString() }}</span></span>
        </div>
      </div>
    </div>

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
  </div>
</template>
