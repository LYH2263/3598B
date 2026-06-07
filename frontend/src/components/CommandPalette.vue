<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { ElNotification } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { findCommands, executeCommand, COMMAND_CATEGORIES } from '../commands'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false,
  },
  dialogHandlers: {
    type: Object,
    default: () => ({}),
  },
})

const emit = defineEmits(['update:visible', 'close'])

const router = useRouter()
const authStore = useAuthStore()
const inputRef = ref(null)
const input = ref('')
const activeIndex = ref(0)
const dialogRef = ref(null)

const parsed = computed(() => {
  const raw = (input.value || '').trim()
  if (!raw) return { cmd: '', payload: '' }
  const parts = raw.split(/\s+/)
  if (parts.length === 1) return { cmd: raw, payload: '' }
  return { cmd: parts[0], payload: parts.slice(1).join(' ') }
})

const matchedCommands = computed(() => {
  const kw = parsed.value.cmd || input.value
  return findCommands(kw, authStore.user)
})

const groupedCommands = computed(() => {
  const groups = new Map()
  for (const c of matchedCommands.value) {
    const cat = c.category || COMMAND_CATEGORIES.navigation
    if (!groups.has(cat)) groups.set(cat, [])
    groups.get(cat).push(c)
  }
  const result = []
  for (const [label, items] of groups) {
    result.push({ label, items })
  }
  return result
})

const flatList = computed(() => {
  const list = []
  for (const g of groupedCommands.value) {
    for (const item of g.items) list.push(item)
  }
  return list
})

function close() {
  emit('update:visible', false)
  emit('close')
  input.value = ''
  activeIndex.value = 0
}

function onKeydown(e) {
  if (e.key === 'Escape') {
    e.preventDefault()
    close()
  } else if (e.key === 'ArrowDown') {
    e.preventDefault()
    if (!flatList.value.length) return
    activeIndex.value = (activeIndex.value + 1) % flatList.value.length
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    if (!flatList.value.length) return
    activeIndex.value =
      activeIndex.value <= 0 ? flatList.value.length - 1 : activeIndex.value - 1
  } else if (e.key === 'Enter') {
    e.preventDefault()
    runActive()
  }
}

function runActive() {
  const cmd = flatList.value[activeIndex.value]
  if (!cmd) return
  runCommand(cmd)
}

function runCommand(cmd) {
  const ctx = {
    router,
    authStore,
    payload: parsed.value.payload,
    openDialog: (type, initialPayload) => {
      const handler = props.dialogHandlers[type]
      if (handler) handler(initialPayload || parsed.value.payload)
      else ElNotification({ title: '提示', message: `对话框 ${type} 未注册`, type: 'info' })
    },
    searchUser: (kw) => {
      props.dialogHandlers.searchUser?.(kw)
    },
    searchOrder: (kw) => {
      props.dialogHandlers.searchOrder?.(kw)
    },
  }
  const ok = executeCommand(cmd.id, ctx)
  if (ok) {
    close()
  } else {
    ElNotification({ title: '执行失败', message: '命令无法执行', type: 'warning' })
  }
}

function highlight(text, kw) {
  if (!text || !kw) return text || ''
  const safe = String(text)
  const idx = safe.toLowerCase().indexOf(kw.toLowerCase())
  if (idx < 0) return safe
  return (
    safe.slice(0, idx) +
    '<mark style="background:#fff3a3;color:inherit;padding:0 2px;border-radius:2px">' +
    safe.slice(idx, idx + kw.length) +
    '</mark>' +
    safe.slice(idx + kw.length)
  )
}

function onOverlayClick(e) {
  if (e.target === e.currentTarget) close()
}

watch(
  () => props.visible,
  (v) => {
    if (v) {
      activeIndex.value = 0
      setTimeout(() => inputRef.value?.focus(), 50)
    }
  }
)

watch(
  () => input.value,
  () => {
    activeIndex.value = 0
  }
)

function bindGlobalKey(e) {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    emit('update:visible', !props.visible)
  }
}

onMounted(() => {
  document.addEventListener('keydown', bindGlobalKey)
})
onBeforeUnmount(() => {
  document.removeEventListener('keydown', bindGlobalKey)
})
</script>

