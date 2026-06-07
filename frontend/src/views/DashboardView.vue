<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox, ElNotification } from 'element-plus'

import SimpleBarChart from '../components/SimpleBarChart.vue'
import { useAuthStore } from '../stores/auth'
import http from '../utils/http'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(true)
const actionLoading = ref(false)
const activeTab = ref('overview')

const dashboard = reactive({
  wallet: { balance: '0.00', is_frozen: false, frozen_reason: '' },
  summary: { total_recharge: '0.00', total_consumption: '0.00', pending_recharge_orders: 0 },
  recent_recharges: [],
  recent_consumptions: [],
})

const orderForm = reactive({
  amount: null,
  channel: 'alipay',
  submit_remark: '',
})

const orderFilters = reactive({
  status: '',
  user_id: '',
})

const orders = ref([])

const consumptionFilters = reactive({
  category: '',
  start_date: '',
  end_date: '',
})
const consumptions = ref([])
const consumptionStats = reactive({
  category_stats: [],
  daily_trend: [],
})

const walletLogs = ref([])
const announcements = ref([])
const notifications = reactive({
  unread_count: 0,
  items: [],
})

const adminUsers = ref([])
const adminUserFilters = reactive({
  keyword: '',
  role: '',
  is_active: '',
})

const announcementForm = reactive({
  title: '',
  content: '',
  is_active: true,
})

const isAdmin = computed(() => authStore.user?.profile?.role === 'admin')

const channelMap = {
  alipay: '支付宝',
  wechat: '微信支付',
  bank: '银行卡',
}

const orderStatusMap = {
  pending: { label: '待审核', type: 'warning' },
  approved: { label: '已通过', type: 'success' },
  rejected: { label: '已驳回', type: 'danger' },
}

const categoryMap = {
  water: '水费',
  electricity: '电费',
}

function formatMoney(value) {
  const amount = Number(value ?? 0)
  if (Number.isNaN(amount)) return '0.00'
  return amount.toFixed(2)
}

function formatDateTime(value) {
  if (!value) return '--'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(date)
}

function consumeStatsForCategory() {
  return consumptionStats.category_stats.map((item) => ({
    label: categoryMap[item.category] || item.category,
    value: formatMoney(item.total_cost),
  }))
}

function consumeStatsForTrend() {
  return consumptionStats.daily_trend.map((item) => ({
    label: item.day,
    value: formatMoney(item.total_cost),
  }))
}

async function loadDashboard() {
  const { data } = await http.get('/billing/dashboard/')
  Object.assign(dashboard, data)
}

async function loadOrders() {
  const params = {}
  if (orderFilters.status) params.status = orderFilters.status
  if (isAdmin.value && orderFilters.user_id) params.user_id = orderFilters.user_id
  const { data } = await http.get('/billing/recharge-orders/', { params })
  orders.value = data
}

async function submitRechargeOrder() {
  if (!orderForm.amount || Number(orderForm.amount) <= 0) {
    ElNotification({ title: '提交失败', message: '请输入有效金额。', type: 'warning' })
    return
  }

  actionLoading.value = true
  try {
    await http.post('/billing/recharge-orders/', orderForm)
    ElNotification({ title: '订单已提交', message: '请等待管理员审核。', type: 'success' })
    orderForm.amount = null
    orderForm.submit_remark = ''
    await Promise.all([loadOrders(), loadDashboard(), loadNotifications()])
  } finally {
    actionLoading.value = false
  }
}

async function reviewOrder(order, action) {
  const result = await ElMessageBox.prompt(
    action === 'approved' ? '请输入通过备注（可选）' : '请输入驳回原因',
    action === 'approved' ? '通过订单' : '驳回订单',
    {
      confirmButtonText: '提交',
      cancelButtonText: '取消',
      inputPlaceholder: '请输入审核备注',
    }
  ).catch(() => null)

  if (!result) return

  actionLoading.value = true
  try {
    await http.post(`/billing/recharge-orders/${order.id}/review/`, {
      action,
      review_remark: result.value || '',
    })
    ElNotification({ title: '审核完成', message: '订单状态已更新。', type: 'success' })
    await Promise.all([loadOrders(), loadDashboard(), loadNotifications()])
  } finally {
    actionLoading.value = false
  }
}

async function loadConsumptions() {
  const params = {}
  if (consumptionFilters.category) params.category = consumptionFilters.category
  if (consumptionFilters.start_date) params.start_date = consumptionFilters.start_date
  if (consumptionFilters.end_date) params.end_date = consumptionFilters.end_date

  const { data } = await http.get('/billing/consumptions/', { params })
  consumptions.value = data
}

