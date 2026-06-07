import { defineStore } from 'pinia'
import http from '../utils/http'

const ACCESS_KEY = 'label3598_access_token'
const REFRESH_KEY = 'label3598_refresh_token'
const USER_KEY = 'label3598_user'
const REMEMBER_KEY = 'label3598_remember'

function readStorage(key, remember) {
  return (remember ? localStorage : sessionStorage).getItem(key)
}

function writeStorage(key, value, remember) {
  if (remember) {
    localStorage.setItem(key, value)
    sessionStorage.removeItem(key)
    return
  }
  sessionStorage.setItem(key, value)
  localStorage.removeItem(key)
}

function removeStorage(key) {
  localStorage.removeItem(key)
  sessionStorage.removeItem(key)
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    accessToken: '',
    refreshToken: '',
    user: null,
    rememberMe: false,
  }),
  getters: {
    isLoggedIn: (state) => Boolean(state.accessToken),
  },
  actions: {
    hydrate() {
      const remembered = localStorage.getItem(REMEMBER_KEY) === '1'
      const accessToken = readStorage(ACCESS_KEY, remembered)
      const refreshToken = readStorage(REFRESH_KEY, remembered)
      const userText = readStorage(USER_KEY, remembered)

      this.rememberMe = remembered
      this.accessToken = accessToken || ''
      this.refreshToken = refreshToken || ''
      this.user = userText ? JSON.parse(userText) : null
    },

    setSession({ access, refresh, user, rememberMe }) {
      this.accessToken = access
      this.refreshToken = refresh
      this.user = user
      this.rememberMe = rememberMe

      writeStorage(ACCESS_KEY, access, rememberMe)
      writeStorage(REFRESH_KEY, refresh, rememberMe)
      writeStorage(USER_KEY, JSON.stringify(user), rememberMe)
      localStorage.setItem(REMEMBER_KEY, rememberMe ? '1' : '0')
    },

    clearSession() {
      this.accessToken = ''
      this.refreshToken = ''
      this.user = null
      this.rememberMe = false

      removeStorage(ACCESS_KEY)
      removeStorage(REFRESH_KEY)
      removeStorage(USER_KEY)
      localStorage.removeItem(REMEMBER_KEY)
    },

    async login(payload) {
      const { data } = await http.post('/auth/login/', payload)
      this.setSession({
        access: data.access,
        refresh: data.refresh,
        user: data.user,
        rememberMe: data.remember_me,
      })
      return data
    },

    async register(payload) {
      const { data } = await http.post('/auth/register/', payload)
      return data
    },

    async resetPassword(payload) {
      const { data } = await http.post('/auth/reset-password/', payload)
      return data
    },

    async requestResetEmailCode(payload) {
      const { data } = await http.post('/auth/reset-email-code/', payload)
      return data
    },

    async refreshAccessToken() {
      if (!this.refreshToken) {
        this.clearSession()
        return null
      }

      try {
        const { data } = await http.post('/auth/token/refresh/', {
          refresh: this.refreshToken,
        })
        this.accessToken = data.access
        writeStorage(ACCESS_KEY, data.access, this.rememberMe)
        return data.access
      } catch (error) {
        this.clearSession()
        return null
      }
    },

    async fetchMe() {
      const { data } = await http.get('/auth/me/')
      this.user = data.user
      writeStorage(USER_KEY, JSON.stringify(data.user), this.rememberMe)
      return data.user
    },
  },
})

export function getAccessTokenFromStorage() {
  const remembered = localStorage.getItem(REMEMBER_KEY) === '1'
  return readStorage(ACCESS_KEY, remembered)
}