<template>
  <transition name="palette-fade">
    <div v-if="visible" class="palette-overlay" @click="onOverlayClick" @keydown="onKeydown">
      <div class="palette-dialog" ref="dialogRef" @click.stop>
        <div class="palette-header">
          <el-input
            ref="inputRef"
            v-model="input"
            placeholder="输入命令或关键字，如：冻结 张三、发布公告、订单 RC2026...、/config-center"
            size="large"
            clearable
            @keydown="onKeydown"
          >
            <template #prefix>
              <el-icon color="#409eff"><Search /></el-icon>
            </template>
            <template #suffix>
              <span class="kbd-hint">ESC 关闭</span>
            </template>
          </el-input>
          <div v-if="parsed.payload" class="palette-payload">附带参数：<b>{{ parsed.payload }}</b></div>
        </div>

        <div class="palette-body">
          <div v-if="!flatList.length" class="palette-empty">未匹配到命令，尝试输入关键字搜索</div>
          <template v-else>
            <div v-for="group in groupedCommands" :key="group.label" class="palette-group">
              <div class="palette-group-label">{{ group.label }}</div>
              <ul class="palette-list">
                <li
                  v-for="item in group.items"
                  :key="item.id"
                  class="palette-item"
                  :class="{ active: flatList.findIndex((x) => x.id === item.id) === activeIndex }"
                  @click="runCommand(item)"
                  @mouseenter="activeIndex = flatList.findIndex((x) => x.id === item.id)"
                >
                  <span class="palette-icon">{{ item.icon }}</span>
                  <div class="palette-text">
                    <div class="palette-title" v-html="highlight(item.title, parsed.cmd || input)" />
                    <div class="palette-desc" v-html="highlight(item.description, parsed.cmd || input)" />
                  </div>
                  <span class="palette-enter">↵</span>
                </li>
              </ul>
            </div>
          </template>
        </div>

        <div class="palette-footer">
          <span>💡 提示：按 <kbd>↑</kbd><kbd>↓</kbd> 选择，<kbd>Enter</kbd> 执行，<kbd>Ctrl+K</kbd> 呼出/关闭</span>
        </div>
      </div>
    </div>
  </transition>
</template>

<style scoped>
.palette-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(2px);
  z-index: 5000;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 15vh;
}
.palette-dialog {
  width: min(680px, 92vw);
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.25);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  max-height: 70vh;
}
.palette-header {
  padding: 14px 14px 6px;
  border-bottom: 1px solid #f2f3f5;
}
.palette-header :deep(.el-input__wrapper) {
  border-radius: 10px;
  box-shadow: none;
  background: #f7f8fa;
}
.palette-payload {
  margin-top: 6px;
  font-size: 12px;
  color: #606266;
}
.kbd-hint {
  display: inline-block;
  font-size: 11px;
  padding: 1px 6px;
  background: #f2f3f5;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  color: #606266;
}
.palette-body {
  flex: 1;
  overflow-y: auto;
  padding: 6px;
}
.palette-empty {
  padding: 40px 0;
  text-align: center;
  color: #909399;
  font-size: 13px;
}
.palette-group {
  margin-bottom: 4px;
}
.palette-group-label {
  padding: 6px 10px 2px;
  font-size: 12px;
  font-weight: 600;
  color: #909399;
  letter-spacing: 0.5px;
}
.palette-list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.palette-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.12s;
}
.palette-item:hover,
.palette-item.active {
  background: #ecf5ff;
}
.palette-icon {
  font-size: 18px;
  width: 28px;
  text-align: center;
}
.palette-text {
  flex: 1;
  min-width: 0;
}
.palette-title {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}
.palette-desc {
  font-size: 12px;
  color: #909399;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.palette-enter {
  font-size: 14px;
  color: #c0c4cc;
  font-weight: 700;
}
.palette-footer {
  padding: 10px 14px;
  border-top: 1px solid #f2f3f5;
  font-size: 12px;
  color: #909399;
  background: #fafafa;
}
.palette-footer kbd {
  display: inline-block;
  padding: 0 5px;
  margin: 0 2px;
  background: #fff;
  border: 1px solid #dcdfe6;
  border-bottom-width: 2px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 11px;
  color: #606266;
}
.palette-fade-enter-active,
.palette-fade-leave-active {
  transition: opacity 0.18s ease;
}
.palette-fade-enter-active .palette-dialog,
.palette-fade-leave-active .palette-dialog {
  transition: transform 0.18s ease, opacity 0.18s ease;
}
.palette-fade-enter-from,
.palette-fade-leave-to {
  opacity: 0;
}
.palette-fade-enter-from .palette-dialog,
.palette-fade-leave-to .palette-dialog {
  transform: translateY(-12px) scale(0.98);
  opacity: 0;
}
</style>
