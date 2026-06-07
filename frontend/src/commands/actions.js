import { COMMAND_CATEGORIES } from './registry'

export default [
  {
    id: 'action.freeze-wallet',
    title: '冻结账户',
    description: '打开冻结账户对话框（输入用户名直接执行）',
    category: COMMAND_CATEGORIES.action,
    keywords: ['冻结', 'freeze', '封禁', 'lock'],
    icon: '❄️',
    adminOnly: true,
    handler: ({ openDialog, payload }) => {
      openDialog('freeze', payload)
    },
  },
  {
    id: 'action.unfreeze-wallet',
    title: '解冻账户',
    description: '打开解冻账户对话框',
    category: COMMAND_CATEGORIES.action,
    keywords: ['解冻', 'unfreeze', '解封', 'unlock'],
    icon: '🌞',
    adminOnly: true,
    handler: ({ openDialog, payload }) => {
      openDialog('unfreeze', payload)
    },
  },
  {
    id: 'action.publish-announcement',
    title: '发布公告',
    description: '打开发布公告表单',
    category: COMMAND_CATEGORIES.action,
    keywords: ['发布公告', 'announcement', '公告', '通知'],
    icon: '📢',
    adminOnly: true,
    handler: ({ openDialog, router }) => {
      router.push('/dashboard')
      setTimeout(() => openDialog('publish-announcement'), 100)
    },
  },
  {
    id: 'action.submit-recharge',
    title: '提交充值订单',
    description: '快速提交充值订单',
    category: COMMAND_CATEGORIES.action,
    keywords: ['充值', 'recharge', '支付', '订单'],
    icon: '💳',
    handler: ({ openDialog, router }) => {
      router.push('/dashboard')
      setTimeout(() => openDialog('submit-recharge'), 100)
    },
  },
  {
    id: 'goto.user-detail',
    title: '用户详情',
    description: '输入用户名直接进入用户详情（管理员）',
    category: COMMAND_CATEGORIES.search,
    keywords: ['用户', 'user', '学生', 'member'],
    icon: '👤',
    adminOnly: true,
    handler: ({ searchUser, payload }) => {
      searchUser(payload)
    },
  },
  {
    id: 'goto.order-detail',
    title: '订单详情',
    description: '输入订单号直接打开订单详情，如：订单 RC20260101001',
    category: COMMAND_CATEGORIES.search,
    keywords: ['订单', 'order', '充值', 'RC'],
    icon: '🧾',
    handler: ({ searchOrder, payload }) => {
      searchOrder(payload)
    },
  },
]
