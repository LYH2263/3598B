<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: { type: String, default: '' },
  items: { type: Array, default: () => [] },
  labelKey: { type: String, default: 'period' },
  valueKeys: { type: Array, default: () => ['amount'] },
  valueLabels: { type: Array, default: () => ['金额'] },
  colors: { type: Array, default: () => ['#2d73da', '#2b9f6c', '#f59e0b', '#ef4444'] },
  height: { type: Number, default: 220 },
  formatValue: { type: Function, default: (v) => v },
})

const width = 600
const padding = { top: 24, right: 24, bottom: 40, left: 56 }
const innerW = computed(() => width - padding.left - padding.right)
const innerH = computed(() => props.height - padding.top - padding.bottom)

const allValues = computed(() => {
  const vals = []
  props.items.forEach((item) => {
    props.valueKeys.forEach((key) => {
      const v = Number(item[key] || 0)
      if (!Number.isNaN(v)) vals.push(v)
    })
  })
  return vals
})

const maxVal = computed(() => {
  const m = Math.max(...allValues.value, 0)
  return m === 0 ? 1 : m * 1.15
})

function xPos(i) {
  if (props.items.length <= 1) return padding.left + innerW.value / 2
  return padding.left + (i / (props.items.length - 1)) * innerW.value
}

function yPos(v) {
  return padding.top + innerH.value - (Number(v || 0) / maxVal.value) * innerH.value
}

const pathFor = (key) => {
  return props.items
    .map((item, i) => `${i === 0 ? 'M' : 'L'} ${xPos(i)} ${yPos(item[key])}`)
    .join(' ')
}

const yTicks = computed(() => {
  const ticks = 4
  return Array.from({ length: ticks + 1 }, (_, i) => {
    const val = (maxVal.value / ticks) * i
    return { val, y: yPos(val) }
  })
})

function xLabelRotation() {
  return props.items.length > 10 ? -30 : 0
}
</script>

<template>
  <div class="viz-card">
    <h4 class="viz-title">{{ title }}</h4>
    <div v-if="!items.length" class="viz-empty">暂无统计数据</div>
    <div v-else class="line-chart-wrap">
      <svg :viewBox="`0 0 ${width} ${height}`" class="chart-svg">
        <g v-for="t in yTicks" :key="`yt-${t.val}`">
          <line :x1="padding.left" :x2="width - padding.right" :y1="t.y" :y2="t.y" stroke="#eef2f8" stroke-width="1" />
          <text :x="padding.left - 8" :y="t.y + 4" text-anchor="end" font-size="11" fill="#8a96ae">
            {{ formatValue(t.val) }}
          </text>
        </g>
        <template v-for="(key, idx) in valueKeys" :key="key">
          <path :d="pathFor(key)" fill="none" :stroke="colors[idx % colors.length]" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round" />
          <circle
            v-for="(item, i) in items"
            :key="`dot-${key}-${i}`"
            :cx="xPos(i)"
            :cy="yPos(item[key])"
            r="3.5"
            :fill="colors[idx % colors.length]"
          />
        </template>
        <g>
          <text
            v-for="(item, i) in items"
            :key="`xl-${i}`"
            :x="xPos(i)"
            :y="height - padding.bottom + 18"
            text-anchor="middle"
            font-size="11"
            fill="#8a96ae"
            :transform="`rotate(${xLabelRotation()}, ${xPos(i)}, ${height - padding.bottom + 18})`"
          >
            {{ item[labelKey] }}
          </text>
        </g>
      </svg>
      <div class="legend">
        <span v-for="(label, idx) in valueLabels" :key="label" class="legend-item">
          <span class="legend-dot" :style="{ background: colors[idx % colors.length] }" />
          {{ label }}
        </span>
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
.line-chart-wrap {
  position: relative;
}
.chart-svg {
  width: 100%;
  height: auto;
  display: block;
}
.legend {
  display: flex;
  gap: 14px;
  justify-content: center;
  margin-top: 8px;
  flex-wrap: wrap;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-sub);
}
.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}
</style>
