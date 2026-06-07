<script setup>
import { reactive, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElNotification } from 'element-plus'

import AuthLayout from '../layouts/AuthLayout.vue'
import { resetCodeSchema, resetSchema } from '../validators/auth'
import { useAuthStore } from '../stores/auth'
import http from '../utils/http'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)
const codeLoading = ref(false)
const captchaLoading = ref(false)
const captcha = reactive({
  captcha_id: '',
  question: '',
})

const codeTips = ref('')

const form = reactive({
  account: '',
  security_answer: '',
  email_code: '',
  new_password: '',
  confirm_password: '',
  captcha_answer: '',
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

async function requestEmailCode() {
  const parsed = resetCodeSchema.safeParse({
    account: form.account,
    security_answer: form.security_answer,
    captcha_answer: form.captcha_answer,
  })
  if (!parsed.success) {
    applyZodError(parsed)
    return
  }

  codeLoading.value = true
  try {
    const data = await authStore.requestResetEmailCode({
      account: form.account,
      security_answer: form.security_answer,
      captcha_answer: form.captcha_answer,
      captcha_id: captcha.captcha_id,
    })

    codeTips.value = `邮箱验证码已发送：${data.masked_email}（演示验证码：${data.demo_email_code}）`
    ElNotification({ title: '验证码已发送', message: '请填写邮箱验证码后提交密码重置。', type: 'success' })
  } finally {
    codeLoading.value = false
    await refreshCaptcha()
  }
}

async function handleSubmit() {
  const parsed = resetSchema.safeParse(form)
  if (!parsed.success) {
    applyZodError(parsed)
    return
  }

  loading.value = true
  try {
    await authStore.resetPassword({
      ...form,
      captcha_id: captcha.captcha_id,
    })
    ElNotification({
      title: '密码已更新',
      message: '请使用新密码重新登录。',
      type: 'success',
    })
    await router.push('/login')
  } finally {
    loading.value = false
    await refreshCaptcha()
  }
}

onMounted(refreshCaptcha)
</script>

<template>
  <AuthLayout title="密码重置" subtitle="通过安全问题 + 邮箱验证码完成重置">
    <el-form label-position="top" @submit.prevent>
      <el-form-item label="账号">
        <el-input v-model="form.account" placeholder="请输入用户名 / 学号 / 手机号 / 邮箱" clearable />
      </el-form-item>

      <el-form-item label="安全问题答案">
        <el-input v-model="form.security_answer" placeholder="请输入您设置的安全问题答案" clearable />
      </el-form-item>

      <el-form-item label="验证码（计算题）">
        <el-space fill style="width: 100%">
          <el-input v-model="form.captcha_answer" placeholder="请输入计算结果" />
          <el-button :loading="captchaLoading" @click="refreshCaptcha">{{ captcha.question || '获取验证码' }}</el-button>
        </el-space>
      </el-form-item>

      <el-form-item>
        <el-button :loading="codeLoading" style="width: 100%" @click="requestEmailCode">发送邮箱验证码</el-button>
      </el-form-item>

      <el-alert v-if="codeTips" :title="codeTips" type="info" show-icon :closable="false" style="margin-bottom: 16px" />

      <el-form-item label="邮箱验证码">
        <el-input v-model="form.email_code" placeholder="请输入邮箱验证码" clearable />
      </el-form-item>

      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="新密码">
            <el-input v-model="form.new_password" type="password" show-password placeholder="请输入新密码" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="确认新密码">
            <el-input v-model="form.confirm_password" type="password" show-password placeholder="请再次输入新密码" />
          </el-form-item>
        </el-col>
      </el-row>

      <el-form-item>
        <el-button type="primary" :loading="loading" style="width: 100%" @click="handleSubmit">提交重置</el-button>
      </el-form-item>
      <el-link type="primary" @click="router.push('/login')">返回登录</el-link>
    </el-form>
  </AuthLayout>
</template>
