<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElNotification } from 'element-plus'
import { useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'
import http from '../utils/http'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(true)
const actionLoading = ref(false)
const invoices = ref([])
const titles = ref([])
const invoiceableRecharges = ref([])

const filters = reactive({
  status: '',
})

const createDialogVisible = ref(false)
const invoiceForm = reactive({
  title_id: null,
  remark: '',
  selectedRecharges: [],
})

const invoiceStatusMap = {
  pending: { label: '待处理', type: 'warning' },
  issued: { label: '已开具', type: 'success' },
  rejected: { label: '已驳回', type: 'danger' },
  void: { label: '已作废', type: 'info' },
}

const channelMap = {
  alipay: '支付宝',
  wechat: '支付宝',
  bank: '银行卡',
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

const selectedTotal = computed(() => {
  let total = 0
  for (const item of invoiceForm.selectedRecharges) {
    total += Number(item.amount || 0)
  }
  return total.toFixed(2)
})

async function loadInvoices() {
  const params = {}
  if (filters.status) params.status = filters.status
  const { data } = await http.get('/refund-invoice/invoices/', { params })
  invoices.value = data
}

async function loadTitles() {
  const { data } = await http.get('/refund-invoice/invoice-titles/')
  titles.value = data
}

async function loadInvoiceableRecharges() {
  const { data } = await http.get('/refund-invoice/invoices/invoiceable-recharges/')
  invoiceableRecharges.value = data
}

function openCreateDialog() {
  invoiceForm.title_id = titles.value.find((t) => t.is_default)?.id || null
  invoiceForm.remark = ''
  invoiceForm.selectedRecharges = []
  createDialogVisible.value = true
}

function toggleRecharge(recharge, checked) {
  if (checked) {
    if (invoiceForm.selectedRecharges.find((x) => x.recharge_record_id === recharge.id)) return
    invoiceForm.selectedRecharges.push({
      recharge_record_id: recharge.id,
      amount: Number(recharge.remaining_invoiceable),
    })
  } else {
    invoiceForm.selectedRecharges = invoiceForm.selectedRecharges.filter(
      (x) => x.recharge_record_id !== recharge.id
    )
  }
}

function updateItemAmount(rechargeId, amount) {
  const item = invoiceForm.selectedRecharges.find((x) => x.recharge_record_id === rechargeId)
  if (item) {
    item.amount = Number(amount)
  }
}

function isRechargeSelected(rechargeId) {
  return invoiceForm.selectedRecharges.some((x) => x.recharge_record_id === rechargeId)
}

function getRechargeAmount(rechargeId) {
  const item = invoiceForm.selectedRecharges.find((x) => x.recharge_record_id === rechargeId)
  return item ? item.amount : 0
}

async function submitInvoice() {
  if (!invoiceForm.title_id) {
    ElNotification({ title: '提交失败', message: '请选择发票抬头。', type: 'warning' })
    return
  }
  if (invoiceForm.selectedRecharges.length === 0) {
    ElNotification({ title: '提交失败', message: '请选择要开票的充值记录。', type: 'warning' })
    return
  }
  for (const item of invoiceForm.selectedRecharges) {
    if (!item.amount || item.amount <= 0) {
      ElNotification({ title: '提交失败', message: '每笔开票金额必须大于 0。', type: 'warning' })
      return
    }
  }

  actionLoading.value = true
  try {
    await http.post('/refund-invoice/invoices/', {
      title_id: invoiceForm.title_id,
      items: invoiceForm.selectedRecharges,
      remark: invoiceForm.remark,
    })
    ElNotification({ title: '申请已提交', message: '开票申请已提交，请等待管理员处理。', type: 'success' })
    createDialogVisible.value = false
    await loadInvoices()
  } finally {
    actionLoading.value = false
  }
}

async function refreshAll() {
  loading.value = true
  try {
    await Promise.all([loadInvoices(), loadTitles(), loadInvoiceableRecharges()])
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
  await refreshAll()
})
</script>

<template>
  <main class="page-shell animated-in">
    <section class="dashboard-wrap">
      <el-card class="section-card" shadow="never">
        <el-row justify="space-between" align="middle" :gutter="12">
          <el-col :xs="24" :sm="18">
            <h2 class="section-title">我的发票</h2>
            <p style="margin: 0; color: var(--text-sub)">对已入账充值发起开票申请，支持多笔合并开票</p>
          </el-col>
          <el-col :xs="24" :sm="6" style="text-align: right">
            <el-button style="margin-right: 8px" @click="router.push('/invoice-titles')">抬头管理</el-button>
            <el-button style="margin-right: 8px" @click="refreshAll">刷新</el-button>
            <el-button type="primary" @click="openCreateDialog">申请开票</el-button>
          </el-col>
        </el-row>
      </el-card>

      <el-skeleton :loading="loading" animated :rows="6">
        <template #default>
          <el-card class="section-card" shadow="never">
            <el-row :gutter="12" style="margin-bottom: 12px">
              <el-col :span="6">
                <el-select v-model="filters.status" style="width: 100%" placeholder="按状态筛选" clearable @change="loadInvoices">
                  <el-option label="待处理" value="pending" />
                  <el-option label="已开具" value="issued" />
                  <el-option label="已驳回" value="rejected" />
                  <el-option label="已作废" value="void" />
                </el-select>
              </el-col>
            </el-row>

            <el-table :data="invoices" stripe border empty-text="暂无开票记录">
              <el-table-column prop="invoice_no" label="开票申请单号" min-width="180" />
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
              <el-table-column label="下载" min-width="100">
                <template #default="{ row }">
                  <el-link v-if="row.download_url" type="primary" :href="row.download_url" target="_blank">下载发票</el-link>
                  <span v-else style="color: var(--text-sub)">--</span>
                </template>
              </el-table-column>
              <el-table-column label="申请时间" min-width="165">
                <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
              </el-table-column>
              <el-table-column label="处理时间" min-width="165">
                <template #default="{ row }">{{ formatDateTime(row.reviewed_at) }}</template>
              </el-table-column>
              <el-table-column prop="review_remark" label="处理备注" min-width="150" show-overflow-tooltip />
            </el-table>
          </el-card>
        </template>
      </el-skeleton>

      <el-dialog v-model="createDialogVisible" title="申请开票" width="680px">
        <el-form label-position="top" @submit.prevent>
          <el-form-item label="选择发票抬头">
            <el-select v-model="invoiceForm.title_id" style="width: 100%" placeholder="请选择发票抬头">
              <el-option v-for="t in titles" :key="t.id" :label="`${t.title_type === 'personal' ? '个人' : '单位'} - ${t.title_name}${t.is_default ? ' (默认)' : ''}`" :value="t.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="选择充值记录（可多选合并开票）">
            <el-table :data="invoiceableRecharges" stripe border empty-text="暂无可开票的充值记录" max-height="300px">
              <el-table-column label="选择" width="60">
                <template #default="{ row }">
                  <el-checkbox :model-value="isRechargeSelected(row.id)" @change="(val) => toggleRecharge(row, val)" />
                </template>
              </el-table-column>
              <el-table-column label="时间" min-width="165">
                <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
              </el-table-column>
              <el-table-column label="原金额" min-width="100">
                <template #default="{ row }">¥ {{ formatMoney(row.amount) }}</template>
              </el-table-column>
              <el-table-column label="剩余可开票" min-width="120">
                <template #default="{ row }">¥ {{ formatMoney(row.remaining_invoiceable) }}</template>
              </el-table-column>
              <el-table-column label="开票金额" min-width="180">
                <template #default="{ row }">
                  <el-input-number
                    v-if="isRechargeSelected(row.id)"
                    :model-value="getRechargeAmount(row.id)"
                    :min="0"
                    :max="Number(row.remaining_invoiceable)"
                    :precision="2"
                    :step="10"
                    style="width: 100%"
                    @update:model-value="(val) => updateItemAmount(row.id, val)"
                  />
                  <span v-else style="color: var(--text-sub)">--</span>
                </template>
              </el-table-column>
            </el-table>
          </el-form-item>
          <el-form-item>
            <div style="font-weight: 600; color: var(--el-color-primary); font-size: 16px">
              已选金额合计：¥ {{ selectedTotal }}
            </div>
          </el-form-item>
          <el-form-item label="备注（可选）">
            <el-input v-model="invoiceForm.remark" type="textarea" :rows="2" placeholder="请输入备注信息" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="createDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="actionLoading" @click="submitInvoice">提交申请</el-button>
        </template>
      </el-dialog>
    </section>
  </main>
</template>
