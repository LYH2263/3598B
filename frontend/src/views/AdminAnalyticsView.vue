<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElNotification } from 'element-plus'

import LineChart from '../components/LineChart.vue'
import PieChart from '../components/PieChart.vue'
import AreaChart from '../components/AreaChart.vue'
import SimpleBarChart from '../components/SimpleBarChart.vue'
import PinnedReportPreview from '../components/PinnedReportPreview.vue'
import { useAuthStore } from '../stores/auth'
import { useAnalyticsStore } from '../stores/analytics'
import { useReportsStore } from '../stores/reports'
import { downloadCSV } from '../utils/csv'

const router = useRouter()
const authStore = useAuthStore()
const analyticsStore = useAnalyticsStore()
const reportsStore = useReportsStore()

const timeWindowOptions = [
  { label: '近 7 天', value: '7d' },
  { label: '近 30 天', value: '30d' },
  { label: '近 90 天', value: '90d' },
  { label: '近 1 年', value: '1y' },
]

const KPI_DEFS = [
  { key: 'total_users', label: '总用户数', icon: '👥', color: '#2d73da', format: (v) => v },
  { key: 'active_users', label: '活跃用户', icon: '🔥', color: '#f59e0b', format: (v) => v },
  { key: 'total_recharge', label: '充值总额', icon: '💰', color: '#2b9f6c', format: (v) => `¥ ${Number(v || 0).toFixed(2)}` },
  { key: 'total_consumption', label: '消费总额', icon: '⚡', color: '#8b5cf6', format: (v) => `¥ ${Number(v || 0).toFixed(2)}` },
  { key: 'frozen_accounts', label: '冻结账户', icon: '❄️', color: '#ef4444', format: (v) => v },
  { key: 'pending_orders', label: '待审订单', icon: '⏳', color: '#06b6d4', format: (v) => v },
]

const DEFAULT_CARDS = [
  { id: 'kpis', type: 'kpis', title: '核心指标', colSpan: 2 },
  { id: 'recharge-trend', type: 'chart-recharge-trend', title: '充值趋势', colSpan: 1 },
  { id: 'consumption-trend', type: 'chart-consumption-trend', title: '消费趋势', colSpan: 1 },
  { id: 'user-growth', type: 'chart-user-growth', title: '用户增长', colSpan: 1 },
  { id: 'recharge-channel', type: 'chart-recharge-channel', title: '充值渠道分布', colSpan: 1 },
  { id: 'consumption-category', type: 'chart-consumption-category', title: '消费类目分布', colSpan: 1 },
  { id: 'users-by-role', type: 'chart-users-by-role', title: '用户角色分布', colSpan: 1 },
]

const cards = ref([])
const draggedCard = ref(null)
const dragOverId = ref(null)
const pinnedReportData = ref({})

const isAdmin = computed(() => authStore.user?.profile?.role === 'admin')

function initCards() {
  if (analyticsStore.dashboardLayout && analyticsStore.dashboardLayout.length) {
    cards.value = [...analyticsStore.dashboardLayout]
  } else {
    cards.value = [...DEFAULT_CARDS]
  }
}

function formatMoney(v) {
  return `¥ ${Number(v || 0).toFixed(2)}`
}

const channelMap = { alipay: '支付宝', wechat: '微信支付', bank: '银行卡' }
const categoryMap = { water: '水费', electricity: '电费' }
const roleMap = { student: '学生', admin: '管理员', unknown: '未知' }

const rechargeByChannelItems = computed(() =>
  analyticsStore.distributions.recharge_by_channel.map((it) => ({
    label: channelMap[it.channel] || it.channel,
    value: Number(it.amount || 0).toFixed(2),
  }))
)

const consumptionByCategoryItems = computed(() =>
  analyticsStore.distributions.consumption_by_category.map((it) => ({
    label: categoryMap[it.category] || it.category,
    value: Number(it.amount || 0).toFixed(2),
  }))
)

const usersByRoleItems = computed(() =>
  analyticsStore.distributions.users_by_role.map((it) => ({
    label: roleMap[it.role] || it.role,
    value: it.count,
  }))
)

function onDragStart(e, card) {
  draggedCard.value = card
  e.dataTransfer.effectAllowed = 'move'
}

function onDragOver(e, cardId) {
  e.preventDefault()
  dragOverId.value = cardId
}

function onDragLeave() {
  dragOverId.value = null
}

