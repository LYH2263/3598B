<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessageBox, ElNotification } from 'element-plus'
import { useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'
import http from '../utils/http'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(true)
const actionLoading = ref(false)
const refunds = ref([])
const refundableRecharges = ref([])

const filters = reactive({
  status: '',
})

const createDialogVisible = ref(false)
const refundForm = reactive({
  recharge_record_id: null,
  amount: null,
  reason: '',
  attachment_url: '',
})

const refundStatusMap = {
  pending: { label: '待审核', type: 'warning' },
  approved: { label: '已通过', type: 'success' },
  rejected: { label: '已拒绝', type: 'danger' },
  cancelled: { label: '已撤销', type: 'info' },
}

const channelMap = {
  alipay: '支付宝',
  wechat: '微信支付',
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

async function loadRefunds() {
  const params = {}
  if (filters.status) params.status = filters.status
  const { data } = await http.get('/refund-invoice/refunds/', { params })
  refunds.value = data
}

async function loadRefundableRecharges() {
  const { data } = await http.get('/refund-invoice/refunds/refundable-recharges/')
  refundableRecharges.value = data
}

function openCreateDialog() {
  refundForm.recharge_record_id = null
  refundForm.amount = null
  refundForm.reason = ''
  refundForm.attachment_url = ''
  createDialogVisible.value = true
}

function onRechargeChange(rechargeId) {
  const recharge = refundableRecharges.value.find((r) => r.id === rechargeId)
  if (recharge) {
    refundForm.amount = Number(recharge.remaining_amount)
  }
}

async function submitRefund() {
  if (!refundForm.recharge_record_id) {
    ElNotification({ title: '提交失败', message: '请选择充值记录。', type: 'warning' })
    return
  }
  if (!refundForm.amount || Number(refundForm.amount) <= 0) {
    ElNotification({ title: '提交失败', message: '请输入有效金额。', type: 'warning' })
    return
  }
  if (!refundForm.reason.trim()) {
    ElNotification({ title: '提交失败', message: '请输入退费原因。', type: 'warning' })
    return
  }
  actionLoading.value = true
  try {
    await http.post('/refund-invoice/refunds/', refundForm)
    ElNotification({ title: '申请已提交', message: '退费申请已提交，请等待管理员审核。', type: 'success' })
    createDialogVisible.value = false
    await loadRefunds()
  } finally {
    actionLoading.value = false
  }
}

async function cancelRefund(refund) {
  try {
    await ElMessageBox.confirm('确定撤销该退费申请吗？', '撤销确认', {
      confirmButtonText: '撤销',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch (_e) {
    return
  }
  try {
    await http.post(`/refund-invoice/refunds/${refund.id}/cancel/`)
    ElNotification({ title: '已撤销', message: '退费申请已撤销。', type: 'success' })
    await loadRefunds()
  } catch (_e) {}
}

async function refreshAll() {
  loading.value = true
  try {
    await Promise.all([loadRefunds(), loadRefundableRecharges()])
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
            <h2 class="section-title">我的退费</h2>
            <p style="margin: 0; color: var(--text-sub)">对已入账充值发起退费申请，审核通过后从钱包扣除</p>
          </el-col>
          <el-col :xs="24" :sm="6" style="text-align: right">
            <el-button style="margin-right: 8px" @click="refreshAll">刷新</el-button>
            <el-button type="primary" @click="openCreateDialog">申请退费</el-button>
          </el-col>
        </el-row>
      </el-card>

      <el-skeleton :loading="loading" animated :rows="6">
        <template #default>
          <el-card class="section-card" shadow="never">
            <el-row :gutter="12" style="margin-bottom: 12px">
              <el-col :span="6">
                <el-select v-model="filters.status" style="width: 100%" placeholder="按状态筛选" clearable @change="loadRefunds">
                  <el-option label="待审核" value="pending" />
                  <el-option label="已通过" value="approved" />
                  <el-option label="已拒绝" value="rejected" />
                  <el-option label="已撤销" value="cancelled" />
                </el-select>
              </el-col>
            </el-row>

            <el-table :data="refunds" stripe border empty-text="暂无退费记录">
              <el-table-column prop="refund_no" label="退费单号" min-width="180" />
              <el-table-column label="关联充值金额" min-width="130">
                <template #default="{ row }">¥ {{ formatMoney(row.recharge_amount) }}</template>
              </el-table-column>
              <el-table-column label="申请金额" min-width="110">
                <template #default="{ row }">¥ {{ formatMoney(row.amount) }}</template>
              </el-table-column>
              <el-table-column prop="reason" label="退费原因" min-width="200" show-overflow-tooltip />
              <el-table-column label="状态" min-width="110">
                <template #default="{ row }">
                  <el-tag :type="refundStatusMap[row.status]?.type || 'info'" effect="plain">
                    {{ refundStatusMap[row.status]?.label || row.status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="申请时间" min-width="165">
                <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
              </el-table-column>
              <el-table-column label="审核时间" min-width="165">
                <template #default="{ row }">{{ formatDateTime(row.reviewed_at) }}</template>
              </el-table-column>
              <el-table-column prop="review_remark" label="审核备注" min-width="150" show-overflow-tooltip />
              <el-table-column label="操作" min-width="100" fixed="right">
                <template #default="{ row }">
                  <el-button size="small" type="warning" plain :disabled="row.status !== 'pending'" @click="cancelRefund(row)">撤销</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </template>
      </el-skeleton>

      <el-dialog v-model="createDialogVisible" title="申请退费" width="560px">
        <el-form label-position="top" @submit.prevent>
          <el-form-item label="选择充值记录">
            <el-select v-model="refundForm.recharge_record_id" style="width: 100%" placeholder="请选择可退费的充值记录" @change="onRechargeChange">
              <el-option
                v-for="r in refundableRecharges"
                :key="r.id"
                :label="`${formatDateTime(r.created_at)} 原金额 ¥${formatMoney(r.amount)} 剩余可退 ¥${formatMoney(r.remaining_amount)}`"
                :value="r.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="退费金额（元）">
            <el-input-number v-model="refundForm.amount" :min="0" :precision="2" :step="10" style="width: 100%" />
          </el-form-item>
          <el-form-item label="退费原因">
            <el-input v-model="refundForm.reason" type="textarea" :rows="3" placeholder="请详细说明退费原因" />
          </el-form-item>
          <el-form-item label="附件链接（可选）">
            <el-input v-model="refundForm.attachment_url" placeholder="请输入凭证附件链接" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="createDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="actionLoading" @click="submitRefund">提交申请</el-button>
        </template>
      </el-dialog>
    </section>
  </main>
</template>
