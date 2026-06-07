import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus, { ElNotification } from 'element-plus'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import 'element-plus/dist/index.css'

import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth'
import './style.css'

const app = createApp(App)
app.config.errorHandler = (error) => {
  ElNotification({
    title: '页面异常',
    message: '页面出现异常，请刷新后重试。',
    type: 'error',
  })
}

app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })

const authStore = useAuthStore()
authStore.hydrate()

app.mount('#app')
