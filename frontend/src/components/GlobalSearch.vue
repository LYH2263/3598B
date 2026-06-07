<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Loading } from '@element-plus/icons-vue'
import http from '../utils/http'

const props = defineProps({
  placeholder: {
    type: String,
    default: '全局搜索用户、订单、公告、配置...  (Ctrl+K 命令面板)',
  },
  limit: {
    type: Number,
    default: 5,
  },
})

const emit = defineEmits(['select', 'viewAll', 'openPalette'])

const router = useRouter()
const keyword = ref('')
const loading = ref(false)
const dropdownVisible = ref(false)
const result = ref({ keyword: '', groups: [], is_admin: false })
const debounceTimer = ref(null)
const inputRef = ref(null)
const containerRef = ref(null)
const activeIndex = ref(-1)

const flattenedItems = computed(() => {
  const items = []
  for (const g of result.value.groups || []) {
    for (const item of g.items) {
      items.push({ ...item, _category: g.category, _label: g.label })
    }
    if (g.has_more) {
      items.push({ _viewAll: true, _category: g.category, _label: g.label, title: `查看全部${g.label}...` })
    }
  }
  return items
})

function handleDocClick(e) {
  if (containerRef.value && !containerRef.value.contains(e.target)) {
    dropdownVisible.value = false
  }
}

function clearTimer() {
  if (debounceTimer.value) {
    clearTimeout(debounceTimer.value)
    debounceTimer.value = null
  }
}

async function doSearch() {
  const q = keyword.value.trim()
  if (!q) {
    result.value = { keyword: '', groups: [] }
    activeIndex.value = -1
    return
  }
  loading.value = true
  try {
    const { data } = await http.get('/search/', {
      params: { q, limit: props.limit },
    })
    result.value = data
    activeIndex.value = -1
  } catch (e) {
    result.value = { keyword: q, groups: [] }
  } finally {
    loading.value = false
  }
}

function onInput() {
  clearTimer()
  dropdownVisible.value = true
  debounceTimer.value = setTimeout(() => doSearch(), 250)
}

function onFocus() {
  if (keyword.value.trim()) {
    dropdownVisible.value = true
  }
}

function onBlur() {
  setTimeout(() => {
    dropdownVisible.value = false
  }, 150)
}

function highlight(text, kw) {
  if (!text || !kw) return text || ''
  const safeText = String(text)
  const idx = safeText.toLowerCase().indexOf(kw.toLowerCase())
  if (idx < 0) return safeText
  return (
    safeText.slice(0, idx) +
    '<mark style="background:#fff3a3;color:inherit;padding:0 2px;border-radius:2px">' +
    safeText.slice(idx, idx + kw.length) +
    '</mark>' +
    safeText.slice(idx + kw.length)
  )
}

function selectItem(item) {
  if (item._viewAll) {
    emit('viewAll', { category: item._category, keyword: result.value.keyword })
    dropdownVisible.value = false
    keyword.value = ''
    return
  }
  emit('select', item)
  dropdownVisible.value = false
  if (item.url) {
    router.push({ path: item.url, query: item.url_params || {} })
  }
  keyword.value = ''
}

function viewAll(category) {
  emit('viewAll', { category, keyword: result.value.keyword })
  dropdownVisible.value = false
  keyword.value = ''
}

function onKeyDown(e) {
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    if (!flattenedItems.value.length) return
    activeIndex.value = (activeIndex.value + 1) % flattenedItems.value.length
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    if (!flattenedItems.value.length) return
    activeIndex.value =
      activeIndex.value <= 0 ? flattenedItems.value.length - 1 : activeIndex.value - 1
  } else if (e.key === 'Enter') {
    if (activeIndex.value >= 0 && flattenedItems.value[activeIndex.value]) {
      e.preventDefault()
      selectItem(flattenedItems.value[activeIndex.value])
    }
  } else if (e.key === 'Escape') {
    dropdownVisible.value = false
    keyword.value = ''
  } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    emit('openPalette')
  }
}

watch(keyword, () => {
  if (!keyword.value) {
    activeIndex.value = -1
  }
})

onBeforeUnmount(() => {
  clearTimer()
  document.removeEventListener('click', handleDocClick)
})

document.addEventListener('click', handleDocClick)
</script>

<template>
  <div class="global-search-wrap" ref="containerRef">
    <el-input
      ref="inputRef"
      v-model="keyword"
      :placeholder="placeholder"
      clearable
      :prefix-icon="Search"
      class="global-search-input"
      size="default"
      @input="onInput"
      @focus="onFocus"
      @blur="onBlur"
      @keydown="onKeyDown"
    >
      <template #suffix>
        <span class="kbd-hint" @click.stop="$emit('openPalette')">Ctrl+K</span>
      </template>
    </el-input>

    <transition name="fade">
      <div v-if="dropdownVisible && keyword.trim()" class="global-search-dropdown" @mousedown.prevent>
        <div v-if="loading" class="gs-loading">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>搜索中...</span>
        </div>

        <div v-else-if="!result.groups.length" class="gs-empty">未找到匹配结果</div>

        <template v-else>
          <div v-for="group in result.groups" :key="group.category" class="gs-group">
            <div class="gs-group-header">
              <span class="gs-group-label">{{ group.label }}</span>
              <el-button
                v-if="group.has_more"
                link
                type="primary"
                size="small"
                @click="viewAll(group.category)"
              >
                查看全部 →
              </el-button>
            </div>
            <ul class="gs-item-list">
              <li
                v-for="(item, idx) in group.items"
                :key="`${group.category}-${item.id}`"
                class="gs-item"
                :class="{ active: flattenedItems.findIndex((x) => x.id === item.id && x._category === group.category) === activeIndex }"
                @click="selectItem(item)"
              >
                <div class="gs-item-title" v-html="highlight(item.title, result.keyword)" />
                <div class="gs-item-subtitle" v-html="highlight(item.subtitle, result.keyword)" />
              </li>
            </ul>
          </div>
        </template>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.global-search-wrap {
  position: relative;
  width: 360px;
  max-width: 100%;
  z-index: 2000;
}
.global-search-input :deep(.el-input__wrapper) {
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}
.kbd-hint {
  display: inline-block;
  font-size: 11px;
  padding: 1px 6px;
  background: #f2f3f5;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  color: #606266;
  cursor: pointer;
  user-select: none;
}
.global-search-dropdown {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  right: 0;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  max-height: 60vh;
  overflow-y: auto;
  padding: 6px;
  z-index: 3000;
}
.gs-loading,
.gs-empty {
  padding: 20px;
  text-align: center;
  color: #909399;
  font-size: 13px;
}
.gs-group {
  margin-bottom: 4px;
}
.gs-group-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 10px 2px;
  font-size: 12px;
  color: #909399;
  font-weight: 600;
  border-bottom: 1px solid #f2f3f5;
}
.gs-group-label {
  letter-spacing: 0.5px;
}
.gs-item-list {
  list-style: none;
  margin: 0;
  padding: 2px;
}
.gs-item {
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s;
}
.gs-item:hover,
.gs-item.active {
  background: #ecf5ff;
}
.gs-item-title {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 2px;
}
.gs-item-subtitle {
  font-size: 12px;
  color: #909399;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
