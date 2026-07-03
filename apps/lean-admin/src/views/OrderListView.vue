<script setup>
// 訂單管理列表頁（Stage A：無狀態 CRUD）。
// 教學重點——這一頁就是「認識積木」上半的完整詞彙表：
//   看全部訂單   → table + pagination     （讀清單）
//   篩選         → input + select + button（讀清單·帶條件）
//   新增 / 編輯  → button → dialog + form （建立 / 修改）
//   刪除         → button → dialog 確認   （刪除）
// 七個元件、四個 API，每個都因為一個動作而存在。
//
// 鐵則的分工（重要）：表單裡的「小計/總計」是前端算給人看的即時回饋；
// 送出後一律以後端回傳為準——錢的真相在後端（見後端 models.py）。
import { computed, onMounted, reactive, ref } from 'vue'
import {
  createCustomer,
  createOrder,
  deleteOrder,
  listCustomers,
  listOrders,
  updateOrder,
} from '@/api/order'

// ── 列表狀態 ────────────────────────────────────────────
const orders = ref([])
const count = ref(0)
const page = ref(1)
const pageSize = 10
const q = ref('')                 // input：模糊搜客戶名
const filterCustomerId = ref('')  // select：精準篩客戶
const customers = ref([])
const loading = ref(false)
const errorMsg = ref('')

const totalPages = computed(() => Math.max(1, Math.ceil(count.value / pageSize)))

