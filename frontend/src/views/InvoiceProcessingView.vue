<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessageBox, ElNotification } from 'element-plus'
import { useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'
import http from '../utils/http'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(true)
const actionLoading = ref(false)
const invoices = ref([])
const selectedInvoice = ref(null)

const filters = reactive({
  status: 'pending',
  user_id: '',
})

const processDialogVisible = ref(false)
const processForm = reactive({
  action: 'issued',
  invoice_number: '',
  download_url: '',
  review_remark: '',
})

const voidDialogVisible = ref(false)
const voidForm = reactive({
  review_remark: '',
})

const invoiceStatusMap = {
  pending: { label: '待处理', type: 'warning' },
  issued: { label: '已开具', type: 'success' },
  rejected: { label: '已驳回', type: 'danger' },
  void: { label: '已作废', type: 'info' },
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

async function loadInvoices() {
  const params = {}
  if (filters.status) params.status = filters.status
  if (filters.user_id) params.user_id = filters.user_id
  const { data } = await http.get('/refund-invoice/invoices/', { params })
  invoices.value = data
}

function openProcessDialog(invoice) {
  selectedInvoice.value = invoice
  processForm.action = 'issued'
  processForm.invoice_number = ''
  processForm.download_url = ''
  processForm.review_remark = ''
  processDialogVisible.value = true
}

async function submitProcess() {
  if (processForm.action === 'issued') {
    if (!processForm.invoice_number.trim()) {
      ElNotification({ title: '提交失败', message: '请输入电子发票号。', type: 'warning' })
      return
    }
    if (!processForm.download_url.trim()) {
      ElNotification({ title: '提交失败', message: '请输入发票下载链接。', type: 'warning' })
      return
    }
  } else {
    if (!processForm.review_remark.trim()) {
      ElNotification({ title: '提交失败', message: '驳回时必须填写原因。', type: 'warning' })
      return
    }
  }

  actionLoading.value = true
  try {
    await http.post(`/refund-invoice/invoices/${selectedInvoice.value.id}/process/`, {
      action: processForm.action,
      invoice_number: processForm.invoice_number,
      download_url: processForm.download_url,
      review_remark: processForm.review_remark,
    })
    ElNotification({ title: '处理完成', message: '开票申请状态已更新。', type: 'success' })
    processDialogVisible.value = false
    await loadInvoices()
  } finally {
    actionLoading.value = false
  }
}

function openVoidDialog(invoice) {
  selectedInvoice.value = invoice
  voidForm.review_remark = ''
  voidDialogVisible.value = true
}

async function submitVoid() {
  actionLoading.value = true
  try {
    await http.post(`/refund-invoice/invoices/${selectedInvoice.value.id}/void/`, {
      review_remark: voidForm.review_remark,
    })
    ElNotification({ title: '作废成功', message: '发票已作废。', type: 'success' })
    voidDialogVisible.value = false
    await loadInvoices()
  } finally {
    actionLoading.value = false
  }
}

async function refreshAll() {
  loading.value = true
  try {
    await loadInvoices()
  } finally {
    loading.value = false
  }
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
    ElNotification({ title: '无权限', message: '仅管理员可访问此页面。', type: 'warning' })
    await router.push('/dashboard')
    return
  }
  await refreshAll()
})
</script>

