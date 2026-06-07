<script setup>
import AppErrorBoundary from './components/AppErrorBoundary.vue'
</script>

<template>
  <AppErrorBoundary>
    <RouterView />
  </AppErrorBoundary>
</template>
