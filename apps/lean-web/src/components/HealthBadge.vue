<script setup>
// 可重用的小元件：顯示後端連線狀態。
// 教學重點：用 defineProps 接收外部傳進來的資料；元件只管「怎麼顯示」。
defineProps({
  status: {
    type: String,
    default: 'checking', // checking | ok | error
  },
})
</script>

<template>
  <p v-if="status === 'checking'">檢查後端連線中…</p>
  <p v-else-if="status === 'ok'" style="color: green;">後端連線正常 ✓</p>
  <p v-else style="color: crimson;">後端連線失敗 ✗（請確認後端是否已啟動）</p>
</template>
