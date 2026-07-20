<script setup>
// 一頁式品牌官網——純前端起手種子（scenario/landing）。
// 教練照玩家的五個答案，只改下面這個 site 設定物件 + style.css 的主題 token。
// 純展示、不打後端 → npm run dev 就跑、npm run build 出靜態檔、免 Docker/DB。
// 玩家若選「要收名單」的全端版，教練才另接 /api/v1/web/inquiry（見 scenarios/landing.md）。
import { ref } from 'vue'

// ── 教練改這裡（來自對話 Q1/Q2/Q3/Q4）───────────────────────────
const site = {
  brand: '你的招牌',                          // 取名（序章）
  tagline: '一句話說清楚，你替誰解決什麼。',    // Q2 標語（教練代擬）
  intro: '把你最想讓人知道的一段話放這裡——你是誰、為什麼值得信任。',
  // Q4「客人怎麼找你」決定這顆按鈕（純前端＝連結）：
  cta: { label: '聯絡我', href: 'mailto:hello@example.com' },
  // Q1 決定這三張亮點卡的內容：
  features: [
    { title: '亮點一', desc: '你最強的一件事，用客人聽得懂的話講。' },
    { title: '亮點二', desc: '第二個讓人選你的理由。' },
    { title: '亮點三', desc: '第三個。三張剛好，別貪多。' },
  ],
}
// ───────────────────────────────────────────────────────────────

const navOpen = ref(false)
const scrollTo = (id) => {
  navOpen.value = false
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })
}
</script>

<template>
  <header class="nav">
    <a class="brand" href="#top" @click.prevent="scrollTo('top')">{{ site.brand }}</a>
    <nav :class="['links', { open: navOpen }]">
      <a href="#features" @click.prevent="scrollTo('features')">亮點</a>
      <a href="#about" @click.prevent="scrollTo('about')">關於</a>
      <a class="cta-sm" :href="site.cta.href">{{ site.cta.label }}</a>
    </nav>
    <button class="burger" aria-label="選單" @click="navOpen = !navOpen">≡</button>
  </header>

  <main id="top">
    <section class="hero">
      <h1>{{ site.tagline }}</h1>
      <p class="lede">{{ site.intro }}</p>
      <a class="cta" :href="site.cta.href">{{ site.cta.label }}</a>
    </section>

    <section id="features" class="features">
      <article v-for="(f, i) in site.features" :key="i" class="card">
        <span class="num">{{ String(i + 1).padStart(2, '0') }}</span>
        <h3>{{ f.title }}</h3>
        <p>{{ f.desc }}</p>
      </article>
    </section>

    <section id="about" class="about">
      <h2>關於 {{ site.brand }}</h2>
      <p>{{ site.intro }}</p>
      <a class="cta ghost" :href="site.cta.href">{{ site.cta.label }}</a>
    </section>
  </main>

  <footer class="foot">
    <span>© {{ site.brand }}</span>
    <span class="made">用 lean-stack 做的一頁式 🐻</span>
  </footer>
</template>
