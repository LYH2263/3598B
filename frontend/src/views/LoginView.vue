<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElNotification } from 'element-plus'

import AuthLayout from '../layouts/AuthLayout.vue'
import { loginSchema } from '../validators/auth'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)

const form = reactive({
  account: '',
  password: '',
  remember_me: true,
})

const demoAccounts = [
  { label: '管理员', account: 'admin_3598', password: 'Admin@123456' },
  { label: '学生', account: 'student_3598', password: 'Student@123456' },
]

function fillDemoAccount(item) {
  form.account = item.account
  form.password = item.password
}

function applyZodError(result) {
  const first = result.error.issues[0]
  ElNotification({
    title: '输入校验失败',
    message: first?.message || '请检查输入内容。',
    type: 'warning',
  })
}

async function handleSubmit() {
  const parsed = loginSchema.safeParse(form)
  if (!parsed.success) {
    applyZodError(parsed)
    return
  }

  loading.value = true
  try {
    await authStore.login({ ...form })
    ElNotification({ title: '登录成功', message: '欢迎进入充值系统。', type: 'success' })
    await router.push({ name: 'dashboard' })
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <AuthLayout title="账号登录" subtitle="支持用户名 / 学号 / 手机号 / 邮箱登录">
    <el-form label-position="top" @submit.prevent>
      <el-form-item label="账号">
        <el-input v-model="form.account" placeholder="请输入账号" clearable />
      </el-form-item>
      <el-form-item label="密码">
        <el-input v-model="form.password" type="password" show-password placeholder="请输入密码" clearable />
      </el-form-item>
      <el-form-item label="演示账号（点击填充）">
        <el-space wrap>
          <el-button
            v-for="item in demoAccounts"
            :key="item.account"
            size="small"
            type="primary"
            plain
            @click="fillDemoAccount(item)"
          >
            {{ item.label }}：{{ item.account }}
          </el-button>
        </el-space>
      </el-form-item>
      <el-form-item>
        <el-checkbox v-model="form.remember_me">记住我（7天内免重复登录）</el-checkbox>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loading" style="width: 100%" @click="handleSubmit">立即登录</el-button>
      </el-form-item>
      <el-space>
        <el-link type="primary" @click="router.push('/register')">没有账号，去注册</el-link>
        <el-link type="warning" @click="router.push('/reset-password')">忘记密码</el-link>
      </el-space>
    </el-form>
  </AuthLayout>
</template>
