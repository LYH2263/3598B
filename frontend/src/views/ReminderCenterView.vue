<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import { Bell, Check, Money, Warning, Clock, CircleCheck } from '@element-plus/icons-vue'

import { useReminderStore } from '../stores/reminder'

const router = useRouter()
const reminderStore = useReminderStore()

const loading = ref(false)
const activeStatus = ref('')

const statusOptions = [
  { label: '全部', value: '' },
  { label: '待处理', value: 'pending' },
  { label: '已处理', value: 'handled' },
  { label: '自动解决', value: 'resolved_auto' },
  { label: '已停止', value: 'stopped' },
]

const triggerTypeMap = {
  low_balance: { label: '余额不足', type: 'warning', icon: Money },
  no_recharge_predicted_overdue: { label: '久未充值', type: 'warning', icon: Clock },
  bill_due_soon: { label: '账单即将到期', type: 'info', icon: Bell },
  bill_overdue: { label: '账单已逾期', type: 'danger', icon: Warning },
}

const statusMap = {
  pending: { label: '待处理', type: 'warning' },
  handled: { label: '已处理', type: 'success' },
  resolved_auto: { label: '自动解决', type: 'info' },
  stopped: { label: '已停止', type: 'info' },
}

const channelMap = {
  inapp: { label: '站内通知', type: 'primary' },
  email: { label: '邮件通知', type: 'success' },
  parent: { label: '家长通知', type: 'warning' },
  admin_ticket: { label: '管理员工单', type: 'danger' },
}

const filteredReminders = computed(() => {
  if (!activeStatus.value) return reminderStore.myReminders
  return reminderStore.myReminders.filter((r) => r.status === activeStatus.value)
})

async function loadReminders() {
  loading.value = true
  try {
    await reminderStore.fetchMyReminders(activeStatus.value || undefined)
  } finally {
    loading.value = false
  }
}

async function handleMarkHandled(reminder) {
  try {
    const { value: note } = await ElMessageBox.prompt(
      '请输入处理备注（可选）',
      '标记为已处理',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        inputPlaceholder: '请输入处理备注...',
        inputValidator: () => true,
      }
    )
    await reminderStore.markHandled(reminder.id, note || '')
    ElMessage.success('已标记为已处理')
  } catch (e) {
    if (e !== 'cancel') {
      ElNotification.error({ title: '操作失败', message: e?.response?.data?.detail || '请稍后重试' })
    }
  }
}

function goRecharge() {
  router.push('/dashboard')
}

function formatDate(dt) {
  if (!dt) return '-'
  return new Date(dt).toLocaleString('zh-CN', { hour12: false })
}

onMounted(() => {
  loadReminders()
})
</script>

<template>
  <div class="p-6 max-w-6xl mx-auto">
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-gray-800 flex items-center gap-2">
        <Bell class="text-blue-500" />
        提醒中心
      </h1>
      <p class="text-gray-500 mt-1">
        您当前有
        <span class="text-red-500 font-semibold">{{ reminderStore.myPendingCount }}</span>
        条待处理的催缴提醒
      </p>
    </div>

    <div class="bg-white rounded-lg shadow-sm p-4 mb-4">
      <el-radio-group v-model="activeStatus" @change="loadReminders">
        <el-radio-button
          v-for="opt in statusOptions"
          :key="opt.value"
          :label="opt.value"
        >
          {{ opt.label }}
        </el-radio-button>
      </el-radio-group>
    </div>

    <div v-loading="loading" class="space-y-3">
      <el-empty v-if="filteredReminders.length === 0 && !loading" description="暂无提醒" />

      <div
        v-for="reminder in filteredReminders"
        :key="reminder.id"
        class="bg-white rounded-lg shadow-sm border-l-4 p-4 transition hover:shadow-md"
        :class="{
          'border-orange-400': reminder.trigger_type === 'low_balance',
          'border-yellow-400': reminder.trigger_type === 'no_recharge_predicted_overdue',
          'border-blue-400': reminder.trigger_type === 'bill_due_soon',
          'border-red-500': reminder.trigger_type === 'bill_overdue',
        }"
      >
        <div class="flex items-start justify-between gap-4">
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 flex-wrap mb-2">
              <el-tag :type="triggerTypeMap[reminder.trigger_type]?.type || 'info'" size="small">
                <el-icon class="mr-1">
                  <component :is="triggerTypeMap[reminder.trigger_type]?.icon || Bell" />
                </el-icon>
                {{ triggerTypeMap[reminder.trigger_type]?.label || reminder.trigger_type }}
              </el-tag>
              <el-tag :type="statusMap[reminder.status]?.type || 'info'" size="small" effect="plain">
                {{ statusMap[reminder.status]?.label || reminder.status }}
              </el-tag>
              <el-tag
                v-if="reminder.status === 'pending'"
                :type="channelMap[reminder.current_channel]?.type || 'primary'"
                size="small"
                effect="dark"
              >
                当前：{{ channelMap[reminder.current_channel]?.label }}
              </el-tag>
              <span class="text-xs text-gray-400 ml-auto">
                {{ formatDate(reminder.created_at) }}
              </span>
            </div>

            <h3 class="text-lg font-semibold text-gray-800 mb-1">{{ reminder.title }}</h3>
            <p class="text-gray-600 whitespace-pre-wrap">{{ reminder.content }}</p>

            <div v-if="reminder.handled_note" class="mt-3 p-2 bg-gray-50 rounded text-sm text-gray-600">
              <strong>处理备注：</strong>{{ reminder.handled_note }}
              <span class="text-gray-400 ml-2">{{ formatDate(reminder.handled_at) }}</span>
            </div>

            <div v-if="reminder.events && reminder.events.length > 0" class="mt-3">
              <p class="text-xs text-gray-400 mb-1">通知历史：</p>
              <div class="flex flex-wrap gap-1">
                <el-tag
                  v-for="evt in reminder.events"
                  :key="evt.id"
                  :type="channelMap[evt.channel]?.type || 'info'"
                  size="small"
                  effect="plain"
                >
                  {{ channelMap[evt.channel]?.label }} · {{ formatDate(evt.sent_at) }}
                </el-tag>
              </div>
            </div>
          </div>

          <div v-if="reminder.status === 'pending'" class="flex flex-col gap-2 shrink-0">
            <el-button type="primary" :icon="Check" @click="handleMarkHandled(reminder)">
              标记已处理
            </el-button>
            <el-button type="success" :icon="Money" @click="goRecharge">
              立即充值
            </el-button>
          </div>
          <div v-else-if="reminder.status === 'handled'" class="shrink-0">
            <el-icon class="text-green-500 text-2xl"><CircleCheck /></el-icon>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
