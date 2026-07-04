<script setup>
// 商品管理頁（最單純 CRUD）。規則見 intents/商品管理.md。
// 教學重點——跟會員同型的「加一頁」，兩條鐵則長在 UI 上：
//   {一 sku 一商品} → 建立撞 sku 後端回 422,前端顯示白話。
//   {下架不刪}      → 沒有「刪除」,只有「下架 / 重新上架」。
// sku 建立後不給改（是商品的識別）——編輯只讓改品名/牌價。
// 提醒：改牌價只影響「之後的新訂單」,已成立訂單的明細是快照、不受影響（見訂單頁）。
import { onMounted, reactive, ref } from 'vue'
import { Plus, Pencil } from '@lucide/vue'
import {
  createProduct,
  deactivateProduct,
  listProducts,
  reactivateProduct,
  updateProduct,
} from '@/api/product'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import DataTable from '@/components/DataTable.vue'
import { TableCell } from '@/components/ui/table'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'

const products = ref([])
const q = ref('')
const loading = ref(false)
const errorMsg = ref('')

// 欄位定義（餵給 DataTable）。品名吃剩餘寬度；狀態欄放可直接切的 Switch。
const columns = [
  { label: '品號', width: 'w-36' },
  { label: '品名' },
  { label: '牌價', width: 'w-28', align: 'right' },
  { label: '狀態', width: 'w-24', align: 'center' },
]

async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    // 這頁看全部（含下架,才能重新上架）；訂單頁的商品 select 才用 activeOnly。
    products.value = (await listProducts({ pageSize: 100, q: q.value })).items
  } catch (e) {
    errorMsg.value = '載入失敗,請稍後再試'
    console.error(e)
  } finally {
    loading.value = false
  }
}

onMounted(load)

// ── 新增 / 編輯 dialog ──────────────────────────────────
const showForm = ref(false)
const editingId = ref(null) // null = 新增；有值 = 編輯（sku 不可改）
const form = reactive({ sku: '', name: '', unit_price: 0 })
const formError = ref('')

function openCreate() {
  editingId.value = null
  form.sku = ''
  form.name = ''
  form.unit_price = 0
  formError.value = ''
  showForm.value = true
}

function openEdit(p) {
  editingId.value = p.id
  form.sku = p.sku
  form.name = p.name
  form.unit_price = p.unit_price
  formError.value = ''
  showForm.value = true
}

async function submitForm() {
  formError.value = ''
  if ((!editingId.value && !form.sku) || !form.name) {
    formError.value = '品號與品名必填'
    return
  }
  try {
    if (editingId.value)
      await updateProduct(editingId.value, { name: form.name, unit_price: Number(form.unit_price) })
    else await createProduct({ sku: form.sku, name: form.name, unit_price: Number(form.unit_price) })
    showForm.value = false
    load()
  } catch (e) {
    formError.value = e.response?.data?.detail || '儲存失敗,請稍後再試'
    console.error(e)
  }
}

// ── 下架 / 重新上架（沒有刪除）─────────────────────────
const busyId = ref(null)
async function toggleActive(p) {
  busyId.value = p.id
  try {
    const updated = p.is_active ? await deactivateProduct(p.id) : await reactivateProduct(p.id)
    const i = products.value.findIndex((x) => x.id === p.id)
    if (i > -1) products.value[i] = updated
  } catch (e) {
    errorMsg.value = '操作失敗,請稍後再試'
    console.error(e)
  } finally {
    busyId.value = null
  }
}
</script>

<template>
  <div class="flex h-full flex-col">
    <h1 class="shrink-0 text-lg font-semibold leading-none tracking-tight">商品列表</h1>

    <div class="mt-5 flex min-h-0 flex-1 flex-col rounded-lg border bg-card p-5 shadow-sm">
      <p v-if="errorMsg" class="text-destructive mb-3 shrink-0 text-sm">{{ errorMsg }}</p>

      <!-- 工具列 -->
      <div class="mb-4 flex shrink-0 items-center justify-between gap-2">
        <div class="flex flex-wrap items-center gap-2">
          <Input v-model="q" placeholder="搜品名…" class="w-40" @keyup.enter="load" />
          <Button variant="outline" @click="load">搜尋</Button>
        </div>
        <Button @click="openCreate"><Plus class="size-4" /> 新增商品</Button>
      </div>

      <!-- 表格：水電全包在 DataTable；狀態欄放可直接切的 Switch（下架不刪），操作只留編輯 -->
      <DataTable :items="products" :columns="columns" :loading="loading">
        <template #row="{ item: p }">
          <TableCell class="tabular-nums">{{ p.sku }}</TableCell>
          <TableCell class="font-medium">{{ p.name }}</TableCell>
          <TableCell class="text-right tabular-nums">{{ p.unit_price.toLocaleString() }}</TableCell>
          <TableCell class="text-center">
            <Switch
              :model-value="p.is_active"
              :disabled="busyId === p.id"
              title="上架 / 下架（下架不刪）"
              @update:model-value="() => toggleActive(p)"
            />
          </TableCell>
        </template>
        <template #actions="{ item: p }">
          <Button variant="ghost" size="icon-sm" class="text-muted-foreground hover:text-foreground" title="編輯" @click="openEdit(p)">
            <Pencil class="size-4" />
          </Button>
        </template>
        <template #empty>沒有商品——按上方「＋ 新增商品」建第一個</template>
      </DataTable>
    </div>

    <!-- 新增/編輯 dialog -->
    <Dialog v-model:open="showForm">
      <DialogContent class="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{{ editingId ? '編輯商品' : '新增商品' }}</DialogTitle>
          <DialogDescription>{{ editingId ? '品號是商品識別,建立後不可改。改牌價只影響之後的新訂單。' : '一個品號只能對到一個商品。' }}</DialogDescription>
        </DialogHeader>
        <div class="flex flex-col gap-3 py-2">
          <div class="flex flex-col gap-1.5">
            <Label>品號 sku</Label>
            <Input v-model="form.sku" placeholder="SVC-CLEAN" :disabled="!!editingId" />
          </div>
          <div class="flex flex-col gap-1.5">
            <Label>品名</Label>
            <Input v-model="form.name" placeholder="居家深度打掃" />
          </div>
          <div class="flex flex-col gap-1.5">
            <Label>牌價</Label>
            <Input v-model.number="form.unit_price" type="number" min="0" placeholder="1800" />
          </div>
          <p v-if="formError" class="text-destructive text-sm">{{ formError }}</p>
        </div>
        <DialogFooter>
          <Button variant="outline" @click="showForm = false">取消</Button>
          <Button @click="submitForm">儲存</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
