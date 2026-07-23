<script setup>
// 訂單新增／編輯頁（換頁式，非 dialog）。同一個 view 兩用：
//   /orders/new       → 新增（沒有 :id）
//   /orders/:id/edit  → 編輯（有 :id）
// 表單同一套：選客戶 ＋ 從產品目錄挑明細（後端抄快照）。
// 編輯只有出貨前（待付款/待出貨）能改——後端 update_order 會擋（非法回 422）。
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Plus, X, ArrowLeft, ChevronDown } from '@lucide/vue'
import { createOrder, getOrder, updateOrder } from '@/api/order'
import { listProducts } from '@/api/product'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import CustomerSelectDialog from '@/components/CustomerSelectDialog.vue'

const route = useRoute()
const router = useRouter()
const isCreate = !route.params.id // 沒有 :id = 新增模式
const orderId = isCreate ? null : Number(route.params.id)

const order = ref(null)
const products = ref([])
const loading = ref(true)
const errorMsg = ref('')
const selectedMember = ref(null)       // 已選客戶（顯示用；id 進 form.member_id）
const showCustomerDialog = ref(false)

const activeProducts = computed(() => products.value.filter((p) => p.is_active))
const productMap = computed(() => Object.fromEntries(products.value.map((p) => [String(p.id), p])))

const form = reactive({ member_id: '', items: [], contact_name: '', contact_phone: '', shipping_address: '', expected_ship_date: '' })
const formError = ref('')
const saving = ref(false)

function blankItem() {
  return { product_id: '', quantity: 1 }
}
function addItem() {
  form.items.push(blankItem())
}
function removeItem(idx) {
  if (form.items.length <= 1) {
    formError.value = '鐵則：一張訂單至少要有一筆明細'
    return
  }
  form.items.splice(idx, 1)
}
const itemUnitPrice = (i) => Number(productMap.value[String(i.product_id)]?.unit_price ?? 0)
const itemSubtotal = (i) => (Number(i.quantity) || 0) * itemUnitPrice(i)
const formTotal = computed(() => form.items.reduce((sum, i) => sum + itemSubtotal(i), 0))

