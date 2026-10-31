<script setup>
import { useRoute } from 'vue-router'

const route = useRoute()
</script>

<template>
  <div class="soon">
    <p class="soon__badge">批次 {{ route.meta.batch ?? '—' }}</p>
    <h1 class="soon__title">{{ route.meta.title }}</h1>
    <p class="soon__desc">
      该页面排在第 {{ route.meta.batch ?? '?' }} 批次，当前批次（2：单人双模式闭环）不交付。
      先建占位是为了不让底部 Tab 与扫码入口点到死链。
    </p>
  </div>
</template>

<style scoped>
.soon {
  margin-top: 22vh;
  border-radius: 1.5rem;
  padding: 26px 22px;
  text-align: center;
  background: var(--color-surface);
  box-shadow: 0 8px 30px rgb(var(--rgb-black) / 0.04);
}

.soon__badge {
  display: inline-block;
  margin: 0 0 10px;
  border-radius: 999px;
  padding: 3px 10px;
  font-size: 10.5px;
  letter-spacing: 0.06em;
  color: var(--color-white);
  background: var(--color-ink);
}

.soon__title {
  margin: 0 0 8px;
  font-size: 20px;
  font-weight: 720;
}

.soon__desc {
  margin: 0;
  font-size: 12px;
  line-height: 1.65;
  color: var(--color-text-soft);
}
</style>
