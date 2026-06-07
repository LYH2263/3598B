<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  Bell,
  Search,
  Refresh,
  Warning,
  Money,
  User,
  Stop,
  Play,
  Plus,
  DataAnalysis,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'

import { useReminderStore } from '../stores/reminder'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const reminderStore = useReminderStore()
const authStore = useAuthStore()

const activeTab = ref('list')
const loading = ref(false)
const scanLoading = ref(false)

const filters = reactive({
  status: '',
  trigger_type: '',
  keyword: '',
  user_id: '',
  page: 1,
  page_size: 20,
})

const stats = computed(() => reminderStore.adminStats)

const triggerTypeOptions = [
  { label: '全部类型', value: '' },
  { label: '余额低于阈值', value: 'low_balance' },
  { label: '久未充值预计欠费', value: 'no_recharge_predicted_overdue' },
  { label: '账单临近到期', value: 'bill_due_soon' },
  { label: '账单逾期', value: 'bill_overdue' },
]

const statusOptions = [
  { label: '全部状态', value: '' },
  { label: '待处理', value: 'pending' },
  { label: '已处理', value: 'handled' },
  { label: '自动解决', value: 'resolved_auto' },
  { label: '已停止', value: 'stopped' },
]

const triggerTypeMap = {
  low_balance: { label: '余额不足', type: 'warning' },
  no_recharge_predicted_overdue: { label: '久未充值', type: 'warning' },
  bill_due_soon: { label: '账单即将到期', type: 'info' },
  bill_overdue: { label: '账单已逾期', type: 'danger' },
}

const statusMap = {
  pending: { label: '待处理', type: 'warning' },
  handled: { label: '已处理', type: 'success' },
  resolved_auto: { label: '自动解决', type: 'info' },
  stopped: { label: '已停止', type: 'info' },
}

const channelMap = {
  inapp: { label: '站内', type: 'primary' },
  email: { label: '邮件', type: 'success' },
  parent: { label: '家长', type: 'warning' },
  admin_ticket: { label: '工单', type: 'danger' },
}

const triggerDialogVisible = ref(false)
const triggerForm = reactive({
  user_id: null,
  trigger_type: 'low_balance',
  title: '',
  content: '',
  related_bill_id: null,
})

const stopDialogVisible = ref(false)
const stopForm = reactive({
  user_id: null,
  username: '',
  reason: '',
})

async function loadStats() {
  await reminderStore.fetchAdminStats()
}

async function loadList() {
  loading.value = true
  try {
    const params = { ...filters }
    if (!params.status) delete params.status
    if (!params.trigger_type) delete params.trigger_type
    if (!params.keyword) delete params.keyword
    if (!params.user_id) delete params.user_id
    await reminderStore.fetchAdminReminders(params)
  } finally {
    loading.value = false
  }
}

async function loadExemptions() {
  loading.value = true
  try {
    await reminderStore.fetchExemptions(true)
  } finally {
    loading.value = false
  }
}

function handleTabChange(tab) {
  if (tab === 'list') loadList()
  if (tab === 'exemptions') loadExemptions()
}

async function handleSearch() {
  filters.page = 1
  await loadList()
}

async function handlePageChange(page) {
  filters.page = page
  await loadList()
}

async function handleRunScan() {
  try {
    scanLoading.value = true
    const result = await reminderStore.runAdminScan()
    ElMessage.success(
      `扫描完成：新建${result.scan.created}条，升级${result.escalate.escalated}条，自动解决${result.resolve.resolved}条`
    )
    await Promise.all([loadStats(), loadList()])
  } catch (e) {
    ElNotification.error({ title: '扫描失败', message: e?.response?.data?.detail || '请稍后重试' })
  } finally {
    scanLoading.value = false
  }
}

function openTriggerDialog() {
  Object.assign(triggerForm, {
    user_id: null,
    trigger_type: 'low_balance',
    title: '',
    content: '',
    related_bill_id: null,
  })
  triggerDialogVisible.value = true
}

async function submitTrigger() {
  if (!triggerForm.user_id || !triggerForm.title || !triggerForm.content) {
    ElMessage.warning('请填写完整信息')
    return
  }
  try {
    await reminderStore.triggerManualReminder({ ...triggerForm })
    ElMessage.success('催缴提醒已发送')
    triggerDialogVisible.value = false
    await loadList()
  } catch (e) {
    ElNotification.error({ title: '发送失败', message: e?.response?.data?.detail || '请稍后重试' })
  }
}

