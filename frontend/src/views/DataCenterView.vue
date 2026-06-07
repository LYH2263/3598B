<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'

import { useAuthStore } from '../stores/auth'
import http from '../utils/http'

const router = useRouter()
const authStore = useAuthStore()

const activeTab = ref('tasks')
const loading = ref(false)
const dataTypes = ref([])

function formatDateTime(value) {
  if (!value) return '--'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hour12: false,
  }).format(date)
}

function getStatusTagType(status) {
  const map = {
    submitted: 'info',
    running: 'warning',
    success: 'success',
    failed: 'danger',
    partial: 'warning',
  }
  return map[status] || 'info'
}

function getTaskTypeLabel(type) {
  const map = { import: '导入', export: '导出' }
  return map[type] || type
}

function getDataTypeLabel(key) {
  const dt = dataTypes.value.find(d => d.key === key)
  return dt ? dt.label : key
}

async function loadDataTypes() {
  try {
    const { data } = await http.get('/data-center/data-types/')
    dataTypes.value = data
  } catch (_e) {}
}

// ============ 任务列表 ============
const tasks = ref([])
const taskStats = ref({})
const taskTotal = ref(0)
const taskFilters = reactive({
  task_type: '',
  data_type: '',
  status: '',
  keyword: '',
  page: 1,
  page_size: 20,
})
const taskLoading = ref(false)

async function loadTasks() {
  taskLoading.value = true
  try {
    const params = { ...taskFilters }
    const { data } = await http.get('/data-center/tasks/', { params })
    tasks.value = data.items
    taskTotal.value = data.total
  } finally {
    taskLoading.value = false
  }
}

async function loadTaskStats() {
  try {
    const { data } = await http.get('/data-center/tasks/stats/')
    taskStats.value = data
  } catch (_e) {}
}

async function rerunTask(task) {
  try {
    await ElMessageBox.confirm(
      `确定要重新执行「${getTaskTypeLabel(task.task_type)} - ${getDataTypeLabel(task.data_type)}」任务吗？`,
      '重跑确认',
      { confirmButtonText: '执行重跑', cancelButtonText: '取消', type: 'warning' },
    )
  } catch (_e) { return }
  try {
    const { data } = await http.post('/data-center/tasks/rerun/', { task_id: task.id })
    ElNotification({ title: '重跑已提交', message: data.detail, type: 'success' })
    await loadTasks()
  } catch (_e) {}
}

