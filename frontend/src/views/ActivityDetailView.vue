<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'

import { useAuthStore } from '../stores/auth'
import http from '../utils/http'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const activityId = computed(() => Number(route.params.id))
const loading = ref(true)
const actionLoading = ref(false)

const activity = ref(null)
const myRegistration = ref(null)
const reviews = ref([])

const checkInInput = ref('')
const checkInVisible = ref(false)

const reviewDialogVisible = ref(false)
const reviewForm = reactive({
  rating: 5,
  content: '',
})

const isAdmin = computed(() => authStore.user?.profile?.role === 'admin')
const isStudent = computed(() => authStore.user?.profile?.role === 'student')

const statusMap = {
  draft: { label: '草稿', type: 'info' },
  published: { label: '报名中', type: 'success' },
  ongoing: { label: '进行中', type: 'primary' },
  ended: { label: '已结束', type: 'warning' },
}

const registrationStatusMap = {
  pending: { label: '待审核', type: 'warning' },
  approved: { label: '已报名', type: 'success' },
  rejected: { label: '已驳回', type: 'danger' },
  checked_in: { label: '已签到(实际参与)', type: 'primary' },
  cancelled: { label: '已取消', type: 'info' },
}

const canRegister = computed(() => {
  if (!activity.value) return false
  if (!isStudent.value) return false
  if (myRegistration.value) return false
  return activity.value.can_register
})

const canCheckIn = computed(() => {
  if (!activity.value || !myRegistration.value) return false
  if (!isStudent.value) return false
  return (
    ['published', 'ongoing'].includes(activity.value.status) &&
    ['approved'].includes(myRegistration.value.status)
  )
})

const canReview = computed(() => {
  if (!activity.value || !myRegistration.value) return false
  if (!isStudent.value) return false
  return activity.value.status === 'ended' && myRegistration.value.status === 'checked_in'
})

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

async function loadActivity() {
  loading.value = true
  try {
    const { data } = await http.get(`/activities/activities/${activityId.value}/`)
    activity.value = data
    await loadMyRegistration()
    await loadReviews()
  } finally {
    loading.value = false
  }
}

async function loadMyRegistration() {
  if (!isStudent.value) return
  try {
    const { data } = await http.get('/activities/registrations/my/')
    const mine = (data || []).find((r) => r.activity === activityId.value)
    myRegistration.value = mine || null
  } catch (_e) {
    myRegistration.value = null
  }
}

async function loadReviews() {
  try {
    const { data } = await http.get(`/activities/activities/${activityId.value}/reviews/`)
    reviews.value = data || []
  } catch (_e) {
    reviews.value = []
  }
}

async function handleRegister() {
  if (!canRegister.value) return
  const tip = activity.value.require_payment
    ? `报名将从您的钱包扣除 ¥${formatMoney(activity.value.fee_amount)}，确定报名吗？`
    : '确定报名此活动吗？'
  try {
    await ElMessageBox.confirm(tip, '报名确认', {
      confirmButtonText: '确定报名',
      cancelButtonText: '取消',
      type: 'info',
    })
  } catch (_e) {
    return
  }
  actionLoading.value = true
  try {
    await http.post(`/activities/activities/${activityId.value}/register/`)
    ElNotification({ title: '报名成功', message: activity.value.require_approval ? '请等待管理员审核。' : '您已成功报名，请准时参加。', type: 'success' })
    await loadMyRegistration()
    await loadActivity()
  } catch (e) {
    ElNotification({ title: '报名失败', message: e.response?.data?.detail || '请稍后重试。', type: 'error' })
  } finally {
    actionLoading.value = false
  }
}

function openCheckIn() {
  checkInInput.value = ''
  checkInVisible.value = true
}

async function submitCheckIn() {
  if (!checkInInput.value.trim()) {
    ElMessage.warning('请输入签到码。')
    return
  }
  actionLoading.value = true
  try {
    await http.post(`/activities/activities/${activityId.value}/check-in/`, {
      check_in_code: checkInInput.value.trim(),
    })
    ElNotification({ title: '签到成功', message: '您已完成活动签到。', type: 'success' })
    checkInVisible.value = false
    await loadMyRegistration()
  } catch (e) {
    ElNotification({ title: '签到失败', message: e.response?.data?.detail || '签到码不正确。', type: 'error' })
  } finally {
    actionLoading.value = false
  }
}

function openReview() {
  reviewForm.rating = 5
  reviewForm.content = ''
  reviewDialogVisible.value = true
}

