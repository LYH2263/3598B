import { defineStore } from 'pinia'
import http from '../utils/http'

export const useAnalyticsStore = defineStore('analytics', {
  state: () => ({
    loading: false,
    timeWindow: '7d',
    kpis: {
      total_users: 0,
      active_users: 0,
      frozen_accounts: 0,
      pending_orders: 0,
      total_recharge: 0,
      total_consumption: 0,
      recharge_count: 0,
      consumption_count: 0,
    },
    trends: {
      recharge: [],
      consumption: [],
      user_growth: [],
    },
    distributions: {
      recharge_by_channel: [],
      consumption_by_category: [],
      users_by_role: [],
    },
    dashboardLayout: [],
    pinnedReports: [],
  }),
  actions: {
    setTimeWindow(window) {
      this.timeWindow = window
      return this.loadPlatformData()
    },
    async loadPlatformData() {
      this.loading = true
      try {
        const { data } = await http.get('/billing/analytics/platform/', {
          params: { window: this.timeWindow },
        })
        this.kpis = data.kpis
        this.trends = data.trends
        this.distributions = data.distributions
      } finally {
        this.loading = false
      }
    },
    async loadDashboardLayout() {
      try {
        const { data } = await http.get('/billing/analytics/dashboard-pref/')
        this.dashboardLayout = data.layout || []
      } catch (_e) {
        this.dashboardLayout = []
      }
    },
    async saveDashboardLayout(layout) {
      this.dashboardLayout = layout
      try {
        await http.put('/billing/analytics/dashboard-pref/', { layout })
      } catch (_e) {}
    },
  },
})
