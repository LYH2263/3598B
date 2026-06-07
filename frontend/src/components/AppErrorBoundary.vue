<script setup>
import { onErrorCaptured } from 'vue'
import { ElNotification } from 'element-plus'

onErrorCaptured(() => {
  ElNotification({
    title: '页面异常',
    message: '页面出现异常，请稍后重试。',
    type: 'error',
  })
  return false
})
</script>

<template>
  <slot />
</template>
