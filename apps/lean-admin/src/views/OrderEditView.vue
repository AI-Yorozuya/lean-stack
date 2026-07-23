<script setup>
// 訂單新增／編輯頁（換頁式）。/orders/new = 新增；/orders/:id/edit = 編輯。
// 客戶、產品都用「彈出對話框搜尋分頁挑選」；明細是可捲動表格、總計對齊小計欄。
// 編輯只有待付款能改——後端 update_order 會擋（非法回 422）。
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Plus, X, ArrowLeft, Search } from '@lucide/vue'
import { createOrder, getOrder, updateOrder } from '@/api/order'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell, TableFooter } from '@/components/ui/table'
import LoadingState from '@/components/LoadingState.vue'
import NumberInput from '@/components/NumberInput.vue'
import CustomerSelectDialog from '@/components/CustomerSelectDialog.vue'
import ProductSelectDialog from '@/components/ProductSelectDialog.vue'

const route = useRoute()
const router = useRouter()
const isCreate = !route.params.id
const orderId = isCreate ? null : Number(route.params.id)

const order = ref(null)
const loading = ref(true)
const errorMsg = ref('')
const selectedMember = ref(null)
const showCustomerDialog = ref(false)
const showProductDialog = ref(false)

// 明細品項自帶 name/unit_price 快照（挑選當下抄一份），顯示與算小計都不靠外部產品清單。
const form = reactive({ member_id: '', items: [], contact_name: '', contact_phone: '', shipping_address: '', expected_ship_date: '' })
const formError = ref('')
const saving = ref(false)

const money = (n) => Number(n).toLocaleString()
const itemSubtotal = (i) => (Number(i.quantity) || 0) * Number(i.unit_price)
const formTotal = computed(() => form.items.reduce((sum, i) => sum + itemSubtotal(i), 0))

function removeItem(idx) {
  form.items.splice(idx, 1)
}

onMounted(async () => {
  try {
    if (isCreate) {
      form.items = []
    } else {
      const o = await getOrder(orderId)
      order.value = o
      selectedMember.value = o.member
      form.member_id = String(o.member.id)
      form.items = o.items.map((i) => ({ product_id: i.product_id, name: i.name, unit_price: i.unit_price, quantity: i.quantity }))
      form.contact_name = o.contact_name || ''
      form.contact_phone = o.contact_phone || ''
      form.shipping_address = o.shipping_address || ''
      form.expected_ship_date = o.expected_ship_date || ''
    }
  } catch (e) {
    errorMsg.value = '載入失敗,請稍後再試'
    console.error(e)
  } finally {
    loading.value = false
  }
})

function goBack() {
  router.push('/orders')
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
    if (isCreate) await createOrder(payload)
    else await updateOrder(orderId, payload)
    goBack()
  } catch (e) {
    formError.value = e.response?.data?.detail || '儲存失敗,請稍後再試'
    console.error(e)
  } finally {
    saving.value = false
  }
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
</script>

