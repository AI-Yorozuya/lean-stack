<script setup>
// 報價單詳細頁（唯讀檢視 + 狀態機動作）。刻意跟 OrderDetailView 同形。
//   回上頁 header ＋「下一步」推進鈕（送出/成交）＋ 作廢；下面兩張卡（摘要 / 明細）。
// 狀態機動作直接照後端回的 available_actions 長——合法才顯示按鈕，非法後端擋（422）。
// 成交（win）＝承重牆：後端會生一張訂單，這裡把回傳的 order_id 變成一個連結，點得過去看那張訂單。
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Pencil, ArrowRight } from '@lucide/vue'
import { getQuotation, transitionQuotation } from '@/api/quotation'
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
const quotationId = Number(route.params.id)

const quotation = ref(null)
const loading = ref(true)
const errorMsg = ref('')
const acting = ref(false)

// 狀態文字樣式：進行中粗體黑、終態灰（跟清單一致）。
const statusClass = (s) => (s === 'DRAFT' || s === 'SENT' ? 'font-medium text-foreground' : 'text-muted-foreground')
// 合法動作由後端回（available_actions）：有 send/win 才顯示推進鈕、有 void 才顯示作廢。
const has = (a) => quotation.value?.available_actions?.includes(a) ?? false
// 非終態（還有動作可做）＝可編輯。
const isEditable = computed(() => (quotation.value?.available_actions?.length ?? 0) > 0)

async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    quotation.value = await getQuotation(quotationId)
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
    quotation.value = await transitionQuotation(quotationId, action) // 回傳更新後的報價（含新的 available_actions、order_id）
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || '操作失敗,請稍後再試'
    console.error(e)
  } finally {
    acting.value = false
  }
}

// 成交是終態、且會生訂單 → 先確認
const showWin = ref(false)
async function confirmWin() {
  showWin.value = false
  await doAction('win')
}
// 作廢是終態、不可逆 → 先確認
const showVoid = ref(false)
async function confirmVoid() {
  showVoid.value = false
  await doAction('void')
}
</script>

<template>
  <div class="flex h-full flex-col">
    <!-- 回上頁 header：返回 + 單號 + 狀態 + 動作區（靠右）-->
    <div class="flex shrink-0 items-center gap-3">
      <Button variant="ghost" size="icon-sm" title="返回報價單列表" @click="router.push('/quotations')">
        <ArrowLeft class="size-4" />
      </Button>
      <h1 class="text-lg font-semibold leading-none tracking-tight">報價單 {{ quotation?.quote_no || '' }}</h1>
      <span v-if="quotation" :class="statusClass(quotation.status)" class="text-sm">· {{ quotation.status_display }}</span>

      <div v-if="quotation" class="ml-auto flex items-center gap-2">
        <Button v-if="has('send')" :disabled="acting" @click="doAction('send')">送出</Button>
        <Button v-if="has('win')" :disabled="acting" @click="showWin = true">成交</Button>
        <Button v-if="isEditable" variant="outline" :disabled="acting" @click="router.push(`/quotations/${quotation.id}/edit`)">
          <Pencil class="size-4" /> 編輯
        </Button>
        <Button v-if="has('void')" variant="outline" class="text-destructive hover:text-destructive" :disabled="acting" @click="showVoid = true">
          作廢
        </Button>
      </div>
    </div>

    <p v-if="errorMsg" class="text-destructive mt-4 shrink-0 text-sm">{{ errorMsg }}</p>

    <!-- 載入中：有質感的品牌 loading -->
    <LoadingState v-if="loading" class="mt-5" />

    <!-- 內容 -->
    <div v-else-if="quotation" class="mt-5 flex min-h-0 flex-1 flex-col gap-4 overflow-auto">
      <!-- 成交後：承重牆的成果——生出來的訂單，點得過去 -->
      <div v-if="quotation.order_id" class="shrink-0 rounded-lg border border-primary/30 bg-primary/5 px-5 py-3">
        <button type="button" class="flex items-center gap-2 text-sm font-medium text-primary hover:underline" @click="router.push(`/orders/${quotation.order_id}`)">
          已成交，這張報價生成了一筆訂單 <ArrowRight class="size-4" /> 前往訂單
        </button>
      </div>

      <!-- 摘要卡 -->
      <div class="shrink-0 rounded-lg border bg-card p-5 shadow-sm">
        <dl class="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-4">
          <div><dt class="text-muted-foreground text-xs">客戶</dt><dd class="mt-1 font-medium">{{ quotation.customer.name }}</dd></div>
          <div><dt class="text-muted-foreground text-xs">電話</dt><dd class="mt-1 tabular-nums">{{ quotation.customer.phone || '—' }}</dd></div>
          <div><dt class="text-muted-foreground text-xs">建立日期</dt><dd class="mt-1 tabular-nums">{{ quotation.created_at }}</dd></div>
          <div><dt class="text-muted-foreground text-xs">修改日期</dt><dd class="mt-1 tabular-nums">{{ quotation.updated_at }}</dd></div>
          <div class="col-span-2 sm:col-span-4"><dt class="text-muted-foreground text-xs">備註</dt><dd class="mt-1">{{ quotation.note || '—' }}</dd></div>
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
              <TableRow v-for="it in quotation.items" :key="it.id">
                <TableCell class="font-medium">{{ it.name }}</TableCell>
                <TableCell class="text-right tabular-nums">{{ it.unit_price.toLocaleString() }}</TableCell>
                <TableCell class="text-right tabular-nums">{{ it.quantity }}</TableCell>
                <TableCell class="text-right tabular-nums">{{ it.subtotal.toLocaleString() }}</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
        <!-- 總計列 -->
        <div class="flex shrink-0 items-center justify-end gap-8 border-t px-5 py-3 text-sm">
          <span class="font-semibold">總計 <span class="tabular-nums">{{ quotation.total.toLocaleString() }}</span></span>
        </div>
      </div>
    </div>

    <!-- 成交確認 -->
    <Dialog :open="showWin" @update:open="(v) => { if (!v) showWin = false }">
      <DialogContent class="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>報價單 {{ quotation?.quote_no }} 成交？</DialogTitle>
          <DialogDescription>成交後進入「已成交」終態、不可再改，並會自動生成一筆訂單（用報價的價格）。</DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" @click="showWin = false">先不要</Button>
          <Button :disabled="acting" @click="confirmWin">確定成交，生訂單</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- 作廢確認 -->
    <Dialog :open="showVoid" @update:open="(v) => { if (!v) showVoid = false }">
      <DialogContent class="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>作廢報價單 {{ quotation?.quote_no }}？</DialogTitle>
          <DialogDescription>作廢後進入「已作廢」終態、不可再改（沒談成才作廢）。</DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" @click="showVoid = false">不作廢</Button>
          <Button variant="destructive" :disabled="acting" @click="confirmVoid">確定作廢</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