async function loadConsumptionStats() {
  const params = {}
  if (consumptionFilters.start_date) params.start_date = consumptionFilters.start_date
  if (consumptionFilters.end_date) params.end_date = consumptionFilters.end_date
  const { data } = await http.get('/billing/consumptions/stats/', { params })
  Object.assign(consumptionStats, data)
}

async function loadWalletLogs() {
  const { data } = await http.get('/billing/wallet-logs/')
  walletLogs.value = data
}

async function loadAnnouncements() {
  const params = isAdmin.value ? { include_inactive: true } : {}
  const { data } = await http.get('/notices/announcements/', { params })
  announcements.value = data
}

async function publishAnnouncement() {
  if (!announcementForm.title.trim() || !announcementForm.content.trim()) {
    ElNotification({ title: '发布失败', message: '请填写公告标题和内容。', type: 'warning' })
    return
  }

  actionLoading.value = true
  try {
    const { data } = await http.post('/notices/announcements/', announcementForm)
    ElNotification({ title: '公告已发布', message: `已推送 ${data.push_count} 位用户。`, type: 'success' })
    announcementForm.title = ''
    announcementForm.content = ''
    announcementForm.is_active = true
    await loadAnnouncements()
  } finally {
    actionLoading.value = false
  }
}

async function loadNotifications() {
  const { data } = await http.get('/notices/notifications/')
  notifications.unread_count = data.unread_count
  notifications.items = data.items
}

async function markNotificationRead(notification) {
  await http.post('/notices/notifications/read/', { notification_id: notification.id })
  await loadNotifications()
}

async function markAllNotificationsRead() {
  await http.post('/notices/notifications/read/', { mark_all: true })
  await loadNotifications()
}

async function loadAdminUsers() {
  const params = {}
  if (adminUserFilters.keyword) params.keyword = adminUserFilters.keyword
  if (adminUserFilters.role) params.role = adminUserFilters.role
  if (adminUserFilters.is_active) params.is_active = adminUserFilters.is_active
  const { data } = await http.get('/auth/admin/users/', { params })
  adminUsers.value = data
}

async function updateUserRole(row, role) {
  await http.patch(`/auth/admin/users/${row.id}/`, { role })
  ElNotification({ title: '角色已更新', message: '用户角色修改成功。', type: 'success' })
  await loadAdminUsers()
}

async function updateUserStatus(row, value) {
  await http.patch(`/auth/admin/users/${row.id}/`, { is_active: value })
  ElNotification({ title: '账号状态已更新', message: '启用状态修改成功。', type: 'success' })
  await loadAdminUsers()
}

async function walletAction(row, action) {
  const result = await ElMessageBox.prompt(
    action === 'freeze' ? '请输入冻结原因' : '请输入解冻备注（可选）',
    action === 'freeze' ? '冻结账户' : '解冻账户',
    {
      confirmButtonText: '提交',
      cancelButtonText: '取消',
      inputPlaceholder: '请输入说明',
    }
  ).catch(() => null)

  if (!result) return

  await http.post(`/billing/wallets/${row.id}/action/`, {
    action,
    reason: result.value || '',
  })
  ElNotification({
    title: action === 'freeze' ? '账户已冻结' : '账户已解冻',
    message: '钱包状态更新成功。',
    type: 'success',
  })
  await Promise.all([loadAdminUsers(), loadWalletLogs()])
}

async function refreshAll() {
  loading.value = true
  try {
    const tasks = [loadDashboard(), loadOrders(), loadConsumptions(), loadConsumptionStats(), loadWalletLogs(), loadAnnouncements(), loadNotifications()]
    if (isAdmin.value) tasks.push(loadAdminUsers())
    await Promise.all(tasks)
  } finally {
    loading.value = false
  }
}

async function logout() {
  authStore.clearSession()
  await router.push('/login')
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

  activeTab.value = isAdmin.value ? 'orders' : 'overview'
  await refreshAll()
})
</script>

