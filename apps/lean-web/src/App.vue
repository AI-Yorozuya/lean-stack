<script setup>
// 對外門市——版型抓 _project/lean-commerce 的 storefront。這版是「真的能下單」：
//   ① 商品讀 lean-stack 同一個後端 /api/v1/product（改後台→這裡跟著變）
//   ② 登入（示範登入：email 對到會員即可，不驗密碼——後端刻意還沒 auth）
//   ③ 結帳 = 真的 POST /api/v1/order → 回後台訂單列表就看得到那張「待付款」單
//   ④ 招牌 STORE_NAME 就是免費體驗 F1「換招牌」要改的字
import { ref, computed, onMounted } from 'vue'

const STORE_NAME = '選物小舖' // ← 換招牌改這裡

const products = ref([])
const loading = ref(true)
const errorMsg = ref('')

const cart = ref([]) // 購物車：放商品物件
const cartOpen = ref(false)
const toast = ref('')
let toastTimer = null

// 登入（示範）：me = 目前登入的會員；存 localStorage，重整仍在。
const me = ref(JSON.parse(localStorage.getItem('lw_me') || 'null'))
const loginOpen = ref(false)
const loginEmail = ref('hero@ai-yorozuya.com') // 預填測試客，一鍵登入
const loginPw = ref('12345678')                // 示範密碼，也先幫她填好
const DEMO_PW = '12345678'                      // 前端示範用（真 auth 是後端待做的接縫）
const loginErr = ref('')
const placing = ref(false)

const money = (n) => 'NT$ ' + Number(n).toLocaleString()
const subtotal = computed(() => cart.value.reduce((s, p) => s + Number(p.unit_price), 0))

function flash(msg, ms = 1800) {
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
function scrollTo(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })
}

// ── 登入 / 登出（示範：email 對到會員 + 前端示範密碼；真驗密碼是後端待做的接縫）──
async function doLogin() {
  loginErr.value = ''
  const email = loginEmail.value.trim().toLowerCase()
  if (loginPw.value !== DEMO_PW) { loginErr.value = '密碼錯誤（示範密碼：12345678）'; return }
  try {
    const members = (await (await fetch('/api/v1/member?page_size=100')).json()).items
    const found = members.find((m) => m.email.toLowerCase() === email)
    if (!found) { loginErr.value = '查無此帳號（試 hero@ai-yorozuya.com）'; return }
    me.value = { id: found.id, name: found.name, email: found.email }
    localStorage.setItem('lw_me', JSON.stringify(me.value))
    loginOpen.value = false
    flash(`歡迎，${found.name}`)
  } catch (e) {
    loginErr.value = '登入失敗，請確認後端有起來。'
    console.error(e)
  }
}
function logout() {
  me.value = null
  localStorage.removeItem('lw_me')
}

// ── 結帳 = 真的建一張訂單（沒登入先叫登入；沒金流，訂單落在「待付款」）──
async function checkout() {
  if (!me.value) { loginOpen.value = true; return }
  if (!cart.value.length || placing.value) return
  const grouped = {} // 同商品合併成 quantity
  for (const p of cart.value) grouped[p.id] = (grouped[p.id] || 0) + 1
  const items = Object.entries(grouped).map(([product_id, quantity]) => ({ product_id: Number(product_id), quantity }))
  placing.value = true
  try {
    const res = await fetch('/api/v1/order', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ member_id: me.value.id, items }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || '下單失敗')
    }
    const order = await res.json()
    cart.value = []
    cartOpen.value = false
    flash(`訂單成立 ${order.order_no}　（回後台看得到這張「待付款」單）`, 3200)
  } catch (e) {
    flash('下單失敗：' + e.message, 2600)
    console.error(e)
  } finally {
    placing.value = false
  }
}

