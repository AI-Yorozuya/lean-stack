<script setup>
// 對外門市首頁——版型抓 _project/lean-commerce 的 storefront（hero / trust / featured / 會員 band）。
// 差別：① 商品讀 lean-stack「同一個後端」/api/v1/product（改後台→這裡跟著變）
//       ② 購物車是「假的」：加清單、算小計、跳提示，不真結帳（示範用）
//       ③ 招牌 STORE_NAME 就是免費體驗 F1「換招牌」要改的字
import { ref, computed, onMounted } from 'vue'

const STORE_NAME = '選物小舖' // ← 換招牌改這裡

const products = ref([])
const loading = ref(true)
const errorMsg = ref('')

const cart = ref([]) // 假購物車：放商品物件（示範用）
const cartOpen = ref(false)
const toast = ref('')
let toastTimer = null

const money = (n) => 'NT$ ' + Number(n).toLocaleString()
const subtotal = computed(() => cart.value.reduce((s, p) => s + Number(p.unit_price), 0))

function flash(msg, ms = 1600) {
  toast.value = msg
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => (toast.value = ''), ms)
}
function addToCart(p) {
  cart.value.push(p)
  cartOpen.value = true
}
function removeAt(i) {
  cart.value.splice(i, 1)
}
function fakeCheckout() {
  cartOpen.value = false
  flash('這是示範門市，先不結帳 😄', 2000)
}
function scrollTo(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })
}

