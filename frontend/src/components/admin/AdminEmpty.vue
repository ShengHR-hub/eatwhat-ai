<script setup>
defineProps({
  title: { type: String, default: '暂无数据' },
  reason: { type: String, default: '当前筛选没有可展示的记录' },
})
</script>

<template>
  <div class="admin-empty" role="status">
    <span class="admin-empty__icon" aria-hidden="true">∅</span>
    <strong>{{ title }}</strong>
    <p>{{ reason }}</p>
  </div>
</template>
