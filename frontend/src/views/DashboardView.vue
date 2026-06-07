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

const myRoom = reactive({
  room: null,
  history: [],
})

const myActivities = ref([])
const calendarActivities = ref([])

const activityStatusMap = {
  draft: { label: '草稿', type: 'info' },
  published: { label: '报名中', type: 'success' },
  ongoing: { label: '进行中', type: 'primary' },
  ended: { label: '已结束', type: 'warning' },
}

const activityRegistrationStatusMap = {
  pending: { label: '待审核', type: 'warning' },
  approved: { label: '已报名', type: 'success' },
  rejected: { label: '已驳回', type: 'danger' },
  checked_in: { label: '已签到(实际参与)', type: 'primary' },
  cancelled: { label: '已取消', type: 'info' },
}

const buildings = ref([])
const buildingForm = reactive({
  name: '',
  description: '',
})
const buildingDialogVisible = ref(false)
const editingBuildingId = ref(null)

const rooms = ref([])
const roomFilters = reactive({
  building_id: '',
  keyword: '',
  only_active: '',
})
const roomForm = reactive({
  building: null,
  room_number: '',
  capacity: 4,
  is_active: true,
  description: '',
})
const roomDialogVisible = ref(false)
const editingRoomId = ref(null)

const selectedRoom = ref(null)
const roomDetailDialogVisible = ref(false)
const roomResidents = ref([])
const roomHistory = ref([])

const bindDialogVisible = ref(false)
const bindForm = reactive({
  user_id: null,
  room_id: null,
  remark: '',
})
const availableStudents = ref([])
const studentKeyword = ref('')
const studentOnlyUnassigned = ref(true)

const unbindDialogVisible = ref(false)
const unbindForm = reactive({
  user_id: null,
  remark: '',
})

const changeRoomDialogVisible = ref(false)
const changeRoomForm = reactive({
  user_id: null,
  new_room_id: null,
  remark: '',
})
const changeRoomTargetUser = ref(null)

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

async function loadMyRoom() {
  const { data } = await http.get('/dormitory/my-room/')
  Object.assign(myRoom, data)
}

async function loadBuildings() {
  const { data } = await http.get('/dormitory/buildings/')
  buildings.value = data
}

async function openBuildingCreate() {
  editingBuildingId.value = null
  buildingForm.name = ''
  buildingForm.description = ''
  buildingDialogVisible.value = true
}

async function openBuildingEdit(building) {
  editingBuildingId.value = building.id
  buildingForm.name = building.name
  buildingForm.description = building.description || ''
  buildingDialogVisible.value = true
}

async function saveBuilding() {
  if (!buildingForm.name.trim()) {
    ElNotification({ title: '保存失败', message: '请输入楼栋名称。', type: 'warning' })
    return
  }
  actionLoading.value = true
  try {
    if (editingBuildingId.value) {
      await http.put(`/dormitory/buildings/${editingBuildingId.value}/`, buildingForm)
      ElNotification({ title: '修改成功', message: '楼栋信息已更新。', type: 'success' })
    } else {
      await http.post('/dormitory/buildings/', buildingForm)
      ElNotification({ title: '创建成功', message: '楼栋已添加。', type: 'success' })
    }
    buildingDialogVisible.value = false
    await Promise.all([loadBuildings(), loadRooms()])
  } finally {
    actionLoading.value = false
  }
}

