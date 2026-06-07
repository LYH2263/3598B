import { defineStore } from 'pinia'
import http from '../utils/http'

export const useReminderStore = defineStore('reminder', {
  state: () => ({
    myReminders: [],
    myPendingCount: 0,
    adminReminders: [],
    adminTotal: 0,
    adminStats: null,
    exemptions: [],
  }),
  actions: {
    async fetchMyReminders(status) {
      const params = {}
      if (status) params.status = status
      const { data } = await http.get('/reminder/my/', { params })
      this.myReminders = data.items
      this.myPendingCount = data.pending_count
      return data
    },

    async markHandled(reminderId, note = '') {
      const { data } = await http.post('/reminder/my/handle/', {
        reminder_id: reminderId,
        note,
      })
      await this.fetchMyReminders()
      return data
    },

    async fetchAdminReminders(params = {}) {
      const { data } = await http.get('/reminder/admin/list/', { params })
      this.adminReminders = data.items
      this.adminTotal = data.total
      return data
    },

    async fetchAdminStats() {
      const { data } = await http.get('/reminder/admin/stats/')
      this.adminStats = data
      return data
    },

    async triggerManualReminder(payload) {
      const { data } = await http.post('/reminder/admin/trigger/', payload)
      return data
    },

    async stopAllForUser(userId, reason = '') {
      const { data } = await http.post('/reminder/admin/stop-all/', {
        user_id: userId,
        reason,
      })
      return data
    },

    async resumeForUser(userId) {
      const { data } = await http.post('/reminder/admin/resume/', {
        user_id: userId,
      })
      return data
    },

    async runAdminScan() {
      const { data } = await http.post('/reminder/admin/scan/')
      return data
    },

    async fetchExemptions(onlyExempted = false) {
      const { data } = await http.get('/reminder/admin/exemptions/', {
        params: { only_exempted: onlyExempted },
      })
      this.exemptions = data
      return data
    },
  },
})
