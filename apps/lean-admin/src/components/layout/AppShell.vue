<script setup>
// 應用外殼（app shell）：常駐的左側 sidebar + 頂部 bar + 中間內容區。
// 配色走白底極簡（參考 ERPNext desk 側欄）；結構（可收合 + 多層選單）參考 top-admin。
// 所有頁面都長在這個殼裡（見 App.vue 把 <router-view/> 塞進 <slot/>）。
//
// 教學重點：
//   - 「版面」與「頁面」分離：殼負責導覽/框架，頁面只管自己的內容。
//   - nav 支援兩種：單一項（有 to）與群組（有 children）。加頁往這個陣列加一筆。
//   - active 用 derive（讀 route，不用 watch）；含 active 子項的群組自動展開。
//   - 可收合（w-56 完整 ⇄ w-16 icon-only），狀態存 localStorage、小螢幕自動收。
import { ref, onBeforeMount, onMounted, onBeforeUnmount } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
// 選單 icon 一律取「同一套 lucide、視覺重量相近的實心輪廓物件」——參 top-admin 的
// constants/icons.js（避免混入 Activity 那種稀疏脈衝線，破壞整體一致性）。
import { LayoutDashboard, ShoppingCart, RefreshCw, ChevronDown, ChevronsLeft, ChevronsRight } from '@lucide/vue'
import { getHealth } from '@/api'
import HealthBadge from '@/components/HealthBadge.vue'

// 導覽：單一項 { to, label, icon }；群組 { label, icon, children:[{ to, label }] }。
const nav = [
  { to: '/', label: '首頁', icon: LayoutDashboard },
  {
    label: '訂單管理',
    icon: ShoppingCart,
    children: [
      { to: '/orders', label: '無狀態示範' },
      { to: '/orders/lifecycle', label: '有狀態示範' },
    ],
  },
  { to: '/job', label: '非同步示範', icon: RefreshCw },
]

const route = useRoute()
// active 一律 exact 比對（leaf 頁面）。
const isItemActive = (to) => route.path === to
const isGroupActive = (item) => item.children.some((c) => route.path === c.to)

// ── 群組展開狀態（手動開的 ∪ 含 active 子項的都算開）──
const openGroups = ref(new Set())
const isGroupOpen = (item) => openGroups.value.has(item.label) || isGroupActive(item)
function toggleGroup(item) {
  // 收合狀態下點群組 → 先把側欄展開，再打開該群組。
  if (!expanded.value) {
    expanded.value = true
    localStorage.setItem(STORAGE_KEY, 'true')
    openGroups.value.add(item.label)
    return
  }
  if (openGroups.value.has(item.label)) openGroups.value.delete(item.label)
  else openGroups.value.add(item.label)
}

// ── 收合狀態（localStorage 持久化 + 小螢幕自動收）──
const expanded = ref(true)
const STORAGE_KEY = 'leanSidebarExpanded'
const MOBILE_BP = 1024
const isMobile = () => typeof window !== 'undefined' && window.innerWidth < MOBILE_BP

onBeforeMount(() => {
  if (isMobile()) {
    expanded.value = false
    return
  }
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored !== null) expanded.value = stored === 'true'
})

function toggle() {
  expanded.value = !expanded.value
  localStorage.setItem(STORAGE_KEY, String(expanded.value))
}

function handleResize() {
  if (isMobile() && expanded.value) expanded.value = false
}

// ── 後端連線狀態（殼掛載時打一次 health）──
const status = ref('checking') // checking | ok | error
onMounted(async () => {
  window.addEventListener('resize', handleResize)
  try {
    const data = await getHealth()
    status.value = data.status === 'ok' ? 'ok' : 'error'
  } catch (e) {
    console.error('health check failed:', e)
    status.value = 'error'
  }
})
onBeforeUnmount(() => window.removeEventListener('resize', handleResize))
</script>