<template>
  <main class="page-shell animated-in">
    <section class="dashboard-wrap">
      <el-card class="section-card" shadow="never">
        <el-row justify="space-between" align="middle" :gutter="12">
          <el-col :xs="24" :sm="18">
            <h2 class="section-title">开票处理</h2>
            <p style="margin: 0; color: var(--text-sub)">处理学生的开票申请，回填电子发票号与下载链接</p>
          </el-col>
          <el-col :xs="24" :sm="6" style="text-align: right">
            <el-button @click="refreshAll">刷新</el-button>
          </el-col>
        </el-row>
      </el-card>

      <el-skeleton :loading="loading" animated :rows="6">
        <template #default>
          <el-card class="section-card" shadow="never">
            <el-row :gutter="12" style="margin-bottom: 12px">
              <el-col :span="6">
                <el-select v-model="filters.status" style="width: 100%" placeholder="按状态筛选" @change="loadInvoices">
                  <el-option label="待处理" value="pending" />
                  <el-option label="已开具" value="issued" />
                  <el-option label="已驳回" value="rejected" />
                  <el-option label="已作废" value="void" />
                </el-select>
              </el-col>
              <el-col :span="6">
                <el-input v-model="filters.user_id" placeholder="按用户ID筛选" clearable />
              </el-col>
              <el-col :span="6">
                <el-button type="primary" @click="loadInvoices">查询</el-button>
              </el-col>
            </el-row>

            <el-table :data="invoices" stripe border empty-text="暂无开票申请">
              <el-table-column prop="invoice_no" label="申请单号" min-width="180" />
              <el-table-column prop="user_name" label="申请人" min-width="120" />
              <el-table-column label="抬头信息" min-width="200">
                <template #default="{ row }">
                  <div v-if="row.title_info">
                    <div style="font-weight: 600">{{ row.title_info.title_name }}</div>
                    <div style="color: var(--text-sub); font-size: 12px">
                      {{ row.title_info.title_type === 'personal' ? '个人' : '单位' }}
                      <span v-if="row.title_info.tax_no">｜{{ row.title_info.tax_no }}</span>
                    </div>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="开票金额" min-width="120">
                <template #default="{ row }">¥ {{ formatMoney(row.total_amount) }}</template>
              </el-table-column>
              <el-table-column label="状态" min-width="100">
                <template #default="{ row }">
                  <el-tag :type="invoiceStatusMap[row.status]?.type || 'info'" effect="plain">
                    {{ invoiceStatusMap[row.status]?.label || row.status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="invoice_number" label="发票号" min-width="160" />
              <el-table-column label="申请时间" min-width="165">
                <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
              </el-table-column>
              <el-table-column label="操作" min-width="240" fixed="right">
                <template #default="{ row }">
                  <el-space>
                    <el-button v-if="row.status === 'pending'" size="small" type="primary" @click="openProcessDialog(row)">处理</el-button>
                    <el-button v-if="row.status === 'issued'" size="small" type="warning" plain @click="openVoidDialog(row)">作废</el-button>
                  </el-space>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </template>
      </el-skeleton>

      <el-dialog v-model="processDialogVisible" title="处理开票申请" width="560px">
        <el-form label-position="top" @submit.prevent>
          <el-form-item label="处理动作">
            <el-radio-group v-model="processForm.action">
              <el-radio value="issued">开具发票</el-radio>
              <el-radio value="rejected">驳回申请</el-radio>
            </el-radio-group>
          </el-form-item>
          <template v-if="processForm.action === 'issued'">
            <el-form-item label="电子发票号">
              <el-input v-model="processForm.invoice_number" placeholder="请输入电子发票号码" />
            </el-form-item>
            <el-form-item label="发票下载链接">
              <el-input v-model="processForm.download_url" placeholder="请输入电子发票下载链接" />
            </el-form-item>
          </template>
          <el-form-item v-else label="驳回原因">
            <el-input v-model="processForm.review_remark" type="textarea" :rows="3" placeholder="请详细说明驳回原因" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="processDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="actionLoading" @click="submitProcess">提交</el-button>
        </template>
      </el-dialog>

      <el-dialog v-model="voidDialogVisible" title="作废发票" width="520px">
        <el-form label-position="top" @submit.prevent>
          <el-form-item label="作废原因（可选）">
            <el-input v-model="voidForm.review_remark" type="textarea" :rows="3" placeholder="请输入作废说明" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="voidDialogVisible = false">取消</el-button>
          <el-button type="danger" :loading="actionLoading" @click="submitVoid">确认作废</el-button>
        </template>
      </el-dialog>
    </section>
  </main>
</template>
