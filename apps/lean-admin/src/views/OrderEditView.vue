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

    <!-- 大卡片：表單（可捲）+ 底部按鈕 -->
    <div class="mt-5 flex min-h-0 flex-1 flex-col rounded-lg border bg-card shadow-sm">
      <p v-if="errorMsg" class="text-destructive p-5 text-sm">{{ errorMsg }}</p>

      <div v-if="!loading && !errorMsg" class="flex min-h-0 flex-1 flex-col gap-4 overflow-auto p-5">
        <p class="text-muted-foreground text-sm">選客戶、從產品目錄挑明細；小計/總計是顯示用,存檔後以後端計算為準。</p>

        <div class="flex max-w-md flex-col gap-1.5">
          <Label>客戶</Label>
          <!-- 新增：開對話框搜尋挑選（客戶多也不怕）；編輯：唯讀（訂單成立後不可換客戶）。 -->
          <button
            v-if="isCreate"
            type="button"
            class="bg-background hover:bg-muted/50 flex h-9 items-center justify-between rounded-md border px-3 text-sm transition-colors"
            @click="showCustomerDialog = true"
          >
            <span :class="selectedMember ? 'font-medium' : 'text-muted-foreground'">{{ selectedMember ? selectedMember.name : '選擇客戶…' }}</span>
            <ChevronDown class="size-4 opacity-60" />
          </button>
          <template v-else>
            <div class="bg-muted/40 flex h-9 items-center rounded-md border px-3 text-sm font-medium">{{ selectedMember?.name }}</div>
            <p class="text-muted-foreground text-xs">訂單成立後不可換客戶（帳已開給原客戶）。</p>
          </template>
        </div>

        <div class="flex max-w-2xl flex-col gap-2">
          <Label>明細（從產品目錄挑；小計 = 數量 × 單價,自動算）</Label>
          <div v-for="(item, idx) in form.items" :key="idx" class="flex items-center gap-2">
            <Select v-model="item.product_id">
              <SelectTrigger class="flex-1"><SelectValue placeholder="選擇產品" /></SelectTrigger>
              <SelectContent>
                <SelectItem v-for="p in activeProducts" :key="p.id" :value="String(p.id)">
                  {{ p.name }}（{{ p.unit_price.toLocaleString() }}）
                </SelectItem>
              </SelectContent>
            </Select>
            <Input v-model.number="item.quantity" type="number" min="1" class="w-20" />
            <span class="text-muted-foreground w-28 text-right text-sm tabular-nums">= {{ itemSubtotal(item).toLocaleString() }}</span>
            <Button variant="ghost" size="icon-sm" class="text-destructive" @click="removeItem(idx)"><X class="size-4" /></Button>
          </div>
          <Button variant="outline" size="sm" class="w-fit" @click="addItem"><Plus class="size-4" /> 加一筆明細</Button>
        </div>

        <!-- 收貨資訊（選填）-->
        <div class="flex max-w-2xl flex-col gap-3">
          <Label>收貨資訊（選填）</Label>
          <div class="grid grid-cols-2 gap-3">
            <Input v-model="form.contact_name" placeholder="聯絡人" />
            <Input v-model="form.contact_phone" placeholder="聯絡人電話" />
          </div>
          <Input v-model="form.shipping_address" placeholder="收貨地址" maxlength="200" />
          <div class="flex items-center gap-2">
            <span class="text-muted-foreground shrink-0 text-sm">預計出貨日</span>
            <Input v-model="form.expected_ship_date" type="date" class="w-44" />
          </div>
        </div>

        <p class="font-semibold">
          總計：{{ formTotal.toLocaleString() }}
          <span class="text-muted-foreground ml-2 text-sm font-normal">（顯示用；存檔後以後端計算為準）</span>
        </p>
        <p v-if="formError" class="text-destructive text-sm">{{ formError }}</p>
      </div>

      <!-- 底部按鈕列（釘在卡底）-->
      <div class="flex shrink-0 justify-end gap-2 border-t p-4">
        <Button variant="outline" @click="goBack">取消</Button>
        <Button :disabled="saving || loading" @click="submitForm">儲存</Button>
      </div>
    </div>

    <CustomerSelectDialog v-model:open="showCustomerDialog" @select="onSelectCustomer" />
  </div>
</template>