<template>
  <div class="flex h-screen w-screen overflow-hidden">
    <!-- ── 左側 sidebar（白底極簡，可收合）───────────────── -->
    <aside
      class="flex h-full flex-col overflow-hidden border-r border-neutral-200 bg-white transition-[width] duration-200"
      :class="expanded ? 'w-56' : 'w-16'"
    >
      <!-- Logo（學 top-admin 的三件事：①整塊是「回首頁」的連結 ②h-14 對齊頂 bar、
           展開/收合都靠同一顆標記垂直對齊下方選單 icon ③標題收斂質感 text-base +
           tracking-wide）。沒有品牌圖檔，用 monogram 方塊當標記。 -->
      <button
        type="button"
        title="回首頁"
        class="flex h-14 shrink-0 cursor-pointer items-center gap-2.5 overflow-hidden border-b border-neutral-200 text-left transition-opacity hover:opacity-70"
        :class="expanded ? 'justify-start px-4' : 'justify-center'"
        @click="$router.push('/')"
      >
        <div class="flex size-7 shrink-0 items-center justify-center rounded-md bg-neutral-900 text-sm font-bold text-white">L</div>
        <span v-show="expanded" class="whitespace-nowrap text-base font-semibold tracking-wide text-neutral-800">lean-stack 後台</span>
      </button>

      <!-- Menu -->
      <nav class="flex flex-1 flex-col gap-0.5 overflow-x-hidden overflow-y-auto p-2">
        <template v-for="item in nav" :key="item.label">
          <!-- 單一項 -->
          <RouterLink v-if="item.to" v-slot="{ isActive }" :to="item.to" custom>
            <button
              :title="item.label"
              :class="[
                'flex w-full items-center rounded-md text-sm transition-colors',
                expanded ? 'gap-3 px-3 py-2' : 'justify-center px-0 py-2.5',
                isItemActive(item.to)
                  ? 'relative bg-neutral-100 font-medium text-neutral-900 before:absolute before:top-1/2 before:left-0 before:h-5 before:w-[3px] before:-translate-y-1/2 before:rounded-full before:bg-neutral-900'
                  : 'text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900',
              ]"
              @click="$router.push(item.to)"
            >
              <component :is="item.icon" class="size-[18px] shrink-0" />
              <span v-show="expanded" class="whitespace-nowrap">{{ item.label }}</span>
            </button>
          </RouterLink>

          <!-- 群組（父 + 子）-->
          <template v-else>
            <button
              :title="item.label"
              :class="[
                'flex w-full items-center rounded-md text-sm transition-colors',
                expanded ? 'gap-3 px-3 py-2' : 'justify-center px-0 py-2.5',
                isGroupActive(item)
                  ? 'font-medium text-neutral-900'
                  : 'text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900',
              ]"
              @click="toggleGroup(item)"
            >
              <component :is="item.icon" class="size-[18px] shrink-0" />
              <template v-if="expanded">
                <span class="flex-1 whitespace-nowrap text-left">{{ item.label }}</span>
                <ChevronDown class="size-4 transition-transform duration-200" :class="isGroupOpen(item) ? 'rotate-180' : ''" />
              </template>
            </button>

            <!-- 子項（只在展開 + 群組打開時顯示）-->
            <div v-show="expanded && isGroupOpen(item)" class="mt-0.5 flex flex-col gap-0.5">
              <RouterLink v-for="child in item.children" :key="child.to" :to="child.to" custom>
                <button
                  :class="[
                    'flex w-full items-center rounded-md py-2 pl-11 pr-3 text-left text-sm transition-colors',
                    isItemActive(child.to)
                      ? 'relative bg-neutral-100 font-medium text-neutral-900 before:absolute before:top-1/2 before:left-0 before:h-4 before:w-[3px] before:-translate-y-1/2 before:rounded-full before:bg-neutral-900'
                      : 'text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900',
                  ]"
                  @click="$router.push(child.to)"
                >
                  <span class="whitespace-nowrap">{{ child.label }}</span>
                </button>
              </RouterLink>
            </div>
          </template>
        </template>
      </nav>

      <div v-show="expanded" class="p-4 text-xs text-neutral-400">教學 sandbox · admin</div>
    </aside>

    <!-- ── 右側：頂部 bar + 內容 ─────────────────────── -->
    <div class="flex flex-1 flex-col overflow-hidden">
      <header class="flex h-14 shrink-0 items-center justify-between border-b border-neutral-200 bg-white px-6">
        <button
          type="button"
          :title="expanded ? '收合側邊欄' : '展開側邊欄'"
          class="inline-flex size-9 items-center justify-center rounded-lg text-neutral-500 transition-all hover:bg-neutral-100 hover:text-neutral-900 active:scale-95"
          @click="toggle"
        >
          <ChevronsLeft v-if="expanded" class="size-5" />
          <ChevronsRight v-else class="size-5" />
        </button>

        <!-- 後端連線指示（auth 之後換成使用者選單）-->
        <HealthBadge :status="status" />
      </header>

      <main class="main-content min-w-0 flex-1 overflow-auto p-6">
        <slot />
      </main>
    </div>
  </div>
</template>

<style scoped>
/* 內容區底色（極淺灰，讓白卡片浮起來）+ 中性捲軸。 */
.main-content {
  background-color: #f7f7f8;
}
.main-content::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
.main-content::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.18);
  border-radius: 3px;
}
nav::-webkit-scrollbar {
  width: 4px;
}
nav::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.12);
  border-radius: 2px;
}
</style>