onMounted(async () => {
  try {
    // 產品目錄給明細下拉用；客戶改由對話框自己搜尋分頁載入（不預抓整包）。
    const p = await listProducts({ pageSize: 100 })
    products.value = p.items
    if (isCreate) {
      form.items = [blankItem()] // 新增：一張空明細起手
    } else {
      const o = await getOrder(orderId)
      order.value = o
      selectedMember.value = o.member
      form.member_id = String(o.member.id)
      form.items = o.items.map((i) => ({ product_id: String(i.product_id), quantity: i.quantity }))
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
  if (form.items.some((i) => !i.product_id)) {
    formError.value = '每一筆明細都要選一個產品'
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

// 對話框選定客戶（含新客戶建立後回選）。
function onSelectCustomer(m) {
  selectedMember.value = m
  form.member_id = String(m.id)
}
</script>

<template>
  <div class="flex h-full flex-col">
    <div class="flex shrink-0 items-center gap-2">
      <Button variant="ghost" size="icon-sm" title="返回" @click="goBack"><ArrowLeft class="size-4" /></Button>
      <h1 class="text-lg font-semibold leading-none tracking-tight">{{ isCreate ? '新增訂單' : `編輯訂單 ${order?.order_no || ''}` }}</h1>
    </div>

    <!-- 表單：分卡片區塊（客戶 / 明細 / 收貨），底部按鈕列釘住 -->
    <div class="mt-5 flex min-h-0 flex-1 flex-col">
      <p v-if="errorMsg" class="text-destructive text-sm">{{ errorMsg }}</p>

      <div v-if="!loading && !errorMsg" class="flex min-h-0 flex-1 flex-col gap-4 overflow-auto pb-2">
        <!-- 客戶卡 -->
        <div class="overflow-hidden rounded-lg border bg-card shadow-sm">
          <div class="border-b px-4 py-2.5 text-sm font-semibold">客戶</div>
          <div class="p-4">
            <button
              v-if="isCreate"
              type="button"
              class="bg-background hover:bg-muted/50 flex h-9 w-full max-w-md items-center justify-between rounded-md border px-3 text-sm transition-colors"
              @click="showCustomerDialog = true"
            >
              <span :class="selectedMember ? 'font-medium' : 'text-muted-foreground'">{{ selectedMember ? selectedMember.name : '選擇客戶…' }}</span>
              <ChevronDown class="size-4 opacity-60" />
            </button>
            <div v-else class="bg-muted/40 flex h-9 w-full max-w-md items-center rounded-md border px-3 text-sm font-medium">{{ selectedMember?.name }}</div>
          </div>
        </div>

        <!-- 收貨卡 -->
        <div class="overflow-hidden rounded-lg border bg-card shadow-sm">
          <div class="border-b px-4 py-2.5 text-sm font-semibold">收貨資訊<span class="text-muted-foreground ml-1 text-xs font-normal">（選填）</span></div>
          <div class="flex flex-col gap-3 p-4">
            <div class="grid grid-cols-1 gap-3 sm:grid-cols-[1fr_1fr_1.6fr]">
              <div class="flex flex-col gap-1">
                <Label class="text-muted-foreground text-xs">聯絡人</Label>
                <Input v-model="form.contact_name" />
              </div>
              <div class="flex flex-col gap-1">
                <Label class="text-muted-foreground text-xs">聯絡人電話</Label>
                <Input v-model="form.contact_phone" />
              </div>
              <div class="flex flex-col gap-1">
                <Label class="text-muted-foreground text-xs">收貨地址</Label>
                <Input v-model="form.shipping_address" maxlength="200" />
              </div>
            </div>
            <div class="flex flex-col gap-1 sm:w-48">
              <Label class="text-muted-foreground text-xs">預計出貨日</Label>
              <Input v-model="form.expected_ship_date" type="date" />
            </div>
          </div>
        </div>

        <!-- 明細卡：正式表格，加一筆在 header 右邊（品項多也不怕，整頁捲動）-->
        <div class="overflow-hidden rounded-lg border bg-card shadow-sm">
          <div class="flex items-center justify-between border-b px-4 py-2.5">
            <span class="text-sm font-semibold">明細</span>
            <Button variant="outline" size="sm" @click="addItem"><Plus class="size-4" /> 新增品項</Button>
          </div>
          <div class="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>品名</TableHead>
                  <TableHead class="w-24 text-center">數量</TableHead>
                  <TableHead class="w-32 text-right">小計</TableHead>
                  <TableHead class="w-12"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow v-for="(item, idx) in form.items" :key="idx">
                  <TableCell>
                    <Select v-model="item.product_id">
                      <SelectTrigger><SelectValue placeholder="選擇產品" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem v-for="p in activeProducts" :key="p.id" :value="String(p.id)">
                          {{ p.name }}（{{ p.unit_price.toLocaleString() }}）
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </TableCell>
                  <TableCell class="text-center">
                    <Input v-model.number="item.quantity" type="number" min="1" class="mx-auto w-20 text-center" />
                  </TableCell>
                  <TableCell class="text-right tabular-nums">{{ itemSubtotal(item).toLocaleString() }}</TableCell>
                  <TableCell class="text-center">
                    <Button variant="ghost" size="icon-sm" class="text-destructive" @click="removeItem(idx)"><X class="size-4" /></Button>
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </div>
          <p v-if="formError" class="text-destructive px-4 pt-2 text-sm">{{ formError }}</p>
          <div class="flex items-center justify-end border-t px-4 py-2.5 text-sm">
            <span class="font-semibold">總計 <span class="tabular-nums">{{ formTotal.toLocaleString() }}</span></span>
          </div>
        </div>
      </div>

      <!-- 底部按鈕列 -->
      <div class="flex shrink-0 justify-end gap-2 pt-4">
        <Button variant="outline" @click="goBack">取消</Button>
        <Button :disabled="saving || loading" @click="submitForm">儲存</Button>
      </div>
    </div>

    <CustomerSelectDialog v-model:open="showCustomerDialog" @select="onSelectCustomer" />
  </div>
</template>