<template>
  <main class="page-shell animated-in">
    <section class="dashboard-wrap">
      <el-card class="section-card" shadow="never">
        <el-row justify="space-between" align="middle" :gutter="12">
          <el-col :xs="24" :sm="18">
            <h2 class="section-title">学生水电充值管理系统</h2>
            <p style="margin: 0; color: var(--text-sub)">
              当前身份：{{ isAdmin ? '管理员' : '学生' }} ｜ 未读通知：{{ notifications.unread_count }}
            </p>
          </el-col>
          <el-col :xs="24" :sm="6" style="text-align: right">
            <el-button style="margin-right: 8px" @click="refreshAll">刷新数据</el-button>
            <el-button type="danger" plain @click="logout">退出登录</el-button>
          </el-col>
        </el-row>
      </el-card>

      <el-skeleton :loading="loading" animated :rows="8">
        <template #template>
          <el-card class="section-card" shadow="never">
            <el-skeleton-item variant="h3" style="width: 40%" />
            <el-skeleton-item variant="text" style="width: 100%" />
            <el-skeleton-item variant="text" style="width: 100%" />
          </el-card>
        </template>

        <template #default>
          <section class="summary-grid">
            <article class="summary-card">
              <div class="label">账户余额</div>
              <div class="value">¥ {{ formatMoney(dashboard.wallet.balance) }}</div>
              <div class="summary-note">{{ dashboard.wallet.is_frozen ? '账户已冻结' : '账户可正常使用' }}</div>
            </article>
            <article class="summary-card">
              <div class="label">累计充值</div>
              <div class="value">¥ {{ formatMoney(dashboard.summary.total_recharge) }}</div>
              <div class="summary-note">待审核充值单：{{ dashboard.summary.pending_recharge_orders || 0 }}</div>
            </article>
            <article class="summary-card">
              <div class="label">累计消费</div>
              <div class="value">¥ {{ formatMoney(dashboard.summary.total_consumption) }}</div>
              <div class="summary-note">消息中心支持公告与订单提醒</div>
            </article>
          </section>

          <el-card class="section-card" shadow="never">
            <el-tabs v-model="activeTab">
              <el-tab-pane v-if="!isAdmin" label="总览" name="overview">
                <div class="form-grid">
                  <el-card class="section-card" shadow="never">
                    <h3 class="section-title">快速提交充值订单</h3>
                    <el-form label-position="top" @submit.prevent>
                      <el-form-item label="充值金额（元）">
                        <el-input-number v-model="orderForm.amount" :min="0" :precision="2" :step="10" style="width: 100%" />
                      </el-form-item>
                      <el-form-item label="充值渠道">
                        <el-select v-model="orderForm.channel" style="width: 100%">
                          <el-option label="支付宝" value="alipay" />
                          <el-option label="微信支付" value="wechat" />
                          <el-option label="银行卡" value="bank" />
                        </el-select>
                      </el-form-item>
                      <el-form-item label="备注">
                        <el-input v-model="orderForm.submit_remark" placeholder="请输入订单备注（可选）" />
                      </el-form-item>
                      <el-button type="primary" :loading="actionLoading" style="width: 100%" @click="submitRechargeOrder">提交充值订单</el-button>
                    </el-form>
                  </el-card>

                  <el-card class="section-card" shadow="never">
                    <h3 class="section-title">余额变动日志</h3>
                    <el-table :data="walletLogs.slice(0, 8)" stripe border empty-text="暂无余额日志">
                      <el-table-column label="时间" min-width="165">
                        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
                      </el-table-column>
                      <el-table-column prop="change_type" label="类型" min-width="100" />
                      <el-table-column label="变动" min-width="110">
                        <template #default="{ row }">{{ formatMoney(row.amount_delta) }}</template>
                      </el-table-column>
                    </el-table>
                  </el-card>
                </div>
              </el-tab-pane>

              <el-tab-pane :label="isAdmin ? '订单审核' : '充值订单'" name="orders">
                <el-row :gutter="12" style="margin-bottom: 12px">
                  <el-col :span="8">
                    <el-select v-model="orderFilters.status" style="width: 100%" placeholder="按状态筛选">
                      <el-option label="全部状态" value="" />
                      <el-option label="待审核" value="pending" />
                      <el-option label="已通过" value="approved" />
                      <el-option label="已驳回" value="rejected" />
                    </el-select>
                  </el-col>
                  <el-col v-if="isAdmin" :span="8">
                    <el-input v-model="orderFilters.user_id" placeholder="按用户ID筛选" clearable />
                  </el-col>
                  <el-col :span="8">
                    <el-button @click="loadOrders">查询订单</el-button>
                  </el-col>
                </el-row>

                <el-table :data="orders" stripe border empty-text="暂无订单记录">
                  <el-table-column prop="order_no" label="订单号" min-width="180" />
                  <el-table-column prop="user_name" label="用户" min-width="120" />
                  <el-table-column label="金额" min-width="100">
                    <template #default="{ row }">¥ {{ formatMoney(row.amount) }}</template>
                  </el-table-column>
                  <el-table-column label="渠道" min-width="100">
                    <template #default="{ row }">{{ channelMap[row.channel] || row.channel }}</template>
                  </el-table-column>
                  <el-table-column label="状态" min-width="110">
                    <template #default="{ row }">
                      <el-tag :type="orderStatusMap[row.status]?.type || 'info'" effect="plain">
                        {{ orderStatusMap[row.status]?.label || row.status }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="提交时间" min-width="165">
                    <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
                  </el-table-column>
                  <el-table-column v-if="isAdmin" label="操作" min-width="180" fixed="right">
                    <template #default="{ row }">
                      <el-space>
                        <el-button size="small" type="success" :disabled="row.status !== 'pending'" @click="reviewOrder(row, 'approved')">通过</el-button>
                        <el-button size="small" type="danger" :disabled="row.status !== 'pending'" @click="reviewOrder(row, 'rejected')">驳回</el-button>
                      </el-space>
                    </template>
                  </el-table-column>
                </el-table>
              </el-tab-pane>

              <el-tab-pane v-if="isAdmin" label="用户管理" name="users">
                <el-row :gutter="12" style="margin-bottom: 12px">
                  <el-col :span="8">
                    <el-input v-model="adminUserFilters.keyword" placeholder="搜索用户名/学号/手机号" clearable />
                  </el-col>
                  <el-col :span="6">
                    <el-select v-model="adminUserFilters.role" style="width: 100%" placeholder="角色筛选">
                      <el-option label="全部角色" value="" />
                      <el-option label="学生" value="student" />
                      <el-option label="管理员" value="admin" />
                    </el-select>
                  </el-col>
                  <el-col :span="6">
                    <el-select v-model="adminUserFilters.is_active" style="width: 100%" placeholder="状态筛选">
                      <el-option label="全部状态" value="" />
                      <el-option label="启用" value="true" />
                      <el-option label="禁用" value="false" />
                    </el-select>
                  </el-col>
                  <el-col :span="4"><el-button @click="loadAdminUsers">查询用户</el-button></el-col>
                </el-row>

                <el-table :data="adminUsers" stripe border empty-text="暂无用户数据">
                  <el-table-column prop="id" label="ID" width="70" />
                  <el-table-column prop="username" label="用户名" min-width="120" />
                  <el-table-column prop="email" label="邮箱" min-width="180" />
                  <el-table-column label="角色" min-width="140">
                    <template #default="{ row }">
                      <el-select :model-value="row.profile.role" size="small" @change="(val) => updateUserRole(row, val)">
                        <el-option label="学生" value="student" />
                        <el-option label="管理员" value="admin" />
                      </el-select>
                    </template>
                  </el-table-column>
                  <el-table-column label="启用" min-width="90">
                    <template #default="{ row }">
                      <el-switch :model-value="row.is_active" @change="(val) => updateUserStatus(row, val)" />
                    </template>
                  </el-table-column>
                  <el-table-column label="钱包余额" min-width="110">
                    <template #default="{ row }">¥ {{ formatMoney(row.balance) }}</template>
                  </el-table-column>
                  <el-table-column label="冻结状态" min-width="130">
                    <template #default="{ row }">
                      <el-tag :type="row.wallet_frozen ? 'danger' : 'success'" effect="plain">
                        {{ row.wallet_frozen ? '已冻结' : '正常' }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="钱包操作" min-width="170" fixed="right">
                    <template #default="{ row }">
                      <el-space>
                        <el-button size="small" type="danger" plain :disabled="row.wallet_frozen" @click="walletAction(row, 'freeze')">冻结</el-button>
                        <el-button size="small" type="success" plain :disabled="!row.wallet_frozen" @click="walletAction(row, 'unfreeze')">解冻</el-button>
                      </el-space>
                    </template>
                  </el-table-column>
                </el-table>
              </el-tab-pane>

              <el-tab-pane :label="isAdmin ? '消费统计' : '消费统计'" :name="isAdmin ? 'consumption-admin' : 'users'">
                <el-row :gutter="12" style="margin-bottom: 12px">
                  <el-col :span="6">
                    <el-select v-model="consumptionFilters.category" style="width: 100%" placeholder="按类别筛选">
                      <el-option label="全部类别" value="" />
                      <el-option label="水费" value="water" />
                      <el-option label="电费" value="electricity" />
                    </el-select>
                  </el-col>
                  <el-col :span="6">
                    <el-date-picker v-model="consumptionFilters.start_date" value-format="YYYY-MM-DD" type="date" placeholder="开始日期" style="width: 100%" />
                  </el-col>
                  <el-col :span="6">
                    <el-date-picker v-model="consumptionFilters.end_date" value-format="YYYY-MM-DD" type="date" placeholder="结束日期" style="width: 100%" />
                  </el-col>
                  <el-col :span="6">
                    <el-button @click="() => Promise.all([loadConsumptions(), loadConsumptionStats()])">查询统计</el-button>
                  </el-col>
                </el-row>

                <div class="form-grid" style="margin-bottom: 14px">
                  <SimpleBarChart title="分类消费金额（元）" :items="consumeStatsForCategory()" />
                  <SimpleBarChart title="每日消费趋势（元）" :items="consumeStatsForTrend()" color="#2b9f6c" />
                </div>

                <el-table :data="consumptions" stripe border empty-text="暂无消费记录">
                  <el-table-column label="时间" min-width="165">
                    <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
                  </el-table-column>
                  <el-table-column label="类别" min-width="100">
                    <template #default="{ row }">{{ categoryMap[row.category] || row.category }}</template>
                  </el-table-column>
                  <el-table-column label="用量" min-width="90">
                    <template #default="{ row }">{{ formatMoney(row.usage) }}</template>
                  </el-table-column>
                  <el-table-column label="金额" min-width="100">
                    <template #default="{ row }">¥ {{ formatMoney(row.cost_amount) }}</template>
                  </el-table-column>
                  <el-table-column prop="user_name" label="用户" min-width="120" />
                  <el-table-column prop="remark" label="备注" min-width="180" show-overflow-tooltip />
                </el-table>
              </el-tab-pane>

              <el-tab-pane :label="isAdmin ? '公告发布' : '公告通知'" name="announcements">
                <template v-if="isAdmin">
                  <el-form label-position="top" class="section-card" shadow="never" @submit.prevent>
                    <el-form-item label="公告标题">
                      <el-input v-model="announcementForm.title" placeholder="请输入公告标题" clearable />
                    </el-form-item>
                    <el-form-item label="公告内容">
                      <el-input v-model="announcementForm.content" type="textarea" :rows="4" placeholder="请输入公告内容" />
                    </el-form-item>
                    <el-form-item>
                      <el-switch v-model="announcementForm.is_active" active-text="立即生效" inactive-text="仅保存" />
                    </el-form-item>
                    <el-button type="primary" :loading="actionLoading" @click="publishAnnouncement">发布公告并推送通知</el-button>
                  </el-form>
                </template>

                <div class="table-grid" style="margin-top: 14px">
                  <el-card class="section-card" shadow="never">
                    <h3 class="section-title">公告历史</h3>
                    <el-timeline>
                      <el-timeline-item v-for="item in announcements" :key="item.id" :timestamp="formatDateTime(item.published_at)">
                        <h4 style="margin: 0 0 6px">{{ item.title }}</h4>
                        <p style="margin: 0; color: var(--text-sub)">{{ item.content }}</p>
                      </el-timeline-item>
                    </el-timeline>
                  </el-card>

                  <el-card class="section-card" shadow="never">
                    <h3 class="section-title">我的通知</h3>
                    <el-button size="small" style="margin-bottom: 8px" @click="markAllNotificationsRead">全部标记已读</el-button>
                    <el-table :data="notifications.items" stripe border empty-text="暂无通知">
                      <el-table-column prop="title" label="标题" min-width="160" show-overflow-tooltip />
                      <el-table-column label="类型" min-width="100">
                        <template #default="{ row }">{{ row.notice_type_display }}</template>
                      </el-table-column>
                      <el-table-column label="时间" min-width="165">
                        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
                      </el-table-column>
                      <el-table-column label="状态" min-width="100">
                        <template #default="{ row }">
                          <el-tag :type="row.is_read ? 'info' : 'warning'" effect="plain">{{ row.is_read ? '已读' : '未读' }}</el-tag>
                        </template>
                      </el-table-column>
                      <el-table-column label="操作" min-width="90">
                        <template #default="{ row }">
                          <el-button size="small" :disabled="row.is_read" @click="markNotificationRead(row)">已读</el-button>
                        </template>
                      </el-table-column>
                    </el-table>
                  </el-card>
                </div>
              </el-tab-pane>
            </el-tabs>
          </el-card>
        </template>
      </el-skeleton>
    </section>
  </main>
</template>
