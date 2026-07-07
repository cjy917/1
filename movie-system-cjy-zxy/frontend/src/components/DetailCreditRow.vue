<!--
  【详情页 D1】演职员/类型等可点击行
  用法：01-DetailHeroSection 传入 label、names、to(name) 生成 router-link
-->
<script setup>
defineProps({
  label: { type: String, required: true },           // 如「导演」「主演」
  names: { type: Array, default: () => [] },        // 姓名列表
  to: { type: Function, required: true },            // name => RouteLocation（跳转 PersonView 等）
})
</script>

<template>
  <p v-if="names.length" class="detail-hero__credit-row">
    <span class="detail-hero__label">{{ label }}：</span>
    <span class="detail-hero__credit-list">
      <template v-for="(name, index) in names" :key="`${label}-${name}-${index}`">
        <router-link class="detail-hero__credit-link" :to="to(name)">{{ name }}</router-link>
        <span v-if="index < names.length - 1" class="detail-hero__credit-sep">|</span>
      </template>
    </span>
  </p>
</template>
