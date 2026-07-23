<script setup>
// 訂單新增／編輯頁（換頁式，非 dialog）。同一個 view 兩用：
//   /orders/new       → 新增（沒有 :id）
//   /orders/:id/edit  → 編輯（有 :id）
// 表單同一套：選客戶 ＋ 從產品目錄挑明細（後端抄快照）。
// 編輯只有出貨前（待付款/待出貨）能改——後端 update_order 會擋（非法回 422）。
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Plus, X, ArrowLeft } from '@lucide/vue'
import { createOrder, getOrder, updateOrder } from '@/api/order'
import { createMember, listMembers } from '@/api/member'
import { listProducts } from '@/api/product'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

const route = useRoute()
const router = useRouter()
const isCreate = !route.params.id // 沒有 :id = 新增模式
const orderId = isCreate ? null : Number(route.params.id)

const order = ref(null)
const members = ref([])
const products = ref([])
const loading = ref(true)
const errorMsg = ref('')

const activeProducts = computed(() => products.value.filter((p) => p.is_active))
const productMap = computed(() => Object.fromEntries(products.value.map((p) => [String(p.id), p])))

const form = reactive({ member_id: '', items: [] })
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
    // 客戶/產品目錄兩種模式都要（下拉選單用）；編輯模式再多抓這張訂單來帶入表單。
    const [m, p] = await Promise.all([
      listMembers({ pageSize: 100 }),
      listProducts({ pageSize: 100 }),
    ])
    members.value = m.items
    products.value = p.items
    if (isCreate) {
      form.items = [blankItem()] // 新增：一張空明細起手
    } else {
      const o = await getOrder(orderId)
      order.value = o
      form.member_id = String(o.member.id)
      form.items = o.items.map((i) => ({ product_id: String(i.product_id), quantity: i.quantity }))
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

// ── 快速新增客戶 ──
const showNewMember = ref(false)
const newMember = reactive({ name: '', email: '', phone: '' })
const newMemberError = ref('')
async function submitNewMember() {
  newMemberError.value = ''
  if (!newMember.name || !newMember.email) {
    newMemberError.value = '姓名與 email 必填'
    return
  }
  try {
    const created = await createMember({ ...newMember })
    members.value = (await listMembers({ pageSize: 100 })).items
    form.member_id = String(created.id)
    newMember.name = ''
    newMember.email = ''
    newMember.phone = ''
    showNewMember.value = false
  } catch (e) {
    newMemberError.value = e.response?.data?.detail || '建立失敗'
  }
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

        <div class="flex max-w-2xl flex-col gap-1.5">
          <Label>客戶</Label>
          <div class="flex gap-2">
            <Select v-model="form.member_id">
              <SelectTrigger class="flex-1"><SelectValue placeholder="選擇客戶" /></SelectTrigger>
              <SelectContent>
                <SelectItem v-for="m in members" :key="m.id" :value="String(m.id)">{{ m.name }}</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline" @click="showNewMember = !showNewMember">＋ 新客戶</Button>
          </div>
          <div v-if="showNewMember" class="bg-muted flex flex-col gap-2 rounded-md p-2">
            <div class="flex gap-2">
              <Input v-model="newMember.name" placeholder="姓名" />
              <Input v-model="newMember.email" placeholder="email" />
              <Input v-model="newMember.phone" placeholder="電話（選填）" />
              <Button @click="submitNewMember">建立</Button>
            </div>
            <p v-if="newMemberError" class="text-destructive text-sm">{{ newMemberError }}</p>
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
