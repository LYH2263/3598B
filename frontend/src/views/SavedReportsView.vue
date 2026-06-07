<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElNotification, ElMessageBox, ElDialog } from 'element-plus'

import SimpleBarChart from '../components/SimpleBarChart.vue'
import LineChart from '../components/LineChart.vue'
import PieChart from '../components/PieChart.vue'
import AreaChart from '../components/AreaChart.vue'
import PinnedReportPreview from '../components/PinnedReportPreview.vue'
import { useAuthStore } from '../stores/auth'
import { useReportsStore } from '../stores/reports'
import { useAnalyticsStore } from '../stores/analytics'
import { DATASETS } from '../utils/datasets'
import { downloadCSV } from '../utils/csv'

const router = useRouter()
const authStore = useAuthStore()
const reportsStore = useReportsStore()
const analyticsStore = useAnalyticsStore()

const runningId = ref(null)
const runResults = reactive({})
const previewDialogVisible = ref(false)
const previewReport = ref(null)

const isAdmin = computed(() => authStore.user?.profile?.role === 'admin')

const datasetLabel = (key) => DATASETS[key]?.label || key
const chartTypeLabel = (key) => ({
  bar: '柱状图', line: '折线图', area: '面积图', pie: '饼图', donut: '环形图',
}[key] || key)

async function runReport(report) {
  runningId.value = report.id
  try {
    const data = await reportsStore.runReport(report.id)
    runResults.value[report.id] = data
    previewReport.value = report
    previewDialogVisible.value = true
    ElNotification({ title: '运行完成', message: `报表「${report.name}」已重新生成数据。`, type: 'success' })
  } finally {
    runningId.value = null
  }
}

function exportReportCSV(report) {
  const data = runResults.value[report.id]
  if (!data?.data?.length) {
    ElNotification({ title: '无法导出', message: '请先运行报表获取数据。', type: 'warning' })
    return
  }
  const dataset = DATASETS[report.dataset]
  const headers = []
  const dim = report.dimensions?.[0] || 'period'
  const dimMeta = dataset?.dimensions?.find((d) => d.key === dim)
  headers.push({ key: dim === 'day' || dim === 'week' || dim === 'month' ? 'period' : dim, label: dimMeta?.label || '维度' })
  report.measures.forEach((m) => {
    const meta = dataset?.measures?.find((x) => x.key === m)
    headers.push({ key: m, label: meta?.label || m })
  })
  downloadCSV(report.name, data.data, headers)
}

async function togglePin(report) {
  try {
    await reportsStore.updateReport(report.id, { is_pinned: !report.is_pinned })
    ElNotification({
      title: report.is_pinned ? '已取消固定' : '已固定到看板',
      message: `报表「${report.name}」${report.is_pinned ? '已从看板移除' : '将在下次打开看板时显示'}。`,
      type: 'success',
    })
  } catch (_e) {}
}

async function deleteReport(report) {
  try {
    await ElMessageBox.confirm(`确定删除报表「${report.name}」吗？此操作不可恢复。`, '删除确认', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch (_e) {
    return
  }
  try {
    await reportsStore.deleteReport(report.id)
    ElNotification({ title: '已删除', message: '报表已删除。', type: 'success' })
  } catch (_e) {}
}

function formatDateTime(v) {
  if (!v) return '--'
  const d = new Date(v)
  if (Number.isNaN(d.getTime())) return v
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hour12: false,
  }).format(d)
}

onMounted(async () => {
  if (!isAdmin.value) {
    ElNotification({ title: '无权限', message: '仅管理员可访问报表管理。', type: 'warning' })
    router.push('/dashboard')
    return
  }
  await reportsStore.loadList()
})
</script>