function onDrop(e, targetCard) {
  e.preventDefault()
  if (!draggedCard.value || draggedCard.value.id === targetCard.id) {
    draggedCard.value = null
    dragOverId.value = null
    return
  }
  const fromIdx = cards.value.findIndex((c) => c.id === draggedCard.value.id)
  const toIdx = cards.value.findIndex((c) => c.id === targetCard.id)
  if (fromIdx >= 0 && toIdx >= 0) {
    const newCards = [...cards.value]
    const [moved] = newCards.splice(fromIdx, 1)
    newCards.splice(toIdx, 0, moved)
    cards.value = newCards
    persistLayout()
  }
  draggedCard.value = null
  dragOverId.value = null
}

function onDragEnd() {
  draggedCard.value = null
  dragOverId.value = null
}

let layoutSaveTimer = null
function persistLayout() {
  if (layoutSaveTimer) clearTimeout(layoutSaveTimer)
  layoutSaveTimer = setTimeout(() => {
    analyticsStore.saveDashboardLayout(cards.value)
    ElNotification({ title: '布局已保存', message: '看板布局已更新到个人偏好。', type: 'success' })
  }, 400)
}

function removeCard(cardId) {
  cards.value = cards.value.filter((c) => c.id !== cardId)
  persistLayout()
}

function resetLayout() {
  cards.value = [...DEFAULT_CARDS]
  persistLayout()
}

function exportDashboardCSV() {
  const rows = []
  analyticsStore.trends.recharge.forEach((r) => {
    rows.push({ period: r.period, metric: '充值金额', value: r.amount })
    rows.push({ period: r.period, metric: '充值笔数', value: r.count })
  })
  analyticsStore.trends.consumption.forEach((r) => {
    rows.push({ period: r.period, metric: '消费金额', value: r.amount })
    rows.push({ period: r.period, metric: '消费笔数', value: r.count })
  })
  analyticsStore.trends.user_growth.forEach((r) => {
    rows.push({ period: r.period, metric: '新增用户', value: r.count })
  })
  downloadCSV('dashboard-summary', rows, [
    { key: 'period', label: '周期' },
    { key: 'metric', label: '指标' },
    { key: 'value', label: '数值' },
  ])
}

async function loadPinnedReports() {
  await reportsStore.loadList()
  const pinned = reportsStore.list.filter((r) => r.is_pinned)
  for (const report of pinned) {
    try {
      const data = await reportsStore.runReport(report.id)
      pinnedReportData.value[report.id] = data
    } catch (_e) {}
  }
  const pinnedCards = pinned.map((r) => ({
    id: `report-${r.id}`,
    type: 'pinned-report',
    reportId: r.id,
    title: r.name,
    colSpan: 1,
  }))
  const existingIds = new Set(cards.value.map((c) => c.id))
  pinnedCards.forEach((pc) => {
    if (!existingIds.has(pc.id)) cards.value.push(pc)
  })
}

onMounted(async () => {
  if (!isAdmin.value) {
    ElNotification({ title: '无权限', message: '仅管理员可访问数据看板。', type: 'warning' })
    router.push('/dashboard')
    return
  }
  await analyticsStore.loadDashboardLayout()
  initCards()
  await Promise.all([analyticsStore.loadPlatformData(), loadPinnedReports()])
})
</script>

