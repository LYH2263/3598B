<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'

import { useAuthStore } from '../stores/auth'
import http from '../utils/http'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(true)
const actionLoading = ref(false)
const campuses = ref([])
const filters = reactive({
  keyword: '',
  only_active: '',
})

const dialogVisible = ref(false)
const editingId = ref(null)
const form = reactive({
  name: '',
  code: '',
  address: '',
  description: '',
  is_active: true,
})

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

async function loadCampuses() {
  loading.value = true
  try {
    const params = {}
    if (filters.keyword) params.keyword = filters.keyword
    if (filters.only_active) params.only_active = filters.only_active
    const { data } = await http.get('/config/campuses/', { params })
    campuses.value = data
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  form.name = ''
  form.code = ''
  form.address = ''
  form.description = ''
  form.is_active = true
  dialogVisible.value = true
}

function openEdit(campus) {
  editingId.value = campus.id
  form.name = campus.name
  form.code = campus.code
  form.address = campus.address || ''
  form.description = campus.description || ''
  form.is_active = campus.is_active
  dialogVisible.value = true
}

async function save() {
  if (!form.name.trim()) {
    ElNotification({ title: '保存失败', message: '请输入校区名称。', type: 'warning' })
    return
  }
  if (!form.code.trim()) {
    ElNotification({ title: '保存失败', message: '请输入校区编码。', type: 'warning' })
    return
  }
  actionLoading.value = true
  try {
    if (editingId.value) {
      await http.put(`/config/campuses/${editingId.value}/`, { ...form })
      ElNotification({ title: '修改成功', message: '校区信息已更新。', type: 'success' })
    } else {
      await http.post('/config/campuses/', { ...form })
      ElNotification({ title: '创建成功', message: '校区已添加。', type: 'success' })
    }
    dialogVisible.value = false
    await loadCampuses()
  } finally {
    actionLoading.value = false
  }
}

async function remove(campus) {
  try {
    await ElMessageBox.confirm(
      `确定删除校区「${campus.name}」吗？`,
      '删除确认',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
  } catch (_e) {
    return
  }
  actionLoading.value = true
  try {
    await http.delete(`/config/campuses/${campus.id}/`)
    ElNotification({ title: '删除成功', message: '校区已删除。', type: 'success' })
    await loadCampuses()
  } catch (_e) {
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
  await loadCampuses()
})
</script>

<template>
  <main class="page-shell animated-in">
    <el-card class="section-card" shadow="never">
      <el-row justify="space-between" align="middle" :gutter="12">
        <el-col :xs="24" :sm="16">
          <h2 class="section-title">🏫 校区管理</h2>
          <p style="margin: 0; color: var(--text-sub)">
            维护校区信息，配置可按校区维度覆盖，用户归属于一个校区。
          </p>
        </el-col>
        <el-col :xs="24" :sm="8" style="text-align: right">
          <el-button style="margin-right: 8px" @click="router.push('/config-center')">⚙️ 配置中心</el-button>
          <el-button style="margin-right: 8px" @click="router.push('/dashboard')">返回首页</el-button>
          <el-button type="primary" @click="openCreate">+ 新增校区</el-button>
          <el-button type="danger" plain @click="logout">退出登录</el-button>
        </el-col>
      </el-row>
    </el-card>

    <el-card class="section-card" shadow="never">
      <el-row :gutter="12" style="margin-bottom: 14px">
        <el-col :span="8">
          <el-input v-model="filters.keyword" placeholder="搜索校区名称/编码/地址" clearable @keyup.enter="loadCampuses" />
        </el-col>
        <el-col :span="6">
          <el-select v-model="filters.only_active" style="width: 100%" placeholder="状态筛选" clearable @change="loadCampuses">
            <el-option label="仅启用" value="true" />
            <el-option label="仅停用" value="false" />
          </el-select>
        </el-col>
        <el-col :span="10" style="text-align: right">
          <el-button @click="loadCampuses">🔍 查询</el-button>
        </el-col>
      </el-row>

      <el-skeleton :loading="loading" animated :rows="5">
        <template #default>
          <el-table :data="campuses" stripe border empty-text="暂无校区数据">
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column prop="code" label="校区编码" min-width="120" />
            <el-table-column prop="name" label="校区名称" min-width="150" />
            <el-table-column prop="address" label="地址" min-width="200" show-overflow-tooltip />
            <el-table-column prop="description" label="备注" min-width="200" show-overflow-tooltip />
            <el-table-column prop="user_count" label="用户数" width="100" align="center" />
            <el-table-column label="状态" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="row.is_active ? 'success' : 'info'" effect="plain">
                  {{ row.is_active ? '启用' : '停用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="创建时间" min-width="165">
              <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="180" fixed="right" align="center">
              <template #default="{ row }">
                <el-space>
                  <el-button size="small" type="primary" plain @click="openEdit(row)">编辑</el-button>
                  <el-button size="small" type="danger" plain @click="remove(row)">删除</el-button>
                </el-space>
              </template>
            </el-table-column>
          </el-table>
        </template>
      </el-skeleton>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑校区' : '新增校区'" width="520px">
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="校区编码">
          <el-input v-model="form.code" placeholder="例如：main、east、west" />
        </el-form-item>
        <el-form-item label="校区名称">
          <el-input v-model="form.name" placeholder="例如：主校区、东校区、西校区" />
        </el-form-item>
        <el-form-item label="校区地址">
          <el-input v-model="form.address" placeholder="可选" />
        </el-form-item>
        <el-form-item label="备注说明">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="可选" />
        </el-form-item>
        <el-form-item label="是否启用">
          <el-switch v-model="form.is_active" active-text="启用" inactive-text="停用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="actionLoading" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </main>
</template>
