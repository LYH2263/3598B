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
const activeGroup = ref('')
const groups = ref([])
const configItems = ref([])
const campuses = ref([])
const selectedCampusId = ref(null)
const changeLogs = ref([])
const logFilters = reactive({
  group: '',
  campus_id: '',
})

const editingItem = ref(null)
const editDialogVisible = ref(false)
const editForm = reactive({
  value: '',
  remark: '',
})

const groupLabelMap = {
  pricing: '费率与价格',
  wallet: '钱包与充值',
  security: '安全与认证',
  notification: '通知与推送',
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

function getGroupLabel(group) {
  return groupLabelMap[group] || group
}

async function loadGroups() {
  const { data } = await http.get('/config/groups/')
  groups.value = data
  if (!activeGroup.value && groups.value.length > 0) {
    activeGroup.value = groups.value[0]
  }
}

async function loadCampuses() {
  const { data } = await http.get('/config/campuses/simple/')
  campuses.value = data
}

async function loadConfigs() {
  if (!activeGroup.value) return
  loading.value = true
  try {
    const params = {}
    if (selectedCampusId.value) params.campus_id = selectedCampusId.value
    const { data } = await http.get(`/config/groups/${activeGroup.value}/`, { params })
    configItems.value = data
  } finally {
    loading.value = false
  }
}

async function loadChangeLogs() {
  const params = {}
  if (logFilters.group) params.group = logFilters.group
  if (logFilters.campus_id) params.campus_id = logFilters.campus_id
  const { data } = await http.get('/config/change-logs/', { params })
  changeLogs.value = data
}

async function initConfig() {
  try {
    const { data } = await http.post('/config/init/')
    ElNotification({ title: '初始化完成', message: data.detail, type: 'success' })
    await Promise.all([loadGroups(), loadConfigs()])
  } catch (_e) {}
}

function openEditDialog(item) {
  editingItem.value = item
  const currentValue = selectedCampusId.value && item.has_campus_override
    ? item.campus_value
    : (selectedCampusId.value ? item.global_value : item.effective_value)
  editForm.value = currentValue !== undefined ? currentValue : (item.default_value || '')
  editForm.remark = ''
  editDialogVisible.value = true
}

async function saveConfig() {
  if (!editingItem.value) return
  actionLoading.value = true
  try {
    await http.post(
      `/config/groups/${editingItem.value.group}/keys/${editingItem.value.key}/`,
      {
        value: String(editForm.value),
        campus_id: selectedCampusId.value || null,
        remark: editForm.remark,
      }
    )
    ElNotification({ title: '保存成功', message: '配置已更新，立即生效。', type: 'success' })
    editDialogVisible.value = false
    await Promise.all([loadConfigs(), loadChangeLogs()])
  } finally {
    actionLoading.value = false
  }
}

async function clearCampusOverride(item) {
  try {
    await ElMessageBox.confirm(
      `确定要清除「${item.description}」的校区覆盖配置吗？清除后将使用全局配置。`,
      '清除确认',
      { confirmButtonText: '清除', cancelButtonText: '取消', type: 'warning' }
    )
  } catch (_e) {
    return
  }
  actionLoading.value = true
  try {
    await http.post(
      `/config/groups/${item.group}/keys/${item.key}/`,
      {
        value: '',
        campus_id: selectedCampusId.value,
        remark: '清除校区覆盖',
      }
    )
    ElNotification({ title: '清除成功', message: '已恢复使用全局配置。', type: 'success' })
    await Promise.all([loadConfigs(), loadChangeLogs()])
  } finally {
    actionLoading.value = false
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
  if (authStore.user?.profile?.role !== 'admin') {
    ElMessage.warning('仅管理员可访问')
    await router.push('/dashboard')
    return
  }
  await Promise.all([loadGroups(), loadCampuses(), loadChangeLogs()])
  await loadConfigs()
})
</script>

<template>
  <main class="page-shell animated-in">
    <el-card class="section-card" shadow="never">
      <el-row justify="space-between" align="middle" :gutter="12">
        <el-col :xs="24" :sm="16">
          <h2 class="section-title">⚙️ 系统配置中心</h2>
          <p style="margin: 0; color: var(--text-sub)">
            按分组管理系统运行参数，支持全局默认 + 校区维度覆盖，变更实时生效并全程留痕。
          </p>
        </el-col>
        <el-col :xs="24" :sm="8" style="text-align: right">
          <el-button style="margin-right: 8px" @click="router.push('/campus-manage')">🏫 校区管理</el-button>
          <el-button style="margin-right: 8px" @click="router.push('/dashboard')">返回首页</el-button>
          <el-button type="primary" plain @click="initConfig">初始化默认配置</el-button>
          <el-button type="danger" plain @click="logout">退出登录</el-button>
        </el-col>
      </el-row>
    </el-card>

    <el-row :gutter="16">
      <el-col :xs="24" :md="16">
        <el-card class="section-card" shadow="never">
          <el-row :gutter="12" style="margin-bottom: 14px" align="middle">
            <el-col :span="8">
              <el-select v-model="activeGroup" style="width: 100%" placeholder="选择配置分组" @change="loadConfigs">
                <el-option v-for="g in groups" :key="g" :label="getGroupLabel(g)" :value="g" />
              </el-select>
            </el-col>
            <el-col :span="8">
              <el-select v-model="selectedCampusId" style="width: 100%" placeholder="选择校区查看/编辑覆盖" clearable @change="loadConfigs">
                <el-option label="全局默认配置" :value="null" />
                <el-option v-for="c in campuses" :key="c.id" :label="`${c.name} (${c.code})`" :value="c.id" />
              </el-select>
            </el-col>
            <el-col :span="8" style="text-align: right">
              <el-tag v-if="selectedCampusId" type="warning" effect="plain">正在编辑「校区覆盖」配置</el-tag>
              <el-tag v-else type="success" effect="plain">正在编辑「全局默认」配置</el-tag>
            </el-col>
          </el-row>

          <el-skeleton :loading="loading" animated :rows="6">
            <template #default>
              <el-table :data="configItems" stripe border empty-text="暂无配置项，请点击「初始化默认配置」">
                <el-table-column label="配置键" min-width="200">
                  <template #default="{ row }">
                    <div style="font-weight: 600">{{ row.key }}</div>
                    <div style="color: var(--text-sub); font-size: 12px; margin-top: 2px">{{ row.description }}</div>
                  </template>
                </el-table-column>
                <el-table-column label="值类型" width="100">
                  <template #default="{ row }">
                    <el-tag size="small" effect="plain">{{ row.value_type_label }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="全局默认值" min-width="130">
                  <template #default="{ row }">
                    <code style="background: var(--el-fill-color-light); padding: 2px 6px; border-radius: 4px">
                      {{ row.global_value || '(未设置)' }}
                    </code>
                  </template>
                </el-table-column>
                <el-table-column v-if="selectedCampusId" label="校区覆盖值" min-width="130">
                  <template #default="{ row }">
                    <code v-if="row.has_campus_override" style="background: #eaf4ff; color: #409eff; padding: 2px 6px; border-radius: 4px">
                      {{ row.campus_value }}
                    </code>
                    <span v-else style="color: var(--text-sub)">（使用全局）</span>
                  </template>
                </el-table-column>
                <el-table-column label="当前有效值" min-width="130">
                  <template #default="{ row }">
                    <strong style="color: var(--el-color-primary)">{{ row.effective_value }}</strong>
                  </template>
                </el-table-column>
                <el-table-column label="取值范围" min-width="140">
                  <template #default="{ row }">
                    <span v-if="row.min_value !== null || row.max_value !== null">
                      {{ row.min_value ?? '-∞' }} ~ {{ row.max_value ?? '+∞' }}
                    </span>
                    <span v-else style="color: var(--text-sub)">无限制</span>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="180" fixed="right">
                  <template #default="{ row }">
                    <el-space>
                      <el-button size="small" type="primary" plain :disabled="!row.is_editable" @click="openEditDialog(row)">
                        {{ selectedCampusId ? '编辑校区值' : '编辑全局值' }}
                      </el-button>
                      <el-button
                        v-if="selectedCampusId && row.has_campus_override"
                        size="small"
                        type="danger"
                        plain
                        @click="clearCampusOverride(row)"
                      >清除覆盖</el-button>
                    </el-space>
                  </template>
                </el-table-column>
              </el-table>
            </template>
          </el-skeleton>
        </el-card>
      </el-col>

      <el-col :xs="24" :md="8">
        <el-card class="section-card" shadow="never">
          <h3 class="section-title" style="margin-top: 0">📋 变更日志</h3>
          <el-row :gutter="8" style="margin-bottom: 10px">
            <el-col :span="12">
              <el-select v-model="logFilters.group" style="width: 100%" placeholder="按分组筛选" clearable @change="loadChangeLogs">
                <el-option v-for="g in groups" :key="g" :label="getGroupLabel(g)" :value="g" />
              </el-select>
            </el-col>
            <el-col :span="12">
              <el-select v-model="logFilters.campus_id" style="width: 100%" placeholder="按校区筛选" clearable @change="loadChangeLogs">
                <el-option label="仅全局" value="0" />
                <el-option v-for="c in campuses" :key="c.id" :label="c.name" :value="String(c.id)" />
              </el-select>
            </el-col>
          </el-row>
          <el-timeline style="max-height: 600px; overflow-y: auto">
            <el-timeline-item
              v-for="log in changeLogs"
              :key="log.id"
              :timestamp="formatDateTime(log.changed_at)"
              type="primary"
            >
              <div style="font-weight: 600">{{ log.config_key_group }}.{{ log.config_key_name }}</div>
              <div style="color: var(--text-sub); font-size: 12px">
                <el-tag size="small" effect="plain">{{ log.campus_name }}</el-tag>
                <span style="margin-left: 6px">操作人：{{ log.changed_by_username }}</span>
              </div>
              <div style="margin-top: 4px; font-size: 13px">
                <code style="color: #f56c6c">{{ log.old_value || '(空)' }}</code>
                <span style="margin: 0 6px">→</span>
                <code style="color: #67c23a">{{ log.new_value || '(空)' }}</code>
              </div>
              <div v-if="log.remark" style="color: var(--text-sub); font-size: 12px; margin-top: 2px">
                备注：{{ log.remark }}
              </div>
            </el-timeline-item>
            <div v-if="!changeLogs.length" style="color: var(--text-sub); text-align: center; padding: 20px 0">
              暂无变更记录
            </div>
          </el-timeline>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="editDialogVisible" :title="selectedCampusId ? '编辑校区配置值' : '编辑全局配置值'" width="480px">
      <div v-if="editingItem" style="margin-bottom: 14px">
        <div style="color: var(--text-sub); font-size: 13px">配置键</div>
        <div style="font-weight: 600; margin-top: 2px">{{ editingItem.group }}.{{ editingItem.key }}</div>
        <div style="color: var(--text-sub); font-size: 13px; margin-top: 6px">{{ editingItem.description }}</div>
        <div style="color: var(--text-sub); font-size: 13px; margin-top: 6px">
          类型：<el-tag size="small" effect="plain">{{ editingItem.value_type_label }}</el-tag>
          <span v-if="editingItem.min_value !== null || editingItem.max_value !== null" style="margin-left: 8px">
            范围：{{ editingItem.min_value ?? '-∞' }} ~ {{ editingItem.max_value ?? '+∞' }}
          </span>
        </div>
      </div>
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="配置值">
          <el-switch
            v-if="editingItem?.value_type === 'boolean'"
            v-model="editForm.value"
            active-value="true"
            inactive-value="false"
            active-text="是"
            inactive-text="否"
          />
          <el-input-number
            v-else-if="editingItem?.value_type === 'integer'"
            v-model="editForm.value"
            :min="editingItem.min_value ? Number(editingItem.min_value) : undefined"
            :max="editingItem.max_value ? Number(editingItem.max_value) : undefined"
            :precision="0"
            style="width: 100%"
          />
          <el-input-number
            v-else-if="editingItem?.value_type === 'decimal'"
            v-model="editForm.value"
            :min="editingItem.min_value ? Number(editingItem.min_value) : undefined"
            :max="editingItem.max_value ? Number(editingItem.max_value) : undefined"
            :precision="4"
            :step="0.01"
            style="width: 100%"
          />
          <el-input
            v-else-if="editingItem?.value_type === 'json'"
            v-model="editForm.value"
            type="textarea"
            :rows="4"
            placeholder="请输入 JSON 字符串"
          />
          <el-select
            v-else-if="editingItem?.options?.length"
            v-model="editForm.value"
            style="width: 100%"
          >
            <el-option v-for="opt in editingItem.options" :key="opt.value || opt" :label="opt.label || opt" :value="String(opt.value || opt)" />
          </el-select>
          <el-input v-else v-model="editForm.value" />
        </el-form-item>
        <el-form-item label="变更备注（可选）">
          <el-input v-model="editForm.remark" placeholder="请输入本次变更的原因或说明" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="actionLoading" @click="saveConfig">保存变更</el-button>
      </template>
    </el-dialog>
  </main>
</template>
