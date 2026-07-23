<script setup>
// 帳款頁：客戶應收總覽（一列一客戶，欠最多的在前）。點客戶 → 看他的分錄流。
// 唯讀投影：這頁不改帳——收款/作廢都在訂單那邊做，帳款是後端把分錄算出來的結果。
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { listReceivables } from '@/api/billing'
import { Button } from '@/components/ui/button'
import DataTable from '@/components/DataTable.vue'
import { TableCell } from '@/components/ui/table'

const router = useRouter()

const columns = [
  { label: '客戶', width: 'w-48' },
  { label: '應收合計', width: 'w-32', align: 'right' },
  { label: '已收合計', width: 'w-32', align: 'right' },
  { label: '未收餘額', width: 'w-32', align: 'right' },
  { label: '分錄', width: 'w-20', align: 'right' },
]

const rows = ref([])
const totalBalance = ref(0)
const loading = ref(false)
const errorMsg = ref('')
const onlyOutstanding = ref(false)

const money = (n) => Number(n).toLocaleString()

async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await listReceivables({ onlyOutstanding: onlyOutstanding.value })
    rows.value = res.items
    totalBalance.value = res.total_balance
  } catch (e) {
    errorMsg.value = '載入失敗,請稍後再試'
    console.error(e)
  } finally {
    loading.value = false
  }
}
onMounted(load)

function toggleOutstanding() {
  onlyOutstanding.value = !onlyOutstanding.value
  load()
}
</script>

<template>
  <div class="flex h-full flex-col">
    <div class="flex shrink-0 items-baseline gap-3">
      <h1 class="text-lg font-semibold leading-none tracking-tight">帳款（應收帳款）</h1>
      <span class="text-muted-foreground text-sm">總未收餘額 <span class="text-foreground font-semibold tabular-nums">{{ money(totalBalance) }}</span></span>
    </div>

    <div class="mt-5 flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border bg-card shadow-sm">
      <div class="flex min-h-0 flex-1 flex-col p-5">
        <p v-if="errorMsg" class="text-destructive mb-3 shrink-0 text-sm">{{ errorMsg }}</p>

        <!-- 工具列：篩選（只看還有欠款的）。收款/開帳都在訂單那邊做，這頁不放建立鈕。 -->
        <div class="mb-4 flex shrink-0 items-center gap-2">
          <Button :variant="onlyOutstanding ? 'default' : 'outline'" size="sm" @click="toggleOutstanding">
            只看還有欠款的
          </Button>
          <span class="text-muted-foreground text-sm">餘額＝應收 − 已收 − 沖銷（後端由分錄推導）</span>
        </div>

        <DataTable :items="rows" :columns="columns" :loading="loading">
          <template #row="{ item: r }">
            <TableCell class="font-medium">
              <button type="button" class="hover:text-primary hover:underline" @click="router.push(`/billing/customers/${r.customer.id}`)">{{ r.customer.name }}</button>
            </TableCell>
            <TableCell class="text-right tabular-nums">{{ money(r.charged) }}</TableCell>
            <TableCell class="text-right tabular-nums">{{ money(r.paid) }}</TableCell>
            <TableCell class="text-right tabular-nums">
              <span :class="r.balance > 0 ? 'font-semibold text-foreground' : 'text-muted-foreground'">{{ money(r.balance) }}</span>
            </TableCell>
            <TableCell class="text-right tabular-nums text-muted-foreground">{{ r.entry_count }}</TableCell>
          </template>
          <template #empty>
            {{ onlyOutstanding ? '沒有還在欠款的客戶——都收齊了' : '還沒有帳款——建一張訂單就會開出應收' }}
          </template>
        </DataTable>
      </div>
    </div>
  </div>
</template>
