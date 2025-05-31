<template>
  <div class="bili-app-container">
    <header class="bili-header" ref="appHeaderRef">
      <div class="bili-header-content">
        <div class="bili-header-left">
          <router-link to="/" class="bili-logo-link">
            <img src="/logo.png" alt="Logo" class="bili-logo-img" />
          </router-link>
          <nav class="bili-main-nav">
            <router-link to="/" class="bili-nav-item" active-class="is-active-nav">首页</router-link>
            <router-link to="/featured" class="bili-nav-item" active-class="is-active-nav">精选</router-link>
            <router-link to="/gallery" class="bili-nav-item disabled-nav" :event="isGalleryDisabled ? '' : 'click'" active-class="is-active-nav">图集</router-link>
          </nav>
        </div>
        <div class="bili-header-center" ref="headerCenterRef">
          <el-input
            placeholder="搜索名称、标签 (空格分隔多标签)"
            class="bili-search-input"
            :prefix-icon="SearchIcon"
            v-model="globalSearchTerm"
            @keyup.enter="handleGlobalSearch"
            clearable
            @clear="handleClearSearch"
            @focus="handleSearchFocus"
            @blur="hideSearchHistoryWithDelay"
            ref="searchInputRef"
          >
            <template #append>
              <el-button :icon="SearchIcon" @click="handleGlobalSearch" />
            </template>
          </el-input>
          <div 
            v-if="showSearchHistory && searchHistory.length > 0" 
            class="search-history-dropdown"
            :style="dropdownStyle"
            @mousedown.prevent="onDropdownInteraction"
            ref="searchHistoryDropdownRef"
          >
            <el-tag
              v-for="(item, index) in searchHistory"
              :key="index"
              closable
              @close.stop="removeSearchHistoryItem(item)"
              @click.stop="applySearchHistoryItem(item)"
              class="history-tag"
            >
              {{ item }}
            </el-tag>
          </div>
        </div>
        <div class="bili-header-right" ref="headerRightRef">
          <!-- 你可以在这里放一些占位或实际的右侧按钮 -->
        </div>
      </div>
    </header>
    <main class="bili-main-wrapper">
      <div class="bili-main-content" ref="mainContentRef">
        <router-view :key="route.fullPath" @view-mounted="adjustLayoutDebounced" @view-updated="adjustLayoutDebounced" />
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, computed, nextTick, onBeforeUnmount, reactive } from 'vue';
import { Search as SearchIcon } from '@element-plus/icons-vue';
import { useRouter, useRoute } from 'vue-router';
import { debounce } from 'lodash-es';

const router = useRouter();
const route = useRoute();
const globalSearchTerm = ref('');
const searchHistory = ref([]);
const MAX_HISTORY = 5;
const showSearchHistory = ref(false);

const appHeaderRef = ref(null);
const headerCenterRef = ref(null);
const searchInputRef = ref(null);
const searchHistoryDropdownRef = ref(null);
const headerRightRef = ref(null); 
const mainContentRef = ref(null);

const dropdownStyle = reactive({});
let blurTimeoutId = null;

const isGalleryDisabled = computed(() => route.matched.some(record => record.meta.disabled));

const adjustLayout = () => {
  if (showSearchHistory.value && searchInputRef.value && searchInputRef.value.$el && headerCenterRef.value && searchHistoryDropdownRef.value) {
    const inputEl = searchInputRef.value.$el;
    const inputRect = inputEl.getBoundingClientRect();
    const headerCenterContainerRect = headerCenterRef.value.getBoundingClientRect();

    dropdownStyle.width = `${inputRect.width}px`;
    dropdownStyle.left = `${inputEl.offsetLeft}px`; // offsetLeft is relative to offsetParent
    dropdownStyle.top = `${inputEl.offsetHeight + 2}px`; 
  }
};

const adjustLayoutDebounced = debounce(adjustLayout, 50);

watch(showSearchHistory, (newValue) => {
  if (newValue) {
    nextTick(() => {
      adjustLayout(); 
    });
  }
});

const loadSearchHistory = () => {
  const history = localStorage.getItem('videoSearchHistory');
  if (history) { searchHistory.value = JSON.parse(history); }
};
const saveSearchHistory = () => {
  localStorage.setItem('videoSearchHistory', JSON.stringify(searchHistory.value));
};
const addSearchHistoryItem = (term) => {
  if (!term || term.trim() === '') return;
  const trimmedTerm = term.trim();
  const existingIndex = searchHistory.value.indexOf(trimmedTerm);
  if (existingIndex > -1) { searchHistory.value.splice(existingIndex, 1); }
  searchHistory.value.unshift(trimmedTerm);
  if (searchHistory.value.length > MAX_HISTORY) { searchHistory.value.pop(); }
  saveSearchHistory();
};
const removeSearchHistoryItem = (item) => {
  searchHistory.value = searchHistory.value.filter(h => h !== item);
  saveSearchHistory();
  if (searchHistory.value.length > 0) {
    showSearchHistory.value = true;
    nextTick(adjustLayout);
  } else {
    showSearchHistory.value = false;
  }
};
const applySearchHistoryItem = (item) => {
  globalSearchTerm.value = item;
  handleGlobalSearch(); 
};
const handleGlobalSearch = () => {
  const searchTermValue = globalSearchTerm.value.trim();
  addSearchHistoryItem(searchTermValue);
  showSearchHistory.value = false;
  const query = {};
  if (searchTermValue) { query.search_term = searchTermValue; }
  router.push({ name: 'VideoList', query: query });
};
const handleClearSearch = () => {
    globalSearchTerm.value = '';
    showSearchHistory.value = false;
    router.push({ name: 'VideoList', query: {} });
};
const handleSearchFocus = () => {
    if (blurTimeoutId) { clearTimeout(blurTimeoutId); blurTimeoutId = null; }
    if (searchHistory.value.length > 0) {
        showSearchHistory.value = true;
    }
};
const hideSearchHistoryWithDelay = () => {
    if (blurTimeoutId) { clearTimeout(blurTimeoutId); }
    blurTimeoutId = setTimeout(() => {
        showSearchHistory.value = false;
        blurTimeoutId = null;
    }, 250); 
};
const onDropdownInteraction = () => {
    if (blurTimeoutId) { clearTimeout(blurTimeoutId); blurTimeoutId = null; }
    showSearchHistory.value = true;
};

