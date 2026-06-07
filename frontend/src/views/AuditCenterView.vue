<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import { Download, View, Warning, Clock, User } from '@element-plus/icons-vue'

import { useAuthStore } from '../stores/auth'
import http from '../utils/http'

const router = useRouter()
const authStore = useAuthStore()

const activeTab = ref('overview')
const loading = ref(false)
const metaData = ref({ categories: [], actions: [], statuses: [] })

function formatDateTime(value) {
  if (!value) return '--'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
  }).format(date)
}

function getCategoryLabel(key) {
  const item = metaData.value.categories.find(c => c.key === key)
  return item ? item.label : key
}

function getActionLabel(key) {
  const item = metaData.value.actions.find(a => a.key === key)
  return item ? item.label : key
}

function getStatusLabel(key) {
  const item = metaData.value.statuses.find(s => s.key === key)
  return item ? item.label : key
}

function getStatusTagType(status) {
  const map = { success: 'success', failed: 'danger' }
  return map[status] || 'info'
}

function getCategoryTagType(category) {
  const map = {
    user: 'primary',
    role: 'warning',
    order: 'success',
    wallet: 'danger',
    auth: 'warning',
    config: 'info',
    data: '',
    other: 'info',
  }
  return map[category] || ''
}

async function loadMetaData() {
  try {
    const { data } = await http.get('/audit/meta/')
    metaData.value = data
  } catch (_e) {}
}

// ============ 总览 ============
const overview = reactive({
  summary: {},
  byCategory: [],
  recentLogs: [],
})
const overviewLoading = ref(false)

async function loadOverview() {
  overviewLoading.value = true
  try {
    const { data } = await http.get('/audit/overview/')
    overview.summary = data.summary || {}
    overview.byCategory = data.by_category || []
    overview.recentLogs = data.recent_logs || []
  } finally {
    overviewLoading.value = false
  }
}

// ============ 审计日志列表 ============
const logList = ref([])
const logTotal = ref(0)
const logLoading = ref(false)
const logFilters = reactive({
  keyword: '',
  category: '',
  action: '',
  status: '',
  operator_username: '',
  target_type: '',
  target_id: '',
  ip_address: '',
  is_suspicious: '',
  start_date: '',
  end_date: '',
  page: 1,
  page_size: 20,
})

async function loadLogs() {
  logLoading.value = true
  try {
    const params = { ...logFilters }
    if (!params.is_suspicious) delete params.is_suspicious
    if (!params.start_date) delete params.start_date
    if (!params.end_date) delete params.end_date
    const { data } = await http.get('/audit/logs/', { params })
    logList.value = data.items || []
    logTotal.value = data.total || 0
  } finally {
    logLoading.value = false
  }
}

function resetLogFilters() {
  logFilters.keyword = ''
  logFilters.category = ''
  logFilters.action = ''
  logFilters.status = ''
  logFilters.operator_username = ''
  logFilters.target_type = ''
  logFilters.target_id = ''
  logFilters.ip_address = ''
  logFilters.is_suspicious = ''
  logFilters.start_date = ''
  logFilters.end_date = ''
  logFilters.page = 1
  loadLogs()
}

const selectedLog = ref(null)
const logDetailVisible = ref(false)

function viewLogDetail(log) {
  selectedLog.value = log
  logDetailVisible.value = true
}

// ============ 可疑行为 ============
const suspiciousData = reactive({
  stats: {},
  items: [],
})
const suspiciousLoading = ref(false)
const suspiciousHours = ref(24)

async function loadSuspicious() {
  suspiciousLoading.value = true
  try {
    const { data } = await http.get('/audit/suspicious/', { params: { hours: suspiciousHours.value } })
    suspiciousData.stats = data.stats || {}
    suspiciousData.items = data.items || []
  } finally {
    suspiciousLoading.value = false
  }
}

// ============ 操作回放 ============
const replayMode = ref('user')
const replayTargetId = ref('')
const replayTargetType = ref('')
const replayTimeline = ref([])
const replayLoading = ref(false)
const replayCount = ref(0)

