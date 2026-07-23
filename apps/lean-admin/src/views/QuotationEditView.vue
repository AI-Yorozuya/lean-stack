<script setup>
// 報價單新增／編輯頁（換頁式，非 dialog）。刻意跟 OrderEditView 同形。同一個 view 兩用：
//   /quotations/new       → 新增（沒有 :id）
//   /quotations/:id/edit  → 編輯（有 :id）
// 表單：選客戶 ＋ 從產品目錄挑明細（後端抄快照）＋ 備註。
// 編輯只有草稿能改——後端 update_quotation 會擋（送出後回 422）。
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Plus, X, ArrowLeft } from '@lucide/vue'
import { createQuotation, getQuotation, updateQuotation } from '@/api/quotation'
import { createMember, listMembers } from '@/api/member'
import { listProducts } from '@/api/product'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

const route = useRoute()
const router = useRouter()
const isCreate = !route.params.id
const quotationId = isCreate ? null : Number(route.params.id)

const quotation = ref(null)
const members = ref([])
const products = ref([])
const loading = ref(true)
const errorMsg = ref('')

const activeProducts = computed(() => products.value.filter((p) => p.is_active))
const productMap = computed(() => Object.fromEntries(products.value.map((p) => [String(p.id), p])))

const form = reactive({ customer_id: '', items: [], note: '' })
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
    formError.value = '鐵則：一張報價至少要有一筆明細'
    return
  }
  form.items.splice(idx, 1)
}
const itemUnitPrice = (i) => Number(productMap.value[String(i.product_id)]?.unit_price ?? 0)
const itemSubtotal = (i) => (Number(i.quantity) || 0) * itemUnitPrice(i)
const formTotal = computed(() => form.items.reduce((sum, i) => sum + itemSubtotal(i), 0))

onMounted(async () => {
  try {
    const [m, p] = await Promise.all([
      listMembers({ pageSize: 100 }),
      listProducts({ pageSize: 100 }),
    ])
    members.value = m.items
    products.value = p.items
    if (isCreate) {
      form.items = [blankItem()]
    } else {
      const q = await getQuotation(quotationId)
      quotation.value = q
      form.customer_id = String(q.customer.id)
      form.note = q.note || ''
      form.items = q.items.map((i) => ({ product_id: String(i.product_id), quantity: i.quantity }))
    }
  } catch (e) {
    errorMsg.value = '載入失敗,請稍後再試'
    console.error(e)
  } finally {
    loading.value = false
  }
})

function goBack() {
  router.push('/quotations')
}

async function submitForm() {
  formError.value = ''
  if (!form.customer_id) {
    formError.value = '請選擇客戶'
    return
  }
  if (form.items.some((i) => !i.product_id)) {
    formError.value = '每一筆明細都要選一個產品'
    return
  }
  saving.value = true
  const payload = {
    customer_id: Number(form.customer_id),
    items: form.items.map((i) => ({ product_id: Number(i.product_id), quantity: Number(i.quantity) })),
    note: form.note,
  }
  try {
    if (isCreate) await createQuotation(payload)
    else await updateQuotation(quotationId, payload)
    goBack()
  } catch (e) {
    formError.value = e.response?.data?.detail || '儲存失敗,請稍後再試'
    console.error(e)
  } finally {
    saving.value = false
  }
}

// ── 快速新增客戶 ──
const showNewCustomer = ref(false)
const newCustomer = reactive({ name: '', email: '', phone: '' })
const newCustomerError = ref('')
async function submitNewCustomer() {
  newCustomerError.value = ''
  if (!newCustomer.name || !newCustomer.email) {
    newCustomerError.value = '姓名與 email 必填'
    return
  }
  try {
    const created = await createMember({ ...newCustomer })
    members.value = (await listMembers({ pageSize: 100 })).items
    form.customer_id = String(created.id)
    newCustomer.name = ''
    newCustomer.email = ''
    newCustomer.phone = ''
    showNewCustomer.value = false
  } catch (e) {
    newCustomerError.value = e.response?.data?.detail || '建立失敗'
  }
}
</script>

<template>
  <div class="flex h-full flex-col">
    <div class="flex shrink-0 items-center gap-2">
      <Button variant="ghost" size="icon-sm" title="返回" @click="goBack"><ArrowLeft class="size-4" /></Button>
      <h1 class="text-lg font-semibold leading-none tracking-tight">{{ isCreate ? '新增報價' : `編輯報價 ${quotation?.quote_no || ''}` }}</h1>
    </div>

    <!-- 大卡片：表單（可捲）+ 底部按鈕 -->
    <div class="mt-5 flex min-h-0 flex-1 flex-col rounded-lg border bg-card shadow-sm">
      <p v-if="errorMsg" class="text-destructive p-5 text-sm">{{ errorMsg }}</p>

      <div v-if="!loading && !errorMsg" class="flex min-h-0 flex-1 flex-col gap-4 overflow-auto p-5">
        <p class="text-muted-foreground text-sm">選客戶、從產品目錄挑明細；小計/總計是顯示用,存檔後以後端計算為準。</p>

        <div class="flex max-w-2xl flex-col gap-1.5">
          <Label>客戶</Label>
          <div class="flex gap-2">
            <Select v-model="form.customer_id">
              <SelectTrigger class="flex-1"><SelectValue placeholder="選擇客戶" /></SelectTrigger>
              <SelectContent>
                <SelectItem v-for="m in members" :key="m.id" :value="String(m.id)">{{ m.name }}</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline" @click="showNewCustomer = !showNewCustomer">＋ 新客戶</Button>
          </div>
          <div v-if="showNewCustomer" class="bg-muted flex flex-col gap-2 rounded-md p-2">
            <div class="flex gap-2">
              <Input v-model="newCustomer.name" placeholder="姓名" />
              <Input v-model="newCustomer.email" placeholder="email" />
              <Input v-model="newCustomer.phone" placeholder="電話（選填）" />
              <Button @click="submitNewCustomer">建立</Button>
            </div>
            <p v-if="newCustomerError" class="text-destructive text-sm">{{ newCustomerError }}</p>
          </div>
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

        <div class="flex max-w-2xl flex-col gap-1.5">
          <Label>備註（選填）</Label>
          <Input v-model="form.note" placeholder="給這張報價的備註…" maxlength="200" />
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
  </div>
</template>
