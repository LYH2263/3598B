<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElNotification, ElMessageBox } from 'element-plus'

import SimpleBarChart from '../components/SimpleBarChart.vue'
import LineChart from '../components/LineChart.vue'
import PieChart from '../components/PieChart.vue'
import AreaChart from '../components/AreaChart.vue'
import { useAuthStore } from '../stores/auth'
import { useReportsStore } from '../stores/reports'
import { useAnalyticsStore } from '../stores/analytics'
import { DATASETS, CHART_TYPES } from '../utils/datasets'
import { downloadCSV } from '../utils/csv'

const router = useRouter()
const authStore = useAuthStore()
const reportsStore = useReportsStore()
const analyticsStore = useAnalyticsStore()

const step = ref(1)
const previewLoading = ref(false)
const saveLoading = ref(false)

const form = reactive({
  dataset: 'recharge',
  dimensions: ['day'],
  measures: ['amount', 'count'],
  filters: {},
  chart_type: 'bar',
  name: '',
  description: '',
  is_pinned: false,
})

const previewResult = ref(null)

const currentDataset = computed(() => DATASETS[form.dataset])
const timeDimensions = ['day', 'week', 'month']

function buildFilterPayload() {
  const out = {}
  currentDataset.value.filters.forEach((f) => {
    const v = form.filters[f.key]
    if (v !== undefined && v !== null && v !== '') {
      if (f.type === 'date' && v instanceof Date) {
        out[f.key] = v.toISOString().slice(0, 10)
      } else if (f.type === 'date' && typeof v === 'string') {
        out[f.key] = v.slice(0, 10)
      } else {
        out[f.key] = v
      }
    }
  })
  return out
}

async function runPreview() {
  previewLoading.value = true
  try {
    previewResult.value = await reportsStore.queryDataset({
      dataset: form.dataset,
      dimensions: form.dimensions,
      measures: form.measures,
      filters: buildFilterPayload(),
    })
  } finally {
    previewLoading.value = false
  }
}

function goNext() {
  if (step.value < 5) {
    step.value++
    if (step.value === 5) runPreview()
  }
}
function goPrev() {
  if (step.value > 1) step.value--
}

function toggleDimension(key) {
  if (timeDimensions.includes(key)) {
    form.dimensions = form.dimensions.filter((d) => !timeDimensions.includes(d))
    if (!form.dimensions.includes(key)) form.dimensions.push(key)
  } else {
    const idx = form.dimensions.indexOf(key)
    if (idx >= 0) form.dimensions.splice(idx, 1)
    else form.dimensions.push(key)
  }
  if (!form.dimensions.length) form.dimensions = [currentDataset.value.dimensions[0].key]
}

function toggleMeasure(key) {
  const idx = form.measures.indexOf(key)
  if (idx >= 0) {
    if (form.measures.length > 1) form.measures.splice(idx, 1)
  } else {
    form.measures.push(key)
  }
}

const labelKey = computed(() => {
  if (!previewResult.value?.dimension) return 'label'
  const dim = previewResult.value.dimension
  if (timeDimensions.includes(dim)) return 'period'
  return dim
})

const previewItems = computed(() => {
  if (!previewResult.value?.data) return []
  const dim = previewResult.value.dimension
  const rows = previewResult.value.data
  return rows.map((row) => {
    const out = { ...row }
    if (dim === 'channel') out.label = { alipay: '支付宝', wechat: '微信支付', bank: '银行卡' }[row.channel] || row.channel
    else if (dim === 'category') out.label = { water: '水费', electricity: '电费' }[row.category] || row.category
    else if (dim === 'role') out.label = { student: '学生', admin: '管理员', unknown: '未知' }[row.role] || row.role
    return out
  })
})

const measureLabels = computed(() => {
  return form.measures.map(
    (m) => currentDataset.value.measures.find((x) => x.key === m)?.label || m
  )
})

