export const COMMAND_CATEGORIES = {
  navigation: '页面导航',
  action: '快捷操作',
  search: '搜索跳转',
}

const registry = new Map()

export function registerCommands(commands) {
  for (const cmd of commands) {
    if (!cmd || !cmd.id) continue
    registry.set(cmd.id, {
      id: cmd.id,
      title: cmd.title,
      description: cmd.description || '',
      category: cmd.category || COMMAND_CATEGORIES.navigation,
      keywords: cmd.keywords || [],
      icon: cmd.icon || '📋',
      adminOnly: Boolean(cmd.adminOnly),
      handler: cmd.handler || null,
    })
  }
}

export function unregisterCommand(id) {
  registry.delete(id)
}

export function getAllCommands(user) {
  const isAdmin = user?.profile?.role === 'admin'
  const result = []
  for (const cmd of registry.values()) {
    if (cmd.adminOnly && !isAdmin) continue
    result.push(cmd)
  }
  return result
}

export function findCommands(keyword, user) {
  const kw = (keyword || '').trim().toLowerCase()
  const all = getAllCommands(user)
  if (!kw) return all
  return all.filter((cmd) => {
    if (cmd.title.toLowerCase().includes(kw)) return true
    if (cmd.description.toLowerCase().includes(kw)) return true
    if (cmd.id.toLowerCase().includes(kw)) return true
    if (cmd.keywords && cmd.keywords.some((k) => k.toLowerCase().includes(kw))) return true
    return false
  })
}

export function executeCommand(id, context) {
  const cmd = registry.get(id)
  if (!cmd || typeof cmd.handler !== 'function') return false
  try {
    cmd.handler(context)
    return true
  } catch (e) {
    console.error('Command execution failed:', id, e)
    return false
  }
}
