import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/dashboard',
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { guestOnly: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('../views/RegisterView.vue'),
      meta: { guestOnly: true },
    },
    {
      path: '/reset-password',
      name: 'reset-password',
      component: () => import('../views/ResetPasswordView.vue'),
      meta: { guestOnly: true },
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: () => import('../views/DashboardView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/activities',
      name: 'activities',
      component: () => import('../views/ActivitiesView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/activities/manage',
      name: 'activity-manage',
      component: () => import('../views/ActivityManageView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/activities/:id',
      name: 'activity-detail',
      component: () => import('../views/ActivityDetailView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/analytics',
      name: 'analytics',
      component: () => import('../views/AdminAnalyticsView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/reports',
      name: 'reports',
      component: () => import('../views/SavedReportsView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/reports/build',
      name: 'report-builder',
      component: () => import('../views/CustomReportBuilder.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/my-refunds',
      name: 'my-refunds',
      component: () => import('../views/MyRefundsView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/my-invoices',
      name: 'my-invoices',
      component: () => import('../views/MyInvoicesView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/invoice-titles',
      name: 'invoice-titles',
      component: () => import('../views/InvoiceTitlesView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/refund-approval',
      name: 'refund-approval',
      component: () => import('../views/RefundApprovalView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/invoice-processing',
      name: 'invoice-processing',
      component: () => import('../views/InvoiceProcessingView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/config-center',
      name: 'config-center',
      component: () => import('../views/ConfigCenterView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/campus-manage',
      name: 'campus-manage',
      component: () => import('../views/CampusManageView.vue'),
      meta: { requiresAuth: true },
    },
  ],
})

router.beforeEach((to) => {
  const authStore = useAuthStore()
  authStore.hydrate()

  if (to.meta.requiresAuth && !authStore.isLoggedIn) {
    return { name: 'login' }
  }

  if (to.meta.guestOnly && authStore.isLoggedIn) {
    return { name: 'dashboard' }
  }

  return true
})

export default router
