export const DATASETS = {
  recharge: {
    label: '充值流水',
    description: '所有充值入账记录',
    dimensions: [
      { key: 'day', label: '按日' },
      { key: 'week', label: '按周' },
      { key: 'month', label: '按月' },
      { key: 'channel', label: '按渠道' },
    ],
    measures: [
      { key: 'amount', label: '充值金额' },
      { key: 'count', label: '充值笔数' },
      { key: 'user_count', label: '充值人数' },
      { key: 'avg_amount', label: '平均单笔金额' },
    ],
    filters: [
      { key: 'channel', label: '充值渠道', type: 'select', options: [
        { label: '全部', value: '' },
        { label: '支付宝', value: 'alipay' },
        { label: '微信支付', value: 'wechat' },
        { label: '银行卡', value: 'bank' },
      ] },
      { key: 'start_date', label: '开始日期', type: 'date' },
      { key: 'end_date', label: '结束日期', type: 'date' },
    ],
  },
  consumption: {
    label: '消费流水',
    description: '水费/电费扣费记录',
    dimensions: [
      { key: 'day', label: '按日' },
      { key: 'week', label: '按周' },
      { key: 'month', label: '按月' },
      { key: 'category', label: '按类目' },
    ],
    measures: [
      { key: 'amount', label: '消费金额' },
      { key: 'count', label: '消费笔数' },
      { key: 'user_count', label: '消费人数' },
      { key: 'avg_amount', label: '平均单笔金额' },
    ],
    filters: [
      { key: 'category', label: '消费类目', type: 'select', options: [
        { label: '全部', value: '' },
        { label: '水费', value: 'water' },
        { label: '电费', value: 'electricity' },
      ] },
      { key: 'start_date', label: '开始日期', type: 'date' },
      { key: 'end_date', label: '结束日期', type: 'date' },
    ],
  },
  user_growth: {
    label: '用户增长',
    description: '新注册用户数据',
    dimensions: [
      { key: 'day', label: '按日' },
      { key: 'week', label: '按周' },
      { key: 'month', label: '按月' },
      { key: 'role', label: '按角色' },
    ],
    measures: [
      { key: 'count', label: '新增人数' },
      { key: 'user_count', label: '去重人数' },
    ],
    filters: [
      { key: 'role', label: '用户角色', type: 'select', options: [
        { label: '全部', value: '' },
        { label: '学生', value: 'student' },
        { label: '管理员', value: 'admin' },
      ] },
      { key: 'start_date', label: '开始日期', type: 'date' },
      { key: 'end_date', label: '结束日期', type: 'date' },
    ],
  },
}

export const CHART_TYPES = [
  { key: 'bar', label: '柱状图' },
  { key: 'line', label: '折线图' },
  { key: 'area', label: '面积图' },
  { key: 'pie', label: '饼图' },
  { key: 'donut', label: '环形图' },
]
