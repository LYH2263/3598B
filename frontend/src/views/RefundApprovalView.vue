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
const refunds = ref([])

const filters = reactive({
  status: 'pending',
  user_id: '',
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
  if (filters.user_id) params.user_id = filters.user_id
  const { data } = await http.get('/refund-invoice/refunds/', { params })
  refunds.value = data
}

async function reviewRefund(refund, action) {
  const actionLabel = action === 'approved' ? '通过' : '拒绝'
  const result = await ElMessageBox.prompt(
    action === 'approved' ? '请输入通过备注（可选）' : '请输入拒绝原因',
    `${actionLabel}退费申请`,
    {
      confirmButtonText: '提交',
      cancelButtonText: '取消',
      inputPlaceholder: action === 'approved' ? '请输入审核备注' : '请输入拒绝原因',
    }
  ).catch(() => null)

  if (!result) return

  actionLoading.value = true
  try {
    await http.post(`/refund-invoice/refunds/${refund.id}/review/`, {
      action,
      review_remark: result.value || '',
    })
    ElNotification({ title: '审核完成', message: '退费申请状态已更新。', type: 'success' })
    await loadRefunds()
  } finally {
    actionLoading.value = false
  }
}

async function refreshAll() {
  loading.value = true
  try {
    await loadRefunds()
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
            <h2 class="section-title">退费审批</h2>
            <p style="margin: 0; color: var(--text-sub)">审核学生提交的退费申请，通过后从钱包扣减余额</p>
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
                <el-select v-model="filters.status" style="width: 100%" placeholder="按状态筛选" @change="loadRefunds">
                  <el-option label="待审核" value="pending" />
                  <el-option label="已通过" value="approved" />
                  <el-option label="已拒绝" value="rejected" />
                  <el-option label="已撤销" value="cancelled" />
                </el-select>
              </el-col>
              <el-col :span="6">
                <el-input v-model="filters.user_id" placeholder="按用户ID筛选" clearable />
              </el-col>
              <el-col :span="6">
                <el-button type="primary" @click="loadRefunds">查询</el-button>
              </el-col>
            </el-row>

            <el-table :data="refunds" stripe border empty-text="暂无退费申请">
              <el-table-column prop="refund_no" label="退费单号" min-width="180" />
              <el-table-column prop="user_name" label="申请人" min-width="120" />
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
              <el-table-column label="操作" min-width="200" fixed="right">
                <template #default="{ row }">
                  <el-space>
                    <el-button size="small" type="success" :disabled="row.status !== 'pending'" @click="reviewRefund(row, 'approved')">通过</el-button>
                    <el-button size="small" type="danger" :disabled="row.status !== 'pending'" @click="reviewRefund(row, 'rejected')">拒绝</el-button>
                  </el-space>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </template>
      </el-skeleton>
    </section>
  </main>
</template>