async function submitReview() {
  if (!reviewForm.rating) {
    ElMessage.warning('请选择评分。')
    return
  }
  actionLoading.value = true
  try {
    await http.post(`/activities/activities/${activityId.value}/reviews/`, {
      rating: reviewForm.rating,
      content: reviewForm.content,
    })
    ElNotification({ title: '评价成功', message: '感谢您的反馈。', type: 'success' })
    reviewDialogVisible.value = false
    await loadReviews()
    await loadActivity()
  } catch (e) {
    ElNotification({ title: '评价失败', message: e.response?.data?.detail || '请稍后重试。', type: 'error' })
  } finally {
    actionLoading.value = false
  }
}

async function goBack() {
  await router.push('/activities')
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
  await loadActivity()
})
</script>

<template>
  <main class="page-shell animated-in">
    <el-card class="section-card" shadow="never">
      <el-row justify="space-between" align="middle" :gutter="12">
        <el-col :xs="24" :sm="18">
          <el-button link style="padding: 0; margin-bottom: 4px" @click="goBack">← 返回活动列表</el-button>
          <h2 class="section-title" style="margin-top: 0">活动详情</h2>
        </el-col>
        <el-col :xs="24" :sm="6" style="text-align: right">
          <el-button v-if="isAdmin" @click="router.push('/activities/manage')">活动管理</el-button>
        </el-col>
      </el-row>
    </el-card>

    <el-skeleton :loading="loading" animated :rows="8">
      <template #default>
        <div v-if="!activity" style="text-align: center; padding: 60px 0; color: var(--text-sub)">
          活动不存在
        </div>
        <template v-else>
          <el-card class="section-card" shadow="never">
            <el-row :gutter="20">
              <el-col :xs="24" :md="10">
                <div v-if="activity.cover_image" class="detail-cover">
                  <img :src="activity.cover_image" :alt="activity.title" style="width: 100%; height: 100%; object-fit: cover; border-radius: 12px" />
                </div>
                <div v-else class="detail-cover placeholder">
                  <el-icon style="font-size: 72px; color: var(--text-sub)"><Picture /></el-icon>
                </div>
              </el-col>
              <el-col :xs="24" :md="14">
                <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 12px">
                  <h1 style="margin: 0; font-size: 24px; line-height: 1.3">{{ activity.title }}</h1>
                </div>
                <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px">
                  <el-tag :type="statusMap[activity.status]?.type || 'info'" effect="plain">
                    {{ statusMap[activity.status]?.label || activity.status }}
                  </el-tag>
                  <el-tag v-if="activity.require_approval" type="warning" effect="plain">需审核</el-tag>
                  <el-tag v-if="activity.require_payment" type="danger" effect="plain">
                    ¥ {{ formatMoney(activity.fee_amount) }}
                  </el-tag>
                  <el-tag v-else type="success" effect="plain">免费</el-tag>
                  <el-tag v-if="activity.average_rating" type="primary" effect="plain">
                    评分 {{ activity.average_rating }}
                  </el-tag>
                </div>

                <el-descriptions :column="1" border size="default" style="margin-bottom: 16px">
                  <el-descriptions-item label="活动地点">
                    <el-icon><Location /></el-icon>
                    <span style="margin-left: 6px">{{ activity.location }}</span>
                  </el-descriptions-item>
                  <el-descriptions-item label="开始时间">
                    <el-icon><Clock /></el-icon>
                    <span style="margin-left: 6px">{{ formatDateTime(activity.start_time) }}</span>
                  </el-descriptions-item>
                  <el-descriptions-item label="结束时间">
                    <el-icon><Clock /></el-icon>
                    <span style="margin-left: 6px">{{ formatDateTime(activity.end_time) }}</span>
                  </el-descriptions-item>
                  <el-descriptions-item label="报名人数">
                    <el-icon><User /></el-icon>
                    <span style="margin-left: 6px">
                      {{ activity.registered_count || 0 }} / {{ activity.max_participants }} 人
                      <el-tag v-if="activity.is_full" size="small" type="danger" style="margin-left: 6px">已满</el-tag>
                    </span>
                  </el-descriptions-item>
                  <el-descriptions-item v-if="activity.publisher_name" label="发布人">
                    {{ activity.publisher_name }}
                  </el-descriptions-item>
                </el-descriptions>

                <div v-if="myRegistration" style="margin-bottom: 16px">
                  <el-alert type="info" :closable="false" style="margin-bottom: 10px">
                    <template #title>
                      <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap">
                        <span>我的报名状态：</span>
                        <el-tag :type="registrationStatusMap[myRegistration.status]?.type || 'info'" effect="plain">
                          {{ registrationStatusMap[myRegistration.status]?.label || myRegistration.status }}
                        </el-tag>
                        <span v-if="myRegistration.paid_amount > 0" style="color: var(--text-sub); font-size: 13px">
                          已支付：¥ {{ formatMoney(myRegistration.paid_amount) }}
                        </span>
                        <span v-if="myRegistration.check_in_time" style="color: var(--text-sub); font-size: 13px">
                          签到时间：{{ formatDateTime(myRegistration.check_in_time) }}
                        </span>
                      </div>
                    </template>
                  </el-alert>
                </div>

                <div style="display: flex; gap: 10px; flex-wrap: wrap">
                  <el-button
                    v-if="canRegister"
                    type="primary"
                    :loading="actionLoading"
                    size="large"
                    @click="handleRegister"
                  >
                    {{ activity.require_payment ? `立即报名 (¥${formatMoney(activity.fee_amount)})` : '立即报名' }}
                  </el-button>
                  <el-button
                    v-if="canCheckIn"
                    type="success"
                    :loading="actionLoading"
                    size="large"
                    @click="openCheckIn"
                  >
                    活动签到
                  </el-button>
                  <el-button
                    v-if="canReview && !reviews.some((r) => r.user_name === authStore.user?.username)"
                    type="warning"
                    :loading="actionLoading"
                    size="large"
                    @click="openReview"
                  >
                    评价活动
                  </el-button>
                  <el-button
                    v-if="!canRegister && isStudent && !myRegistration && activity.status !== 'ended'"
                    disabled
                    size="large"
                  >
                    {{ activity.is_full ? '名额已满' : '暂不可报名' }}
                  </el-button>
                </div>
              </el-col>
            </el-row>
          </el-card>

          <el-card class="section-card" shadow="never">
            <h3 class="section-title">活动介绍</h3>
            <div class="activity-description" v-html="activity.description ? activity.description.replace(/\n/g, '<br/>') : ''" />
          </el-card>

          <el-card class="section-card" shadow="never">
            <h3 class="section-title">活动评价（{{ reviews.length }}）</h3>
            <div v-if="reviews.length === 0" style="color: var(--text-sub); padding: 20px 0">
              暂无评价
            </div>
            <div v-else>
              <div v-for="review in reviews" :key="review.id" class="review-item">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px">
                  <div style="display: flex; align-items: center; gap: 10px">
                    <el-avatar :size="32">{{ review.user_name?.charAt(0)?.toUpperCase() }}</el-avatar>
                    <span style="font-weight: 600">{{ review.user_name }}</span>
                    <el-rate :model-value="Number(review.rating)" disabled size="small" />
                  </div>
                  <span style="color: var(--text-sub); font-size: 13px">{{ formatDateTime(review.created_at) }}</span>
                </div>
                <div v-if="review.content" style="color: var(--text-primary); padding-left: 42px">
                  {{ review.content }}
                </div>
              </div>
            </div>
          </el-card>
        </template>
      </template>
    </el-skeleton>

    <el-dialog v-model="checkInVisible" title="活动签到" width="420px">
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="请输入管理员提供的 6 位签到码">
          <el-input v-model="checkInInput" placeholder="请输入签到码" maxlength="16" style="font-size: 20px; letter-spacing: 4px" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="checkInVisible = false">取消</el-button>
        <el-button type="primary" :loading="actionLoading" @click="submitCheckIn">确认签到</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="reviewDialogVisible" title="评价活动" width="480px">
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="评分">
          <el-rate v-model="reviewForm.rating" />
        </el-form-item>
        <el-form-item label="评价内容（可选）">
          <el-input v-model="reviewForm.content" type="textarea" :rows="4" placeholder="分享您的参与感受..." maxlength="1000" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="reviewDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="actionLoading" @click="submitReview">提交评价</el-button>
      </template>
    </el-dialog>
  </main>
</template>

<script>
import { Picture, Location, Clock, User } from '@element-plus/icons-vue'
export default {
  components: { Picture, Location, Clock, User },
}
</script>

<style scoped>
.detail-cover {
  width: 100%;
  aspect-ratio: 16 / 9;
  min-height: 200px;
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--el-fill-color-light);
}
.detail-cover.placeholder {
  background: var(--el-fill-color-light);
}
.activity-description {
  line-height: 1.8;
  color: var(--text-primary);
  white-space: pre-wrap;
  font-size: 14px;
}
.review-item {
  padding: 14px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.review-item:last-child {
  border-bottom: none;
}
</style>
