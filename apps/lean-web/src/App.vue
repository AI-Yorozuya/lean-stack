<script setup>
// 對外門市的極簡櫥窗。重點：
//   1) 商品讀 lean-stack「同一個後端」（/api/v1/product?active_only=true）——
//      所以在後台上/下架、改名、改價，這裡重新整理就跟著變。這就是「全端」最直觀的魔法。
//   2) 購物車是「假的」：只把商品加進一個清單、加數字、跳提示，不真的結帳（示範用）。
//   3) 招牌 STORE_NAME 就是免費體驗 F1「換招牌」要改的字（自己改，或叫 AI 改）。
import { ref, onMounted } from 'vue'

const STORE_NAME = '選物小舖' // ← 換招牌改這裡

const products = ref([])
const loading = ref(true)
const errorMsg = ref('')

const cart = ref([]) // 假購物車：放商品名（示範用）
const cartOpen = ref(false)
const toast = ref('')
let toastTimer = null

const money = (n) => 'NT$ ' + Number(n).toLocaleString()

function flash(msg, ms = 1600) {
  toast.value = msg
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => (toast.value = ''), ms)
}

function addToCart(p) {
  cart.value.push(p.name)
  flash(`已加入購物車：${p.name}`)
}

function fakeCheckout() {
  cartOpen.value = false
  flash('這是示範門市，先不結帳 😄', 2000)
}

onMounted(async () => {
  try {
    // 只拿上架商品——後台下架的，門市就看不到。
    const res = await fetch('/api/v1/product?page_size=100&active_only=true')
    const data = await res.json()
    products.value = data.items
  } catch (e) {
    errorMsg.value = '商品載入失敗，請確認後端有起來。'
    console.error(e)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="shop">
    <header class="topbar">
      <div class="brand">🐻 {{ STORE_NAME }}</div>
      <button class="cart-btn" @click="cartOpen = !cartOpen">
        🛒 購物車<span v-if="cart.length" class="badge">{{ cart.length }}</span>
      </button>
    </header>

    <section class="hero">
      <h1>{{ STORE_NAME }}</h1>
      <p>嚴選好物 · 今天也要好好過生活</p>
    </section>

    <main class="wrap">
      <p v-if="loading" class="hint">載入中…</p>
      <p v-else-if="errorMsg" class="hint err">{{ errorMsg }}</p>
      <p v-else-if="!products.length" class="hint">目前沒有上架商品——去後台上架幾個吧。</p>

      <div v-else class="grid">
        <article v-for="p in products" :key="p.id" class="card">
          <div class="thumb">{{ p.name.slice(0, 1) }}</div>
          <div class="info">
            <h3>{{ p.name }}</h3>
            <p class="price">{{ money(p.unit_price) }}</p>
          </div>
          <button class="add" @click="addToCart(p)">加入購物車</button>
        </article>
      </div>
    </main>

    <!-- 假購物車浮層 -->
    <div v-if="cartOpen" class="cart-panel">
      <div class="cart-head"><strong>購物車</strong><button class="x" @click="cartOpen = false">✕</button></div>
      <ul v-if="cart.length">
        <li v-for="(name, i) in cart" :key="i">{{ name }}</li>
      </ul>
      <p v-else class="hint sm">還是空的</p>
      <button class="checkout" :disabled="!cart.length" @click="fakeCheckout">前往結帳</button>
    </div>

    <transition name="fade">
      <div v-if="toast" class="toast">{{ toast }}</div>
    </transition>

    <footer class="foot">lean-web · 示範門市（購物車為假、商品來自 lean-stack 後台）</footer>
  </div>
</template>

<style scoped>
.shop { min-height: 100vh; display: flex; flex-direction: column; }

.topbar {
  position: sticky; top: 0; z-index: 10;
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 24px; background: #fffdfa; border-bottom: 1px solid #ece3d6;
}
.brand { font-size: 18px; font-weight: 700; letter-spacing: 0.02em; }
.cart-btn {
  position: relative; border: 1px solid #e0d5c4; background: #fff; color: #2b2620;
  padding: 8px 14px; border-radius: 999px; font-size: 14px; cursor: pointer; transition: background 0.15s;
}
.cart-btn:hover { background: #f7f0e6; }
.badge {
  margin-left: 6px; background: #c0392b; color: #fff; font-size: 12px;
  padding: 1px 7px; border-radius: 999px;
}

.hero { text-align: center; padding: 56px 24px 40px; }
.hero h1 { font-size: 34px; letter-spacing: 0.04em; }
.hero p { margin-top: 10px; color: #8a7d6b; }

.wrap { flex: 1; width: 100%; max-width: 1040px; margin: 0 auto; padding: 8px 24px 56px; }
.grid {
  display: grid; gap: 18px;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
}
.card {
  background: #fffdfa; border: 1px solid #ece3d6; border-radius: 14px; overflow: hidden;
  display: flex; flex-direction: column; transition: transform 0.15s, box-shadow 0.15s;
}
.card:hover { transform: translateY(-3px); box-shadow: 0 8px 22px rgba(120, 90, 50, 0.1); }
.thumb {
  height: 140px; display: flex; align-items: center; justify-content: center;
  font-size: 44px; font-weight: 700; color: #cbb48f; background: #f3ebdd;
}
.info { padding: 14px 16px 6px; flex: 1; }
.info h3 { font-size: 15px; font-weight: 600; }
.price { margin-top: 6px; color: #b5651d; font-weight: 700; }
.add {
  margin: 8px 12px 12px; padding: 10px; border: none; border-radius: 10px;
  background: #2b2620; color: #fff; font-size: 14px; cursor: pointer; transition: background 0.15s;
}
.add:hover { background: #46403a; }

.hint { text-align: center; color: #8a7d6b; padding: 40px 0; }
.hint.sm { padding: 16px 0; }
.hint.err { color: #c0392b; }

.cart-panel {
  position: fixed; top: 64px; right: 24px; z-index: 20; width: 260px;
  background: #fff; border: 1px solid #ece3d6; border-radius: 14px; padding: 14px;
  box-shadow: 0 12px 30px rgba(120, 90, 50, 0.18);
}
.cart-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.x { border: none; background: none; cursor: pointer; font-size: 15px; color: #8a7d6b; }
.cart-panel ul { list-style: none; max-height: 200px; overflow: auto; }
.cart-panel li { padding: 6px 0; border-bottom: 1px solid #f1e9dc; font-size: 14px; }
.checkout {
  margin-top: 12px; width: 100%; padding: 10px; border: none; border-radius: 10px;
  background: #c0392b; color: #fff; font-size: 14px; cursor: pointer;
}
.checkout:disabled { background: #d9c9c6; cursor: not-allowed; }

.toast {
  position: fixed; bottom: 28px; left: 50%; transform: translateX(-50%); z-index: 30;
  background: #2b2620; color: #fff; padding: 11px 20px; border-radius: 999px; font-size: 14px;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.2);
}
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.foot { text-align: center; padding: 24px; color: #b3a894; font-size: 13px; }
</style>
