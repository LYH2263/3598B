<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: { type: String, default: '' },
  items: { type: Array, default: () => [] },
  labelKey: { type: String, default: 'label' },
  stacks: {
    type: Array,
    default: () => [
      { key: 'approved', label: '已通过', color: '#2b9f6c' },
      { key: 'pending', label: '待审核', color: '#f59e0b' },
      { key: 'rejected', label: '已驳回', color: '#ef4444' },
    ],
  },
  height: { type: Number, default: 220 },
  horizontal: { type: Boolean, default: false },
  formatValue: { type: Function, default: (v) => v },
})

const width = 600
const padding = { top: 24, right: 24, bottom: 40, left: 64 }
const innerW = computed(() => width - padding.left - padding.right)
const innerH = computed(() => props.height - padding.top - padding.bottom)

const rowTotals = computed(() =>
  props.items.map((it) => props.stacks.reduce((s, st) => s + Number(it[st.key] || 0), 0))
)

const maxVal = computed(() => {
  const m = Math.max(...rowTotals.value, 0)
  return m === 0 ? 1 : m * 1.15
})

const barGap = 8
const barThickness = computed(() => {
  if (!props.items.length) return 20
  const avail = props.horizontal ? innerH.value : innerW.value
  return Math.max(12, (avail - barGap * (props.items.length - 1)) / props.items.length)
})

function getStackOffsets(item) {
  let cum = 0
  return props.stacks.map((st) => {
    const value = Number(item[st.key] || 0)
    const offset = cum
    cum += value
    return { key: st.key, color: st.color, value, cumOffset: offset }
  })
}
</script>

<template>
  <div class="viz-card">
    <h4 class="viz-title">{{ title }}</h4>
    <div v-if="!items.length" class="viz-empty">暂无统计数据</div>
    <div v-else>
      <svg :viewBox="`0 0 ${width} ${height}`" class="chart-svg">
        <template v-if="!horizontal">
          <g v-for="(item, i) in items" :key="i">
            <rect
              v-for="(stack, si) in getStackOffsets(item)"
              :key="si"
              :x="padding.left + i * (barThickness + barGap)"
              :y="padding.top + innerH - (stack.cumOffset + stack.value) / maxVal * innerH"
              :width="barThickness"
              :height="(stack.value / maxVal) * innerH"
              :fill="stack.color"
              rx="2"
            />
            <text
              :x="padding.left + i * (barThickness + barGap) + barThickness / 2"
              :y="height - padding.bottom + 18"
              text-anchor="middle"
              font-size="11"
              fill="#8a96ae"
            >
              {{ item[labelKey] }}
            </text>
          </g>
        </template>
        <template v-else>
          <g v-for="(item, i) in items" :key="i">
            <rect
              v-for="(stack, si) in getStackOffsets(item)"
              :key="si"
              :x="padding.left + (stack.cumOffset / maxVal) * innerW"
              :y="padding.top + i * (barThickness + barGap)"
              :width="(stack.value / maxVal) * innerW"
              :height="barThickness"
              :fill="stack.color"
              rx="2"
            />
            <text
              :x="padding.left - 8"
              :y="padding.top + i * (barThickness + barGap) + barThickness / 2 + 4"
              text-anchor="end"
              font-size="11"
              fill="#8a96ae"
            >
              {{ item[labelKey] }}
            </text>
          </g>
        </template>
      </svg>
      <div class="legend">
        <span v-for="st in stacks" :key="st.key" class="legend-item">
          <span class="legend-dot" :style="{ background: st.color }" />
          {{ st.label }}
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
  border-radius: 3px;
  display: inline-block;
}
</style>
