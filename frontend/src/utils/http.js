import axios from 'axios'
import { ElNotification } from 'element-plus'
import { useAuthStore, getAccessTokenFromStorage } from '../stores/auth'

const http = axios.create({
  baseURL: '/api',
  timeout: 12000,
})

http.interceptors.request.use((config) => {
  const token = getAccessTokenFromStorage()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error.response?.status
    const originalConfig = error.config || {}

    if (
      status === 401 &&
      !originalConfig._retry &&
      !originalConfig.url?.includes('/auth/login/') &&
      !originalConfig.url?.includes('/auth/token/refresh/')
    ) {
      originalConfig._retry = true
      const authStore = useAuthStore()
      const newAccess = await authStore.refreshAccessToken()
      if (newAccess) {
        originalConfig.headers = {
          ...(originalConfig.headers || {}),
          Authorization: `Bearer ${newAccess}`,
        }
        return http(originalConfig)
      }
    }

    const message = error.response?.data?.detail || '请求失败，请稍后重试。'
    ElNotification({
      title: '请求异常',
      message,
      type: 'error',
    })

    return Promise.reject(error)
  }
)

export default http