function downloadTaskResult(task) {
  const token = localStorage.getItem('access_token') || ''
  const url = `/api/data-center/tasks/${task.id}/download/`
  const link = document.createElement('a')
  link.href = url
  link.download = ''
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

function downloadTaskErrors(task) {
  const url = `/api/data-center/tasks/${task.id}/errors/download/`
  const link = document.createElement('a')
  link.href = url
  link.download = ''
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

// ============ 导入 Wizard ============
const importStep = ref(0)
const importDataType = ref('')
const importFile = ref(null)
const importFileName = ref('')
const importPreviewData = ref(null)
const importTaskId = ref(null)
const correctedRows = reactive({})
const importSubmitting = ref(false)
const importUploadLoading = ref(false)

function resetImport() {
  importStep.value = 0
  importDataType.value = ''
  importFile.value = null
  importFileName.value = ''
  importPreviewData.value = null
  importTaskId.value = null
  Object.keys(correctedRows).forEach(k => delete correctedRows[k])
}

function onImportFileChange(uploadFile) {
  importFile.value = uploadFile.raw || uploadFile
  importFileName.value = uploadFile.name
}

async function doUploadAndPreview() {
  if (!importDataType.value) {
    ElMessage.warning('请先选择数据类型')
    return
  }
  if (!importFile.value) {
    ElMessage.warning('请选择要上传的文件')
    return
  }
  importUploadLoading.value = true
  try {
    const fd = new FormData()
    fd.append('data_type', importDataType.value)
    fd.append('file_format', importFileName.value.toLowerCase().endsWith('.xlsx') ? 'xlsx' : 'csv')
    fd.append('file', importFile.value)
    const { data } = await http.post('/data-center/import/upload/', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    importPreviewData.value = data
    importTaskId.value = data.task_id
    importStep.value = 1

    if (data.duplicate_task) {
      ElMessageBox.alert(
        `检测到相同文件已于 ${formatDateTime(data.duplicate_task.created_at)} 导入过（状态：${data.duplicate_task.status_display}）。本次导入会自动跳过已导入的行（幂等控制）。`,
        '幂等提醒',
        { type: 'warning', confirmButtonText: '我知道了' },
      )
    }
  } finally {
    importUploadLoading.value = false
  }
}

function updateCorrectedRow(rowNum, fieldKey, value) {
  if (!correctedRows[rowNum]) {
    const originalRow = importPreviewData.value.all_rows.find(r => r.row_number === rowNum)
    correctedRows[rowNum] = { ...(originalRow?.data || {}) }
  }
  correctedRows[rowNum][fieldKey] = value
}

const importErrorRows = computed(() => {
  if (!importPreviewData.value) return []
  return importPreviewData.value.all_rows.filter(r => r.errors && r.errors.length > 0)
})

async function doImportSubmit() {
  if (!importTaskId.value) return
  try {
    await ElMessageBox.confirm(
      `即将正式导入共 ${importPreviewData.value?.total_rows || 0} 行数据，其中错误 ${importPreviewData.value?.error_count || 0} 行、幂等跳过 ${importPreviewData.value?.warning_count || 0} 行。是否继续？`,
      '导入确认',
      { confirmButtonText: '开始导入', cancelButtonText: '取消', type: 'warning' },
    )
  } catch (_e) { return }

  importSubmitting.value = true
  try {
    const { data } = await http.post('/data-center/import/submit/', {
      task_id: importTaskId.value,
      corrected_rows: correctedRows,
    })
    ElNotification({
      title: '导入完成',
      message: `成功 ${data.result.success} 行，失败 ${data.result.failed} 行，跳过 ${data.result.skipped} 行。`,
      type: data.result.failed > 0 ? 'warning' : 'success',
    })
    importStep.value = 2
    await loadTasks()
  } finally {
    importSubmitting.value = false
  }
}

// ============ 导出表单 ============
const exportForm = reactive({
  data_type: '',
  file_format: 'csv',
  fields: [],
  filters: {},
})
const exportSubmitting = ref(false)

const currentExportMeta = computed(() => {
  return dataTypes.value.find(d => d.key === exportForm.data_type)
})

function toggleExportField(fieldKey) {
  const idx = exportForm.fields.indexOf(fieldKey)
  if (idx >= 0) {
    exportForm.fields.splice(idx, 1)
  } else {
    exportForm.fields.push(fieldKey)
  }
}

function selectAllExportFields() {
  if (!currentExportMeta.value) return
  exportForm.fields = currentExportMeta.value.fields.map(f => f.key)
}

function clearExportFields() {
  exportForm.fields = []
}

function resetExportForm() {
  exportForm.data_type = ''
  exportForm.file_format = 'csv'
  exportForm.fields = []
  exportForm.filters = {}
}

async function doExportSubmit() {
  if (!exportForm.data_type) {
    ElMessage.warning('请选择数据类型')
    return
  }
  exportSubmitting.value = true
  try {
    const payload = {
      data_type: exportForm.data_type,
      file_format: exportForm.file_format,
      fields: [...exportForm.fields],
      filters: {},
    }
    for (const k in exportForm.filters) {
      const v = exportForm.filters[k]
      if (v !== '' && v !== null && v !== undefined) {
        payload.filters[k] = v
      }
    }
    const { data } = await http.post('/data-center/export/submit/', payload)
    ElNotification({
      title: '导出完成',
      message: `共导出 ${data.result.total} 条记录。`,
      type: 'success',
    })
    resetExportForm()
    activeTab.value = 'tasks'
    await loadTasks()
  } finally {
    exportSubmitting.value = false
  }
}

// ============ 模板下载 ============
function downloadTemplate(dataType) {
  const url = `/api/data-center/templates/${dataType}/`
  const link = document.createElement('a')
  link.href = url
  link.download = `template_${dataType}.csv`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  ElMessage.success('模板下载已开始')
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
  await Promise.all([loadDataTypes(), loadTasks(), loadTaskStats()])
})
</script>

<template>
  <main class="page-shell animated-in">
    <el-card class="section-card" shadow="never">
      <el-row justify="space-between" align="middle" :gutter="12">
        <el-col :xs="24" :sm="16">
          <h2 class="section-title">📊 数据中心</h2>
          <p style="margin: 0; color: var(--text-sub)">
            统一的批量数据导入与导出中心。支持 4 种数据类型，导入带幂等控制与行级预校验，导出支持字段选择与筛选。
          </p>
        </el-col>
        <el-col :xs="24" :sm="8" style="text-align: right">
          <el-button @click="router.push('/dashboard')">返回首页</el-button>
        </el-col>
      </el-row>
    </el-card>

    <el-card class="section-card" shadow="never">
      <el-tabs v-model="activeTab" type="border-card">
        <!-- ============ 任务列表 Tab ============ -->
        <el-tab-pane label="📋 任务列表" name="tasks">
          <el-row :gutter="16" style="margin-bottom: 16px">
            <el-col :span="4">
              <el-card shadow="hover">
                <div style="color: var(--text-sub); font-size: 12px">全部任务</div>
                <div style="font-size: 24px; font-weight: 700; margin-top: 4px">{{ taskStats.total || 0 }}</div>
              </el-card>
            </el-col>
            <el-col :span="4">
              <el-card shadow="hover">
                <div style="color: var(--text-sub); font-size: 12px">进行中</div>
                <div style="font-size: 24px; font-weight: 700; margin-top: 4px; color: #e6a23c">{{ taskStats.running || 0 }}</div>
              </el-card>
            </el-col>
            <el-col :span="4">
              <el-card shadow="hover">
                <div style="color: var(--text-sub); font-size: 12px">待处理</div>
                <div style="font-size: 24px; font-weight: 700; margin-top: 4px; color: #909399">{{ taskStats.pending || 0 }}</div>
              </el-card>
            </el-col>
            <el-col :span="12">
              <el-row :gutter="8" align="middle" style="height: 100%">
                <el-col :span="6">
                  <el-select v-model="taskFilters.task_type" placeholder="任务类型" clearable style="width: 100%" @change="loadTasks">
                    <el-option label="全部" value="" />
                    <el-option label="导入" value="import" />
                    <el-option label="导出" value="export" />
                  </el-select>
                </el-col>
                <el-col :span="6">
                  <el-select v-model="taskFilters.data_type" placeholder="数据类型" clearable style="width: 100%" @change="loadTasks">
                    <el-option label="全部" value="" />
                    <el-option v-for="dt in dataTypes" :key="dt.key" :label="dt.label" :value="dt.key" />
                  </el-select>
                </el-col>
                <el-col :span="6">
                  <el-select v-model="taskFilters.status" placeholder="状态" clearable style="width: 100%" @change="loadTasks">
                    <el-option label="全部" value="" />
                    <el-option label="提交中" value="submitted" />
                    <el-option label="进行中" value="running" />
                    <el-option label="成功" value="success" />
                    <el-option label="部分成功" value="partial" />
                    <el-option label="失败" value="failed" />
                  </el-select>
                </el-col>
                <el-col :span="6">
                  <el-input v-model="taskFilters.keyword" placeholder="搜索文件名" clearable @keyup.enter="loadTasks" @clear="loadTasks" />
                </el-col>
              </el-row>
            </el-col>
          </el-row>

          <el-table :data="tasks" stripe border v-loading="taskLoading" empty-text="暂无任务">
            <el-table-column label="ID" width="80">
              <template #default="{ row }">#{{ row.id }}</template>
            </el-table-column>
            <el-table-column label="类型" width="100">
              <template #default="{ row }">
                <el-tag :type="row.task_type === 'import' ? 'primary' : 'success'" effect="plain">
                  {{ getTaskTypeLabel(row.task_type) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="数据类型" width="110">
              <template #default="{ row }">{{ getDataTypeLabel(row.data_type) }}</template>
            </el-table-column>
            <el-table-column label="文件名" min-width="180" show-overflow-tooltip>
              <template #default="{ row }">
                {{ row.file_name || `任务 #${row.id}` }}
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="getStatusTagType(row.status)" effect="dark">{{ row.status_display }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="进度" width="160">
              <template #default="{ row }">
                <el-progress :percentage="row.progress_percent" :status="row.status === 'failed' ? 'exception' : (row.status === 'success' ? 'success' : '')" />
              </template>
            </el-table-column>
            <el-table-column label="统计" width="200">
              <template #default="{ row }">
                <div v-if="row.task_type === 'import'" style="font-size: 12px">
                  <span style="color: #67c23a">成功 {{ row.success_rows }}</span> /
                  <span style="color: #f56c6c">失败 {{ row.failed_rows }}</span> /
                  <span style="color: #909399">跳过 {{ row.skipped_rows }}</span>
                </div>
                <div v-else style="font-size: 12px">
                  <span style="color: #67c23a">共 {{ row.success_rows }} 行</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="操作人" width="100">
              <template #default="{ row }">{{ row.operator_name }}</template>
            </el-table-column>
            <el-table-column label="创建时间" width="160">
              <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="240" fixed="right">
              <template #default="{ row }">
                <el-space>
                  <el-button
                    size="small"
                    type="primary"
                    plain
                    :disabled="!row.has_result"
                    @click="downloadTaskResult(row)"
                  >下载结果</el-button>
                  <el-button
                    v-if="row.task_type === 'import'"
                    size="small"
                    type="danger"
                    plain
                    :disabled="!row.has_error_file"
                    @click="downloadTaskErrors(row)"
                  >错误明细</el-button>
                  <el-button
                    size="small"
                    type="warning"
                    plain
                    @click="rerunTask(row)"
                  >重跑</el-button>
                </el-space>
              </template>
            </el-table-column>
          </el-table>

          <div style="margin-top: 16px; text-align: right">
            <el-pagination
              v-model:current-page="taskFilters.page"
              v-model:page-size="taskFilters.page_size"
              :page-sizes="[10, 20, 50]"
              :total="taskTotal"
              layout="total, sizes, prev, pager, next"
              @size-change="loadTasks"
              @current-change="loadTasks"
            />
          </div>
        </el-tab-pane>

        <!-- ============ 导入 Tab ============ -->
        <el-tab-pane label="📥 数据导入" name="import">
          <el-steps :active="importStep" finish-status="success" align-center style="margin-bottom: 24px">
            <el-step title="上传文件与预校验" description="选择类型与文件" />
            <el-step title="查看校验结果并修正" description="修正错误行" />
            <el-step title="正式导入" description="执行导入并下载结果" />
          </el-steps>

          <div v-if="importStep === 0">
            <el-row :gutter="16">
              <el-col :xs="24" :md="12">
                <el-card shadow="never">
                  <h4 style="margin-top: 0">1. 选择数据类型</h4>
                  <el-radio-group v-model="importDataType" style="display: block; margin-bottom: 16px">
                    <el-radio
                      v-for="dt in dataTypes"
                      :key="dt.key"
                      :value="dt.key"
                      style="display: block; margin: 8px 0"
                    >
                      <strong>{{ dt.label }}</strong>
                      <div style="color: var(--text-sub); font-size: 12px; margin-left: 24px; margin-top: 4px">
                        必填字段：{{ dt.import_required_fields.map(f => f.label).join('、') || '无' }}
                      </div>
                    </el-radio>
                  </el-radio-group>

                  <h4>2. 上传数据文件（CSV / XLSX）</h4>
                  <el-upload
                    :auto-upload="false"
                    :show-file-list="true"
                    :limit="1"
                    accept=".csv,.xlsx"
                    :on-change="onImportFileChange"
                    drag
                  >
                    <el-icon class="el-icon--upload"><upload-filled /></el-icon>
                    <div class="el-upload__text">将文件拖到此处，或<em>点击上传</em></div>
                    <template #tip>
                      <div class="el-upload__tip">支持 CSV 和 XLSX 格式，建议先下载对应模板</div>
                    </template>
                  </el-upload>

                  <div style="margin-top: 20px">
                    <el-space>
                      <el-button
                        type="primary"
                        :loading="importUploadLoading"
                        @click="doUploadAndPreview"
                      >上传并预校验</el-button>
                      <el-button @click="resetImport">重置</el-button>
                      <el-button
                        v-if="importDataType"
                        type="success"
                        plain
                        @click="downloadTemplate(importDataType)"
                      >下载模板</el-button>
                    </el-space>
                  </div>
                </el-card>
              </el-col>
              <el-col :xs="24" :md="12">
                <el-card shadow="never">
                  <h4 style="margin-top: 0">💡 导入说明</h4>
                  <ul style="color: var(--text-sub); line-height: 2">
                    <li>支持 CSV（推荐）与 XLSX 两种格式</li>
                    <li>系统对每行数据做预校验，错误行会高亮提示</li>
                    <li>可在第 2 步直接修正错误行数据</li>
                    <li><strong>幂等控制</strong>：同一文件再次上传会自动识别并跳过已导入的行</li>
                    <li>导入完成后可下载「结果汇总」与「错误明细」</li>
                  </ul>
                </el-card>
              </el-col>
            </el-row>
          </div>

          <div v-if="importStep === 1 && importPreviewData">
            <el-alert
              :title="`共 ${importPreviewData.total_rows} 行数据：错误 ${importPreviewData.error_count} 行，幂等跳过 ${importPreviewData.warning_count} 行`"
              :type="importPreviewData.error_count > 0 ? 'warning' : 'success'"
              show-icon
              style="margin-bottom: 16px"
            />

            <el-row :gutter="16" style="margin-bottom: 16px">
              <el-col :span="12">
                <el-statistic title="总行数" :value="importPreviewData.total_rows" />
              </el-col>
              <el-col :span="6">
                <el-statistic title="错误行数" :value="importPreviewData.error_count" value-style="color: #f56c6c" />
              </el-col>
              <el-col :span="6">
                <el-statistic title="幂等跳过" :value="importPreviewData.warning_count" value-style="color: #e6a23c" />
              </el-col>
            </el-row>

            <h4 style="margin-bottom: 12px">错误行修正（点击单元格直接修改）</h4>
            <el-table :data="importErrorRows" stripe border max-height="500" empty-text="无错误行，可直接提交">
              <el-table-column label="行号" width="80">
                <template #default="{ row }">第 {{ row.row_number }} 行</template>
              </el-table-column>
              <el-table-column
                v-for="h in importPreviewData.headers"
                :key="h"
                :label="importPreviewData.field_labels[h] || h"
                min-width="140"
              >
                <template #default="{ row: errorRow }">
                  <el-input
                    :model-value="correctedRows[errorRow.row_number]?.[h] ?? errorRow.data[h]"
                    size="small"
                    @update:model-value="(v) => updateCorrectedRow(errorRow.row_number, h, v)"
                  />
                </template>
              </el-table-column>
              <el-table-column label="错误信息" min-width="240" fixed="right">
                <template #default="{ row }">
                  <el-tag v-for="(e, i) in row.errors" :key="i" type="danger" effect="light" size="small" style="margin: 2px">
                    {{ e }}
                  </el-tag>
                  <el-tag v-if="row.is_idempotent_skip" type="warning" effect="light" size="small" style="margin: 2px">
                    幂等跳过
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>

            <div style="margin-top: 20px">
              <el-space>
                <el-button
                  type="primary"
                  :loading="importSubmitting"
                  @click="doImportSubmit"
                >确认并正式导入</el-button>
                <el-button @click="importStep = 0">返回上一步</el-button>
              </el-space>
            </div>
          </div>

          <div v-if="importStep === 2">
            <el-result icon="success" title="导入任务已完成" sub-title="可在任务列表中下载结果文件和错误明细">
              <template #extra>
                <el-space>
                  <el-button type="primary" @click="activeTab = 'tasks'; loadTasks()">查看任务列表</el-button>
                  <el-button @click="resetImport()">再次导入</el-button>
                </el-space>
              </template>
            </el-result>
          </div>
        </el-tab-pane>

        <!-- ============ 导出 Tab ============ -->
        <el-tab-pane label="📤 数据导出" name="export">
          <el-row :gutter="16">
            <el-col :xs="24" :md="14">
              <el-card shadow="never">
                <el-form label-position="top">
                  <el-form-item label="数据类型" required>
                    <el-select v-model="exportForm.data_type" placeholder="选择要导出的数据类型" style="width: 100%">
                      <el-option v-for="dt in dataTypes" :key="dt.key" :label="dt.label" :value="dt.key" />
                    </el-select>
                  </el-form-item>

                  <el-form-item label="导出格式">
                    <el-radio-group v-model="exportForm.file_format">
                      <el-radio value="csv">CSV</el-radio>
                      <el-radio value="xlsx">XLSX</el-radio>
                    </el-radio-group>
                  </el-form-item>

                  <template v-if="currentExportMeta">
                    <el-form-item label="选择字段">
                      <el-space style="margin-bottom: 8px">
                        <el-button size="small" link type="primary" @click="selectAllExportFields">全选</el-button>
                        <el-button size="small" link type="info" @click="clearExportFields">清空</el-button>
                      </el-space>
                      <el-checkbox-group v-model="exportForm.fields" style="display: flex; flex-wrap: wrap; gap: 10px">
                        <el-checkbox
                          v-for="f in currentExportMeta.fields"
                          :key="f.key"
                          :value="f.key"
                          :label="f.key"
                        >{{ f.label }}</el-checkbox>
                      </el-checkbox-group>
                    </el-form-item>

                    <el-form-item label="筛选条件">
                      <el-row :gutter="12">
                        <template v-for="opt in currentExportMeta.filter_options" :key="opt.key">
                          <el-col :xs="24" :md="12" style="margin-bottom: 10px">
                            <label style="display: block; font-size: 13px; color: var(--text-sub); margin-bottom: 4px">{{ opt.label }}</label>
                            <el-select
                              v-if="opt.type === 'choice'"
                              v-model="exportForm.filters[opt.key]"
                              placeholder="全部"
                              clearable
                              style="width: 100%"
                            >
                              <el-option
                                v-for="o in opt.options"
                                :key="o[0]"
                                :label="o[1]"
                                :value="o[0]"
                              />
                            </el-select>
                            <el-date-picker
                              v-else-if="opt.type === 'date'"
                              v-model="exportForm.filters[opt.key]"
                              type="date"
                              value-format="YYYY-MM-DD"
                              placeholder="选择日期"
                              style="width: 100%"
                            />
                            <el-input-number
                              v-else-if="opt.type === 'number'"
                              v-model="exportForm.filters[opt.key]"
                              :min="0"
                              :precision="2"
                              :step="10"
                              placeholder="请输入"
                              style="width: 100%"
                            />
                            <el-input
                              v-else
                              v-model="exportForm.filters[opt.key]"
                              :placeholder="`输入${opt.label}`"
                              clearable
                            />
                          </el-col>
                        </template>
                      </el-row>
                    </el-form-item>
                  </template>

                  <el-form-item>
                    <el-space>
                      <el-button type="primary" :loading="exportSubmitting" @click="doExportSubmit">
                        开始导出
                      </el-button>
                      <el-button @click="resetExportForm">重置</el-button>
                    </el-space>
                  </el-form-item>
                </el-form>
              </el-card>
            </el-col>
            <el-col :xs="24" :md="10">
              <el-card shadow="never">
                <h4 style="margin-top: 0">💡 导出说明</h4>
                <ul style="color: var(--text-sub); line-height: 2">
                  <li>支持 CSV（默认）与 XLSX 两种格式</li>
                  <li>可自由勾选导出的字段，不选则导出全部</li>
                  <li>支持多维筛选条件：关键字、时间、金额区间等</li>
                  <li>大数据量导出会进入任务队列异步处理</li>
                  <li>导出完成后可在任务列表下载文件</li>
                </ul>
                <el-divider />
                <h4>📦 当前支持的数据类型</h4>
                <el-timeline>
                  <el-timeline-item
                    v-for="dt in dataTypes"
                    :key="dt.key"
                    type="primary"
                    size="large"
                  >
                    <strong>{{ dt.label }}</strong>
                    <div style="color: var(--text-sub); font-size: 12px; margin-top: 2px">
                      共 {{ dt.fields.length }} 个可导出字段
                    </div>
                  </el-timeline-item>
                </el-timeline>
              </el-card>
            </el-col>
          </el-row>
        </el-tab-pane>

        <!-- ============ 模板下载 Tab ============ -->
        <el-tab-pane label="📄 模板下载" name="templates">
          <p style="color: var(--text-sub); margin-bottom: 20px">
            每种数据类型有独立的导入模板，下载模板后按列填写数据即可上传导入。
          </p>
          <el-row :gutter="16">
            <el-col v-for="dt in dataTypes" :key="dt.key" :xs="24" :sm="12" :md="6">
              <el-card shadow="hover" style="height: 100%">
                <h4 style="margin-top: 0">{{ dt.label }}</h4>
                <div style="color: var(--text-sub); font-size: 13px; margin-bottom: 12px">
                  <div>必填字段：</div>
                  <div v-if="dt.import_required_fields.length">
                    <el-tag
                      v-for="f in dt.import_required_fields"
                      :key="f.key"
                      type="danger"
                      effect="light"
                      size="small"
                      style="margin: 2px"
                    >{{ f.label }}</el-tag>
                  </div>
                  <div v-else style="color: #67c23a">无</div>
                  <div style="margin-top: 8px">可选字段：</div>
                  <div>
                    <el-tag
                      v-for="f in dt.import_optional_fields"
                      :key="f.key"
                      effect="light"
                      size="small"
                      style="margin: 2px"
                    >{{ f.label }}</el-tag>
                  </div>
                </div>
                <el-button type="primary" style="width: 100%" @click="downloadTemplate(dt.key)">
                  下载 CSV 模板
                </el-button>
              </el-card>
            </el-col>
          </el-row>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </main>
</template>