onMounted(() => {
  loadSearchHistory();
  if (route.query.search_term) { globalSearchTerm.value = String(route.query.search_term); }
  window.addEventListener('resize', adjustLayoutDebounced);
  // nextTick(adjustLayout); // 初始加载时，showSearchHistory 默认为 false，所以 adjustLayout 不会执行
                           // 等待第一次 focus 时触发
});
onBeforeUnmount(() => {
  window.removeEventListener('resize', adjustLayoutDebounced);
  if (blurTimeoutId) clearTimeout(blurTimeoutId);
});
watch(() => route.query.search_term, (newTerm) => { globalSearchTerm.value = newTerm || ''; });
watch(() => route.fullPath, () => { 
    // 路由切换时，如果下拉框是显示的，可能需要重新计算，但通常会失焦自动隐藏
    if(showSearchHistory.value){
        nextTick(adjustLayout);
    }
});

</script>

<style>
body, html { margin: 0; padding: 0; height: 100%; font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", Helvetica, Arial, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif; background-color: #f1f2f3; color: #18191c;}
#app { height: 100%;}
a { text-decoration: none; color: inherit; }
ul, li { list-style: none; margin: 0; padding: 0; }

.bili-app-container { display: flex; flex-direction: column; min-height: 100vh; }
.bili-header { position: sticky; top: 0; z-index: 1000; background-color: #fff; }
.bili-header-content {
  display: flex;
  align-items: center;
  height: 56px;
  padding: 0 24px;
  border-bottom: 1px solid #e3e5e7;
}
.bili-header-left {
  display: flex;
  align-items: center;
  flex-shrink: 0; 
  margin-right: 20px; 
}
.bili-logo-link { display: flex; align-items: center; margin-right: 24px; }
.bili-logo-img { height: 32px; }
.bili-main-nav { display: flex; align-items: center; gap: 20px; }
.bili-nav-item { padding: 0 8px; font-size: 15px; color: #61666d; transition: color 0.2s; line-height: 56px; display: inline-block; font-weight: 500; }
.bili-nav-item.is-active-nav, .bili-nav-item:hover:not(.disabled-nav) { color: #00a1d6; }
.disabled-nav { color: #aaa !important; cursor: not-allowed; }

.bili-header-center {
  position: relative; 
  flex-grow: 1; 
  display: flex;
  justify-content: center; /* 使内部的 .bili-search-input 容器居中 */
  align-items: center;
  min-width: 0; /* 允许 flex item 收缩 */
}

.bili-search-input { /* el-input 组件 */
  width: 80%;    /* 尝试填满其在 .bili-header-center 内的可用空间 */
  min-width: 150px; /* 最小宽度 */
  max-width: 700px; /* 最大宽度 */
}

.bili-search-input .el-input__wrapper { background-color: #f1f2f3; box-shadow: none; }
.bili-search-input .el-input__wrapper:hover { background-color: #e7e8ea; }
.bili-search-input .el-input-group__append .el-button { background-color: #f1f2f3; border-left: none; border-radius: 0 8px 8px 0; color: #61666d; }
.bili-search-input .el-input-group__append .el-button:hover { background-color: #e7e8ea; color: #00a1d6;}

.search-history-dropdown {
  position: absolute;
  background-color: white;
  border: 1px solid #e3e5e7;
  border-top: none;
  border-radius: 0 0 6px 6px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  padding: 8px;
  z-index: 900;
  display: flex;
  flex-direction: row; 
  flex-wrap: wrap;    
  gap: 6px;   
  box-sizing: border-box;        
}

.history-tag {
  cursor: pointer;
  margin-bottom: 6px; 
}

.bili-header-right {
  display: flex;
  align-items: center;
  flex-shrink: 0; 
  margin-left: 20px; 
  min-width: 1px; /* 确保它至少存在，如果需要平衡，可以给一个固定宽度 */
  width: 250px;  /* 如果左侧宽度约为200px，可以设置这个来帮助平衡中间部分 */
  visibility: hidden;
}

.bili-main-wrapper { flex-grow: 1; display: flex; justify-content: center; padding-top: 16px; }
.bili-main-content { width: 100%; max-width: 1580px; }

:root { --el-color-primary: #00a1d6; --el-border-radius-base: 6px; }
.el-button--primary { background-color: var(--el-color-primary); border-color: var(--el-color-primary); }
.el-button--primary:hover, .el-button--primary:focus { background-color: #00b5e5; border-color: #00b5e5; }
.el-button.is-round { border-radius: 16px; }
.el-popover.el-popper { border-radius: var(--el-border-radius-base); box-shadow: 0 0 10px rgba(0,0,0,0.1); }
</style>