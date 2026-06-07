<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: {
    type: String,
    default: '',
  },
  items: {
    type: Array,
    default: () => [],
  },
  labelKey: {
    type: String,
    default: 'label',
  },
  valueKey: {
    type: String,
    default: 'value',
  },
  color: {
    type: String,
    default: '#2d73da',
  },
})

const maxValue = computed(() => {
  const values = props.items.map((item) => Number(item[props.valueKey] || 0))
  return Math.max(...values, 0)
})

function widthPercent(value) {
  const number = Number(value || 0)
  if (maxValue.value <= 0) return 0
  return Math.max(5, Math.round((number / maxValue.value) * 100))
}
</script>

<template>
  <div class="viz-card">
    <h4 class="viz-title">{{ title }}</h4>
    <div v-if="!items.length" class="viz-empty">暂无统计数据</div>
    <div v-else class="viz-list">
      <div v-for="(item, idx) in items" :key="idx" class="viz-row">
        <div class="viz-label">{{ item[labelKey] }}</div>
        <div class="viz-bar-wrap">
          <div class="viz-bar" :style="{ width: `${widthPercent(item[valueKey])}%`, background: color }"></div>
        </div>
        <div class="viz-value">{{ item[valueKey] }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.viz-card {
  border: 1px solid rgba(90, 128, 201, 0.16);
  border-radius: 12px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.75);
}

.viz-title {
  margin: 0 0 10px;
  font-size: 14px;
  font-weight: 700;
  color: var(--text-main);
}

.viz-empty {
  color: var(--text-sub);
  font-size: 13px;
}

.viz-list {
  display: grid;
  gap: 8px;
}

.viz-row {
  display: grid;
  grid-template-columns: 72px 1fr 72px;
  align-items: center;
  gap: 10px;
}

.viz-label,
.viz-value {
  font-size: 12px;
  color: var(--text-sub);
}

.viz-bar-wrap {
  height: 10px;
  border-radius: 999px;
  background: #ebf1fb;
  overflow: hidden;
}

.viz-bar {
  height: 100%;
  border-radius: 999px;
}
</style>