async function deleteBuilding(building) {
  try {
    await ElMessageBox.confirm(`确定删除楼栋「${building.name}」吗？`, '删除确认', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch (_e) {
    return
  }
  try {
    await http.delete(`/dormitory/buildings/${building.id}/`)
    ElNotification({ title: '删除成功', message: '楼栋已删除。', type: 'success' })
    await Promise.all([loadBuildings(), loadRooms()])
  } catch (_e) {}
}

async function loadRooms() {
  const params = {}
  if (roomFilters.building_id) params.building_id = roomFilters.building_id
  if (roomFilters.keyword) params.keyword = roomFilters.keyword
  if (roomFilters.only_active) params.only_active = roomFilters.only_active
  const { data } = await http.get('/dormitory/rooms/', { params })
  rooms.value = data
}

async function openRoomCreate() {
  editingRoomId.value = null
  roomForm.building = buildings.value[0]?.id || null
  roomForm.room_number = ''
  roomForm.capacity = 4
  roomForm.is_active = true
  roomForm.description = ''
  roomDialogVisible.value = true
}

async function openRoomEdit(room) {
  editingRoomId.value = room.id
  roomForm.building = room.building
  roomForm.room_number = room.room_number
  roomForm.capacity = room.capacity
  roomForm.is_active = room.is_active
  roomForm.description = room.description || ''
  roomDialogVisible.value = true
}

async function saveRoom() {
  if (!roomForm.building) {
    ElNotification({ title: '保存失败', message: '请选择所属楼栋。', type: 'warning' })
    return
  }
  if (!roomForm.room_number.trim()) {
    ElNotification({ title: '保存失败', message: '请输入房间号。', type: 'warning' })
    return
  }
  if (!roomForm.capacity || Number(roomForm.capacity) <= 0) {
    ElNotification({ title: '保存失败', message: '房间容量必须大于 0。', type: 'warning' })
    return
  }
  actionLoading.value = true
  try {
    const payload = { ...roomForm }
    if (editingRoomId.value) {
      await http.put(`/dormitory/rooms/${editingRoomId.value}/`, payload)
      ElNotification({ title: '修改成功', message: '房间信息已更新。', type: 'success' })
    } else {
      await http.post('/dormitory/rooms/', payload)
      ElNotification({ title: '创建成功', message: '房间已添加。', type: 'success' })
    }
    roomDialogVisible.value = false
    await loadRooms()
  } finally {
    actionLoading.value = false
  }
}

async function deleteRoom(room) {
  try {
    await ElMessageBox.confirm(`确定删除房间「${room.building_name} ${room.room_number}」吗？`, '删除确认', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch (_e) {
    return
  }
  try {
    await http.delete(`/dormitory/rooms/${room.id}/`)
    ElNotification({ title: '删除成功', message: '房间已删除。', type: 'success' })
    await loadRooms()
  } catch (_e) {}
}

async function openRoomDetail(room) {
  selectedRoom.value = room
  const { data } = await http.get(`/dormitory/rooms/${room.id}/`)
  roomResidents.value = data.residents
  roomHistory.value = data.history
  roomDetailDialogVisible.value = true
}

async function loadAvailableStudents() {
  const params = {}
  if (studentKeyword.value) params.keyword = studentKeyword.value
  if (studentOnlyUnassigned.value) params.only_unassigned = 'true'
  const { data } = await http.get('/dormitory/students/available/', { params })
  availableStudents.value = data
}

async function openBindDialog(room) {
  bindForm.user_id = null
  bindForm.room_id = room.id
  bindForm.remark = ''
  studentKeyword.value = ''
  studentOnlyUnassigned.value = true
  availableStudents.value = []
  await loadAvailableStudents()
  bindDialogVisible.value = true
}

async function submitBind() {
  if (!bindForm.user_id) {
    ElNotification({ title: '绑定失败', message: '请选择要绑定的学生。', type: 'warning' })
    return
  }
  actionLoading.value = true
  try {
    await http.post('/dormitory/assignments/bind/', bindForm)
    ElNotification({ title: '绑定成功', message: '学生已绑定到房间。', type: 'success' })
    bindDialogVisible.value = false
    await Promise.all([loadRooms(), selectedRoom.value && openRoomDetail(selectedRoom.value)])
  } finally {
    actionLoading.value = false
  }
}

async function openUnbindDialog(resident) {
  unbindForm.user_id = resident.user
  unbindForm.remark = ''
  unbindDialogVisible.value = true
}

async function submitUnbind() {
  actionLoading.value = true
  try {
    await http.post('/dormitory/assignments/unbind/', unbindForm)
    ElNotification({ title: '解绑成功', message: '学生已从房间解绑。', type: 'success' })
    unbindDialogVisible.value = false
    await Promise.all([loadRooms(), selectedRoom.value && openRoomDetail(selectedRoom.value)])
  } finally {
    actionLoading.value = false
  }
}

async function openChangeRoomDialog(resident) {
  changeRoomTargetUser.value = resident
  changeRoomForm.user_id = resident.user
  changeRoomForm.new_room_id = null
  changeRoomForm.remark = ''
  changeRoomDialogVisible.value = true
}

async function submitChangeRoom() {
  if (!changeRoomForm.new_room_id) {
    ElNotification({ title: '换房失败', message: '请选择目标房间。', type: 'warning' })
    return
  }
  actionLoading.value = true
  try {
    await http.post('/dormitory/assignments/change-room/', changeRoomForm)
    ElNotification({ title: '换房成功', message: '学生已换至新房间。', type: 'success' })
    changeRoomDialogVisible.value = false
    await Promise.all([loadRooms(), selectedRoom.value && openRoomDetail(selectedRoom.value)])
  } finally {
    actionLoading.value = false
  }
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

async function loadMyActivities() {
  if (isAdmin.value) return
  try {
    const { data } = await http.get('/activities/registrations/my/')
    myActivities.value = data || []
  } catch (_e) {
    myActivities.value = []
  }
}

async function loadCalendarActivities() {
  if (isAdmin.value) return
  try {
    const { data } = await http.get('/activities/calendar/')
    calendarActivities.value = data || []
  } catch (_e) {
    calendarActivities.value = []
  }
}

async function refreshAll() {
  loading.value = true
  try {
    const tasks = [loadDashboard(), loadOrders(), loadConsumptions(), loadConsumptionStats(), loadWalletLogs(), loadAnnouncements(), loadNotifications(), loadMyRoom()]
    if (isAdmin.value) {
      tasks.push(loadAdminUsers(), loadBuildings(), loadRooms())
    } else {
      tasks.push(loadMyActivities(), loadCalendarActivities())
    }
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
            <el-button v-if="isAdmin" style="margin-right: 8px" type="primary" @click="router.push('/analytics')">📊 数据看板</el-button>
            <el-button v-if="isAdmin" style="margin-right: 8px" @click="router.push('/reports')">📋 自定义报表</el-button>
            <el-button style="margin-right: 8px" @click="router.push('/activities')">校园活动</el-button>
            <el-button v-if="isAdmin" style="margin-right: 8px" type="primary" plain @click="router.push('/activities/manage')">活动管理</el-button>
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
          <section class="summary-grid" :style="{ gridTemplateColumns: !isAdmin && myRoom.room ? 'repeat(4, 1fr)' : 'repeat(3, 1fr)' }">
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
            <article v-if="!isAdmin" class="summary-card">
              <div class="label">我的宿舍</div>
              <div class="value" style="font-size: 20px">
                {{ myRoom.room ? myRoom.room.building_name + ' ' + myRoom.room.room_number : '未分配' }}
              </div>
              <div class="summary-note">
                {{ myRoom.room ? `入住 ${myRoom.room.current_occupancy}/${myRoom.room.capacity} 人` : '请联系管理员分配宿舍' }}
              </div>
            </article>
          </section>

          <el-card class="section-card" shadow="never">
            <el-tabs v-model="activeTab">
              <el-tab-pane v-if="!isAdmin" label="总览" name="overview">
                <el-card v-if="myRoom.room" class="section-card" shadow="never" style="margin-bottom: 14px">
                  <h3 class="section-title">我的宿舍信息</h3>
                  <el-row :gutter="16">
                    <el-col :span="8">
                      <div style="color: var(--text-sub); font-size: 13px">楼栋</div>
                      <div style="font-size: 18px; font-weight: 700; margin-top: 4px">{{ myRoom.room.building_name }}</div>
                    </el-col>
                    <el-col :span="8">
                      <div style="color: var(--text-sub); font-size: 13px">房间号</div>
                      <div style="font-size: 18px; font-weight: 700; margin-top: 4px">{{ myRoom.room.room_number }}</div>
                    </el-col>
                    <el-col :span="8">
                      <div style="color: var(--text-sub); font-size: 13px">入住情况</div>
                      <div style="font-size: 18px; font-weight: 700; margin-top: 4px">{{ myRoom.room.current_occupancy }} / {{ myRoom.room.capacity }} 人</div>
                    </el-col>
                  </el-row>
                  <el-divider style="margin: 12px 0" />
                  <div style="color: var(--text-sub); font-size: 13px; margin-bottom: 6px">入住历史</div>
                  <el-table :data="myRoom.history" stripe border size="small" empty-text="暂无入住历史">
                    <el-table-column label="楼栋" min-width="110">
                      <template #default="{ row }">{{ row.building_name }}</template>
                    </el-table-column>
                    <el-table-column prop="room_number" label="房间号" min-width="90" />
                    <el-table-column label="入住时间" min-width="165">
                      <template #default="{ row }">{{ formatDateTime(row.bound_at) }}</template>
                    </el-table-column>
                    <el-table-column label="退房时间" min-width="165">
                      <template #default="{ row }">{{ formatDateTime(row.unbound_at) }}</template>
                    </el-table-column>
                  </el-table>
                </el-card>
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

              <el-tab-pane v-if="!isAdmin" label="我的活动" name="my-activities">
                <el-row :gutter="12" style="margin-bottom: 12px">
                  <el-col :span="16">
                    <h3 class="section-title" style="margin: 0">我报名的活动</h3>
                  </el-col>
                  <el-col :span="8" style="text-align: right">
                    <el-button type="primary" plain @click="router.push('/activities')">浏览更多活动</el-button>
                  </el-col>
                </el-row>
                <el-table :data="myActivities" stripe border empty-text="暂无报名记录">
                  <el-table-column label="活动" min-width="200">
                    <template #default="{ row }">
                      <div style="cursor: pointer; color: var(--el-color-primary)" @click="router.push(`/activities/${row.activity}`)">
                        {{ row.activity_title }}
                      </div>
                    </template>
                  </el-table-column>
                  <el-table-column label="地点" min-width="140">
                    <template #default="{ row }">{{ row.activity_location }}</template>
                  </el-table-column>
                  <el-table-column label="时间" min-width="320">
                    <template #default="{ row }">
                      {{ formatDateTime(row.activity_start_time) }} ~ {{ formatDateTime(row.activity_end_time) }}
                    </template>
                  </el-table-column>
                  <el-table-column label="状态" min-width="120">
                    <template #default="{ row }">
                      <el-tag :type="activityRegistrationStatusMap[row.status]?.type || 'info'" effect="plain">
                        {{ activityRegistrationStatusMap[row.status]?.label || row.status }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="已支付" min-width="100">
                    <template #default="{ row }">¥ {{ formatMoney(row.paid_amount) }}</template>
                  </el-table-column>
                  <el-table-column label="签到时间" min-width="165">
                    <template #default="{ row }">{{ formatDateTime(row.check_in_time) }}</template>
                  </el-table-column>
                  <el-table-column label="报名时间" min-width="165">
                    <template #default="{ row }">{{ formatDateTime(row.registered_at) }}</template>
                  </el-table-column>
                </el-table>
              </el-tab-pane>

              <el-tab-pane v-if="!isAdmin" label="活动日历" name="activity-calendar">
                <el-row :gutter="12" style="margin-bottom: 12px">
                  <el-col :span="16">
                    <h3 class="section-title" style="margin: 0">近期活动日历</h3>
                  </el-col>
                  <el-col :span="8" style="text-align: right">
                    <el-button @click="loadCalendarActivities">刷新日历</el-button>
                  </el-col>
                </el-row>
                <el-table :data="calendarActivities" stripe border empty-text="暂无活动">
                  <el-table-column label="日期" min-width="220">
                    <template #default="{ row }">
                      <el-icon><Calendar /></el-icon>
                      <span style="margin-left: 6px">{{ formatDateTime(row.start_time) }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column label="活动" min-width="220">
                    <template #default="{ row }">
                      <div style="cursor: pointer; color: var(--el-color-primary)" @click="router.push(`/activities/${row.id}`)">
                        {{ row.title }}
                      </div>
                    </template>
                  </el-table-column>
                  <el-table-column label="地点" min-width="160">
                    <template #default="{ row }">{{ row.location }}</template>
                  </el-table-column>
                  <el-table-column label="状态" min-width="100">
                    <template #default="{ row }">
                      <el-tag :type="activityStatusMap[row.status]?.type || 'info'" effect="plain">
                        {{ activityStatusMap[row.status]?.label || row.status }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="报名情况" min-width="130">
                    <template #default="{ row }">
                      {{ row.registered_count || 0 }} / {{ row.max_participants }} 人
                    </template>
                  </el-table-column>
                </el-table>
              </el-tab-pane>

              <el-tab-pane v-if="isAdmin" label="房间台账" name="dormitory">
                <div style="margin-bottom: 14px">
                  <h3 class="section-title">楼栋管理</h3>
                  <el-row :gutter="12" style="margin-bottom: 10px">
                    <el-col :span="16">
                      <el-button type="primary" @click="openBuildingCreate">新增楼栋</el-button>
                    </el-col>
                  </el-row>
                  <el-table :data="buildings" stripe border empty-text="暂无楼栋数据">
                    <el-table-column prop="id" label="ID" width="70" />
                    <el-table-column prop="name" label="楼栋名称" min-width="140" />
                    <el-table-column prop="description" label="备注" min-width="200" show-overflow-tooltip />
                    <el-table-column prop="room_count" label="房间数" width="100" />
                    <el-table-column label="创建时间" min-width="165">
                      <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
                    </el-table-column>
                    <el-table-column label="操作" min-width="180" fixed="right">
                      <template #default="{ row }">
                        <el-space>
                          <el-button size="small" @click="openBuildingEdit(row)">编辑</el-button>
                          <el-button size="small" type="danger" plain @click="deleteBuilding(row)">删除</el-button>
                        </el-space>
                      </template>
                    </el-table-column>
                  </el-table>
                </div>

                <el-divider />

                <div>
                  <h3 class="section-title">房间管理</h3>
                  <el-row :gutter="12" style="margin-bottom: 10px">
                    <el-col :span="6">
                      <el-select v-model="roomFilters.building_id" style="width: 100%" placeholder="按楼栋筛选" clearable>
                        <el-option v-for="b in buildings" :key="b.id" :label="b.name" :value="b.id" />
                      </el-select>
                    </el-col>
                    <el-col :span="6">
                      <el-input v-model="roomFilters.keyword" placeholder="搜索房间号/楼栋" clearable />
                    </el-col>
                    <el-col :span="6">
                      <el-select v-model="roomFilters.only_active" style="width: 100%" placeholder="状态筛选" clearable>
                        <el-option label="仅启用" value="true" />
                        <el-option label="仅停用" value="false" />
                      </el-select>
                    </el-col>
                    <el-col :span="6" style="text-align: right">
                      <el-button style="margin-right: 8px" @click="loadRooms">查询</el-button>
                      <el-button type="primary" @click="openRoomCreate">新增房间</el-button>
                    </el-col>
                  </el-row>
                  <el-table :data="rooms" stripe border empty-text="暂无房间数据">
                    <el-table-column prop="id" label="ID" width="70" />
                    <el-table-column prop="building_name" label="楼栋" min-width="110" />
                    <el-table-column prop="room_number" label="房间号" min-width="100" />
                    <el-table-column label="入住情况" min-width="120">
                      <template #default="{ row }">
                        <el-tag :type="row.is_full ? 'danger' : 'success'" effect="plain">
                          {{ row.current_occupancy }} / {{ row.capacity }}
                        </el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column label="状态" min-width="90">
                      <template #default="{ row }">
                        <el-tag :type="row.is_active ? 'success' : 'info'" effect="plain">
                          {{ row.is_active ? '启用' : '停用' }}
                        </el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column prop="description" label="备注" min-width="160" show-overflow-tooltip />
                    <el-table-column label="操作" min-width="300" fixed="right">
                      <template #default="{ row }">
                        <el-space wrap>
                          <el-button size="small" type="primary" plain @click="openRoomDetail(row)">查看住户</el-button>
                          <el-button size="small" type="success" plain :disabled="row.is_full || !row.is_active" @click="openBindDialog(row)">绑定住户</el-button>
                          <el-button size="small" @click="openRoomEdit(row)">编辑</el-button>
                          <el-button size="small" type="danger" plain @click="deleteRoom(row)">删除</el-button>
                        </el-space>
                      </template>
                    </el-table-column>
                  </el-table>
                </div>
              </el-tab-pane>
            </el-tabs>
          </el-card>

          <el-dialog v-model="buildingDialogVisible" :title="editingBuildingId ? '编辑楼栋' : '新增楼栋'" width="480px">
            <el-form label-position="top" @submit.prevent>
              <el-form-item label="楼栋名称">
                <el-input v-model="buildingForm.name" placeholder="例如：1号楼、2号宿舍楼" />
              </el-form-item>
              <el-form-item label="备注说明">
                <el-input v-model="buildingForm.description" type="textarea" :rows="3" placeholder="可选" />
              </el-form-item>
            </el-form>
            <template #footer>
              <el-button @click="buildingDialogVisible = false">取消</el-button>
              <el-button type="primary" :loading="actionLoading" @click="saveBuilding">保存</el-button>
            </template>
          </el-dialog>

          <el-dialog v-model="roomDialogVisible" :title="editingRoomId ? '编辑房间' : '新增房间'" width="520px">
            <el-form label-position="top" @submit.prevent>
              <el-form-item label="所属楼栋">
                <el-select v-model="roomForm.building" style="width: 100%" placeholder="请选择楼栋">
                  <el-option v-for="b in buildings" :key="b.id" :label="b.name" :value="b.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="房间号">
                <el-input v-model="roomForm.room_number" placeholder="例如：101、302A" />
              </el-form-item>
              <el-form-item label="房间容量">
                <el-input-number v-model="roomForm.capacity" :min="1" :max="20" style="width: 100%" />
              </el-form-item>
              <el-form-item label="是否启用">
                <el-switch v-model="roomForm.is_active" active-text="启用" inactive-text="停用" />
              </el-form-item>
              <el-form-item label="备注说明">
                <el-input v-model="roomForm.description" type="textarea" :rows="2" placeholder="可选" />
              </el-form-item>
            </el-form>
            <template #footer>
              <el-button @click="roomDialogVisible = false">取消</el-button>
              <el-button type="primary" :loading="actionLoading" @click="saveRoom">保存</el-button>
            </template>
          </el-dialog>

          <el-dialog v-model="roomDetailDialogVisible" width="760px">
            <template #header>
              <span style="font-weight: 700; font-size: 16px">
                {{ selectedRoom?.building_name }} {{ selectedRoom?.room_number }} — 住户清单
              </span>
            </template>
            <div>
              <div style="margin-bottom: 8px">
                <el-tag :type="selectedRoom?.is_full ? 'danger' : 'success'" effect="plain">
                  当前入住 {{ selectedRoom?.current_occupancy }} / {{ selectedRoom?.capacity }} 人
                </el-tag>
                <el-button size="small" type="success" plain style="margin-left: 10px" :disabled="selectedRoom?.is_full || !selectedRoom?.is_active" @click="openBindDialog(selectedRoom)">
                  新增住户
                </el-button>
              </div>
              <div style="color: var(--text-sub); font-size: 13px; margin-bottom: 6px">当前住户</div>
              <el-table :data="roomResidents" stripe border size="small" empty-text="暂无住户" style="margin-bottom: 16px">
                <el-table-column prop="user_name" label="用户名" min-width="120" />
                <el-table-column prop="student_id" label="学号" min-width="120" />
                <el-table-column label="入住时间" min-width="165">
                  <template #default="{ row }">{{ formatDateTime(row.bound_at) }}</template>
                </el-table-column>
                <el-table-column label="操作" min-width="180" fixed="right">
                  <template #default="{ row }">
                    <el-space>
                      <el-button size="small" @click="openChangeRoomDialog(row)">换房</el-button>
                      <el-button size="small" type="danger" plain @click="openUnbindDialog(row)">解绑</el-button>
                    </el-space>
                  </template>
                </el-table-column>
              </el-table>
              <div style="color: var(--text-sub); font-size: 13px; margin-bottom: 6px">历史住户</div>
              <el-table :data="roomHistory" stripe border size="small" empty-text="暂无历史记录">
                <el-table-column prop="user_name" label="用户名" min-width="120" />
                <el-table-column prop="student_id" label="学号" min-width="120" />
                <el-table-column label="入住时间" min-width="165">
                  <template #default="{ row }">{{ formatDateTime(row.bound_at) }}</template>
                </el-table-column>
                <el-table-column label="退房时间" min-width="165">
                  <template #default="{ row }">{{ formatDateTime(row.unbound_at) }}</template>
                </el-table-column>
                <el-table-column prop="operator" label="操作人" min-width="100" />
              </el-table>
            </div>
            <template #footer>
              <el-button @click="roomDetailDialogVisible = false">关闭</el-button>
            </template>
          </el-dialog>

          <el-dialog v-model="bindDialogVisible" title="绑定学生到房间" width="620px">
            <el-form label-position="top" @submit.prevent>
              <el-form-item label="搜索学生">
                <el-row :gutter="12">
                  <el-col :span="15">
                    <el-input v-model="studentKeyword" placeholder="按用户名/学号/邮箱搜索" clearable @change="loadAvailableStudents" />
                  </el-col>
                  <el-col :span="9">
                    <el-switch v-model="studentOnlyUnassigned" active-text="仅未分配" inactive-text="全部学生" @change="loadAvailableStudents" />
                  </el-col>
                </el-row>
              </el-form-item>
              <el-form-item label="选择学生">
                <el-table
                  :data="availableStudents"
                  stripe
                  border
                  size="small"
                  height="240"
                  highlight-current-row
                  @current-change="(row) => (bindForm.user_id = row?.id)"
                  empty-text="暂无可用学生"
                >
                  <el-table-column type="radio" width="50" />
                  <el-table-column prop="username" label="用户名" min-width="120" />
                  <el-table-column prop="student_id" label="学号" min-width="120" />
                  <el-table-column prop="email" label="邮箱" min-width="180" />
                  <el-table-column label="当前房间" min-width="140">
                    <template #default="{ row }">{{ row.current_room || '—' }}</template>
                  </el-table-column>
                </el-table>
              </el-form-item>
              <el-form-item label="备注">
                <el-input v-model="bindForm.remark" type="textarea" :rows="2" placeholder="可选" />
              </el-form-item>
            </el-form>
            <template #footer>
              <el-button @click="bindDialogVisible = false">取消</el-button>
              <el-button type="primary" :loading="actionLoading" @click="submitBind">确认绑定</el-button>
            </template>
          </el-dialog>

          <el-dialog v-model="unbindDialogVisible" title="解绑学生" width="440px">
            <el-alert type="warning" :closable="false" style="margin-bottom: 14px">
              解绑后该房间名额将释放，绑定历史将保留。
            </el-alert>
            <el-form label-position="top" @submit.prevent>
              <el-form-item label="解绑备注">
                <el-input v-model="unbindForm.remark" type="textarea" :rows="2" placeholder="可选" />
              </el-form-item>
            </el-form>
            <template #footer>
              <el-button @click="unbindDialogVisible = false">取消</el-button>
              <el-button type="danger" :loading="actionLoading" @click="submitUnbind">确认解绑</el-button>
            </template>
          </el-dialog>

          <el-dialog v-model="changeRoomDialogVisible" title="学生换房" width="520px">
            <el-alert type="info" :closable="false" style="margin-bottom: 14px">
              将把 <b>{{ changeRoomTargetUser?.user_name }}</b> 从当前房间换至目标房间。原房间名额释放，绑定历史保留。
            </el-alert>
            <el-form label-position="top" @submit.prevent>
              <el-form-item label="目标房间">
                <el-select v-model="changeRoomForm.new_room_id" style="width: 100%" placeholder="请选择目标房间" filterable>
                  <el-option
                    v-for="r in rooms.filter((x) => x.is_active && !x.is_full && x.id !== changeRoomTargetUser?.room)"
                    :key="r.id"
                    :label="`${r.building_name} ${r.room_number}（${r.current_occupancy}/${r.capacity}）`"
                    :value="r.id"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="备注">
                <el-input v-model="changeRoomForm.remark" type="textarea" :rows="2" placeholder="可选" />
              </el-form-item>
            </el-form>
            <template #footer>
              <el-button @click="changeRoomDialogVisible = false">取消</el-button>
              <el-button type="primary" :loading="actionLoading" @click="submitChangeRoom">确认换房</el-button>
            </template>
          </el-dialog>
        </template>
      </el-skeleton>
    </section>
  </main>
</template>

<script>
import { Calendar } from '@element-plus/icons-vue'
export default {
  components: { Calendar },
}
</script>
