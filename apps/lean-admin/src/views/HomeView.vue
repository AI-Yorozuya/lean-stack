<script setup>
// 後台首頁：儀表板入口。連線狀態已移到頂部 bar（每頁都看得到），
// 這頁就當「功能入口卡片」——之後加新功能就多一張卡。
import { RouterLink } from 'vue-router'
import { Users, Package, ShoppingCart, Server, ArrowRight } from '@lucide/vue'
import { Card, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'

const features = [
  { to: '/members', icon: Users, title: '會員', desc: '講「列表 + CRUD」：一 email 一會員、停用不刪。訂單的「下單的人」就是它。' },
  { to: '/products', icon: Package, title: '商品', desc: '講「列表 + CRUD」：一 sku 一商品、下架不刪。訂單明細從這裡挑、抄快照。' },
  { to: '/orders', icon: ShoppingCart, title: '訂單', desc: '講「狀態與流程」：串會員+商品、下單抄快照，再跑生命週期狀態機（非法轉移後端擋）。' },
  { to: '/job', icon: Server, title: '背景任務', desc: '派工給 celery worker、清單輪詢進度——async 整條路的活範例。' },
]
</script>

<template>
  <div>
    <h1 class="text-lg font-semibold leading-none tracking-tight">lean-stack 管理後台</h1>
    <p class="text-muted-foreground mt-1 text-sm">從這裡進到各功能。之後加新功能，就在這裡多一張卡、左側多一條導覽。</p>

    <div class="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <RouterLink v-for="f in features" :key="f.to" :to="f.to" class="group">
        <Card class="h-full gap-0 transition-all group-hover:border-slate-300 group-hover:shadow-md">
          <CardHeader>
            <!-- icon 徽章：與側欄品牌「L」同語彙（深色圓角方塊）-->
            <div class="mb-3 flex size-10 items-center justify-center rounded-lg bg-slate-900 text-white">
              <component :is="f.icon" class="size-5" />
            </div>
            <CardTitle class="flex items-center justify-between gap-2 text-base">
              {{ f.title }}
              <ArrowRight class="text-muted-foreground size-4 shrink-0 transition-transform group-hover:translate-x-0.5" />
            </CardTitle>
            <CardDescription class="mt-1.5 leading-relaxed">{{ f.desc }}</CardDescription>
          </CardHeader>
        </Card>
      </RouterLink>
    </div>
  </div>
</template>