async function saveReport() {
  if (!form.name.trim()) {
    ElNotification({ title: '保存失败', message: '请输入报表名称。', type: 'warning' })
    return
  }
  saveLoading.value = true
  try {
    const payload = {
      name: form.name.trim(),
      description: form.description.trim(),
      dataset: form.dataset,
      dimensions: form.dimensions,
      measures: form.measures,
      filters: buildFilterPayload(),
      chart_type: form.chart_type,
      chart_config: {},
      is_pinned: form.is_pinned,
    }
    await reportsStore.createReport(payload)
    ElNotification({ title: '保存成功', message: '自定义报表已保存。', type: 'success' })
    if (form.is_pinned) await analyticsStore.loadDashboardLayout()
    router.push('/reports')
  } finally {
    saveLoading.value = false
  }
}

function exportPreviewCSV() {
  if (!previewResult.value?.data?.length) return
  const headers = []
  const dim = previewResult.value.dimension
  headers.push({ key: labelKey.value, label: currentDataset.value.dimensions.find((d) => d.key === dim)?.label || '维度' })
  form.measures.forEach((m) => {
    const meta = currentDataset.value.measures.find((x) => x.key === m)
    headers.push({ key: m, label: meta?.label || m })
  })
  const safeName = form.name.trim() || `report-${form.dataset}`
  downloadCSV(safeName, previewItems.value, headers)
}

function canStepNext(s) {
  if (s === 1) return !!form.dataset
  if (s === 2) return form.dimensions.length > 0
  if (s === 3) return form.measures.length > 0
  if (s === 4) return true
  if (s === 5) return true
  return false
}

onMounted(async () => {
  if (authStore.user?.profile?.role !== 'admin') {
    ElNotification({ title: '无权限', message: '仅管理员可访问报表构建器。', type: 'warning' })
    router.push('/dashboard')
  }
  form.filters = {}
  currentDataset.value.filters.forEach((f) => {
    form.filters[f.key] = ''
  })
})
</script>