function openStopDialog(reminder) {
  stopForm.user_id = reminder.user_id || (typeof reminder.user === 'object' ? reminder.user.id : reminder.user)
  stopForm.username = reminder.username || reminder.user?.username || ''
  stopForm.reason = ''
  stopDialogVisible.value = true
}

async function submitStop() {
  try {
    await reminderStore.stopAllForUser(stopForm.user_id, stopForm.reason)
    ElMessage.success('已停止对该学生的所有催缴')
    stopDialogVisible.value = false
    await Promise.all([loadStats(), loadList()])
  } catch (e) {
    ElNotification.error({ title: '操作失败', message: e?.response?.data?.detail || '请稍后重试' })
  }
}

async function handleResume(exemption) {
  try {
    await ElMessageBox.confirm(
      `确定要恢复对 ${exemption.username} 的催缴吗？`,
      '恢复催缴',
      { type: 'warning' }
    )
    await reminderStore.resumeForUser(exemption.user?.id || exemption.id)
    ElMessage.success('已恢复催缴')
    await Promise.all([loadStats(), loadExemptions()])
  } catch (e) {
    if (e !== 'cancel') {
      ElNotification.error({ title: '操作失败', message: e?.response?.data?.detail || '请稍后重试' })
    }
  }
}

function formatDate(dt) {
  if (!dt) return '-'
  return new Date(dt).toLocaleString('zh-CN', { hour12: false })
}

onMounted(() => {
  loadStats()
  loadList()
})
</script>

