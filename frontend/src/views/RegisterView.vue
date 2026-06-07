<script setup>
import { reactive, ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElNotification } from 'element-plus'

import AuthLayout from '../layouts/AuthLayout.vue'
import { registerSchema } from '../validators/auth'
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
  role: 'student',
  username: '',
  student_id: '',
  phone: '',
  email: '',
  security_question: '',
  security_answer: '',
  password: '',
  confirm_password: '',
  captcha_answer: '',
})

const isStudent = computed(() => form.role === 'student')

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
  const parsed = registerSchema.safeParse(form)
  if (!parsed.success) {
    applyZodError(parsed)
    return
  }

  loading.value = true
  try {
    await authStore.register({
      ...form,
      captcha_id: captcha.captcha_id,
    })
    ElNotification({
      title: '注册成功',
      message: '账号创建完成，请登录。',
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
  <AuthLayout title="账号注册" subtitle="支持学生与管理员角色创建，含安全问题保护">
    <el-form label-position="top" @submit.prevent>
      <el-form-item label="角色">
        <el-radio-group v-model="form.role">
          <el-radio-button label="student">学生</el-radio-button>
          <el-radio-button label="admin">管理员</el-radio-button>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="用户名">
        <el-input v-model="form.username" placeholder="请输入用户名" clearable />
      </el-form-item>

      <el-form-item v-if="isStudent" label="学号">
        <el-input v-model="form.student_id" placeholder="请输入学号" clearable />
      </el-form-item>

      <el-form-item label="手机号">
        <el-input v-model="form.phone" placeholder="请输入手机号" clearable />
      </el-form-item>

      <el-form-item label="邮箱">
        <el-input v-model="form.email" placeholder="请输入邮箱" clearable />
      </el-form-item>

      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="安全问题">
            <el-input v-model="form.security_question" placeholder="例如：您的小学名称是？" clearable />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="安全问题答案">
            <el-input v-model="form.security_answer" placeholder="请输入安全答案" clearable />
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="登录密码">
            <el-input v-model="form.password" type="password" show-password placeholder="请输入登录密码" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="确认密码">
            <el-input v-model="form.confirm_password" type="password" show-password placeholder="请再次输入密码" />
          </el-form-item>
        </el-col>
      </el-row>

      <el-form-item label="验证码">
        <el-space fill style="width: 100%">
          <el-input v-model="form.captcha_answer" placeholder="请输入计算结果" />
          <el-button :loading="captchaLoading" @click="refreshCaptcha">{{ captcha.question || '获取验证码' }}</el-button>
        </el-space>
      </el-form-item>

      <el-form-item>
        <el-button type="primary" style="width: 100%" :loading="loading" @click="handleSubmit">创建账号</el-button>
      </el-form-item>

      <el-link type="primary" @click="router.push('/login')">已有账号，返回登录</el-link>
    </el-form>
  </AuthLayout>
</template>