<template>
  <main class="page-shell animated-in">
    <section class="analytics-wrap">
      <el-card class="section-card" shadow="never">
        <el-row justify="space-between" align="middle" :gutter="12">
          <el-col :xs="24" :sm="16">
            <h2 class="section-title" style="margin: 0">🛠 自定义报表构建器</h2>
            <p style="margin: 6px 0 0; color: var(--text-sub)">
              依次选择：数据集 → 维度 → 度量 → 筛选 → 图表类型，预览后保存
            </p>
          </el-col>
          <el-col :xs="24" :sm="8" style="text-align: right">
            <el-button @click="router.push('/analytics')">← 返回看板</el-button>
            <el-button @click="router.push('/reports')">📋 我的报表</el-button>
          </el-col>
        </el-row>
      </el-card>

      <el-steps :active="step" finish-status="success" align-center style="margin-bottom: 18px">
        <el-step title="选择数据集" />
        <el-step title="选择维度" />
        <el-step title="选择度量" />
        <el-step title="筛选条件" />
        <el-step title="图表与保存" />
      </el-steps>

      <el-card class="section-card" shadow="never">
        <div v-if="step === 1" class="step-content">
          <h3 class="section-title">第 1 步：选择数据集</h3>
          <div class="dataset-grid">
            <div
              v-for="(meta, key) in DATASETS"
              :key="key"
              class="dataset-card"
              :class="{ active: form.dataset === key }"
              @click="form.dataset = key"
            >
              <h4>{{ meta.label }}</h4>
              <p>{{ meta.description }}</p>
              <div class="dataset-tags">
                <el-tag size="small" type="info">维度: {{ meta.dimensions.length }}</el-tag>
                <el-tag size="small" type="success">度量: {{ meta.measures.length }}</el-tag>
              </div>
            </div>
          </div>
        </div>

        <div v-else-if="step === 2" class="step-content">
          <h3 class="section-title">第 2 步：选择维度（聚合分组依据）</h3>
          <p class="hint">时间维度（日/周/月）互斥，可与其他维度单选组合。当前数据集：<strong>{{ currentDataset.label }}</strong></p>
          <div class="option-grid">
            <div
              v-for="dim in currentDataset.dimensions"
              :key="dim.key"
              class="option-card"
              :class="{ active: form.dimensions.includes(dim.key), 'time-dim': timeDimensions.includes(dim.key) }"
              @click="toggleDimension(dim.key)"
            >
              <span class="option-check">{{ form.dimensions.includes(dim.key) ? '✓' : '' }}</span>
              <span class="option-label">{{ dim.label }}</span>
            </div>
          </div>
        </div>

        <div v-else-if="step === 3" class="step-content">
          <h3 class="section-title">第 3 步：选择度量（要计算的指标）</h3>
          <p class="hint">至少选择 1 个度量</p>
          <div class="option-grid">
            <div
              v-for="m in currentDataset.measures"
              :key="m.key"
              class="option-card"
              :class="{ active: form.measures.includes(m.key) }"
              @click="toggleMeasure(m.key)"
            >
              <span class="option-check">{{ form.measures.includes(m.key) ? '✓' : '' }}</span>
              <span class="option-label">{{ m.label }}</span>
            </div>
          </div>
        </div>

        <div v-else-if="step === 4" class="step-content">
          <h3 class="section-title">第 4 步：筛选条件（可选）</h3>
          <el-form label-position="top" class="filter-form">
            <el-row :gutter="16">
              <el-col :xs="24" :sm="12" :md="8" v-for="f in currentDataset.filters" :key="f.key">
                <el-form-item :label="f.label">
                  <el-select v-if="f.type === 'select'" v-model="form.filters[f.key]" style="width: 100%" clearable>
                    <el-option v-for="opt in f.options" :key="opt.value" :label="opt.label" :value="opt.value" />
                  </el-select>
                  <el-date-picker
                    v-else-if="f.type === 'date'"
                    v-model="form.filters[f.key]"
                    type="date"
                    value-format="YYYY-MM-DD"
                    style="width: 100%"
                    :placeholder="f.label"
                  />
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>
        </div>

        <div v-else-if="step === 5" class="step-content">
          <h3 class="section-title">第 5 步：预览图表并保存</h3>
          <el-row :gutter="16" style="margin-bottom: 14px">
            <el-col :xs="24" :sm="8">
              <el-form label-position="top">
                <el-form-item label="图表类型">
                  <el-select v-model="form.chart_type" style="width: 100%">
                    <el-option v-for="ct in CHART_TYPES" :key="ct.key" :label="ct.label" :value="ct.key" />
                  </el-select>
                </el-form-item>
              </el-form>
            </el-col>
            <el-col :xs="24" :sm="16" style="display: flex; gap: 8px; align-items: flex-end; flex-wrap: wrap">
              <el-button :loading="previewLoading" type="primary" plain @click="runPreview">🔄 重新预览</el-button>
              <el-button type="success" plain :disabled="!previewResult?.data?.length" @click="exportPreviewCSV">📥 导出 CSV</el-button>
              <el-form-item style="margin: 0">
                <el-switch v-model="form.is_pinned" active-text="保存后同时固定到看板" />
              </el-form-item>
            </el-col>
          </el-row>

          <el-skeleton :loading="previewLoading" animated :rows="4">
            <template #default>
              <div class="preview-chart">
                <SimpleBarChart
                  v-if="form.chart_type === 'bar'"
                  title="预览"
                  :items="previewItems"
                  :label-key="labelKey === 'label' ? 'label' : labelKey"
                  :value-key="form.measures[0]"
                  color="#2d73da"
                />
                <LineChart
                  v-else-if="form.chart_type === 'line'"
                  title="预览"
                  :items="previewResult?.data || []"
                  label-key="period"
                  :value-keys="form.measures"
                  :value-labels="measureLabels"
                  :format-value="(v) => Number(v).toFixed(0)"
                />
                <AreaChart
                  v-else-if="form.chart_type === 'area'"
                  title="预览"
                  :items="previewResult?.data || []"
                  label-key="period"
                  :value-key="form.measures[0]"
                  color="#8b5cf6"
                  :format-value="(v) => Number(v).toFixed(0)"
                />
                <PieChart
                  v-else-if="form.chart_type === 'pie' || form.chart_type === 'donut'"
                  title="预览"
                  :items="previewItems"
                  label-key="label"
                  :value-key="form.measures[0]"
                  :donut="form.chart_type === 'donut'"
                  :format-value="(v) => form.measures[0] === 'amount' ? `¥${v}` : v"
                />
              </div>
              <el-table :data="previewResult?.data?.slice(0, 15) || []" stripe border size="small" style="margin-top: 14px" empty-text="暂无预览数据">
                <el-table-column v-for="h in (previewResult?.measures || []).concat([previewResult?.dimension]).filter(Boolean)" :key="h" :prop="h" :label="h" min-width="120" />
              </el-table>
            </template>
          </el-skeleton>

          <el-divider />
          <h4>保存报表</h4>
          <el-form label-position="top">
            <el-row :gutter="16">
              <el-col :xs="24" :sm="12">
                <el-form-item label="报表名称 *">
                  <el-input v-model="form.name" placeholder="例如：近30天各渠道充值对比" maxlength="100" show-word-limit />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :sm="12">
                <el-form-item label="描述（可选）">
                  <el-input v-model="form.description" placeholder="简要说明报表用途" maxlength="300" show-word-limit />
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>
        </div>

        <div class="step-actions">
          <el-button v-if="step > 1" @click="goPrev">上一步</el-button>
          <el-button v-if="step < 5" type="primary" :disabled="!canStepNext(step)" @click="goNext">下一步</el-button>
          <el-button v-if="step === 5" type="primary" :loading="saveLoading" @click="saveReport">💾 保存报表</el-button>
        </div>
      </el-card>
    </section>
  </main>