<template>
  <main class="page-shell animated-in">
    <section class="analytics-wrap">
      <el-card class="section-card" shadow="never">
        <el-row justify="space-between" align="middle" :gutter="12">
          <el-col :xs="24" :sm="16">
            <h2 class="section-title" style="margin: 0">📋 我的自定义报表</h2>
            <p style="margin: 6px 0 0; color: var(--text-sub)">
              保存的报表可一键运行、导出 CSV、并固定到数据看板
            </p>
          </el-col>
          <el-col :xs="24" :sm="8" style="text-align: right">
            <el-space wrap>
              <el-button type="primary" @click="router.push('/reports/build')">➕ 新建报表</el-button>
              <el-button @click="router.push('/analytics')">📊 数据看板</el-button>
              <el-button @click="router.push('/dashboard')">← 返回</el-button>
            </el-space>
          </el-col>
        </el-row>
      </el-card>

      <el-card class="section-card" shadow="never">
        <el-skeleton :loading="reportsStore.loading" animated :rows="6">
          <template #default>
            <div v-if="!reportsStore.list.length" class="empty-wrap">
              <div style="font-size: 48px; margin-bottom: 12px">📊</div>
              <h3 style="margin: 0 0 6px">暂无自定义报表</h3>
              <p style="margin: 0 0 18px; color: var(--text-sub)">点击右上角「新建报表」开始创建</p>
              <el-button type="primary" @click="router.push('/reports/build')">开始创建</el-button>
            </div>

            <el-table
              v-else
              :data="reportsStore.list"
              stripe
              border
              empty-text="暂无报表"
            >
              <el-table-column prop="name" label="报表名称" min-width="180">
                <template #default="{ row }">
                  <div>
                    <strong>{{ row.name }}</strong>
                    <div v-if="row.description" style="font-size: 12px; color: var(--text-sub); margin-top: 2px">
                      {{ row.description }}
                    </div>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="数据集" min-width="110">
                <template #default="{ row }">
                  <el-tag size="small" type="info">{{ datasetLabel(row.dataset) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="维度" min-width="140">
                <template #default="{ row }">
                  <span v-for="d in row.dimensions" :key="d" style="margin-right: 4px">
                    <el-tag size="small">{{ DATASETS[row.dataset]?.dimensions?.find(x => x.key === d)?.label || d }}</el-tag>
                  </span>
                </template>
              </el-table-column>
              <el-table-column label="度量" min-width="140">
                <template #default="{ row }">
                  <span v-for="m in row.measures" :key="m" style="margin-right: 4px">
                    <el-tag size="small" type="success">{{ DATASETS[row.dataset]?.measures?.find(x => x.key === m)?.label || m }}</el-tag>
                  </span>
                </template>
              </el-table-column>
              <el-table-column label="图表类型" min-width="100">
                <template #default="{ row }">
                  <el-tag size="small" type="warning">{{ chartTypeLabel(row.chart_type) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="更新时间" min-width="165">
                <template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template>
              </el-table-column>
              <el-table-column label="固定到看板" min-width="100" align="center">
                <template #default="{ row }">
                  <el-switch :model-value="row.is_pinned" @change="togglePin(row)" />
                </template>
              </el-table-column>
              <el-table-column label="操作" min-width="280" fixed="right" align="center">
                <template #default="{ row }">
                  <el-space wrap>
                    <el-button size="small" type="primary" :loading="runningId === row.id" @click="runReport(row)">▶ 运行</el-button>
                    <el-button size="small" type="success" plain :disabled="!runResults[row.id]?.data?.length" @click="exportReportCSV(row)">📥 导出CSV</el-button>
                    <el-button size="small" @click="togglePin(row)">{{ row.is_pinned ? '📌 取消固定' : '📍 固定看板' }}</el-button>
                    <el-button size="small" type="danger" plain @click="deleteReport(row)">🗑 删除</el-button>
                  </el-space>
                </template>
              </el-table-column>
            </el-table>
          </template>
        </el-skeleton>
      </el-card>

      <el-dialog v-model="previewDialogVisible" :title="previewReport?.name || '报表预览'" width="780px">
        <div v-if="previewReport && runResults[previewReport.id]">
          <PinnedReportPreview :report="previewReport" :data="runResults[previewReport.id]" />
          <el-table :data="runResults[previewReport.id]?.data?.slice(0, 20) || []" stripe border size="small" style="margin-top: 14px">
            <el-table-column
              v-for="h in (runResults[previewReport.id]?.measures || []).concat([runResults[previewReport.id]?.dimension]).filter(Boolean)"
              :key="h"
              :prop="h"
              :label="h"
              min-width="120"
            />
          </el-table>
        </div>
        <template #footer>
          <el-button @click="previewDialogVisible = false">关闭</el-button>
          <el-button type="success" plain :disabled="!runResults[previewReport?.id]?.data?.length" @click="exportReportCSV(previewReport)">
            📥 导出 CSV
          </el-button>
        </template>
      </el-dialog>
    </section>
  </main>
</template>

<style scoped>
.analytics-wrap {
  max-width: 1300px;
  margin: 0 auto;
  display: grid;
  gap: 18px;
}
.empty-wrap {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-sub);
}
</style>
