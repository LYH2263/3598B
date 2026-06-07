<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: { type: String, default: '' },
  items: { type: Array, default: () => [] },
  labelKey: { type: String, default: 'period' },
  valueKey: { type: String, default: 'count' },
  color: { type: String, default: '#8b5cf6' },
  height: { type: Number, default: 220 },
  formatValue: { type: Function, default: (v) => v },
})

const width = 600
const padding = { top: 24, right: 24, bottom: 40, left: 56 }
const innerW = computed(() => width - padding.left - padding.right)
const innerH = computed(() => props.height - padding.top - padding.bottom)

const maxVal = computed(() => {
  const vals = props.items.map((it) => Number(it[props.valueKey] || 0))
  const m = Math.max(...vals, 0)
  return m === 0 ? 1 : m * 1.15
})

function xPos(i) {
  if (props.items.length <= 1) return padding.left + innerW.value / 2
  return padding.left + (i / (props.items.length - 1)) * innerW.value
}
function yPos(v) {
  return padding.top + innerH.value - (Number(v || 0) / maxVal.value) * innerH.value
}

const areaPath = computed(() => {
  if (!props.items.length) return ''
  const top = props.items.map((it, i) => `${i === 0 ? 'M' : 'L'} ${xPos(i)} ${yPos(it[props.valueKey])}`).join(' ')
  const last = props.items.length - 1
  return `${top} L ${xPos(last)} ${padding.top + innerH.value} L ${xPos(0)} ${padding.top + innerH.value} Z`
})

const linePath = computed(() => {
  return props.items.map((it, i) => `${i === 0 ? 'M' : 'L'} ${xPos(i)} ${yPos(it[props.valueKey])}`).join(' ')
})

const yTicks = computed(() => {
  const ticks = 4
  return Array.from({ length: ticks + 1 }, (_, i) => {
    const val = (maxVal.value / ticks) * i
    return { val, y: yPos(val) }
  })
})
</script>

<template>
  <div class="viz-card">
    <h4 class="viz-title">{{ title }}</h4>
    <div v-if="!items.length" class="viz-empty">暂无统计数据</div>
    <div v-else>
      <svg :viewBox="`0 0 ${width} ${height}`" class="chart-svg">
        <defs>
          <linearGradient :id="'grad-' + color.replace('#', '')" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" :stop-color="color" stop-opacity="0.38" />
            <stop offset="100%" :stop-color="color" stop-opacity="0.04" />
          </linearGradient>
        </defs>
        <g v-for="t in yTicks" :key="`yt-${t.val}`">
          <line :x1="padding.left" :x2="width - padding.right" :y1="t.y" :y2="t.y" stroke="#eef2f8" stroke-width="1" />
          <text :x="padding.left - 8" :y="t.y + 4" text-anchor="end" font-size="11" fill="#8a96ae">
            {{ formatValue(t.val) }}
          </text>
        </g>
        <path :d="areaPath" :fill="`url(#grad-${color.replace('#', '')})`" />
        <path :d="linePath" fill="none" :stroke="color" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round" />
        <circle
          v-for="(item, i) in items"
          :key="i"
          :cx="xPos(i)"
          :cy="yPos(item[valueKey])"
          r="3.5"
          :fill="color"
        />
        <text
          v-for="(item, i) in items"
          :key="`xl-${i}`"
          :x="xPos(i)"
          :y="height - padding.bottom + 18"
          text-anchor="middle"
          font-size="11"
          fill="#8a96ae"
        >
          {{ item[labelKey] }}
        </text>
      </svg>
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
.chart-svg {
  width: 100%;
  height: auto;
  display: block;
}
</style>
