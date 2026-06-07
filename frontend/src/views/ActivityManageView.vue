<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'

import { useAuthStore } from '../stores/auth'
import http from '../utils/http'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(true)
const actionLoading = ref(false)

const activities = ref([])
const filters = reactive({
  keyword: '',
  status: '',
})

const dialogVisible = ref(false)
const editingActivityId = ref(null)
const activityForm = reactive({
  title: '',
  description: '',
  cover_image: '',
  location: '',
  start_time: '',
  end_time: '',
  max_participants: 50,
  require_approval: false,
  require_payment: false,
  fee_amount: 0,
  status: 'draft',
})

const registrationDialogVisible = ref(false)
const currentActivity = ref(null)
const registrations = ref([])
const selectedRegistrations = ref([])
const registrationStatusFilter = ref('')

const checkInCodeDialogVisible = ref(false)
const currentCheckInCode = ref('')

const isAdmin = computed(() => authStore.user?.profile?.role === 'admin')

const statusMap = {
  draft: { label: '草稿', type: 'info' },
  published: { label: '已发布', type: 'success' },
  ongoing: { label: '进行中', type: 'primary' },
  ended: { label: '已结束', type: 'warning' },
}

const registrationStatusMap = {
  pending: { label: '待审核', type: 'warning' },
  approved: { label: '已报名', type: 'success' },
  rejected: { label: '已驳回', type: 'danger' },
  checked_in: { label: '已签到', type: 'primary' },
  cancelled: { label: '已取消', type: 'info' },
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

function formatMoney(value) {
  const amount = Number(value ?? 0)
  if (Number.isNaN(amount)) return '0.00'
  return amount.toFixed(2)
}

async function loadActivities() {
  const params = {}
  if (filters.keyword) params.keyword = filters.keyword
  if (filters.status) params.status = filters.status
  const { data } = await http.get('/activities/activities/', { params })
  activities.value = data
}

async function openActivityCreate() {
  editingActivityId.value = null
  Object.assign(activityForm, {
    title: '',
    description: '',
    cover_image: '',
    location: '',
    start_time: '',
    end_time: '',
    max_participants: 50,
    require_approval: false,
    require_payment: false,
    fee_amount: 0,
    status: 'draft',
  })
  dialogVisible.value = true
}

async function openActivityEdit(activity) {
  editingActivityId.value = activity.id
  Object.assign(activityForm, {
    title: activity.title,
    description: activity.description,
    cover_image: activity.cover_image || '',
    location: activity.location,
    start_time: activity.start_time,
    end_time: activity.end_time,
    max_participants: activity.max_participants,
    require_approval: activity.require_approval,
    require_payment: activity.require_payment,
    fee_amount: Number(activity.fee_amount),
    status: activity.status === 'ongoing' || activity.status === 'ended' ? activity.status : activity.status,
  })
  dialogVisible.value = true
}

async function saveActivity() {
  if (!activityForm.title.trim()) {
    ElNotification({ title: '保存失败', message: '请输入活动标题。', type: 'warning' })
    return
  }
  if (!activityForm.description.trim()) {
    ElNotification({ title: '保存失败', message: '请输入活动介绍。', type: 'warning' })
    return
  }
  if (!activityForm.location.trim()) {
    ElNotification({ title: '保存失败', message: '请输入活动地点。', type: 'warning' })
    return
  }
  if (!activityForm.start_time || !activityForm.end_time) {
    ElNotification({ title: '保存失败', message: '请选择活动开始和结束时间。', type: 'warning' })
    return
  }
  if (activityForm.require_payment && Number(activityForm.fee_amount) <= 0) {
    ElNotification({ title: '保存失败', message: '需要扣费时费用必须大于 0。', type: 'warning' })
    return
  }

  actionLoading.value = true
  try {
    const payload = { ...activityForm }
    if (editingActivityId.value) {
      await http.put(`/activities/activities/${editingActivityId.value}/`, payload)
      ElNotification({ title: '修改成功', message: '活动信息已更新。', type: 'success' })
    } else {
      await http.post('/activities/activities/', payload)
      ElNotification({ title: '创建成功', message: '活动已创建。', type: 'success' })
    }
    dialogVisible.value = false
    await loadActivities()
  } finally {
    actionLoading.value = false
  }
}

async function publishActivity(activity) {
  try {
    await http.post(`/activities/activities/${activity.id}/publish/`)
    ElNotification({ title: '发布成功', message: '活动已发布。', type: 'success' })
    await loadActivities()
  } catch (_e) {}
}

async function deleteActivity(activity) {
  try {
    await ElMessageBox.confirm(`确定删除活动「${activity.title}」吗？`, '删除确认', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch (_e) {
    return
  }
  try {
    await http.delete(`/activities/activities/${activity.id}/`)
    ElNotification({ title: '删除成功', message: '活动已删除。', type: 'success' })
    await loadActivities()
  } catch (_e) {}
}

async function openRegistrations(activity) {
  currentActivity.value = activity
  registrations.value = []
  selectedRegistrations.value = []
  registrationStatusFilter.value = ''
  registrationDialogVisible.value = true
  await loadRegistrations()
}

async function loadRegistrations() {
  if (!currentActivity.value) return
  const params = { activity_id: currentActivity.value.id }
  if (registrationStatusFilter.value) params.status = registrationStatusFilter.value
  const { data } = await http.get('/activities/registrations/', { params })
  registrations.value = data
}

async function reviewRegistration(registration, action) {
  const actionLabel = action === 'approved' ? '通过' : '驳回'
  const result = await ElMessageBox.prompt(
    action === 'approved' ? '请输入通过备注（可选）' : '请输入驳回原因',
    `${actionLabel}报名`,
    {
      confirmButtonText: '提交',
      cancelButtonText: '取消',
      inputPlaceholder: '请输入审核备注',
    }
  ).catch(() => null)

  if (!result) return

  actionLoading.value = true
  try {
    await http.post(`/activities/registrations/${registration.id}/review/`, {
      action,
      review_remark: result.value || '',
    })
    ElNotification({ title: '审核完成', message: '报名状态已更新。', type: 'success' })
    await loadRegistrations()
  } finally {
    actionLoading.value = false
  }
}

async function batchReview(action) {
  if (selectedRegistrations.value.length === 0) {
    ElMessage.warning('请先选择要审核的报名记录。')
    return
  }
  const actionLabel = action === 'approved' ? '批量通过' : '批量驳回'
  const result = await ElMessageBox.prompt(
    action === 'approved' ? '请输入通过备注（可选）' : '请输入驳回原因',
    actionLabel,
    {
      confirmButtonText: '提交',
      cancelButtonText: '取消',
      inputPlaceholder: '请输入审核备注',
    }
  ).catch(() => null)

  if (!result) return

  actionLoading.value = true
  try {
    const { data } = await http.post('/activities/registrations/batch-review/', {
      ids: selectedRegistrations.value,
      action,
      review_remark: result.value || '',
    })
    ElNotification({ title: '批量审核完成', message: `已处理 ${data.updated_count} 条记录。`, type: 'success' })
    selectedRegistrations.value = []
    await loadRegistrations()
  } finally {
    actionLoading.value = false
  }
}

async function generateCheckInCode(activity) {
  try {
    const { data } = await http.post(`/activities/activities/${activity.id}/generate-check-in-code/`)
    currentCheckInCode.value = data.check_in_code
    checkInCodeDialogVisible.value = true
  } catch (_e) {}
}

async function goBack() {
  await router.push('/dashboard')
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
  if (!isAdmin.value) {
    await router.push('/activities')
    return
  }
  try {
    await loadActivities()
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <main class="page-shell animated-in">
    <el-card class="section-card" shadow="never">
      <el-row justify="space-between" align="middle" :gutter="12">
        <el-col :xs="24" :sm="18">
          <h2 class="section-title">活动管理</h2>
          <p style="margin: 0; color: var(--text-sub)">管理员可发布、编辑、管理校园活动及报名审核</p>
        </el-col>
        <el-col :xs="24" :sm="6" style="text-align: right">
          <el-button style="margin-right: 8px" @click="goBack">返回首页</el-button>
          <el-button type="primary" @click="openActivityCreate">新建活动</el-button>
        </el-col>
      </el-row>
    </el-card>

    <el-skeleton :loading="loading" animated :rows="6">
      <template #default>
        <el-card class="section-card" shadow="never">
          <el-row :gutter="12" style="margin-bottom: 14px">
            <el-col :span="8">
              <el-input v-model="filters.keyword" placeholder="搜索活动标题/地点" clearable @change="loadActivities" />
            </el-col>
            <el-col :span="6">
              <el-select v-model="filters.status" style="width: 100%" placeholder="按状态筛选" clearable @change="loadActivities">
                <el-option label="草稿" value="draft" />
                <el-option label="已发布" value="published" />
                <el-option label="进行中" value="ongoing" />
                <el-option label="已结束" value="ended" />
              </el-select>
            </el-col>
            <el-col :span="10" style="text-align: right">
              <el-button @click="loadActivities">刷新</el-button>
            </el-col>
          </el-row>

          <el-table :data="activities" stripe border empty-text="暂无活动数据">
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column prop="title" label="活动标题" min-width="180" show-overflow-tooltip />
            <el-table-column prop="location" label="地点" min-width="140" show-overflow-tooltip />
            <el-table-column label="时间" min-width="300">
              <template #default="{ row }">
                {{ formatDateTime(row.start_time) }} ~ {{ formatDateTime(row.end_time) }}
              </template>
            </el-table-column>
            <el-table-column label="报名情况" min-width="130">
              <template #default="{ row }">
                <el-tag :type="row.is_full ? 'danger' : 'success'" effect="plain">
                  {{ row.registered_count || 0 }} / {{ row.max_participants }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="费用" min-width="100">
              <template #default="{ row }">
                {{ row.require_payment ? `¥ ${formatMoney(row.fee_amount)}` : '免费' }}
              </template>
            </el-table-column>
            <el-table-column label="审核" min-width="90">
              <template #default="{ row }">
                <el-tag v-if="row.require_approval" type="warning" effect="plain">需审核</el-tag>
                <el-tag v-else type="info" effect="plain">免审核</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="状态" min-width="100">
              <template #default="{ row }">
                <el-tag :type="statusMap[row.status]?.type || 'info'" effect="plain">
                  {{ statusMap[row.status]?.label || row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" min-width="340" fixed="right">
              <template #default="{ row }">
                <el-space wrap>
                  <el-button size="small" type="primary" plain @click="openRegistrations(row)">报名名单</el-button>
                  <el-button size="small" type="success" plain @click="generateCheckInCode(row)">生成签到码</el-button>
                  <el-button size="small" type="warning" plain :disabled="row.status !== 'draft'" @click="publishActivity(row)">发布</el-button>
                  <el-button size="small" @click="openActivityEdit(row)">编辑</el-button>
                  <el-button size="small" type="danger" plain @click="deleteActivity(row)">删除</el-button>
                </el-space>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </template>
    </el-skeleton>

    <el-dialog v-model="dialogVisible" :title="editingActivityId ? '编辑活动' : '新建活动'" width="640px">
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="活动标题">
          <el-input v-model="activityForm.title" placeholder="请输入活动标题" maxlength="200" show-word-limit />
        </el-form-item>
        <el-form-item label="活动介绍">
          <el-input v-model="activityForm.description" type="textarea" :rows="5" placeholder="请输入活动详细介绍" maxlength="10000" show-word-limit />
        </el-form-item>
        <el-form-item label="封面图片 URL（可选）">
          <el-input v-model="activityForm.cover_image" placeholder="请输入封面图片链接，可选" />
        </el-form-item>
        <el-form-item label="活动地点">
          <el-input v-model="activityForm.location" placeholder="例如：图书馆报告厅、操场" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="开始时间">
              <el-date-picker v-model="activityForm.start_time" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" placeholder="选择开始时间" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="结束时间">
              <el-date-picker v-model="activityForm.end_time" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" placeholder="选择结束时间" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="人数上限">
          <el-input-number v-model="activityForm.max_participants" :min="1" :max="10000" style="width: 100%" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="是否需要审核报名">
              <el-switch v-model="activityForm.require_approval" active-text="需要" inactive-text="不需要" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="是否需要扣费">
              <el-switch v-model="activityForm.require_payment" active-text="需要" inactive-text="免费" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item v-if="activityForm.require_payment" label="活动费用（元）">
          <el-input-number v-model="activityForm.fee_amount" :min="0" :precision="2" :step="10" style="width: 100%" />
        </el-form-item>
        <el-form-item label="保存状态">
          <el-radio-group v-model="activityForm.status">
            <el-radio label="draft">保存为草稿</el-radio>
            <el-radio label="published">立即发布</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="actionLoading" @click="saveActivity">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="registrationDialogVisible" width="900px" top="5vh">
      <template #header>
        <span style="font-weight: 700; font-size: 16px">
          {{ currentActivity?.title }} — 报名名单
        </span>
      </template>
      <el-row :gutter="12" style="margin-bottom: 12px">
        <el-col :span="6">
          <el-select v-model="registrationStatusFilter" style="width: 100%" placeholder="按状态筛选" clearable @change="loadRegistrations">
            <el-option label="待审核" value="pending" />
            <el-option label="已报名" value="approved" />
            <el-option label="已驳回" value="rejected" />
            <el-option label="已签到" value="checked_in" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-col>
        <el-col :span="18" style="text-align: right">
          <el-button :loading="actionLoading" type="success" plain :disabled="selectedRegistrations.length === 0" @click="batchReview('approved')">批量通过</el-button>
          <el-button :loading="actionLoading" type="danger" plain style="margin-left: 8px" :disabled="selectedRegistrations.length === 0" @click="batchReview('rejected')">批量驳回</el-button>
          <el-button style="margin-left: 8px" @click="loadRegistrations">刷新</el-button>
        </el-col>
      </el-row>
      <el-table
        :data="registrations"
        stripe
        border
        @selection-change="(val) => (selectedRegistrations = val.map((r) => r.id))"
        empty-text="暂无报名记录"
        height="500"
      >
        <el-table-column type="selection" width="50" />
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="user_name" label="用户名" min-width="120" />
        <el-table-column prop="student_id" label="学号" min-width="120" />
        <el-table-column label="状态" min-width="100">
          <template #default="{ row }">
            <el-tag :type="registrationStatusMap[row.status]?.type || 'info'" effect="plain">
              {{ registrationStatusMap[row.status]?.label || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="支付金额" min-width="110">
          <template #default="{ row }">¥ {{ formatMoney(row.paid_amount) }}</template>
        </el-table-column>
        <el-table-column label="报名时间" min-width="165">
          <template #default="{ row }">{{ formatDateTime(row.registered_at) }}</template>
        </el-table-column>
        <el-table-column label="签到时间" min-width="165">
          <template #default="{ row }">{{ formatDateTime(row.check_in_time) }}</template>
        </el-table-column>
        <el-table-column label="操作" min-width="180" fixed="right">
          <template #default="{ row }">
            <el-space>
              <el-button size="small" type="success" :disabled="row.status !== 'pending'" @click="reviewRegistration(row, 'approved')">通过</el-button>
              <el-button size="small" type="danger" :disabled="row.status !== 'pending'" @click="reviewRegistration(row, 'rejected')">驳回</el-button>
            </el-space>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="registrationDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="checkInCodeDialogVisible" title="活动签到码" width="380px">
      <div style="text-align: center; padding: 20px 0">
        <div style="font-size: 14px; color: var(--text-sub); margin-bottom: 12px">请将以下签到码告知现场学生：</div>
        <div style="font-size: 48px; font-weight: 700; letter-spacing: 8px; color: var(--el-color-primary)">
          {{ currentCheckInCode }}
        </div>
        <div style="font-size: 12px; color: var(--text-sub); margin-top: 16px">
          学生在活动详情页输入此签到码即可完成签到
        </div>
      </div>
      <template #footer>
        <el-button type="primary" @click="checkInCodeDialogVisible = false">确定</el-button>
      </template>
    </el-dialog>
  </main>
</template>

<style scoped>
</style>