async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    const data = await listOrders({
      page: page.value,
      pageSize,
      q: q.value,
      customerId: filterCustomerId.value || null,
    })
    orders.value = data.items
    count.value = data.count
  } catch (e) {
    errorMsg.value = '載入失敗，請稍後再試'
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function loadCustomers() {
  customers.value = await listCustomers()
}

function search() {
  page.value = 1
  load()
}

function goPage(p) {
  page.value = Math.min(Math.max(1, p), totalPages.value)
  load()
}

onMounted(() => {
  load()
  loadCustomers()
})

// ── 新增 / 編輯 dialog ──────────────────────────────────
const showForm = ref(false)
const editingId = ref(null) // null = 新增；有值 = 編輯
const form = reactive({ customer_id: '', items: [] })
const formError = ref('')

function blankItem() {
  return { name: '', quantity: 1, unit_price: 0 }
}

function openCreate() {
  editingId.value = null
  form.customer_id = ''
  form.items = [blankItem()]
  formError.value = ''
  showForm.value = true
}

function openEdit(order) {
  editingId.value = order.id
  form.customer_id = order.customer.id
  // 只取表單需要的欄位（id/subtotal 是後端的事）
  form.items = order.items.map((i) => ({
    name: i.name,
    quantity: i.quantity,
    unit_price: i.unit_price,
  }))
  formError.value = ''
  showForm.value = true
}

function addItem() {
  form.items.push(blankItem())
}

function removeItem(idx) {
  // 鐵則 {至少一筆明細}：前端先擋（體驗），後端也會擋（真相）。
  if (form.items.length <= 1) {
    formError.value = '鐵則：一張訂單至少要有一筆明細'
    return
  }
  form.items.splice(idx, 1)
}

// 即時小計/總計——只是顯示給人看；送出後以後端回傳為準。
const itemSubtotal = (i) => (Number(i.quantity) || 0) * (Number(i.unit_price) || 0)
const formTotal = computed(() => form.items.reduce((sum, i) => sum + itemSubtotal(i), 0))

async function submitForm() {
  formError.value = ''
  if (!form.customer_id) {
    formError.value = '請選擇客戶'
    return
  }
  const payload = {
    customer_id: Number(form.customer_id),
    items: form.items.map((i) => ({
      name: i.name,
      quantity: Number(i.quantity),
      unit_price: Number(i.unit_price),
    })),
  }
  try {
    if (editingId.value) await updateOrder(editingId.value, payload)
    else await createOrder(payload)
    showForm.value = false
    load()
  } catch (e) {
    // 後端擋下的（422 = 鐵則/驗證不過）給人看得懂的訊息
    formError.value = e.response?.status === 422 ? '資料不合規則：請檢查明細（數量要 > 0、至少一筆）' : '儲存失敗，請稍後再試'
    console.error(e)
  }
}

// ── 快速新增客戶（下單時客戶還不存在的小門）─────────────
const showNewCustomer = ref(false)
const newCustomer = reactive({ name: '', phone: '' })

async function submitNewCustomer() {
  if (!newCustomer.name) return
  const c = await createCustomer({ ...newCustomer })
  await loadCustomers()
  form.customer_id = c.id // 建完直接選上
  newCustomer.name = ''
  newCustomer.phone = ''
  showNewCustomer.value = false
}

// ── 刪除確認 dialog ─────────────────────────────────────
const deleting = ref(null) // 存要刪的 order 物件

async function confirmDelete() {
  await deleteOrder(deleting.value.id)
  deleting.value = null
  // 刪掉本頁最後一筆時退一頁，別停在空頁上
  if (orders.value.length === 1 && page.value > 1) page.value -= 1
  load()
}
</script>

<template>
  <main class="page">
    <h1>訂單管理</h1>
    <p class="hint">Stage A：無狀態 CRUD——訂單就是一筆「有明細、有客戶」的資料（規則見 intents/訂單管理.md）</p>

    <!-- 篩選列：input + select + button -->
    <div class="toolbar">
      <input v-model="q" placeholder="搜客戶名…" @keyup.enter="search" />
      <select v-model="filterCustomerId" @change="search">
        <option value="">全部客戶</option>
        <option v-for="c in customers" :key="c.id" :value="c.id">{{ c.name }}</option>
      </select>
      <button @click="search">搜尋</button>
      <button class="primary" style="margin-left: auto" @click="openCreate">＋ 新增訂單</button>
    </div>

    <p v-if="errorMsg" class="error">{{ errorMsg }}</p>

    <!-- table -->
    <table>
      <thead>
        <tr><th>#</th><th>客戶</th><th>日期</th><th>明細</th><th class="num">總額</th><th></th></tr>
      </thead>
      <tbody>
        <tr v-for="o in orders" :key="o.id">
          <td>{{ o.id }}</td>
          <td>{{ o.customer.name }}</td>
          <td>{{ o.order_date }}</td>
          <td>{{ o.items.length }} 筆</td>
          <td class="num">{{ o.total.toLocaleString() }}</td>
          <td class="ops">
            <button @click="openEdit(o)">編輯</button>
            <button class="danger" @click="deleting = o">刪除</button>
          </td>
        </tr>
        <tr v-if="!loading && orders.length === 0">
          <td colspan="6" class="empty">沒有訂單——按右上「＋ 新增訂單」開第一張</td>
        </tr>
      </tbody>
    </table>

    <!-- pagination -->
    <div class="pager">
      <button :disabled="page <= 1" @click="goPage(page - 1)">上一頁</button>
      <span>{{ page }} / {{ totalPages }}（共 {{ count }} 筆）</span>
      <button :disabled="page >= totalPages" @click="goPage(page + 1)">下一頁</button>
    </div>

    <!-- 新增/編輯 dialog + form -->
    <div v-if="showForm" class="overlay" @click.self="showForm = false">
      <div class="dialog">
        <h2>{{ editingId ? `編輯訂單 #${editingId}` : '新增訂單' }}</h2>

        <label>客戶</label>
        <div class="row">
          <select v-model="form.customer_id">
            <option value="" disabled>選擇客戶</option>
            <option v-for="c in customers" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
          <button @click="showNewCustomer = !showNewCustomer">＋ 新客戶</button>
        </div>
        <div v-if="showNewCustomer" class="row subform">
          <input v-model="newCustomer.name" placeholder="客戶姓名" />
          <input v-model="newCustomer.phone" placeholder="電話（選填）" />
          <button class="primary" @click="submitNewCustomer">建立</button>
        </div>

        <label>明細（小計 = 數量 × 單價，自動算）</label>
        <div v-for="(item, idx) in form.items" :key="idx" class="row item-row">
          <input v-model="item.name" placeholder="品項名" class="grow" />
          <input v-model.number="item.quantity" type="number" min="1" class="qty" />
          <span>×</span>
          <input v-model.number="item.unit_price" type="number" min="0" class="price" />
          <span class="subtotal">= {{ itemSubtotal(item).toLocaleString() }}</span>
          <button class="danger" @click="removeItem(idx)">✕</button>
        </div>
        <button @click="addItem">＋ 加一筆明細</button>

        <p class="total">總計：{{ formTotal.toLocaleString() }}<small>（顯示用；存檔後以後端計算為準）</small></p>
        <p v-if="formError" class="error">{{ formError }}</p>

        <div class="row end">
          <button @click="showForm = false">取消</button>
          <button class="primary" @click="submitForm">儲存</button>
        </div>
      </div>
    </div>

    <!-- 刪除確認 dialog -->
    <div v-if="deleting" class="overlay" @click.self="deleting = null">
      <div class="dialog narrow">
        <h2>刪除訂單 #{{ deleting.id }}？</h2>
        <p>客戶 {{ deleting.customer.name }}、總額 {{ deleting.total.toLocaleString() }}。刪了就沒了（明細一起刪）。</p>
        <div class="row end">
          <button @click="deleting = null">取消</button>
          <button class="danger" @click="confirmDelete">確定刪除</button>
        </div>
      </div>
    </div>
  </main>
</template>

<style scoped>
.page { font-family: system-ui, sans-serif; max-width: 880px; margin: 2rem auto; padding: 0 1rem; }
h1 { margin-bottom: 0.25rem; }
.hint { color: #888; font-size: 0.85rem; margin-bottom: 1rem; }
.toolbar { display: flex; gap: 0.5rem; margin-bottom: 1rem; }
input, select { padding: 0.4rem 0.6rem; border: 1px solid #ccc; border-radius: 6px; font: inherit; }
button { padding: 0.4rem 0.8rem; border: 1px solid #ccc; border-radius: 6px; background: #fff; cursor: pointer; font: inherit; }
button:hover { background: #f5f5f5; }
button.primary { background: #1a73e8; border-color: #1a73e8; color: #fff; }
button.primary:hover { background: #1765cc; }
button.danger { color: #c62828; border-color: #e0b4b4; }
button:disabled { opacity: 0.4; cursor: default; }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; padding: 0.5rem 0.6rem; border-bottom: 1px solid #eee; }
.num { text-align: right; }
.ops { text-align: right; white-space: nowrap; }
.ops button { margin-left: 0.3rem; }
.empty { text-align: center; color: #999; padding: 2rem 0; }
.pager { display: flex; gap: 1rem; align-items: center; justify-content: center; margin-top: 1rem; }
.error { color: #c62828; }
.overlay { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.35); display: flex; align-items: center; justify-content: center; }
.dialog { background: #fff; border-radius: 10px; padding: 1.5rem; width: min(640px, 92vw); max-height: 88vh; overflow-y: auto; }
.dialog.narrow { width: min(400px, 92vw); }
.dialog label { display: block; margin: 0.9rem 0 0.3rem; font-weight: 600; font-size: 0.9rem; }
.row { display: flex; gap: 0.5rem; align-items: center; margin-bottom: 0.4rem; }
.row.end { justify-content: flex-end; margin-top: 1rem; }
.subform { background: #f7f7f7; padding: 0.5rem; border-radius: 6px; }
.grow { flex: 1; }
.qty { width: 4.5rem; }
.price { width: 6.5rem; }
.subtotal { min-width: 6rem; text-align: right; color: #555; }
.total { margin-top: 0.8rem; font-weight: 700; }
.total small { font-weight: 400; color: #999; margin-left: 0.5rem; }
</style>