<template>
  <div class="flex h-full flex-col">
    <div class="flex shrink-0 items-center gap-3">
      <Button variant="outline" size="sm" class="rounded-full" @click="goBack"><ArrowLeft class="size-4" /> 回上一頁</Button>
      <h1 class="text-lg font-semibold leading-none tracking-tight">{{ isCreate ? '新增訂單' : `編輯訂單 ${order?.order_no || ''}` }}</h1>
    </div>

    <p v-if="errorMsg" class="text-destructive mt-4 shrink-0 text-sm">{{ errorMsg }}</p>
    <LoadingState v-if="loading" class="mt-5" />

    <div v-else-if="!errorMsg" class="mt-5 flex min-h-0 flex-1 flex-col gap-4">
        <!-- 客戶卡 -->
        <div class="shrink-0 overflow-hidden rounded-lg border bg-card shadow-sm">
          <div class="border-b px-4 py-2.5 text-sm font-semibold">客戶</div>
          <div class="p-4">
            <!-- 編輯模式也顯示同一個欄位，只是 disable（訂單成立後不可換客戶）-->
            <button
              type="button"
              :disabled="!isCreate"
              class="bg-background hover:bg-muted/50 disabled:hover:bg-background flex h-9 w-full max-w-md cursor-pointer items-center justify-between rounded-md border px-3 text-sm transition-colors disabled:cursor-not-allowed disabled:opacity-60"
              @click="showCustomerDialog = true"
            >
              <span :class="selectedMember ? 'font-medium' : 'text-muted-foreground'">{{ selectedMember ? selectedMember.name : '搜尋 / 選擇客戶…' }}</span>
              <Search class="text-muted-foreground size-4" />
            </button>
          </div>
        </div>

        <!-- 收貨卡 -->
        <div class="shrink-0 overflow-hidden rounded-lg border bg-card shadow-sm">
          <div class="border-b px-4 py-2.5 text-sm font-semibold">收貨資訊<span class="text-muted-foreground ml-1 text-xs font-normal">（選填）</span></div>
          <div class="p-4">
            <div class="grid grid-cols-1 gap-3 sm:grid-cols-[1fr_1fr_2fr_1.2fr]">
              <div class="flex flex-col gap-1"><Label class="text-muted-foreground text-xs">聯絡人</Label><Input v-model="form.contact_name" /></div>
              <div class="flex flex-col gap-1"><Label class="text-muted-foreground text-xs">聯絡人電話</Label><Input v-model="form.contact_phone" /></div>
              <div class="flex flex-col gap-1"><Label class="text-muted-foreground text-xs">收貨地址</Label><Input v-model="form.shipping_address" maxlength="200" /></div>
              <div class="flex flex-col gap-1"><Label class="text-muted-foreground text-xs">預計出貨日</Label><Input v-model="form.expected_ship_date" type="date" /></div>
            </div>
          </div>
        </div>

        <!-- 明細卡：撐滿剩餘高度，超過就表格 body 內部捲動（同列表頁 DataTable 的 flex 做法）-->
        <div class="flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border bg-card shadow-sm">
          <div class="flex shrink-0 items-center justify-between border-b px-4 py-2.5">
            <span class="text-sm font-semibold">明細</span>
            <Button variant="outline" size="sm" @click="showProductDialog = true"><Plus class="size-4" /> 新增品項</Button>
          </div>
          <!-- 表頭：獨立表，overflow-y-scroll 預留捲軸槽 → 右緣跟表身對齊、底線不被捲軸切斷 -->
          <div class="scroll-thin shrink-0 overflow-x-hidden overflow-y-scroll border-b bg-card">
            <Table class="table-fixed [&_th]:border-b-0">
              <colgroup>
                <col /><col class="w-28" /><col class="w-24" /><col class="w-32" /><col class="w-12" />
              </colgroup>
              <TableHeader>
                <TableRow>
                  <TableHead>品名</TableHead>
                  <TableHead class="text-right">單價</TableHead>
                  <TableHead class="text-center">數量</TableHead>
                  <TableHead class="text-right">小計</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
            </Table>
          </div>
          <!-- 表身：撐滿剩餘高度、內部捲動（捲軸只在這裡出現）-->
          <div class="scroll-thin min-h-0 flex-1 overflow-y-scroll">
            <Table class="table-fixed [&_thead]:hidden">
              <colgroup>
                <col /><col class="w-28" /><col class="w-24" /><col class="w-32" /><col class="w-12" />
              </colgroup>
              <TableBody>
                <TableRow v-for="(item, idx) in form.items" :key="item.product_id">
                  <TableCell class="font-medium">{{ item.name }}</TableCell>
                  <TableCell class="text-right tabular-nums">{{ money(item.unit_price) }}</TableCell>
                  <TableCell class="text-center">
                    <NumberInput v-model="item.quantity" :min="1" />
                  </TableCell>
                  <TableCell class="text-right tabular-nums">{{ money(itemSubtotal(item)) }}</TableCell>
                  <TableCell class="text-center">
                    <Button variant="ghost" size="icon-sm" class="text-destructive" @click="removeItem(idx)"><X class="size-4" /></Button>
                  </TableCell>
                </TableRow>
                <TableRow v-if="!form.items.length" class="hover:bg-transparent">
                  <TableCell colspan="5" class="text-muted-foreground py-10 text-center">還沒有品項——按右上「＋ 新增品項」挑一項</TableCell>
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
                  <TableCell class="text-right font-semibold tabular-nums">{{ money(formTotal) }}</TableCell>
                  <TableCell></TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </div>
          <p v-if="formError" class="text-destructive shrink-0 border-t px-4 py-2 text-sm">{{ formError }}</p>
        </div>

        <div class="flex shrink-0 justify-end gap-2">
          <Button variant="outline" @click="goBack">取消</Button>
          <Button :disabled="saving" @click="submitForm">儲存</Button>
        </div>
    </div>

    <CustomerSelectDialog v-model:open="showCustomerDialog" @select="onSelectCustomer" />
    <ProductSelectDialog v-model:open="showProductDialog" @select="onSelectProduct" />
  </div>
</template>
