<script setup>
// 會員管理頁（最單純 CRUD）。規則見 intents/會員管理.md。
// 教學重點——這是「加一頁」的乾淨範例，也示範兩條鐵則長在 UI 上的樣子：
//   {一 email 一會員} → 建立撞 email 後端回 422，前端顯示白話。
//   {停用不刪}        → 沒有「刪除」，只有「停用 / 重新啟用」（狀態關閉、資料保留）。
// email 建立後不給改（是會員的識別）——編輯只讓改姓名/電話。
import { computed, onMounted, reactive, ref } from 'vue'
import { Plus } from '@lucide/vue'
import {
  createMember,
  deactivateMember,
  listMembers,
  reactivateMember,
  updateMember,
} from '@/api/member'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'

const members = ref([])
const q = ref('')
const filterStatus = ref('all') // all | ACTIVE | INACTIVE
const loading = ref(false)
const errorMsg = ref('')

async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    const data = await listMembers({
      pageSize: 100,
      q: q.value,
      status: filterStatus.value === 'all' ? '' : filterStatus.value,
    })
    members.value = data.items
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
const editingId = ref(null) // null = 新增；有值 = 編輯（email 不可改）
const form = reactive({ name: '', email: '', phone: '' })
const formError = ref('')

function openCreate() {
  editingId.value = null
  form.name = ''
  form.email = ''
  form.phone = ''
  formError.value = ''
  showForm.value = true
}

function openEdit(m) {
  editingId.value = m.id
  form.name = m.name
  form.email = m.email
  form.phone = m.phone
  formError.value = ''
  showForm.value = true
}

async function submitForm() {
  formError.value = ''
  if (!form.name || (!editingId.value && !form.email)) {
    formError.value = '姓名與 email 必填'
    return
  }
  try {
    if (editingId.value) await updateMember(editingId.value, { name: form.name, phone: form.phone })
    else await createMember({ name: form.name, email: form.email, phone: form.phone })
    showForm.value = false
    load()
  } catch (e) {
    formError.value = e.response?.data?.detail || '儲存失敗,請稍後再試'
    console.error(e)
  }
}

// ── 停用 / 重新啟用（沒有刪除）─────────────────────────
const busyId = ref(null)
async function toggleStatus(m) {
  busyId.value = m.id
  try {
    const updated = m.status === 'ACTIVE' ? await deactivateMember(m.id) : await reactivateMember(m.id)
    const i = members.value.findIndex((x) => x.id === m.id)
    if (i > -1) members.value[i] = updated
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
    <h1 class="shrink-0 text-lg font-semibold leading-none tracking-tight">會員列表</h1>

    <div class="mt-5 flex min-h-0 flex-1 flex-col rounded-lg border bg-card p-5 shadow-sm">
      <p v-if="errorMsg" class="text-destructive mb-3 shrink-0 text-sm">{{ errorMsg }}</p>

      <!-- 工具列 -->
      <div class="mb-4 flex shrink-0 items-center justify-between gap-2">
        <div class="flex flex-wrap items-center gap-2">
          <Input v-model="q" placeholder="搜姓名…" class="w-40" @keyup.enter="load" />
          <Select v-model="filterStatus" @update:model-value="load">
            <SelectTrigger class="w-32"><SelectValue placeholder="全部狀態" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部狀態</SelectItem>
              <SelectItem value="ACTIVE">啟用</SelectItem>
              <SelectItem value="INACTIVE">停用</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" @click="load">搜尋</Button>
        </div>
        <Button @click="openCreate"><Plus class="size-4" /> 新增會員</Button>
      </div>

      <!-- 表格 -->
      <div class="flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border">
        <div class="scroll-thin bg-card shrink-0 overflow-y-auto">
          <Table class="table-fixed">
            <colgroup><col /><col class="w-64" /><col class="w-32" /><col class="w-20" /><col class="w-36" /></colgroup>
            <TableHeader>
              <TableRow>
                <TableHead>姓名</TableHead>
                <TableHead>email</TableHead>
                <TableHead>電話</TableHead>
                <TableHead>狀態</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
          </Table>
        </div>
        <div class="scroll-thin min-h-0 flex-1 overflow-y-auto">
          <Table class="table-fixed">
            <colgroup><col /><col class="w-64" /><col class="w-32" /><col class="w-20" /><col class="w-36" /></colgroup>
            <TableBody>
              <TableRow v-for="m in members" :key="m.id">
                <TableCell class="font-medium">{{ m.name }}</TableCell>
                <TableCell class="text-muted-foreground">{{ m.email }}</TableCell>
                <TableCell class="text-muted-foreground">{{ m.phone || '—' }}</TableCell>
                <TableCell>
                  <Badge :variant="m.status === 'ACTIVE' ? 'secondary' : 'outline'">{{ m.status_display }}</Badge>
                </TableCell>
                <TableCell class="text-right whitespace-nowrap">
                  <Button variant="ghost" size="sm" @click="openEdit(m)">編輯</Button>
                  <Button variant="ghost" size="sm" :disabled="busyId === m.id" @click="toggleStatus(m)">
                    {{ m.status === 'ACTIVE' ? '停用' : '重新啟用' }}
                  </Button>
                </TableCell>
              </TableRow>
              <TableRow v-if="!loading && members.length === 0">
                <TableCell colspan="5" class="text-muted-foreground py-16 text-center">
                  沒有會員——按右上「＋ 新增會員」建第一位
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
      </div>
    </div>

    <!-- 新增/編輯 dialog -->
    <Dialog v-model:open="showForm">
      <DialogContent class="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{{ editingId ? '編輯會員' : '新增會員' }}</DialogTitle>
          <DialogDescription>{{ editingId ? 'email 是會員識別,建立後不可改。' : '一個 email 只能對到一位會員。' }}</DialogDescription>
        </DialogHeader>
        <div class="flex flex-col gap-3 py-2">
          <div class="flex flex-col gap-1.5">
            <Label>姓名</Label>
            <Input v-model="form.name" placeholder="王小明" />
          </div>
          <div class="flex flex-col gap-1.5">
            <Label>email</Label>
            <Input v-model="form.email" placeholder="name@example.com" :disabled="!!editingId" />
          </div>
          <div class="flex flex-col gap-1.5">
            <Label>電話</Label>
            <Input v-model="form.phone" placeholder="0912-345-678（選填）" />
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
