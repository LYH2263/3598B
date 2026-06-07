<script setup>
defineProps({
  title: {
    type: String,
    required: true,
  },
  subtitle: {
    type: String,
    required: true,
  },
})
</script>

<template>
  <main class="page-shell animated-in">
    <section class="auth-wrap">
      <article class="panel-info">
        <h1>学生水电充值管理系统</h1>
        <p>
          覆盖学生与管理员双角色，支持注册登录、充值消费、账单追溯与余额管理，
          通过统一 API 与 OpenGauss 数据层实现稳定、可扩展的缴费流程。
        </p>
        <el-divider border-style="dashed" />
        <p>系统特点：中文界面、流程清晰、状态可视、移动端适配。</p>
      </article>
      <article class="panel-form">
        <h2 class="panel-title">{{ title }}</h2>
        <p class="panel-subtitle">{{ subtitle }}</p>
        <slot />
      </article>
    </section>
  </main>
</template>
