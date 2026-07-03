<script setup>
// 分頁 —— 極簡：置中的數字頁碼（含 … 截斷、上/下一頁）。刻意不放「每頁筆數」與「總筆數」：
//   每頁筆數＝企業級大表才需要，這個規模用不到（頁大小固定在 view）；
//   總筆數＝數字頁碼已隱含頁數，小資料省略更乾淨（需要再加回一行小字即可）。
// 當前頁不反黑，只用「加粗深字 + 很淡的底色 pill」輕輕標。
// 用法：<Pagination :page="page" :total-pages="totalPages" @update:page="goPage" />
import { computed } from 'vue'
import { ChevronLeft, ChevronRight } from '@lucide/vue'

const props = defineProps({
  page: { type: Number, required: true },
  totalPages: { type: Number, required: true },
})
const emit = defineEmits(['update:page'])

// 數字截斷：頭尾各留、當前頁前後各一，中間用 …（頁數多時不爆一長排）。
const visiblePages = computed(() => {
  const total = props.totalPages
  const cur = props.page
  const pages = []
  if (total <= 7) {
    for (let i = 1; i <= total; i++) pages.push(i)
  } else if (cur <= 4) {
    for (let i = 1; i <= 5; i++) pages.push(i)
    pages.push('…', total)
  } else if (cur >= total - 3) {
    pages.push(1, '…')
    for (let i = total - 4; i <= total; i++) pages.push(i)
  } else {
    pages.push(1, '…')
    for (let i = cur - 1; i <= cur + 1; i++) pages.push(i)
    pages.push('…', total)
  }
  return pages
})

function go(p) {
  const next = Math.min(Math.max(1, p), props.totalPages)
  if (typeof p === 'number' && next !== props.page) emit('update:page', next)
}

// 文字式方塊（無外框）；當前頁不反黑，只用「加粗+深字+淡底 pill」輕輕標。
const cellBase =
  'flex size-8 items-center justify-center rounded-md text-sm tabular-nums transition-colors disabled:pointer-events-none disabled:opacity-40'
</script>

<template>
  <div class="flex items-center justify-center gap-1">
    <button :class="[cellBase, 'text-muted-foreground hover:bg-muted hover:text-foreground']" :disabled="page <= 1" title="上一頁" @click="go(page - 1)">
      <ChevronLeft class="size-4" />
    </button>

    <template v-for="(p, i) in visiblePages" :key="i">
      <span v-if="p === '…'" class="text-muted-foreground flex size-8 items-center justify-center">…</span>
      <button
        v-else
        :class="[cellBase, p === page ? 'bg-muted text-foreground font-semibold' : 'text-muted-foreground hover:bg-muted hover:text-foreground']"
        @click="go(p)"
      >
        {{ p }}
      </button>
    </template>

    <button :class="[cellBase, 'text-muted-foreground hover:bg-muted hover:text-foreground']" :disabled="page >= totalPages" title="下一頁" @click="go(page + 1)">
      <ChevronRight class="size-4" />
    </button>
  </div>
</template>