<template>
  <main class="page-shell animated-in">
    <section class="analytics-wrap">
      <el-card class="section-card" shadow="never">
        <el-row justify="space-between" align="middle" :gutter="12">
          <el-col :xs="24" :sm="14">
            <h2 class="section-title" style="margin: 0">📊 数据看板</h2>
            <p style="margin: 6px 0 0; color: var(--text-sub)">
              平台级 KPI 总览 · 拖拽卡片可自定义排版
            </p>
          </el-col>
          <el-col :xs="24" :sm="10" style="text-align: right">
            <el-space wrap>
              <el-radio-group v-model="analyticsStore.timeWindow" size="default" @change="analyticsStore.setTimeWindow">
                <el-radio-button v-for="opt in timeWindowOptions" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </el-radio-button>
              </el-radio-group>
              <el-button @click="analyticsStore.loadPlatformData">🔄 刷新</el-button>
              <el-button type="success" plain @click="exportDashboardCSV">📥 导出 CSV</el-button>
              <el-button @click="resetLayout">↺ 重置布局</el-button>
              <el-button type="primary" @click="router.push('/reports/build')">➕ 新建报表</el-button>
              <el-button @click="router.push('/reports')">📋 我的报表</el-button>
              <el-button @click="router.push('/dashboard')">← 返回</el-button>
            </el-space>
          </el-col>
        </el-row>
      </el-card>

      <el-skeleton :loading="analyticsStore.loading" animated :rows="6">
        <template #default>
          <div class="dashboard-grid">
            <div
              v-for="card in cards"
              :key="card.id"
              class="dashboard-card"
              :class="{ 'drag-over': dragOverId === card.id, dragging: draggedCard?.id === card.id, 'col-span-2': card.colSpan === 2 }"
              draggable="true"
              @dragstart="onDragStart($event, card)"
              @dragover="onDragOver($event, card.id)"
              @dragleave="onDragLeave"
              @drop="onDrop($event, card)"
              @dragend="onDragEnd"
            >
              <div class="card-header">
                <span class="drag-handle">⋮⋮</span>
                <strong>{{ card.title }}</strong>
                <el-button v-if="card.type !== 'kpis'" link size="small" type="danger" @click="removeCard(card.id)">移除</el-button>
              </div>

              <div v-if="card.type === 'kpis'" class="kpi-grid">
                <div v-for="kpi in KPI_DEFS" :key="kpi.key" class="kpi-item" :style="{ '--accent': kpi.color }">
                  <div class="kpi-icon">{{ kpi.icon }}</div>
                  <div class="kpi-info">
                    <div class="kpi-label">{{ kpi.label }}</div>
                    <div class="kpi-value">{{ kpi.format(analyticsStore.kpis[kpi.key]) }}</div>
                  </div>
                </div>
              </div>

              <LineChart
                v-else-if="card.type === 'chart-recharge-trend'"
                title=""
                :items="analyticsStore.trends.recharge"
                label-key="period"
                :value-keys="['amount', 'count']"
                :value-labels="['充值金额', '充值笔数']"
                :colors="['#2b9f6c', '#2d73da']"
                :format-value="(v) => Number(v).toFixed(0)"
              />

              <LineChart
                v-else-if="card.type === 'chart-consumption-trend'"
                title=""
                :items="analyticsStore.trends.consumption"
                label-key="period"
                :value-keys="['amount', 'count']"
                :value-labels="['消费金额', '消费笔数']"
                :colors="['#8b5cf6', '#f59e0b']"
                :format-value="(v) => Number(v).toFixed(0)"
              />

              <AreaChart
                v-else-if="card.type === 'chart-user-growth'"
                title=""
                :items="analyticsStore.trends.user_growth"
                label-key="period"
                value-key="count"
                color="#06b6d4"
                :format-value="(v) => Number(v).toFixed(0)"
              />

              <PieChart
                v-else-if="card.type === 'chart-recharge-channel'"
                title=""
                :items="rechargeByChannelItems"
                donut
                :format-value="(v) => `¥${v}`"
              />

              <PieChart
                v-else-if="card.type === 'chart-consumption-category'"
                title=""
                :items="consumptionByCategoryItems"
                donut
                :format-value="(v) => `¥${v}`"
              />

              <SimpleBarChart
                v-else-if="card.type === 'chart-users-by-role'"
                title=""
                :items="usersByRoleItems"
                color="#8b5cf6"
              />

              <div v-else-if="card.type === 'pinned-report'" class="pinned-report-wrap">
                <PinnedReportPreview
                  :report="reportsStore.list.find(r => r.id === card.reportId)"
                  :data="pinnedReportData[card.reportId]"
                />
              </div>

              <div v-else class="viz-empty">未知卡片类型</div>
            </div>
          </div>
        </template>
      </el-skeleton>
    </section>
  </main>
</template>

<style scoped>
.analytics-wrap {
  max-width: 1400px;
  margin: 0 auto;
  display: grid;
  gap: 18px;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
}

.dashboard-card {
  border-radius: 16px;
  padding: 12px;
  background: var(--card-bg);
  box-shadow: var(--shadow-soft);
  border: 2px solid transparent;
  transition: border-color 0.2s, transform 0.2s;
  cursor: grab;
}

.dashboard-card.col-span-2 {
  grid-column: span 2;
}

.dashboard-card.drag-over {
  border-color: var(--brand);
  background: rgba(35, 103, 209, 0.05);
}

.dashboard-card.dragging {
  opacity: 0.5;
  transform: scale(0.98);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  font-size: 14px;
  color: var(--text-main);
}

.drag-handle {
  color: #b4bed1;
  cursor: grab;
  user-select: none;
  font-size: 14px;
  letter-spacing: -2px;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.kpi-item {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 14px;
  border-radius: 12px;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(255, 255, 255, 0.6) 100%);
  border-left: 4px solid var(--accent);
}

.kpi-icon {
  font-size: 28px;
  line-height: 1;
}

.kpi-label {
  font-size: 13px;
  color: var(--text-sub);
}

.kpi-value {
  font-size: 24px;
  font-weight: 800;
  color: var(--text-main);
  margin-top: 2px;
}

.viz-empty {
  color: var(--text-sub);
  font-size: 13px;
  padding: 20px;
  text-align: center;
}

@media (max-width: 960px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
  .dashboard-card.col-span-2 {
    grid-column: span 1;
  }
  .kpi-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