</template>

<style scoped>
.analytics-wrap {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  gap: 18px;
}
.step-content {
  min-height: 300px;
}
.hint {
  color: var(--text-sub);
  font-size: 13px;
  margin-bottom: 14px;
}
.dataset-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 14px;
}
.dataset-card {
  border: 2px solid rgba(90, 128, 201, 0.18);
  border-radius: 14px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;
  background: #fff;
}
.dataset-card:hover {
  border-color: var(--brand-soft);
  transform: translateY(-2px);
}
.dataset-card.active {
  border-color: var(--brand);
  background: linear-gradient(135deg, rgba(35, 103, 209, 0.08), rgba(90, 149, 237, 0.04));
  box-shadow: 0 6px 20px rgba(35, 103, 209, 0.12);
}
.dataset-card h4 {
  margin: 0 0 6px;
  font-size: 16px;
  font-weight: 700;
}
.dataset-card p {
  margin: 0 0 10px;
  font-size: 13px;
  color: var(--text-sub);
}
.dataset-tags {
  display: flex;
  gap: 6px;
}
.option-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
}
.option-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border: 2px solid rgba(90, 128, 201, 0.18);
  border-radius: 12px;
  cursor: pointer;
  background: #fff;
  transition: all 0.2s;
}
.option-card:hover {
  border-color: var(--brand-soft);
}
.option-card.active {
  border-color: var(--brand);
  background: rgba(35, 103, 209, 0.06);
}
.option-check {
  width: 22px;
  height: 22px;
  border-radius: 6px;
  border: 2px solid #c6d0e0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 13px;
  color: #fff;
}
.option-card.active .option-check {
  background: var(--brand);
  border-color: var(--brand);
}
.option-label {
  font-weight: 600;
  font-size: 14px;
}
.filter-form {
  max-width: 100%;
}
.step-actions {
  display: flex;
  justify-content: space-between;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid rgba(90, 128, 201, 0.14);
}
.preview-chart {
  max-width: 100%;
}
</style>
