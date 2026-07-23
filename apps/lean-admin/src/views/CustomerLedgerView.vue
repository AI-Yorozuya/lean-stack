<script setup>
// 單一客戶的帳款分錄流（唯讀）。看得到每一筆錢的來龍去脈＋跑動餘額——這就是 append-only ledger 的好處：
// 餘額對不上時，一筆一筆攤開對。收款/開帳/沖銷都在訂單那邊做，這頁只呈現。
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from '@lucide/vue'
import { getCustomerLedger } from '@/api/billing'
import { Button } from '@/components/ui/button'
import LoadingState from '@/components/LoadingState.vue'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'

const route = useRoute()
const router = useRouter()
const customerId = Number(route.params.id)

const data = ref(null)
const loading = ref(true)
const errorMsg = ref('')

const money = (n) => Number(n).toLocaleString()
// 應收（欠款增加）＝正常黑字；收款/沖銷（欠款減少）＝灰字，一眼分方向。
const kindClass = (k) => (k === 'CHARGE' ? 'text-foreground' : 'text-muted-foreground')

async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    data.value = await getCustomerLedger(customerId)
  } catch (e) {
    errorMsg.value = '載入失敗,請稍後再試'
    console.error(e)
  } finally {
    loading.value = false
  }
}
onMounted(load)
</script>

<template>
  <div class="flex h-full flex-col">
    <!-- 回上頁 header -->
    <div class="flex shrink-0 items-center gap-3">
      <Button variant="ghost" size="icon-sm" title="返回帳款總覽" @click="router.push('/billing')">
        <ArrowLeft class="size-4" />
      </Button>
      <h1 class="text-lg font-semibold leading-none tracking-tight">帳款 · {{ data?.customer.name || '' }}</h1>
    </div>

    <p v-if="errorMsg" class="text-destructive mt-4 shrink-0 text-sm">{{ errorMsg }}</p>
    <LoadingState v-if="loading" class="mt-5" />

    <div v-else-if="data" class="mt-5 flex min-h-0 flex-1 flex-col gap-4 overflow-auto">
      <!-- 摘要卡 -->
      <div class="shrink-0 rounded-lg border bg-card p-5 shadow-sm">
        <dl class="grid grid-cols-3 gap-x-6">
          <div><dt class="text-muted-foreground text-xs">應收合計</dt><dd class="mt-1 tabular-nums">{{ money(data.charged) }}</dd></div>
          <div><dt class="text-muted-foreground text-xs">已收合計</dt><dd class="mt-1 tabular-nums">{{ money(data.paid) }}</dd></div>
          <div><dt class="text-muted-foreground text-xs">未收餘額</dt><dd class="mt-1 text-lg font-semibold tabular-nums">{{ money(data.balance) }}</dd></div>
        </dl>
      </div>

      <!-- 分錄流卡 -->
      <div class="flex min-h-0 flex-col overflow-hidden rounded-lg border bg-card shadow-sm">
        <div class="shrink-0 border-b px-5 py-3 text-sm font-medium">分錄流（依時間序；每筆錢都留痕）</div>
        <div class="scroll-thin min-h-0 flex-1 overflow-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead class="w-28">日期</TableHead>
                <TableHead class="w-20">類型</TableHead>
                <TableHead>說明</TableHead>
                <TableHead class="w-28">關聯訂單</TableHead>
                <TableHead class="w-28 text-right">金額</TableHead>
                <TableHead class="w-32 text-right">餘額</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="e in data.entries" :key="e.id">
                <TableCell class="tabular-nums">{{ e.date }}</TableCell>
                <TableCell><span :class="kindClass(e.kind)">{{ e.kind_display }}</span></TableCell>
                <TableCell class="text-muted-foreground">{{ e.memo }}</TableCell>
                <TableCell class="tabular-nums">
                  <button v-if="e.order_no" type="button" class="hover:text-primary hover:underline" @click="router.push(`/orders/${e.order_id ?? ''}`)">{{ e.order_no }}</button>
                  <span v-else>—</span>
                </TableCell>
                <TableCell class="text-right tabular-nums" :class="kindClass(e.kind)">
                  {{ e.signed_amount > 0 ? '+' : '' }}{{ money(e.signed_amount) }}
                </TableCell>
                <TableCell class="text-right font-medium tabular-nums">{{ money(e.running_balance) }}</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  </div>
</template>
