<script setup>
// 訂單管理 Stage B：有狀態示範（訂單生命週期狀態機）。
// 教學重點——這一頁就是「認識積木」下半 + 三問「會判斷」的素材：
//   訂單有了 status，動作要看「當下狀態合不合法」才做得了。
//   每個訂單只長出「目前合法」的動作按鈕（available_actions 由後端給）。
//   非法轉移（跳步 / 改已出貨 / 終態再轉）→ 後端回 422，前端顯示白話原因。
//
// 真相在後端：前端只是「照後端說的合法動作長按鈕」，就算前端亂長，
// 後端 apply_transition 還是會擋（見 apps/order/models.py 的 TRANSITIONS）。
import { onMounted, ref, computed } from 'vue'
import { listOrders, transitionOrder } from '@/api/order'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'

// 狀態 → 顯示（label 用後端的 status_display，variant 走黑白語彙）
const STATUS = {
  PENDING: 'outline',
  PAID: 'secondary',
  SHIPPED: 'default',
  COMPLETED: 'default',
  REFUNDED: 'outline',
}
// 動作 code → 中文 + 按鈕樣式（主線用實心、退款用外框）
const ACTIONS = {
  pay: { label: '收款', variant: 'default' },
  ship: { label: '出貨', variant: 'default' },
  complete: { label: '完成', variant: 'default' },
  refund: { label: '退款', variant: 'outline' },
}

const orders = ref([])
const loading = ref(false)
const busyId = ref(null)
const errorMsg = ref('')

// ── 狀態篩選 tab（參考 top-admin 訂單頁：卡片頂一排狀態 tab，點了篩該狀態）──
const statusTabs = [
  { key: 'all', label: '全部' },
  { key: 'PENDING', label: '待付款' },
  { key: 'PAID', label: '已付款' },
  { key: 'SHIPPED', label: '已出貨' },
  { key: 'COMPLETED', label: '已完成' },
  { key: 'REFUNDED', label: '已退款' },
]
const activeStatus = ref('all')
// 客戶端篩選（本頁一次撈全部，資料量小；點 tab 只是過濾顯示）。
const filteredOrders = computed(() =>
  activeStatus.value === 'all' ? orders.value : orders.value.filter((o) => o.status === activeStatus.value),
)
const statusCount = (key) =>
  key === 'all' ? orders.value.length : orders.value.filter((o) => o.status === key).length

async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    const data = await listOrders({ pageSize: 100 })
    orders.value = data.items
  } catch (e) {
    errorMsg.value = '載入失敗,請稍後再試'
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function doAction(order, action) {
  errorMsg.value = ''
  busyId.value = order.id
  try {
    const updated = await transitionOrder(order.id, action)
    const i = orders.value.findIndex((o) => o.id === order.id)
    if (i > -1) orders.value[i] = updated
  } catch (e) {
    // 後端擋下的非法轉移（422）帶白話原因，直接顯示。
    errorMsg.value = e.response?.data?.detail || '操作失敗,請稍後再試'
    console.error(e)
  } finally {
    busyId.value = null
  }
}

onMounted(load)
</script>

<template>
  <div class="flex h-full flex-col">
    <h1 class="shrink-0 text-2xl font-semibold tracking-tight">訂單列表</h1>

    <!-- 大卡片：頂部狀態 tab（全寬）+ 內容（含表格）-->
    <div class="mt-4 flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg bg-white shadow-sm">
      <!-- 狀態篩選 tab（參 top-admin：淺色 strip，active 白底融入下方白色內容；點了篩該狀態）-->
      <div class="flex shrink-0 overflow-x-auto bg-muted/50">
        <button
          v-for="tab in statusTabs"
          :key="tab.key"
          type="button"
          :class="[
            'cursor-pointer whitespace-nowrap px-4 py-3 text-sm transition-colors',
            activeStatus === tab.key ? 'bg-white font-medium text-foreground' : 'text-muted-foreground hover:text-foreground',
          ]"
          @click="activeStatus = tab.key"
        >
          {{ tab.label }}
          <span class="text-muted-foreground ml-1 text-xs tabular-nums">{{ statusCount(tab.key) }}</span>
        </button>
      </div>

      <!-- 內容 -->
      <div class="flex min-h-0 flex-1 flex-col p-6">
      <p v-if="errorMsg" class="text-destructive mb-3 shrink-0 text-sm">{{ errorMsg }}</p>

      <!-- 表格：表頭固定（捲軸不碰它）＋ 表身內捲；兩張 table 同一組 colgroup 對齊 -->
      <div class="flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border">
        <!-- 表頭（固定；保留捲軸槽對齊表身；容器底色＝表頭色，保留槽不露白）-->
        <div class="scroll-thin bg-muted shrink-0 overflow-y-auto [scrollbar-gutter:stable]">
          <Table class="table-fixed">
            <colgroup>
              <col class="w-28" /><col /><col class="w-28" /><col class="w-28" /><col class="w-28" /><col class="w-52" />
            </colgroup>
            <TableHeader>
              <TableRow>
                <TableHead>單號</TableHead>
                <TableHead>會員</TableHead>
                <TableHead class="text-right">總額</TableHead>
                <TableHead class="text-right">已收</TableHead>
                <TableHead>狀態</TableHead>
                <TableHead>可做的動作</TableHead>
              </TableRow>
            </TableHeader>
          </Table>
        </div>
        <!-- 表身（內捲；捲軸只在這）-->
        <div class="scroll-thin min-h-0 flex-1 overflow-y-auto [scrollbar-gutter:stable]">
          <Table class="table-fixed">
            <colgroup>
              <col class="w-28" /><col /><col class="w-28" /><col class="w-28" /><col class="w-28" /><col class="w-52" />
            </colgroup>
            <TableBody>
              <TableRow v-for="o in filteredOrders" :key="o.id">
                <TableCell class="text-muted-foreground tabular-nums">{{ o.order_no }}</TableCell>
                <TableCell class="font-medium">{{ o.member.name }}</TableCell>
                <TableCell class="text-right tabular-nums">{{ o.total.toLocaleString() }}</TableCell>
                <TableCell class="text-muted-foreground text-right tabular-nums">{{ o.paid_amount.toLocaleString() }}</TableCell>
                <TableCell>
                  <Badge :variant="STATUS[o.status]">{{ o.status_display }}</Badge>
                </TableCell>
                <TableCell>
                  <div class="flex flex-wrap gap-1.5">
                    <Button
                      v-for="a in o.available_actions"
                      :key="a"
                      size="sm"
                      :variant="ACTIONS[a].variant"
                      :disabled="busyId === o.id"
                      @click="doAction(o, a)"
                    >
                      {{ ACTIONS[a].label }}
                    </Button>
                    <span v-if="o.available_actions.length === 0" class="text-muted-foreground text-xs">終態 · 鎖定</span>
                  </div>
                </TableCell>
              </TableRow>
              <TableRow v-if="!loading && filteredOrders.length === 0">
                <TableCell colspan="6" class="text-muted-foreground py-10 text-center">
                  {{ activeStatus === 'all' ? '還沒有訂單——先到「訂單(無狀態)」開一張，再回來推進它的生命週期' : '此狀態目前沒有訂單' }}
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
      </div>
      </div>
    </div>
  </div>
</template>