async function doReplay() {
  if (!replayTargetId.value) {
    ElMessage.warning('请输入目标 ID')
    return
  }
  replayLoading.value = true
  try {
    const params = {
      mode: replayMode.value,
      target_id: replayTargetId.value,
    }
    if (replayMode.value !== 'user' && replayTargetType.value) {
      params.target_type = replayTargetType.value
    }
    const { data } = await http.get('/audit/replay/', { params })
    replayTimeline.value = data.timeline || []
    replayCount.value = data.count || 0
  } finally {
    replayLoading.value = false
  }
}

// ============ 审计报表 ============
const reportData = reactive({
  summary: {},
  byCategory: [],
  byAction: [],
  byOperator: [],
  byStatus: [],
  trend: [],
  suspicious: {},
})
const reportLoading = ref(false)
const reportPeriod = ref('week')

async function loadReport() {
  reportLoading.value = true
  try {
    const { data } = await http.get('/audit/report/', { params: { period: reportPeriod.value } })
    reportData.summary = data.summary || {}
    reportData.byCategory = data.by_category || []
    reportData.byAction = data.by_action || []
    reportData.byOperator = data.by_operator || []
    reportData.byStatus = data.by_status || []
    reportData.trend = data.trend || []
    reportData.suspicious = data.suspicious || {}
  } finally {
    reportLoading.value = false
  }
}

const reportCategoryLabels = computed(() => reportData.byCategory.map(i => i.category_display || i.category))
const reportCategoryValues = computed(() => reportData.byCategory.map(i => i.count))