<template>
  <div class="p-6 max-w-7xl mx-auto">
    <div class="mb-6 flex items-center justify-between flex-wrap gap-4">
      <div>
        <h1 class="text-2xl font-bold text-gray-800 flex items-center gap-2">
          <DataAnalysis class="text-blue-500" />
          催缴管理
        </h1>
        <p class="text-gray-500 mt-1">查看和管理全平台催缴提醒</p>
      </div>
      <div class="flex gap-2">
        <el-button type="primary" :icon="Plus" @click="openTriggerDialog">
          手动触发催缴
        </el-button>
        <el-button
          type="warning"
          :icon="Refresh"
          :loading="scanLoading"
          @click="handleRunScan"
        >
          立即执行扫描
        </el-button>
      </div>
    </div>

    <div v-if="stats" class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      <div class="bg-white rounded-lg shadow-sm p-4">
        <div class="text-gray-500 text-sm">待处理</div>
        <div class="text-2xl font-bold text-orange-500 mt-1">{{ stats.total_pending }}</div>
      </div>
      <div class="bg-white rounded-lg shadow-sm p-4">
        <div class="text-gray-500 text-sm">已处理</div>
        <div class="text-2xl font-bold text-green-500 mt-1">{{ stats.total_handled }}</div>
      </div>
      <div class="bg-white rounded-lg shadow-sm p-4">
        <div class="text-gray-500 text-sm">自动解决</div>
        <div class="text-2xl font-bold text-blue-500 mt-1">{{ stats.total_resolved_auto }}</div>
      </div>
      <div class="bg-white rounded-lg shadow-sm p-4">
        <div class="text-gray-500 text-sm">已免除催缴学生</div>
        <div class="text-2xl font-bold text-gray-500 mt-1">{{ stats.exempted_count }}</div>
      </div>
    </div>

    <el-tabs v-model="activeTab" @tab-change="handleTabChange">
      <el-tab-pane label="催缴列表" name="list">
        <div class="bg-white rounded-lg shadow-sm p-4 mb-4">
          <div class="flex flex-wrap gap-4 items-end">
            <el-select
              v-model="filters.status"
              placeholder="状态"
              style="width: 140px"
              clearable
            >
              <el-option
                v-for="opt in statusOptions"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
            <el-select
              v-model="filters.trigger_type"
              placeholder="触发类型"
              style="width: 180px"
              clearable
            >
              <el-option
                v-for="opt in triggerTypeOptions"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
            <el-input
              v-model="filters.keyword"
              placeholder="搜索用户名/标题/内容"
              style="width: 240px"
              clearable
              :prefix-icon="Search"
              @keyup.enter="handleSearch"
            />
            <el-button type="primary" :icon="Search" @click="handleSearch">筛选</el-button>
            <el-button @click="() => {
              Object.assign(filters, { status: '', trigger_type: '', keyword: '', user_id: '', page: 1 })
              loadList()
            }">重置</el-button>
          </div>
        </div>

        <el-table
          v-loading="loading"
          :data="reminderStore.adminReminders"
          stripe
          style="width: 100%"
        >
          <el-table-column prop="username" label="学生" width="140">
            <template #default="{ row }">
              <div class="flex items-center gap-1">
                <el-icon><User /></el-icon>
                <span>{{ row.username }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="类型" width="140">
            <template #default="{ row }">
              <el-tag :type="triggerTypeMap[row.trigger_type]?.type || 'info'" size="small">
                {{ triggerTypeMap[row.trigger_type]?.label || row.trigger_type }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="statusMap[row.status]?.type || 'info'" size="small">
                {{ statusMap[row.status]?.label || row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="当前渠道" width="100">
            <template #default="{ row }">
              <el-tag v-if="row.status === 'pending'" :type="channelMap[row.current_channel]?.type" size="small">
                {{ channelMap[row.current_channel]?.label }}
              </el-tag>
              <span v-else class="text-gray-400">-</span>
            </template>
          </el-table-column>
          <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
          <el-table-column prop="content" label="内容" min-width="280" show-overflow-tooltip />
          <el-table-column label="创建时间" width="160">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }">
              <el-button
                v-if="row.status === 'pending'"
                type="danger"
                size="small"
                :icon="Stop"
                @click="openStopDialog(row)"
              >
                停止催缴
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="mt-4 flex justify-end">
          <el-pagination
            v-model:current-page="filters.page"
            v-model:page-size="filters.page_size"
            :page-sizes="[10, 20, 50, 100]"
            :total="reminderStore.adminTotal"
            layout="total, sizes, prev, pager, next, jumper"
            @current-change="handlePageChange"
            @size-change="() => { filters.page = 1; loadList() }"
          />
        </div>
      </el-tab-pane>

      <el-tab-pane label="免除催缴名单" name="exemptions">
        <el-table v-loading="loading" :data="reminderStore.exemptions" stripe style="width: 100%">
          <el-table-column prop="username" label="学生" width="160" />
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.is_exempted ? 'danger' : 'success'" size="small">
                {{ row.is_exempted ? '已免除' : '正常' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="reason" label="免除原因" min-width="240" show-overflow-tooltip />
          <el-table-column label="设置时间" width="160">
            <template #default="{ row }">
              {{ formatDate(row.exempted_at) }}
            </template>
          </el-table-column>
          <el-table-column prop="exempted_by_name" label="设置人" width="120" />
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button
                v-if="row.is_exempted"
                type="success"
                size="small"
                :icon="Play"
                @click="handleResume(row)"
              >
                恢复催缴
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="triggerDialogVisible" title="手动触发催缴" width="520px">
      <el-form :model="triggerForm" label-width="90px">
        <el-form-item label="用户ID">
          <el-input-number v-model="triggerForm.user_id" :min="1" controls-position="right" />
        </el-form-item>
        <el-form-item label="触发类型">
          <el-select v-model="triggerForm.trigger_type" style="width: 100%">
            <el-option
              v-for="opt in triggerTypeOptions.filter((o) => o.value)"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="triggerForm.title" maxlength="200" show-word-limit />
        </el-form-item>
        <el-form-item label="内容">
          <el-input
            v-model="triggerForm.content"
            type="textarea"
            :rows="4"
            maxlength="2000"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="关联账单ID">
          <el-input-number v-model="triggerForm.related_bill_id" :min="1" controls-position="right" />
          <span class="text-xs text-gray-400 ml-2">可选</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="triggerDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitTrigger">发送</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="stopDialogVisible" title="停止对该学生的所有催缴" width="460px">
      <el-alert
        type="warning"
        :closable="false"
        class="mb-4"
        show-icon
        title="此操作将停止该学生所有当前待处理的催缴提醒，并免除后续自动催缴。"
      />
      <el-form :model="stopForm" label-width="90px">
        <el-form-item label="学生">
          <el-input v-model="stopForm.username" disabled />
        </el-form-item>
        <el-form-item label="原因">
          <el-input
            v-model="stopForm.reason"
            type="textarea"
            :rows="3"
            maxlength="500"
            show-word-limit
            placeholder="请输入停止催缴的原因"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="stopDialogVisible = false">取消</el-button>
        <el-button type="danger" @click="submitStop">确认停止</el-button>
      </template>
    </el-dialog>
  </div>
</template>
