import { defineStore } from 'pinia'
import http from '../utils/http'

export const useReportsStore = defineStore('reports', {
  state: () => ({
    loading: false,
    list: [],
    currentPreview: null,
  }),
  actions: {
    async loadList() {
      this.loading = true
      try {
        const { data } = await http.get('/billing/analytics/reports/')
        this.list = data
      } finally {
        this.loading = false
      }
    },
    async createReport(payload) {
      const { data } = await http.post('/billing/analytics/reports/', payload)
      await this.loadList()
      return data
    },
    async updateReport(id, payload) {
      const { data } = await http.put(`/billing/analytics/reports/${id}/`, payload)
      await this.loadList()
      return data
    },
    async deleteReport(id) {
      await http.delete(`/billing/analytics/reports/${id}/`)
      await this.loadList()
    },
    async runReport(id) {
      const { data } = await http.post(`/billing/analytics/reports/${id}/`)
      return data
    },
    async queryDataset(payload) {
      const { data } = await http.post('/billing/analytics/query/', payload)
      this.currentPreview = data
      return data
    },
  },
})