// ============ 导出 ============
async function doExport(format = 'csv') {
  try {
    await ElMessageBox.confirm(
      '确定要导出当前筛选条件下的审计日志吗？最多导出 10000 条。',
      '导出确认',
      { confirmButtonText: '导出', cancelButtonText: '取消', type: 'info' },
    )
  } catch (_e) { return }

  const params = {
    format,
    keyword: logFilters.keyword,
    category: logFilters.category,
    action: logFilters.action,
    status: logFilters.status,
    operator_username: logFilters.operator_username,
    target_type: logFilters.target_type,
    target_id: logFilters.target_id,
    ip_address: logFilters.ip_address,
  }
  if (logFilters.is_suspicious) params.is_suspicious = logFilters.is_suspicious
  if (logFilters.start_date) params.start_date = logFilters.start_date
  if (logFilters.end_date) params.end_date = logFilters.end_date

  const queryStr = new URLSearchParams(params).toString()
  const token = localStorage.getItem('access_token') || ''
  const url = `/api/audit/export/?${queryStr}`

  if (format === 'json') {
    try {
      const headers = {}
      if (token) headers.Authorization = `Bearer ${token}`
      const resp = await fetch(url, { headers })
      const blob = await resp.blob()
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = `audit_logs_${Date.now()}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
    } catch (e) {
      window.open(url, '_blank')
    }
  } else {
    window.open(url, '_blank')
  }
  ElNotification({ title: '导出已开始', message: '审计日志导出中，请稍候', type: 'success' })
}

onMounted(async () => {
  if (!authStore.user) {
    try {
      await authStore.fetchMe()
    } catch (_error) {
      authStore.clearSession()
      await router.push('/login')
      return
    }
  }
  if (authStore.user?.profile?.role !== 'admin') {
    ElMessage.warning('仅管理员可访问')
    await router.push('/dashboard')
    return
  }
  await loadMetaData()
  await loadOverview()
})
</script>

<template>
  <main class="page-shell animated-in">
    <el-card class="section-card" shadow="never">
      <el-row justify="space-between" align="middle" :gutter="12">
        <el-col :xs="24" :sm="16">
          <h2 class="section-title">🛡️ 审计中台</h2>
          <p style="margin: 0; color: var(--text-sub)">
            全平台关键操作审计日志，支持多维筛选、时间线回放、可疑行为检测、统计报表与导出。
          </p>
        </el-col>
        <el-col :xs="24" :sm="8" style="text-align: right">
          <el-space>
            <el-button type="primary" :icon="Download" plain @click="doExport('csv')">导出 CSV</el-button>
            <el-button @click="router.push('/dashboard')">返回首页</el-button>
          </el-space>
        </el-col>
      </el-row>
    </el-card>

    <el-card class="section-card" shadow="never">
      <el-tabs v-model="activeTab" type="border-card">
        <!-- ============ 总览 Tab ============ -->
        <el-tab-pane label="📊 总览" name="overview">
          <el-row :gutter="16" style="margin-bottom: 20px">
            <el-col :xs="12" :sm="6">
              <el-card shadow="hover" v-loading="overviewLoading">
                <div style="color: var(--text-sub); font-size: 12px">审计日志总数</div>
                <div style="font-size: 24px; font-weight: 700; margin-top: 4px">{{ overview.summary.total_logs || 0 }}</div>
              </el-card>
            </el-col>
            <el-col :xs="12" :sm="6">
              <el-card shadow="hover" v-loading="overviewLoading">
                <div style="color: var(--text-sub); font-size: 12px">近 24 小时</div>
                <div style="font-size: 24px; font-weight: 700; margin-top: 4px; color: #409eff">
                  {{ overview.summary.last_24h_count || 0 }}
                </div>
              </el-card>
            </el-col>
            <el-col :xs="12" :sm="6">
              <el-card shadow="hover" v-loading="overviewLoading">
                <div style="color: var(--text-sub); font-size: 12px">可疑行为(累计)</div>
                <div style="font-size: 24px; font-weight: 700; margin-top: 4px; color: #e6a23c">
                  {{ overview.summary.suspicious_total || 0 }}
                </div>
              </el-card>
            </el-col>
            <el-col :xs="12" :sm="6">
              <el-card shadow="hover" v-loading="overviewLoading">
                <div style="color: var(--text-sub); font-size: 12px">失败操作(累计)</div>
                <div style="font-size: 24px; font-weight: 700; margin-top: 4px; color: #f56c6c">
                  {{ overview.summary.failed_total || 0 }}
                </div>
              </el-card>
            </el-col>
          </el-row>

          <el-row :gutter="16">
            <el-col :xs="24" :md="8">
              <el-card shadow="never">
                <h4 style="margin-top: 0">📁 操作分类分布(近 7 天)</h4>
                <el-table :data="overview.byCategory" size="small" v-loading="overviewLoading">
                  <el-table-column prop="label" label="分类" />
                  <el-table-column prop="count" label="次数" width="100" align="right" />
                </el-table>
              </el-card>
            </el-col>
            <el-col :xs="24" :md="16">
              <el-card shadow="never">
                <el-row justify="space-between" align="middle">
                  <el-col><h4 style="margin: 0">🕒 最近操作</h4></el-col>
                  <el-col><el-button link type="primary" @click="activeTab = 'logs'">查看全部 →</el-button></el-col>
                </el-row>
                <el-table :data="overview.recentLogs" size="small" v-loading="overviewLoading" style="margin-top: 12px">
                  <el-table-column label="时间" width="160">
                    <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
                  </el-table-column>
                  <el-table-column label="操作人" width="120" prop="operator_username" />
                  <el-table-column label="分类" width="100">
                    <template #default="{ row }">
                      <el-tag :type="getCategoryTagType(row.category)" size="small" effect="plain">
                        {{ getCategoryLabel(row.category) }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="动作">
                    <template #default="{ row }">{{ getActionLabel(row.action) }}</template>
                  </el-table-column>
                  <el-table-column label="目标" min-width="160" show-overflow-tooltip prop="target_display" />
                  <el-table-column label="状态" width="80">
                    <template #default="{ row }">
                      <el-tag :type="getStatusTagType(row.status)" size="small">{{ getStatusLabel(row.status) }}</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="可疑" width="60" align="center">
                    <template #default="{ row }">
                      <el-icon v-if="row.is_suspicious" style="color: #e6a23c"><Warning /></el-icon>
                    </template>
                  </el-table-column>
                </el-table>
              </el-card>
            </el-col>
          </el-row>
        </el-tab-pane>

        <!-- ============ 审计日志 Tab ============ -->
        <el-tab-pane label="📋 审计日志" name="logs">
          <el-card shadow="never" style="margin-bottom: 16px">
            <el-row :gutter="12" align="middle">
              <el-col :xs="12" :sm="6" style="margin-bottom: 10px">
                <el-input v-model="logFilters.keyword" placeholder="关键字搜索" clearable @keyup.enter="loadLogs" @clear="loadLogs" />
              </el-col>
              <el-col :xs="12" :sm="4" style="margin-bottom: 10px">
                <el-select v-model="logFilters.category" placeholder="操作分类" clearable style="width: 100%" @change="loadLogs">
                  <el-option v-for="c in metaData.categories" :key="c.key" :label="c.label" :value="c.key" />
                </el-select>
              </el-col>
              <el-col :xs="12" :sm="4" style="margin-bottom: 10px">
                <el-select v-model="logFilters.action" placeholder="操作动作" clearable style="width: 100%" @change="loadLogs">
                  <el-option v-for="a in metaData.actions" :key="a.key" :label="a.label" :value="a.key" />
                </el-select>
              </el-col>
              <el-col :xs="12" :sm="4" style="margin-bottom: 10px">
                <el-select v-model="logFilters.status" placeholder="状态" clearable style="width: 100%" @change="loadLogs">
                  <el-option v-for="s in metaData.statuses" :key="s.key" :label="s.label" :value="s.key" />
                </el-select>
              </el-col>
              <el-col :xs="12" :sm="4" style="margin-bottom: 10px">
                <el-input v-model="logFilters.operator_username" placeholder="操作人" clearable @keyup.enter="loadLogs" @clear="loadLogs" />
              </el-col>
              <el-col :xs="12" :sm="4" style="margin-bottom: 10px">
                <el-input v-model="logFilters.ip_address" placeholder="IP地址" clearable @keyup.enter="loadLogs" @clear="loadLogs" />
              </el-col>
              <el-col :xs="12" :sm="4" style="margin-bottom: 10px">
                <el-select v-model="logFilters.is_suspicious" placeholder="是否可疑" clearable style="width: 100%" @change="loadLogs">
                  <el-option label="仅可疑" value="true" />
                  <el-option label="仅正常" value="false" />
                </el-select>
              </el-col>
              <el-col :xs="12" :sm="4" style="margin-bottom: 10px">
                <el-input v-model="logFilters.target_id" placeholder="目标对象ID" clearable @keyup.enter="loadLogs" @clear="loadLogs" />
              </el-col>
              <el-col :xs="12" :sm="4" style="margin-bottom: 10px">
                <el-date-picker
                  v-model="logFilters.start_date"
                  type="date"
                  placeholder="开始日期"
                  value-format="YYYY-MM-DD"
                  style="width: 100%"
                  @change="loadLogs"
                />
              </el-col>
              <el-col :xs="12" :sm="4" style="margin-bottom: 10px">
                <el-date-picker
                  v-model="logFilters.end_date"
                  type="date"
                  placeholder="结束日期"
                  value-format="YYYY-MM-DD"
                  style="width: 100%"
                  @change="loadLogs"
                />
              </el-col>
              <el-col :xs="24" style="text-align: right; margin-bottom: 10px">
                <el-space>
                  <el-button type="primary" @click="loadLogs">查询</el-button>
                  <el-button @click="resetLogFilters">重置</el-button>
                  <el-button type="success" :icon="Download" @click="doExport('csv')">导出</el-button>
                </el-space>
              </el-col>
            </el-row>
          </el-card>

          <el-table
            :data="logList"
            stripe
            border
            v-loading="logLoading"
            empty-text="暂无审计日志"
            @row-click="viewLogDetail"
            style="cursor: pointer"
          >
            <el-table-column label="ID" width="70" align="center">
              <template #default="{ row }">#{{ row.id }}</template>
            </el-table-column>
            <el-table-column label="时间" width="160">
              <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作人" width="110" prop="operator_username" />
            <el-table-column label="角色" width="80" prop="operator_role" />
            <el-table-column label="分类" width="100">
              <template #default="{ row }">
                <el-tag :type="getCategoryTagType(row.category)" size="small" effect="plain">
                  {{ getCategoryLabel(row.category) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="动作" width="100">
              <template #default="{ row }">{{ getActionLabel(row.action) }}</template>
            </el-table-column>
            <el-table-column label="目标对象" min-width="150" show-overflow-tooltip>
              <template #default="{ row }">
                <div v-if="row.target_display">{{ row.target_display }}</div>
                <div v-else style="color: var(--text-sub)">{{ row.target_type }} #{{ row.target_id }}</div>
              </template>
            </el-table-column>
            <el-table-column label="IP" width="120" prop="ip_address" />
            <el-table-column label="状态" width="70">
              <template #default="{ row }">
                <el-tag :type="getStatusTagType(row.status)" size="small">{{ getStatusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="耗时" width="80" align="right">
              <template #default="{ row }">{{ row.duration_ms }}ms</template>
            </el-table-column>
            <el-table-column label="可疑" width="60" align="center">
              <template #default="{ row }">
                <el-icon v-if="row.is_suspicious" style="color: #e6a23c"><Warning /></el-icon>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="70" fixed="right">
              <template #default="{ row }">
                <el-button size="small" link type="primary" @click.stop="viewLogDetail(row)">
                  <el-icon><View /></el-icon>
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <div style="margin-top: 16px; text-align: right">
            <el-pagination
              v-model:current-page="logFilters.page"
              v-model:page-size="logFilters.page_size"
              :page-sizes="[10, 20, 50, 100]"
              :total="logTotal"
              layout="total, sizes, prev, pager, next"
              @size-change="loadLogs"
              @current-change="loadLogs"
            />
          </div>
        </el-tab-pane>

        <!-- ============ 可疑行为 Tab ============ -->
        <el-tab-pane label="⚠️ 可疑行为" name="suspicious">
          <el-card shadow="never" style="margin-bottom: 16px">
            <el-row align="middle" :gutter="12">
              <el-col :span="4">
                <el-select v-model="suspiciousHours" style="width: 100%" @change="loadSuspicious">
                  <el-option :value="1" label="近 1 小时" />
                  <el-option :value="6" label="近 6 小时" />
                  <el-option :value="24" label="近 24 小时" />
                  <el-option :value="72" label="近 3 天" />
                  <el-option :value="168" label="近 7 天" />
                </el-select>
              </el-col>
              <el-col :span="20" style="text-align: right">
                <el-button type="primary" @click="loadSuspicious">刷新</el-button>
              </el-col>
            </el-row>
          </el-card>

          <el-row :gutter="16" style="margin-bottom: 16px">
            <el-col :xs="12" :sm="6">
              <el-card shadow="hover">
                <div style="color: var(--text-sub); font-size: 12px">可疑事件总数</div>
                <div style="font-size: 28px; font-weight: 700; color: #e6a23c; margin-top: 4px">
                  {{ suspiciousData.stats.total_suspicious || 0 }}
                </div>
              </el-card>
            </el-col>
          </el-row>

          <el-row :gutter="16" v-if="suspiciousData.stats.top_users && suspiciousData.stats.top_users.length">
            <el-col :xs="24" :md="8">
              <el-card shadow="never">
                <h4 style="margin-top: 0">🏆 高风险用户 TOP 10</h4>
                <el-table :data="suspiciousData.stats.top_users" size="small" v-loading="suspiciousLoading">
                  <el-table-column label="排名" type="index" width="60" />
                  <el-table-column label="用户" prop="operator_username" />
                  <el-table-column label="可疑次数" width="100" align="right" prop="count" />
                </el-table>
              </el-card>
            </el-col>
            <el-col :xs="24" :md="16">
              <el-card shadow="never">
                <h4 style="margin-top: 0">📋 可疑行为列表</h4>
                <el-table :data="suspiciousData.items" stripe border size="small" v-loading="suspiciousLoading">
                  <el-table-column label="时间" width="160">
                    <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
                  </el-table-column>
                  <el-table-column label="操作人" width="110" prop="operator_username" />
                  <el-table-column label="分类" width="90">
                    <template #default="{ row }">{{ getCategoryLabel(row.category) }}</template>
                  </el-table-column>
                  <el-table-column label="动作" width="90">
                    <template #default="{ row }">{{ getActionLabel(row.action) }}</template>
                  </el-table-column>
                  <el-table-column label="目标" min-width="140" show-overflow-tooltip prop="target_display" />
                  <el-table-column label="IP" width="120" prop="ip_address" />
                  <el-table-column label="可疑原因" min-width="200">
                    <template #default="{ row }">
                      <el-tag
                        v-for="(r, i) in (row.suspicious_reasons || [])"
                        :key="i"
                        type="warning"
                        effect="light"
                        size="small"
                        style="margin: 2px"
                      >
                        {{ r }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" width="70">
                    <template #default="{ row }">
                      <el-button size="small" link type="primary" @click="viewLogDetail(row)">详情</el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </el-card>
            </el-col>
          </el-row>
        </el-tab-pane>

        <!-- ============ 操作回放 Tab ============ -->
        <el-tab-pane label="🎞️ 操作回放" name="replay">
          <el-card shadow="never" style="margin-bottom: 16px">
            <el-row align="middle" :gutter="12">
              <el-col :xs="24" :sm="5">
                <el-radio-group v-model="replayMode">
                  <el-radio value="user">按用户</el-radio>
                  <el-radio value="target">按对象</el-radio>
                </el-radio-group>
              </el-col>
              <el-col :xs="24" :sm="5">
                <el-input
                  v-model="replayTargetId"
                  :placeholder="replayMode === 'user' ? '用户 ID' : '目标对象 ID'"
                  @keyup.enter="doReplay"
                />
              </el-col>
              <el-col v-if="replayMode === 'target'" :xs="24" :sm="5">
                <el-input v-model="replayTargetType" placeholder="目标对象类型(如 auth.user)" @keyup.enter="doReplay" />
              </el-col>
              <el-col :xs="24" :sm="9" style="text-align: right">
                <el-button type="primary" @click="doReplay" :loading="replayLoading">生成回放</el-button>
              </el-col>
            </el-row>
          </el-card>

          <el-alert
            v-if="replayCount > 0"
            :title="`共找到 ${replayCount} 条相关操作，按时间升序排列`"
            type="info"
            show-icon
            style="margin-bottom: 16px"
          />

          <div v-if="replayTimeline.length" v-loading="replayLoading">
            <el-timeline>
              <el-timeline-item
                v-for="item in replayTimeline"
                :key="item.id"
                :timestamp="formatDateTime(item.time)"
                :type="item.is_suspicious ? 'warning' : 'primary'"
                :hollow="item.status !== 'success'"
                size="large"
              >
                <el-card :shadow="item.is_suspicious ? 'always' : 'never'" :style="item.is_suspicious ? 'border-color: #e6a23c' : ''">
                  <el-row justify="space-between" align="middle">
                    <el-col>
                      <el-space>
                        <strong>{{ item.operator }}</strong>
                        <el-tag size="small">{{ item.category }}</el-tag>
                        <el-tag :type="item.status === 'success' ? 'success' : 'danger'" size="small">
                          {{ item.action }}
                        </el-tag>
                        <el-tag v-if="item.is_suspicious" type="warning" effect="dark" size="small">可疑</el-tag>
                      </el-space>
                    </el-col>
                  </el-row>
                  <p style="margin: 8px 0; color: var(--text-sub)">目标: {{ item.target || '-' }}</p>
                  <el-row :gutter="12" v-if="item.before && Object.keys(item.before).length">
                    <el-col :span="12">
                      <div style="color: #909399; font-size: 12px; margin-bottom: 4px">变更前</div>
                      <pre style="background: #f5f7fa; padding: 8px; margin: 0; border-radius: 4px; font-size: 12px; max-height: 120px; overflow: auto">{{ JSON.stringify(item.before, null, 2) }}</pre>
                    </el-col>
                    <el-col :span="12">
                      <div style="color: #67c23a; font-size: 12px; margin-bottom: 4px">变更后</div>
                      <pre style="background: #f0f9eb; padding: 8px; margin: 0; border-radius: 4px; font-size: 12px; max-height: 120px; overflow: auto">{{ JSON.stringify(item.after, null, 2) }}</pre>
                    </el-col>
                  </el-row>
                  <p v-if="item.remark" style="margin-top: 8px; color: var(--text-sub); font-size: 13px">
                    💬 {{ item.remark }}
                  </p>
                </el-card>
              </el-timeline-item>
            </el-timeline>
          </div>
          <el-empty v-else-if="!replayLoading" description="输入目标 ID 后点击生成回放" />
        </el-tab-pane>

        <!-- ============ 审计报表 Tab ============ -->
        <el-tab-pane label="📈 审计报表" name="report">
          <el-card shadow="never" style="margin-bottom: 16px">
            <el-row align="middle" :gutter="12">
              <el-col :span="6">
                <el-radio-group v-model="reportPeriod" @change="loadReport">
                  <el-radio value="week">周报</el-radio>
                  <el-radio value="month">月报</el-radio>
                </el-radio-group>
              </el-col>
              <el-col :span="18" style="text-align: right">
                <el-button type="primary" @click="loadReport" :loading="reportLoading">刷新报表</el-button>
              </el-col>
            </el-row>
          </el-card>

          <el-row :gutter="16" style="margin-bottom: 16px">
            <el-col :xs="12" :sm="6">
              <el-card shadow="hover" v-loading="reportLoading">
                <div style="color: var(--text-sub); font-size: 12px">总操作数</div>
                <div style="font-size: 24px; font-weight: 700; margin-top: 4px">
                  {{ reportData.summary.total_count || 0 }}
                </div>
              </el-card>
            </el-col>
            <el-col :xs="12" :sm="6">
              <el-card shadow="hover" v-loading="reportLoading">
                <div style="color: var(--text-sub); font-size: 12px">成功操作</div>
                <div style="font-size: 24px; font-weight: 700; margin-top: 4px; color: #67c23a">
                  {{ reportData.summary.success_count || 0 }}
                </div>
              </el-card>
            </el-col>
            <el-col :xs="12" :sm="6">
              <el-card shadow="hover" v-loading="reportLoading">
                <div style="color: var(--text-sub); font-size: 12px">失败操作</div>
                <div style="font-size: 24px; font-weight: 700; margin-top: 4px; color: #f56c6c">
                  {{ reportData.summary.failed_count || 0 }}
                </div>
              </el-card>
            </el-col>
            <el-col :xs="12" :sm="6">
              <el-card shadow="hover" v-loading="reportLoading">
                <div style="color: var(--text-sub); font-size: 12px">可疑事件</div>
                <div style="font-size: 24px; font-weight: 700; margin-top: 4px; color: #e6a23c">
                  {{ reportData.summary.suspicious_count || 0 }}
                </div>
              </el-card>
            </el-col>
          </el-row>

          <el-row :gutter="16">
            <el-col :xs="24" :md="8">
              <el-card shadow="never" v-loading="reportLoading">
                <h4 style="margin-top: 0">📊 操作分类统计</h4>
                <el-table :data="reportData.byCategory" size="small">
                  <el-table-column prop="category_display" label="分类" />
                  <el-table-column prop="count" label="次数" width="80" align="right" />
                  <el-table-column label="占比" width="100">
                    <template #default="{ row }">
                      {{ ((row.count / (reportData.summary.total_count || 1)) * 100).toFixed(1) }}%
                    </template>
                  </el-table-column>
                </el-table>
              </el-card>
            </el-col>
            <el-col :xs="24" :md="8">
              <el-card shadow="never" v-loading="reportLoading">
                <h4 style="margin-top: 0">🔧 Top 操作动作</h4>
                <el-table :data="reportData.byAction.slice(0, 10)" size="small">
                  <el-table-column prop="action_display" label="动作" />
                  <el-table-column prop="count" label="次数" width="80" align="right" />
                </el-table>
              </el-card>
            </el-col>
            <el-col :xs="24" :md="8">
              <el-card shadow="never" v-loading="reportLoading">
                <h4 style="margin-top: 0">👥 活跃操作人 TOP</h4>
                <el-table :data="reportData.byOperator.slice(0, 10)" size="small">
                  <el-table-column label="排名" type="index" width="50" />
                  <el-table-column prop="operator_username" label="用户" />
                  <el-table-column prop="operator_role" label="角色" width="70" />
                  <el-table-column prop="count" label="次数" width="70" align="right" />
                </el-table>
              </el-card>
            </el-col>
          </el-row>

          <el-card shadow="never" style="margin-top: 16px" v-loading="reportLoading">
            <h4 style="margin-top: 0">📈 操作趋势</h4>
            <el-table :data="reportData.trend" size="small">
              <el-table-column prop="period" label="周期" />
              <el-table-column prop="count" label="操作次数" align="right" />
            </el-table>
          </el-card>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- ============ 日志详情 Dialog ============ -->
    <el-dialog v-model="logDetailVisible" title="审计日志详情" width="720px" destroy-on-close>
      <el-descriptions v-if="selectedLog" :column="2" border>
        <el-descriptions-item label="日志ID">#{{ selectedLog.id }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatDateTime(selectedLog.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="操作人">{{ selectedLog.operator_username }} ({{ selectedLog.operator_role }})</el-descriptions-item>
        <el-descriptions-item label="IP地址">{{ selectedLog.ip_address || '-' }}</el-descriptions-item>
        <el-descriptions-item label="分类">
          <el-tag :type="getCategoryTagType(selectedLog.category)">{{ getCategoryLabel(selectedLog.category) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="动作">{{ getActionLabel(selectedLog.action) }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusTagType(selectedLog.status)">{{ getStatusLabel(selectedLog.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="耗时">{{ selectedLog.duration_ms }} ms</el-descriptions-item>
        <el-descriptions-item label="目标类型">{{ selectedLog.target_type || '-' }}</el-descriptions-item>
        <el-descriptions-item label="目标ID">{{ selectedLog.target_id || '-' }}</el-descriptions-item>
        <el-descriptions-item label="目标描述" :span="2">{{ selectedLog.target_display || '-' }}</el-descriptions-item>
        <el-descriptions-item label="请求路径">{{ selectedLog.request_path || '-' }}</el-descriptions-item>
        <el-descriptions-item label="请求方法">{{ selectedLog.request_method || '-' }}</el-descriptions-item>
        <el-descriptions-item label="是否可疑" :span="2">
          <el-tag v-if="selectedLog.is_suspicious" type="warning">
            是 - {{ (selectedLog.suspicious_reasons || []).join('、') }}
          </el-tag>
          <span v-else>否</span>
        </el-descriptions-item>
        <el-descriptions-item label="备注" :span="2">{{ selectedLog.remark || '-' }}</el-descriptions-item>
        <el-descriptions-item v-if="selectedLog.error_message" label="错误信息" :span="2">
          <span style="color: #f56c6c">{{ selectedLog.error_message }}</span>
        </el-descriptions-item>
      </el-descriptions>
      <el-row v-if="selectedLog && (selectedLog.before_data && Object.keys(selectedLog.before_data).length || selectedLog.after_data && Object.keys(selectedLog.after_data).length)" :gutter="12" style="margin-top: 16px">
        <el-col :span="12">
          <div style="color: #909399; font-size: 13px; margin-bottom: 6px">📋 变更前数据</div>
          <pre style="background: #f5f7fa; padding: 12px; border-radius: 6px; max-height: 200px; overflow: auto">{{ JSON.stringify(selectedLog.before_data, null, 2) }}</pre>
        </el-col>
        <el-col :span="12">
          <div style="color: #67c23a; font-size: 13px; margin-bottom: 6px">✅ 变更后数据</div>
          <pre style="background: #f0f9eb; padding: 12px; border-radius: 6px; max-height: 200px; overflow: auto">{{ JSON.stringify(selectedLog.after_data, null, 2) }}</pre>
        </el-col>
      </el-row>
      <div v-if="selectedLog" style="margin-top: 16px; color: var(--text-sub); font-size: 12px">
        日志哈希: {{ selectedLog.hash_value || '-' }}
      </div>
      <template #footer>
        <el-button @click="logDetailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </main>
</template>

<style scoped>
pre {
  white-space: pre-wrap;
  word-wrap: break-word;
}
</style>
