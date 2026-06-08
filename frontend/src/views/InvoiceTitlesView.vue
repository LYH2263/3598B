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
const titles = ref([])

const dialogVisible = ref(false)
const editingId = ref(null)
const titleForm = reactive({
  title_type: 'personal',
  title_name: '',
  tax_no: '',
  email: '',
  is_default: false,
})

const titleTypeMap = {
  personal: { label: '个人', type: 'info' },
  company: { label: '单位', type: 'primary' },
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

async function loadTitles() {
  const { data } = await http.get('/refund-invoice/invoice-titles/')
  titles.value = data
}

function openCreateDialog() {
  editingId.value = null
  titleForm.title_type = 'personal'
  titleForm.title_name = ''
  titleForm.tax_no = ''
  titleForm.email = ''
  titleForm.is_default = false
  dialogVisible.value = true
}

function openEditDialog(title) {
  editingId.value = title.id
  titleForm.title_type = title.title_type
  titleForm.title_name = title.title_name
  titleForm.tax_no = title.tax_no
  titleForm.email = title.email
  titleForm.is_default = title.is_default
  dialogVisible.value = true
}

async function saveTitle() {
  if (!titleForm.title_name.trim()) {
    ElNotification({ title: '保存失败', message: '请输入发票抬头名称。', type: 'warning' })
    return
  }
  if (!titleForm.email.trim()) {
    ElNotification({ title: '保存失败', message: '请输入接收邮箱。', type: 'warning' })
    return
  }
  if (titleForm.title_type === 'company' && !titleForm.tax_no.trim()) {
    ElNotification({ title: '保存失败', message: '单位抬头必须填写纳税人识别号。', type: 'warning' })
    return
  }

  actionLoading.value = true
  try {
    if (editingId.value) {
      await http.put(`/refund-invoice/invoice-titles/${editingId.value}/`, titleForm)
      ElNotification({ title: '修改成功', message: '发票抬头已更新。', type: 'success' })
    } else {
      await http.post('/refund-invoice/invoice-titles/', titleForm)
      ElNotification({ title: '创建成功', message: '发票抬头已添加。', type: 'success' })
    }
    dialogVisible.value = false
    await loadTitles()
  } finally {
    actionLoading.value = false
  }
}

async function setDefault(title) {
  try {
    await http.post(`/refund-invoice/invoice-titles/${title.id}/set-default/`)
    ElNotification({ title: '设置成功', message: '已设为默认抬头。', type: 'success' })
    await loadTitles()
  } catch (_e) {}
}

async function deleteTitle(title) {
  try {
    await ElMessageBox.confirm(`确定删除抬头「${title.title_name}」吗？`, '删除确认', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch (_e) {
    return
  }
  try {
    await http.delete(`/refund-invoice/invoice-titles/${title.id}/`)
    ElNotification({ title: '删除成功', message: '发票抬头已删除。', type: 'success' })
    await loadTitles()
  } catch (_e) {}
}

async function refreshAll() {
  loading.value = true
  try {
    await loadTitles()
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
            <h2 class="section-title">抬头管理</h2>
            <p style="margin: 0; color: var(--text-sub)">维护发票抬头信息，支持个人和单位两种类型</p>
          </el-col>
          <el-col :xs="24" :sm="6" style="text-align: right">
            <el-button style="margin-right: 8px" @click="refreshAll">刷新</el-button>
            <el-button type="primary" @click="openCreateDialog">新增抬头</el-button>
          </el-col>
        </el-row>
      </el-card>

      <el-skeleton :loading="loading" animated :rows="4">
        <template #default>
          <el-card class="section-card" shadow="never">
            <el-table :data="titles" stripe border empty-text="暂无发票抬头">
              <el-table-column label="类型" min-width="90">
                <template #default="{ row }">
                  <el-tag :type="titleTypeMap[row.title_type]?.type || 'info'" effect="plain">
                    {{ titleTypeMap[row.title_type]?.label || row.title_type }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="title_name" label="抬头名称" min-width="200" />
              <el-table-column prop="tax_no" label="税号" min-width="180" />
              <el-table-column prop="email" label="接收邮箱" min-width="200" />
              <el-table-column label="默认" min-width="90">
                <template #default="{ row }">
                  <el-tag v-if="row.is_default" type="success" effect="plain">默认</el-tag>
                  <span v-else style="color: var(--text-sub)">--</span>
                </template>
              </el-table-column>
              <el-table-column label="创建时间" min-width="165">
                <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
              </el-table-column>
              <el-table-column label="操作" min-width="260" fixed="right">
                <template #default="{ row }">
                  <el-space>
                    <el-button size="small" type="primary" plain :disabled="row.is_default" @click="setDefault(row)">设为默认</el-button>
                    <el-button size="small" @click="openEditDialog(row)">编辑</el-button>
                    <el-button size="small" type="danger" plain @click="deleteTitle(row)">删除</el-button>
                  </el-space>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </template>
      </el-skeleton>

      <el-dialog v-model="dialogVisible" :title="editingId ? '编辑抬头' : '新增抬头'" width="520px">
        <el-form label-position="top" @submit.prevent>
          <el-form-item label="抬头类型">
            <el-radio-group v-model="titleForm.title_type">
              <el-radio value="personal">个人</el-radio>
              <el-radio value="company">单位</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="抬头名称">
            <el-input v-model="titleForm.title_name" :placeholder="titleForm.title_type === 'personal' ? '请输入个人姓名' : '请输入单位全称'" />
          </el-form-item>
          <el-form-item v-if="titleForm.title_type === 'company'" label="纳税人识别号">
            <el-input v-model="titleForm.tax_no" placeholder="请输入纳税人识别号" />
          </el-form-item>
          <el-form-item label="接收邮箱">
            <el-input v-model="titleForm.email" placeholder="请输入接收电子发票的邮箱" />
          </el-form-item>
          <el-form-item>
            <el-switch v-model="titleForm.is_default" active-text="设为默认抬头" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="actionLoading" @click="saveTitle">保存</el-button>
        </template>
      </el-dialog>
    </section>
  </main>
</template>