// Hero 輪播：挑幾件顏色鮮明的商品跑馬燈（換掉原本的熊）。
const heroSkus = ['SWEAT-WINE', 'SWEAT-FOREST', 'SHORTS-NAVY', 'SWEAT-MUSTARD', 'SHORTS-BRICK']
const heroSlides = computed(() => heroSkus.map((s) => products.value.find((p) => p.sku === s)).filter(Boolean))
const slideIdx = ref(0)

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
  // 每 3.2 秒換一張
  setInterval(() => {
    if (heroSlides.value.length) slideIdx.value = (slideIdx.value + 1) % heroSlides.value.length
  }, 3200)
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
          <template v-if="me">
            <span class="hi">你好，{{ me.name }}</span>
            <a class="nlink" @click="logout">登出</a>
          </template>
          <a v-else class="nlink" @click="loginOpen = true">登入</a>
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
          <div class="himg">
            <img v-for="(p, i) in heroSlides" :key="p.id" :src="p.image_url" :alt="p.name" class="cslide" :class="{ on: i === slideIdx }" />
            <div v-if="heroSlides.length > 1" class="dots">
              <button v-for="(p, i) in heroSlides" :key="i" type="button" :class="{ on: i === slideIdx }" :aria-label="`第 ${i + 1} 張`" @click="slideIdx = i" />
            </div>
          </div>
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
            <div class="media">
              <img v-if="p.image_url" :src="p.image_url" :alt="p.name" loading="lazy" />
              <span v-else class="initial rd-serif">{{ p.name.slice(0, 1) }}</span>
            </div>
            <div class="body">
              <div class="name rd-serif">{{ p.name }}</div>
              <div class="price rd-num">{{ money(p.unit_price) }}</div>
              <button class="add-btn" @click="addToCart(p)">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M6 8h12l-1 12H7L6 8z"/><path d="M9 8V6a3 3 0 0 1 6 0v2"/></svg>
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
        <p class="tiny">lean-web · 示範門市（登入下真單、無金流；商品／訂單走 lean-stack 後端）</p>
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
            <div class="dr-thumb">
              <img v-if="p.image_url" :src="p.image_url" :alt="p.name" />
              <span v-else class="rd-serif">{{ p.name.slice(0, 1) }}</span>
            </div>
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
          <p class="dr-who">{{ me ? `以「${me.name}」的身分結帳（無金流，訂單落待付款）` : '結帳需要先登入' }}</p>
          <button class="rd-btn dr-checkout" :disabled="!cart.length || placing" @click="checkout">
            {{ placing ? '下單中…' : me ? '前往結帳' : '登入並結帳' }}
          </button>
        </div>
      </aside>
    </transition>

    <!-- 登入對話框（示範登入：email 對到會員即可，不驗密碼）-->
    <transition name="scrim">
      <div v-if="loginOpen" class="scrim" @click="loginOpen = false" />
    </transition>
    <transition name="pop">
      <div v-if="loginOpen" class="modal">
        <div class="m-head"><strong class="rd-serif">會員登入</strong><button class="x" @click="loginOpen = false">✕</button></div>
        <p class="m-hint">示範門市：帳號密碼都幫你帶好了，直接按登入。（真的驗密碼是後端待做的接縫，這裡先做前端示範。）</p>
        <label class="m-label">Email</label>
        <input v-model="loginEmail" class="m-input" placeholder="hero@ai-yorozuya.com" @keyup.enter="doLogin" />
        <label class="m-label">密碼</label>
        <input v-model="loginPw" type="password" class="m-input" placeholder="12345678" @keyup.enter="doLogin" />
        <p v-if="loginErr" class="m-err">{{ loginErr }}</p>
        <button class="rd-btn m-btn" @click="doLogin">登入</button>
      </div>
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
.nav { display: flex; align-items: center; gap: 18px; }
.nlink { font: 500 14px 'Noto Sans TC'; color: var(--ink700); }
.nlink:hover { color: var(--accent); }
.hi { font: 500 14px 'Noto Sans TC'; color: var(--ink900); }
.cart { position: relative; border: 1px solid var(--line2); background: #fff; color: var(--ink900); width: 42px; height: 42px; border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: background 0.15s; }
.cart:hover { background: var(--cream); }
.badge { position: absolute; top: -4px; right: -4px; background: var(--accent); color: #fff; font: 700 11px 'Plus Jakarta Sans'; min-width: 18px; height: 18px; border-radius: 999px; display: flex; align-items: center; justify-content: center; padding: 0 4px; }

.hero-wrap { padding-top: 28px; }
.hero { display: grid; grid-template-columns: 1.05fr 1fr; border-radius: var(--r); overflow: hidden; border: 1px solid var(--line); min-height: 440px; }
.copy { background: var(--cream); padding: 64px 56px; display: flex; flex-direction: column; justify-content: center; }
.h1 { font-weight: 500; font-size: 50px; line-height: 1.25; color: #201810; margin: 20px 0 22px; letter-spacing: 0.5px; }
.lead { font-size: 15px; line-height: 1.85; color: var(--ink600); max-width: 380px; margin: 0 0 32px; }
.cta { display: flex; align-items: center; gap: 18px; }
.himg { position: relative; background: #f0efeb; overflow: hidden; }
.cslide { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; object-position: center 42%; opacity: 0; transition: opacity 0.7s ease; }
.cslide.on { opacity: 1; }
.dots { position: absolute; bottom: 14px; left: 0; right: 0; display: flex; justify-content: center; gap: 7px; z-index: 2; }
.dots button { width: 8px; height: 8px; border-radius: 999px; border: none; background: rgba(40, 30, 20, 0.28); cursor: pointer; padding: 0; transition: background 0.2s, width 0.2s; }
.dots button.on { background: var(--accent); width: 20px; }

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
.media { aspect-ratio: 1/1; background: linear-gradient(135deg, #f3ebdd, #e7d6c0); display: flex; align-items: center; justify-content: center; overflow: hidden; }
.media img { width: 100%; height: 100%; object-fit: cover; }
.initial { font-size: 54px; font-weight: 600; color: #cbb48f; }
.body { padding: 15px; display: flex; flex-direction: column; gap: 9px; }
.name { font: 600 15px 'Noto Serif TC'; color: var(--ink900); line-height: 1.35; }
.price { font: 800 18px 'Plus Jakarta Sans'; color: var(--accent); }
.add-btn { margin-top: 2px; border: none; background: var(--accent); color: #fff; font: 600 13.5px 'Noto Sans TC'; padding: 11px; border-radius: 10px; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px; transition: filter 0.15s; }
.add-btn:hover { filter: brightness(0.94); }

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
.dr-thumb { width: 46px; height: 46px; border-radius: 10px; overflow: hidden; background: linear-gradient(135deg, #f3ebdd, #e7d6c0); display: flex; align-items: center; justify-content: center; font-size: 20px; color: #cbb48f; flex-shrink: 0; }
.dr-thumb img { width: 100%; height: 100%; object-fit: cover; }
.dr-info { flex: 1; min-width: 0; }
.dr-name { font: 500 14px 'Noto Sans TC'; color: var(--ink900); }
.dr-price { font: 700 13px 'Plus Jakarta Sans'; color: var(--accent); margin-top: 2px; }
.dr-x { border: none; background: none; font-size: 12px; color: var(--ink400); cursor: pointer; }
.dr-x:hover { color: #c0392b; }
.dr-empty { flex: 1; display: flex; align-items: center; justify-content: center; color: var(--ink400); }
.dr-foot { border-top: 1px solid var(--line); padding: 18px 22px; }
.dr-sum { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px; font: 600 15px 'Noto Sans TC'; }
.dr-sum .rd-num { font-size: 20px; font-weight: 800; }
.dr-who { font-size: 12px; color: var(--ink400); margin-bottom: 12px; }
.dr-checkout { width: 100%; }
.dr-checkout:disabled { opacity: 0.5; cursor: not-allowed; filter: none; }

/* 登入對話框 */
.modal { position: fixed; z-index: 55; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 360px; max-width: 90vw; background: #fffdfa; border-radius: 16px; padding: 22px 24px; box-shadow: 0 30px 60px -20px rgba(40, 30, 20, 0.5); }
.m-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
.m-head strong { font-size: 19px; }
.m-hint { font-size: 12.5px; color: var(--ink400); line-height: 1.6; margin-bottom: 16px; }
.m-label { font-size: 12px; color: var(--ink3, var(--ink400)); display: block; margin-bottom: 6px; }
.m-input { width: 100%; padding: 12px 14px; border: 1.5px solid var(--line2); border-radius: 10px; font-size: 14px; color: var(--ink900); background: #fff; outline: none; transition: border-color 0.15s; }
.m-input:focus { border-color: var(--accent); }
.m-err { color: #c0392b; font-size: 13px; margin-top: 8px; }
.m-btn { width: 100%; margin-top: 16px; }
.pop-enter-active, .pop-leave-active { transition: opacity 0.18s, transform 0.18s; }
.pop-enter-from, .pop-leave-to { opacity: 0; transform: translate(-50%, -46%); }

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
