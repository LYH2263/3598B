<script setup>
import { reactive, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElNotification } from 'element-plus'

import AuthLayout from '../layouts/AuthLayout.vue'
import { loginSchema } from '../validators/auth'
import { useAuthStore } from '../stores/auth'
import http from '../utils/http'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)
const captchaLoading = ref(false)
const captcha = reactive({
  captcha_id: '',
  question: '',
})

const form = reactive({
  account: '',
  password: '',
  captcha_answer: '',
  remember_me: true,
})

function applyZodError(result) {
  const first = result.error.issues[0]
  ElNotification({
    title: '输入校验失败',
    message: first?.message || '请检查输入内容。',
    type: 'warning',
  })
}

async function refreshCaptcha() {
  captchaLoading.value = true
  try {
    const { data } = await http.get('/auth/captcha/')
    captcha.captcha_id = data.captcha_id
    captcha.question = data.question
    form.captcha_answer = ''
  } finally {
    captchaLoading.value = false
  }
}

async function handleSubmit() {
  const parsed = loginSchema.safeParse(form)
  if (!parsed.success) {
    applyZodError(parsed)
    return
  }

  loading.value = true
  try {
    await authStore.login({
      ...form,
      captcha_id: captcha.captcha_id,
    })
    ElNotification({ title: '登录成功', message: '欢迎进入充值系统。', type: 'success' })
    await router.push({ name: 'dashboard' })
  } finally {
    loading.value = false
    await refreshCaptcha()
  }
}

onMounted(refreshCaptcha)
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
      <el-form-item label="验证码（简单计算题演示）">
        <el-space fill style="width: 100%">
          <el-input v-model="form.captcha_answer" placeholder="请输入计算结果" />
          <el-button :loading="captchaLoading" @click="refreshCaptcha">{{ captcha.question || '获取验证码' }}</el-button>
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