onMounted(async () => {
  try {
    const res = await fetch('/api/v1/product?page_size=100&active_only=true')
    products.value = (await res.json()).items
  } catch (e) {
    errorMsg.value = '商品載入失敗，請確認後端有起來。'
    console.error(e)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div>
    <!-- 公告列 -->
    <div class="anno">全站滿 NT$1,000 免運　·　新會員首購 88 折（WELCOME88）　·　7-11／全家 超商取貨</div>

    <!-- Header -->
    <header class="hd">
      <div class="rd-wrap hd-in">
        <a class="logo rd-serif" @click="scrollTo('top')"><img src="/bearhead.png" alt="" class="logo-img" />{{ STORE_NAME }}</a>
        <nav class="nav">
          <a class="nlink" @click="scrollTo('featured')">所有商品</a>
          <button class="cart" title="購物車" @click="cartOpen = true">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M6 8h12l-1 12H7L6 8z"/><path d="M9 8V6a3 3 0 0 1 6 0v2"/></svg>
            <span v-if="cart.length" class="badge">{{ cart.length }}</span>
          </button>
        </nav>
      </div>
    </header>

    <main id="top">
      <!-- Hero -->
      <section class="rd-wrap hero-wrap">
        <div class="hero">
          <div class="copy">
            <div class="rd-kicker">嚴選好物 · 安心購物</div>
            <h1 class="rd-serif h1">嚴選好物，<br />為生活加點質感。</h1>
            <p class="lead">我們用心挑選每一件商品，從下單到收貨都讓你安心。快速出貨，把好東西送到你手上。</p>
            <div class="cta">
              <a class="rd-btn" @click="scrollTo('featured')">立即選購
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="13 6 19 12 13 18"/></svg>
              </a>
              <a class="ulink" @click="flash('會員首購 88 折（示範門市）')">會員首購 88 折</a>
            </div>
          </div>
          <div class="himg" />
        </div>
      </section>

      <!-- Trust strip -->
      <section class="rd-wrap trust-wrap">
        <div class="trust">
          <div class="t">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M1 3h15v13H1z"/><path d="M16 8h4l3 3v5h-7z"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/></svg>
            <div><div class="tt">滿 $1,000 免運</div><div class="ts">全台宅配 / 超商</div></div>
          </div>
          <div class="t">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18"/><path d="M8 14h4"/></svg>
            <div><div class="tt">超商取貨付款</div><div class="ts">7-11 / 全家</div></div>
          </div>
          <div class="t">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15 14"/></svg>
            <div><div class="tt">48H 快速出貨</div><div class="ts">下單即備貨</div></div>
          </div>
          <div class="t">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/></svg>
            <div><div class="tt">電子發票</div><div class="ts">出貨自動開立</div></div>
          </div>
        </div>
      </section>

      <!-- Featured -->
      <section id="featured" class="rd-wrap feat-wrap">
        <div class="sec-head">
          <div>
            <div class="rd-kicker" style="letter-spacing:2px;margin-bottom:6px">FEATURED</div>
            <h2 class="rd-serif sec-h2">精選商品</h2>
          </div>
          <a class="ulink" @click="scrollTo('top')">回頂端</a>
        </div>

        <p v-if="loading" class="empty">載入中…</p>
        <p v-else-if="errorMsg" class="empty err">{{ errorMsg }}</p>
        <p v-else-if="!products.length" class="empty">目前沒有上架商品——去後台上架幾個吧。</p>

        <div v-else class="grid">
          <article v-for="p in products" :key="p.id" class="rd-pcard">
            <div class="media"><span class="initial rd-serif">{{ p.name.slice(0, 1) }}</span></div>
            <div class="body">
              <div class="name rd-serif">{{ p.name }}</div>
              <div class="price rd-num">{{ money(p.unit_price) }}</div>
              <button class="rd-btn-soft" @click="addToCart(p)">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M6 8h12l-1 12H7L6 8z"/><path d="M9 8V6a3 3 0 0 1 6 0v2"/></svg>
                加入購物車
              </button>
            </div>
          </article>
        </div>
      </section>

      <!-- 會員 band -->
      <section class="rd-wrap sub-wrap">
        <div class="sub">
          <div class="sub-img" />
          <div class="sub-copy">
            <div class="rd-kicker" style="color:var(--accent);margin-bottom:16px">MEMBER OFFER</div>
            <h2 class="rd-serif sub-h2">加入會員 · 首購 88 折</h2>
            <p class="sub-p">註冊會員即享首購優惠，並搶先收到新品上架與限時折扣通知。隨時可取消，購物零負擔。</p>
            <button class="sub-btn" @click="flash('加入會員（示範門市）')">加入會員</button>
          </div>
        </div>
      </section>
    </main>

    <footer class="foot">
      <div class="rd-wrap">
        <div class="foot-brand rd-serif"><img src="/bearhead.png" alt="" class="foot-logo" />{{ STORE_NAME }}</div>
        <p>嚴選每一件商品，安心購物、快速到貨。把好東西，送到你的日常。</p>
        <p class="tiny">lean-web · 示範門市（購物車為假、商品來自 lean-stack 後台）</p>
      </div>
    </footer>

    <!-- 假購物車 drawer -->
    <transition name="scrim">
      <div v-if="cartOpen" class="scrim" @click="cartOpen = false" />
    </transition>
    <transition name="drawer">
      <aside v-if="cartOpen" class="drawer">
        <div class="dr-head">
          <strong class="rd-serif">購物車</strong>
          <button class="x" @click="cartOpen = false">✕</button>
        </div>
        <div v-if="cart.length" class="dr-list">
          <div v-for="(p, i) in cart" :key="i" class="dr-item">
            <div class="dr-thumb rd-serif">{{ p.name.slice(0, 1) }}</div>
            <div class="dr-info">
              <div class="dr-name">{{ p.name }}</div>
              <div class="dr-price rd-num">{{ money(p.unit_price) }}</div>
            </div>
            <button class="dr-x" @click="removeAt(i)">移除</button>
          </div>
        </div>
        <p v-else class="dr-empty">購物車還是空的</p>
        <div class="dr-foot">
          <div class="dr-sum"><span>小計</span><span class="rd-num">{{ money(subtotal) }}</span></div>
          <button class="rd-btn dr-checkout" :disabled="!cart.length" @click="fakeCheckout">前往結帳</button>
        </div>
      </aside>
    </transition>

    <transition name="fade">
      <div v-if="toast" class="toast">{{ toast }}</div>
    </transition>
  </div>
</template>

<style scoped>
.anno { background: var(--ink900); color: #f3ece1; text-align: center; font-size: 12.5px; padding: 8px 16px; letter-spacing: 0.02em; }

.hd { position: sticky; top: 0; z-index: 20; background: #fffdfa; border-bottom: 1px solid var(--line); }
.hd-in { display: flex; align-items: center; justify-content: space-between; height: 62px; }
.logo { display: inline-flex; align-items: center; gap: 9px; font-size: 20px; font-weight: 600; letter-spacing: 0.02em; }
.logo-img { height: 26px; width: auto; }
.nav { display: flex; align-items: center; gap: 22px; }
.nlink { font: 500 14px 'Noto Sans TC'; color: var(--ink700); }
.nlink:hover { color: var(--accent); }
.cart { position: relative; border: 1px solid var(--line2); background: #fff; color: var(--ink900); width: 42px; height: 42px; border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: background 0.15s; }
.cart:hover { background: var(--cream); }
.badge { position: absolute; top: -4px; right: -4px; background: var(--accent); color: #fff; font: 700 11px 'Plus Jakarta Sans'; min-width: 18px; height: 18px; border-radius: 999px; display: flex; align-items: center; justify-content: center; padding: 0 4px; }

.hero-wrap { padding-top: 28px; }
.hero { display: grid; grid-template-columns: 1.05fr 1fr; border-radius: var(--r); overflow: hidden; border: 1px solid var(--line); min-height: 440px; }
.copy { background: var(--cream); padding: 64px 56px; display: flex; flex-direction: column; justify-content: center; }
.h1 { font-weight: 500; font-size: 50px; line-height: 1.25; color: #201810; margin: 20px 0 22px; letter-spacing: 0.5px; }
.lead { font-size: 15px; line-height: 1.85; color: var(--ink600); max-width: 380px; margin: 0 0 32px; }
.cta { display: flex; align-items: center; gap: 18px; }
.himg { background: linear-gradient(135deg, var(--soft) 0%, #ecd9c7 55%, #e0cdb6 100%); }

.trust-wrap { padding-top: 22px; }
.trust { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; padding: 22px 0; border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); }
.t { display: flex; align-items: center; gap: 12px; justify-content: center; }
.tt { font: 600 14px 'Noto Sans TC'; }
.ts { font: 400 11px 'Noto Sans TC'; color: var(--ink300); }

.feat-wrap { padding-top: 44px; padding-bottom: 16px; }
.sec-head { display: flex; align-items: flex-end; justify-content: space-between; margin-bottom: 26px; }
.sec-h2 { font: 500 28px 'Noto Serif TC'; color: var(--ink900); margin: 0; }
.grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 24px; }
.empty { color: var(--ink400); padding: 40px 0; text-align: center; }
.empty.err { color: #c0392b; }

.rd-pcard { border: 1px solid var(--line); border-radius: var(--r); overflow: hidden; background: #fff; display: flex; flex-direction: column; transition: box-shadow 0.2s, transform 0.2s; }
.rd-pcard:hover { box-shadow: 0 20px 44px -24px rgba(40, 30, 20, 0.45); transform: translateY(-3px); }
.media { aspect-ratio: 1/1; background: linear-gradient(135deg, #f3ebdd, #e7d6c0); display: flex; align-items: center; justify-content: center; }
.initial { font-size: 54px; font-weight: 600; color: #cbb48f; }
.body { padding: 15px; display: flex; flex-direction: column; gap: 9px; }
.name { font: 600 15px 'Noto Serif TC'; color: var(--ink900); line-height: 1.35; }
.price { font: 800 18px 'Plus Jakarta Sans'; color: var(--accent); }

.sub-wrap { padding-top: 36px; padding-bottom: 8px; }
.sub { display: grid; grid-template-columns: 1fr 1.1fr; border-radius: var(--r); overflow: hidden; background: var(--ink900); min-height: 280px; }
.sub-img { background: linear-gradient(135deg, #2a211a 0%, #463528 100%); }
.sub-copy { padding: 54px 56px; display: flex; flex-direction: column; justify-content: center; color: #fff; }
.sub-h2 { font: 500 32px/1.4 'Noto Serif TC'; margin: 0 0 16px; }
.sub-p { font: 400 14px/1.8 'Noto Sans TC'; color: rgba(255, 255, 255, 0.7); max-width: 380px; margin: 0 0 28px; }
.sub-btn { border: none; background: #fff; color: var(--ink900); font: 600 14px 'Noto Sans TC'; padding: 13px 28px; border-radius: 100px; cursor: pointer; width: fit-content; }

.foot { margin-top: 40px; border-top: 1px solid var(--line); padding: 40px 0 48px; text-align: center; color: var(--ink600); }
.foot-brand { display: inline-flex; align-items: center; gap: 9px; font-size: 20px; font-weight: 600; margin-bottom: 12px; }
.foot-logo { height: 24px; width: auto; }
.foot p { font-size: 14px; margin: 4px 0; }
.foot .tiny { font-size: 12px; color: var(--ink300); margin-top: 14px; }

/* 假購物車 drawer */
.scrim { position: fixed; inset: 0; background: rgba(30, 22, 14, 0.4); z-index: 40; }
.drawer { position: fixed; top: 0; right: 0; z-index: 50; width: 360px; max-width: 88vw; height: 100vh; background: #fffdfa; box-shadow: -20px 0 50px -20px rgba(40, 30, 20, 0.4); display: flex; flex-direction: column; }
.dr-head { display: flex; align-items: center; justify-content: space-between; padding: 18px 22px; border-bottom: 1px solid var(--line); }
.dr-head strong { font-size: 18px; }
.x { border: none; background: none; font-size: 16px; color: var(--ink400); cursor: pointer; }
.dr-list { flex: 1; overflow: auto; padding: 8px 14px; }
.dr-item { display: flex; align-items: center; gap: 12px; padding: 12px 8px; border-bottom: 1px solid #f1e9dc; }
.dr-thumb { width: 46px; height: 46px; border-radius: 10px; background: linear-gradient(135deg, #f3ebdd, #e7d6c0); display: flex; align-items: center; justify-content: center; font-size: 20px; color: #cbb48f; flex-shrink: 0; }
.dr-info { flex: 1; min-width: 0; }
.dr-name { font: 500 14px 'Noto Sans TC'; color: var(--ink900); }
.dr-price { font: 700 13px 'Plus Jakarta Sans'; color: var(--accent); margin-top: 2px; }
.dr-x { border: none; background: none; font-size: 12px; color: var(--ink400); cursor: pointer; }
.dr-x:hover { color: #c0392b; }
.dr-empty { flex: 1; display: flex; align-items: center; justify-content: center; color: var(--ink400); }
.dr-foot { border-top: 1px solid var(--line); padding: 18px 22px; }
.dr-sum { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 14px; font: 600 15px 'Noto Sans TC'; }
.dr-sum .rd-num { font-size: 20px; font-weight: 800; }
.dr-checkout { width: 100%; }
.dr-checkout:disabled { opacity: 0.5; cursor: not-allowed; filter: none; }

.toast { position: fixed; bottom: 28px; left: 50%; transform: translateX(-50%); z-index: 60; background: var(--ink900); color: #fff; padding: 11px 20px; border-radius: 999px; font-size: 14px; box-shadow: 0 8px 20px rgba(0, 0, 0, 0.2); }

.scrim-enter-active, .scrim-leave-active { transition: opacity 0.2s; }
.scrim-enter-from, .scrim-leave-to { opacity: 0; }
.drawer-enter-active, .drawer-leave-active { transition: transform 0.25s ease; }
.drawer-enter-from, .drawer-leave-to { transform: translateX(105%); }
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

@media (max-width: 900px) {
  .hero, .sub { grid-template-columns: 1fr; }
  .copy { padding: 40px 28px; }
  .h1 { font-size: 34px; }
  .himg { min-height: 200px; }
  .trust { grid-template-columns: 1fr 1fr; }
  .grid { grid-template-columns: 1fr 1fr; gap: 16px; }
}
</style>
