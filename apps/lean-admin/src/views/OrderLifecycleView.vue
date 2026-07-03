<script setup>
// 訂單管理 Stage B：有狀態示範（訂單生命週期狀態機）。
// 教學重點——這一頁就是「認識積木」下半 + 三問「會判斷」的素材：
//   訂單有了 status，動作要看「當下狀態合不合法」才做得了。
//   每個訂單只長出「目前合法」的動作按鈕（available_actions 由後端給）。
//   非法轉移（跳步 / 改已出貨 / 終態再轉）→ 後端回 422，前端顯示白話原因。
//
// 真相在後端：前端只是「照後端說的合法動作長按鈕」，就算前端亂長，
// 後端 apply_transition 還是會擋（見 apps/order/models.py 的 TRANSITIONS）。
import { onMounted, ref } from 'vue'
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
  <div>
    <h1 class="text-2xl font-semibold tracking-tight">訂單管理 · 有狀態</h1>

    <!-- 大卡片（標題下一張白卡：狀態機圖例 + 表格都包在裡面）-->
    <div class="mt-4 rounded-lg bg-white p-5 shadow-sm">
      <p v-if="errorMsg" class="text-destructive mb-3 text-sm">{{ errorMsg }}</p>

      <!-- 狀態機圖例（教學：這條路長怎樣）-->
      <div class="bg-muted/50 mb-4 flex flex-wrap items-center gap-x-2 gap-y-2 rounded-lg border p-3 text-sm">
      <Badge variant="outline">待付款</Badge>
      <span class="text-muted-foreground text-xs">—收款→</span>
      <Badge variant="secondary">已付款</Badge>
      <span class="text-muted-foreground text-xs">—出貨→</span>
      <Badge>已出貨</Badge>
      <span class="text-muted-foreground text-xs">—完成→</span>
      <Badge>已完成</Badge>
      <span class="text-muted-foreground ml-2 text-xs">已付款/已出貨 —退款→</span>
      <Badge variant="outline">已退款</Badge>
      <span class="text-muted-foreground ml-1 text-xs">（已完成 / 已退款＝終態,不可再轉）</span>
      </div>

      <!-- 表格：自己一張帶邊框的框 -->
      <div class="overflow-hidden rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead class="w-12">#</TableHead>
            <TableHead>客戶</TableHead>
            <TableHead class="text-right">總額</TableHead>
            <TableHead class="text-right">已收</TableHead>
            <TableHead>狀態</TableHead>
            <TableHead class="w-52">可做的動作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="o in orders" :key="o.id">
            <TableCell class="text-muted-foreground">{{ o.id }}</TableCell>
            <TableCell class="font-medium">{{ o.customer.name }}</TableCell>
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
          <TableRow v-if="!loading && orders.length === 0">
            <TableCell colspan="6" class="text-muted-foreground py-10 text-center">
              還沒有訂單——先到「無狀態示範」開一張,再回來推進它的生命週期
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
      </div>
    </div>
  </div>
</template>
