<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElNotification } from 'element-plus'

import { useAuthStore } from '../stores/auth'
import http from '../utils/http'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(true)
const activities = ref([])

const filters = reactive({
  keyword: '',
  status: '',
  onlyFree: false,
})

const isAdmin = computed(() => authStore.user?.profile?.role === 'admin')

const statusMap = {
  draft: { label: '草稿', type: 'info' },
  published: { label: '报名中', type: 'success' },
  ongoing: { label: '进行中', type: 'primary' },
  ended: { label: '已结束', type: 'warning' },
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
  loading.value = true
  try {
    const params = {}
    if (filters.keyword) params.keyword = filters.keyword
    if (filters.status) params.status = filters.status
    const { data } = await http.get('/activities/activities/', { params })
    let list = data || []
    if (filters.onlyFree) {
      list = list.filter((a) => !a.require_payment)
    }
    activities.value = list
  } finally {
    loading.value = false
  }
}

function openActivityDetail(activity) {
  router.push(`/activities/${activity.id}`)
}

async function goBack() {
  await router.push('/dashboard')
}

async function goToManage() {
  await router.push('/activities/manage')
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
  await loadActivities()
})
</script>

<template>
  <main class="page-shell animated-in">
    <el-card class="section-card" shadow="never">
      <el-row justify="space-between" align="middle" :gutter="12">
        <el-col :xs="24" :sm="16">
          <h2 class="section-title">校园活动</h2>
          <p style="margin: 0; color: var(--text-sub)">浏览、报名校园精彩活动</p>
        </el-col>
        <el-col :xs="24" :sm="8" style="text-align: right">
          <el-button style="margin-right: 8px" @click="goBack">返回首页</el-button>
          <el-button v-if="isAdmin" type="primary" @click="goToManage">活动管理</el-button>
        </el-col>
      </el-row>
    </el-card>

    <el-card class="section-card" shadow="never">
      <el-row :gutter="12" style="margin-bottom: 16px">
        <el-col :span="8">
          <el-input
            v-model="filters.keyword"
            placeholder="搜索活动标题/地点"
            clearable
            @keyup.enter="loadActivities"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-col>
        <el-col :span="6">
          <el-select v-model="filters.status" style="width: 100%" placeholder="按状态筛选" clearable @change="loadActivities">
            <el-option label="报名中" value="published" />
            <el-option label="进行中" value="ongoing" />
            <el-option label="已结束" value="ended" />
          </el-select>
        </el-col>
        <el-col :span="5">
          <el-checkbox v-model="filters.onlyFree" @change="loadActivities">仅看免费活动</el-checkbox>
        </el-col>
        <el-col :span="5" style="text-align: right">
          <el-button type="primary" @click="loadActivities">搜索</el-button>
        </el-col>
      </el-row>

      <el-skeleton :loading="loading" animated :rows="6">
        <template #default>
          <div v-if="activities.length === 0" style="text-align: center; padding: 60px 0; color: var(--text-sub)">
            暂无活动数据
          </div>
          <el-row v-else :gutter="16">
            <el-col v-for="activity in activities" :key="activity.id" :xs="24" :sm="12" :md="8" :lg="6" style="margin-bottom: 16px">
              <el-card
                class="activity-card"
                shadow="hover"
                @click="openActivityDetail(activity)"
                style="cursor: pointer; height: 100%"
              >
                <div v-if="activity.cover_image" class="activity-cover">
                  <img :src="activity.cover_image" :alt="activity.title" style="width: 100%; height: 160px; object-fit: cover; border-radius: 8px" />
                </div>
                <div v-else class="activity-cover-placeholder">
                  <el-icon style="font-size: 48px; color: var(--text-sub)"><Picture /></el-icon>
                </div>
                <div class="activity-title">{{ activity.title }}</div>
                <div class="activity-meta">
                  <el-tag size="small" :type="statusMap[activity.status]?.type || 'info'" effect="plain">
                    {{ statusMap[activity.status]?.label || activity.status }}
                  </el-tag>
                  <el-tag v-if="activity.require_approval" size="small" type="warning" effect="plain" style="margin-left: 6px">需审核</el-tag>
                  <el-tag v-if="activity.require_payment" size="small" type="danger" effect="plain" style="margin-left: 6px">
                    ¥ {{ formatMoney(activity.fee_amount) }}
                  </el-tag>
                  <el-tag v-else size="small" type="success" effect="plain" style="margin-left: 6px">免费</el-tag>
                </div>
                <div class="activity-info">
                  <div class="info-row">
                    <el-icon><Location /></el-icon>
                    <span>{{ activity.location }}</span>
                  </div>
                  <div class="info-row">
                    <el-icon><Clock /></el-icon>
                    <span>{{ formatDateTime(activity.start_time) }}</span>
                  </div>
                  <div class="info-row">
                    <el-icon><User /></el-icon>
                    <span>{{ activity.registered_count || 0 }} / {{ activity.max_participants }} 人</span>
                    <el-tag v-if="activity.is_full" size="small" type="danger" style="margin-left: 6px">已满</el-tag>
                  </div>
                </div>
                <div v-if="activity.average_rating" class="activity-rating">
                  <el-rate :model-value="Number(activity.average_rating)" disabled size="small" />
                  <span style="margin-left: 6px; color: var(--text-sub)">{{ activity.average_rating }} 分</span>
                </div>
              </el-card>
            </el-col>
          </el-row>
        </template>
      </el-skeleton>
    </el-card>
  </main>
</template>

<script>
import { Search, Picture, Location, Clock, User } from '@element-plus/icons-vue'
export default {
  components: { Search, Picture, Location, Clock, User },
}
</script>

<style scoped>
.activity-card {
  display: flex;
  flex-direction: column;
  transition: transform 0.2s ease;
}
.activity-card:hover {
  transform: translateY(-4px);
}
.activity-cover,
.activity-cover-placeholder {
  width: 100%;
  height: 160px;
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--el-fill-color-light);
}
.activity-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 8px;
  line-height: 1.4;
  color: var(--text-primary);
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  min-height: 44px;
}
.activity-meta {
  margin-bottom: 10px;
}
.activity-info {
  color: var(--text-sub);
  font-size: 13px;
}
.info-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}
.activity-rating {
  margin-top: 8px;
  display: flex;
  align-items: center;
}
</style>
