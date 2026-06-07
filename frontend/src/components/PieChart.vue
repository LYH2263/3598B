<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: { type: String, default: '' },
  items: { type: Array, default: () => [] },
  labelKey: { type: String, default: 'label' },
  valueKey: { type: String, default: 'value' },
  colors: { type: Array, default: () => ['#2d73da', '#2b9f6c', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'] },
  size: { type: Number, default: 180 },
  donut: { type: Boolean, default: false },
  formatValue: { type: Function, default: (v) => v },
})

const total = computed(() => props.items.reduce((s, it) => s + Number(it[props.valueKey] || 0), 0))

const cx = props.size / 2
const cy = props.size / 2
const r = props.size / 2 - 10
const rInner = props.donut ? r * 0.55 : 0

const slices = computed(() => {
  let startAngle = -Math.PI / 2
  return props.items.map((item, idx) => {
    const value = Number(item[props.valueKey] || 0)
    const portion = total.value > 0 ? value / total.value : 0
    const angle = portion * Math.PI * 2
    const endAngle = startAngle + angle
    const color = props.colors[idx % props.colors.length]

    const x1 = cx + r * Math.cos(startAngle)
    const y1 = cy + r * Math.sin(startAngle)
    const x2 = cx + r * Math.cos(endAngle)
    const y2 = cy + r * Math.sin(endAngle)

    let outerPath = ''
    if (portion >= 1) {
      outerPath = `M ${cx - r} ${cy} A ${r} ${r} 0 1 1 ${cx + r} ${cy} A ${r} ${r} 0 1 1 ${cx - r} ${cy} Z`
    } else if (portion > 0) {
      const largeArc = angle > Math.PI ? 1 : 0
      outerPath = `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2} Z`
    }

    let path = outerPath
    if (props.donut && portion > 0) {
      const xi1 = cx + rInner * Math.cos(endAngle)
      const yi1 = cy + rInner * Math.sin(endAngle)
      const xi2 = cx + rInner * Math.cos(startAngle)
      const yi2 = cy + rInner * Math.sin(startAngle)
      if (portion >= 1) {
        path = `M ${cx - r} ${cy} A ${r} ${r} 0 1 1 ${cx + r} ${cy} A ${r} ${r} 0 1 1 ${cx - r} ${cy} M ${cx - rInner} ${cy} A ${rInner} ${rInner} 0 1 0 ${cx + rInner} ${cy} A ${rInner} ${rInner} 0 1 0 ${cx - rInner} ${cy} Z`
      } else {
        const largeArc = angle > Math.PI ? 1 : 0
        path = `M ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2} L ${xi1} ${yi1} A ${rInner} ${rInner} 0 ${largeArc} 0 ${xi2} ${yi2} Z`
      }
    }

    const midAngle = startAngle + angle / 2
    const labelX = cx + r * 0.62 * Math.cos(midAngle)
    const labelY = cy + r * 0.62 * Math.sin(midAngle)

    startAngle = endAngle
    return { item, color, path, portion, value, labelX, labelY }
  })
})
</script>

<template>
  <div class="viz-card">
    <h4 class="viz-title">{{ title }}</h4>
    <div v-if="!items.length" class="viz-empty">暂无统计数据</div>
    <div v-else class="pie-chart-wrap">
      <svg :width="size" :height="size" :viewBox="`0 0 ${size} ${size}`" class="chart-svg">
        <path
          v-for="(s, i) in slices"
          :key="i"
          :d="s.path"
          :fill="s.color"
          stroke="#fff"
          stroke-width="2"
          opacity="0.92"
        />
        <text v-if="donut" :x="cx" :y="cy - 4" text-anchor="middle" font-size="13" fill="#8a96ae">总计</text>
        <text v-if="donut" :x="cx" :y="cy + 16" text-anchor="middle" font-size="18" font-weight="700" fill="#21314d">
          {{ formatValue(total) }}
        </text>
      </svg>
      <div class="legend">
        <div v-for="(it, idx) in items" :key="idx" class="legend-row">
          <span class="legend-dot" :style="{ background: colors[idx % colors.length] }" />
          <span class="legend-label">{{ it[labelKey] }}</span>
          <span class="legend-value">{{ formatValue(it[valueKey]) }} ({{ ((Number(it[valueKey] || 0) / Math.max(total, 1)) * 100).toFixed(1) }}%)</span>
        </div>
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
.pie-chart-wrap {
  display: flex;
  gap: 18px;
  align-items: center;
  flex-wrap: wrap;
  justify-content: center;
}
.chart-svg {
  flex-shrink: 0;
}
.legend {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 160px;
}
.legend-row {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 8px;
  align-items: center;
  font-size: 12px;
}
.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 3px;
  display: inline-block;
}
.legend-label {
  color: var(--text-main);
}
.legend-value {
  color: var(--text-sub);
  font-weight: 600;
}
</style>
