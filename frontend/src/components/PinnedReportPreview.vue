<script setup>
import { computed } from 'vue'
import SimpleBarChart from './SimpleBarChart.vue'
import LineChart from './LineChart.vue'
import PieChart from './PieChart.vue'
import AreaChart from './AreaChart.vue'
import { DATASETS } from '../utils/datasets'

const props = defineProps({
  report: { type: Object, default: null },
  data: { type: Object, default: null },
})

const labelKey = computed(() => {
  if (!props.data?.dimension) return 'label'
  const timeDims = ['day', 'week', 'month']
  return timeDims.includes(props.data.dimension) ? 'period' : props.data.dimension
})

const items = computed(() => {
  if (!props.data?.data) return []
  const rows = props.data.data
  const dim = props.data.dimension
  const dataset = DATASETS[props.report?.dataset]
  const dimLabel = dataset?.dimensions?.find((d) => d.key === dim)?.label || dim

  return rows.map((row) => {
    const out = { ...row }
    if (dim === 'channel') out.label = { alipay: '支付宝', wechat: '微信支付', bank: '银行卡' }[row.channel] || row.channel
    else if (dim === 'category') out.label = { water: '水费', electricity: '电费' }[row.category] || row.category
    else if (dim === 'role') out.label = { student: '学生', admin: '管理员', unknown: '未知' }[row.role] || row.role
    else if (row.period) out.label = row.period
    return out
  })
})

const measureKey = computed(() => props.data?.measures?.[0] || 'amount')
const measureLabel = computed(() => {
  const dataset = DATASETS[props.report?.dataset]
  return dataset?.measures?.find((m) => m.key === measureKey.value)?.label || measureKey.value
})

const chartType = computed(() => props.report?.chart_type || 'bar')

function formatVal(v) {
  if (measureKey.value === 'amount') return `¥ ${Number(v || 0).toFixed(2)}`
  return Number(v || 0).toFixed(0)
}
</script>

<template>
  <div class="pinned-preview">
    <div v-if="!report || !data" class="viz-empty">加载中...</div>
    <div v-else>
      <SimpleBarChart
        v-if="chartType === 'bar'"
        title=""
        :items="items"
        :label-key="labelKey === 'label' ? 'label' : labelKey"
        :value-key="measureKey"
        color="#2d73da"
      />
      <LineChart
        v-else-if="chartType === 'line'"
        title=""
        :items="data.data"
        label-key="period"
        :value-keys="[measureKey]"
        :value-labels="[measureLabel]"
        :format-value="(v) => Number(v).toFixed(0)"
      />
      <AreaChart
        v-else-if="chartType === 'area'"
        title=""
        :items="data.data"
        label-key="period"
        :value-key="measureKey"
        color="#8b5cf6"
        :format-value="(v) => Number(v).toFixed(0)"
      />
      <PieChart
        v-else-if="chartType === 'pie' || chartType === 'donut'"
        title=""
        :items="items"
        label-key="label"
        :value-key="measureKey"
        :donut="chartType === 'donut'"
        :format-value="formatVal"
      />
      <SimpleBarChart v-else title="" :items="items" :label-key="labelKey" :value-key="measureKey" />
    </div>
  </div>
</template>

<style scoped>
.viz-empty {
  color: var(--text-sub);
  font-size: 13px;
  padding: 16px;
  text-align: center;
}
.pinned-preview {
  padding: 4px 0;
}
</style>
