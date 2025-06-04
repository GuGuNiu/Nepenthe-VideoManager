<template>
  <div class="bili-app-container">
    <header class="bili-header" ref="appHeaderRef">
      <div class="bili-header-content">
        <div class="bili-header-left" ref="headerLeftElRef">
          <router-link to="/" class="bili-logo-link" @focus.prevent @mousedown.prevent>
            <img src="/logo.png" alt="Logo" class="bili-logo-img" />
          </router-link>
          <nav class="bili-main-nav">
            <router-link to="/" class="bili-nav-item" active-class="is-active-nav">首页</router-link>
            <span class="bili-nav-item disabled-nav" title="暂未开放">精选</span>
            <span class="bili-nav-item disabled-nav" title="暂未开放">人物</span>
            <span class="bili-nav-item disabled-nav" title="暂未开放">拍摄公司</span>
            <span class="bili-nav-item disabled-nav" title="暂未开放">图集</span>
          </nav>
        </div>
        
        <div class="bili-header-right-combined">
          <div class="bili-header-center-search-wrapper" ref="headerSearchWrapperRef">
            <el-input
              placeholder="搜索名称、标签 (空格分隔多标签)"
              class="bili-search-input"
              :style="searchInputStyle" 
              :prefix-icon="SearchIcon"
              v-model="globalSearchTerm"
              @keyup.enter="handleGlobalSearch"
              clearable
              @clear="handleClearSearch"
              @focus="handleSearchFocus"
              @blur="hideSearchHistoryWithDelay"
              ref="searchInputRef"
            />
            <div v-if="showSearchHistory && searchHistory.length > 0" class="search-history-dropdown" :style="dropdownStyle" @mousedown.prevent="onDropdownInteraction" ref="searchHistoryDropdownRef">
              <el-tag v-for="(item, index) in searchHistory" :key="index" closable @close.stop="removeSearchHistoryItem(item)" @click.stop="applySearchHistoryItem(item)" class="history-tag">
                {{ item }}
              </el-tag>
            </div>
          </div>
          <div class="bili-header-right-settings" ref="headerSettingsIconRef">
            <router-link to="/settings" class="bili-header-action-item" title="设置">
              <el-icon :size="20"><SettingIcon /></el-icon>
            </router-link>
          </div>
        </div>
      </div>
    </header>
    <main class="bili-main-wrapper">
      <div class="bili-main-content" ref="mainContentRef">
        <router-view :key="route.fullPath" @view-mounted="adjustSearchLayoutDebounced" @view-updated="adjustSearchLayoutDebounced" />
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, provide, readonly, onMounted, onBeforeUnmount, nextTick, watch, reactive, computed  } from "vue"; 
import { Search as SearchIcon, Setting as SettingIcon } from "@element-plus/icons-vue";
import { useRouter, useRoute } from "vue-router";
import { debounce } from "lodash-es";

const router = useRouter();
const route = useRoute();
const globalSearchTerm = ref("");
const searchHistory = ref([]);
const MAX_HISTORY = 5;
const showSearchHistory = ref(false);

const appHeaderRef = ref(null);
const headerLeftElRef = ref(null); 
const headerSearchWrapperRef = ref(null);
const searchInputRef = ref(null);
const searchHistoryDropdownRef = ref(null);
const headerSettingsIconRef = ref(null);
const mainContentRef = ref(null);

const searchInputStyle = reactive({ width: "300px" }); 
const dropdownStyle = reactive({ width: "300px", left: "0px", top: "0px" });
let blurTimeoutId = null;

const MAX_FRONTEND_LOGS = 200;
const TRIM_FRONTEND_LOGS_TO = 150;
const globalFrontendLogsArray = ref([]);
provide('globalFrontendLogs', readonly(globalFrontendLogsArray));
provide('clearGlobalFrontendLogs', () => { globalFrontendLogsArray.value = []; originalConsole.log('[App.vue] Frontend logs cleared.'); });
const originalConsole = { log: console.log, warn: console.warn, error: console.error, info: console.info, debug: console.debug, };
function formatLogMessageForFrontend(level, args) { const timestamp = new Date().toLocaleTimeString([], { hour12: false }); const message = args.map(arg => { if (arg instanceof Error) return `${arg.name}: ${arg.message}${arg.stack ? `\n${arg.stack}` : ''}`; try { if (typeof arg === 'object' && arg !== null) return JSON.stringify(arg, null, 2); } catch (e) { /* ignore */ } return String(arg); }).join(' '); return `[${timestamp}][FE-${level.toUpperCase()}] ${message}`; }
function addToFrontendLogs(formattedMessage) { globalFrontendLogsArray.value.unshift(formattedMessage); if (globalFrontendLogsArray.value.length > MAX_FRONTEND_LOGS) { globalFrontendLogsArray.value.splice(TRIM_FRONTEND_LOGS_TO); } }
console.log = (...args) => { addToFrontendLogs(formatLogMessageForFrontend('log', args)); originalConsole.log.apply(console, args); };
console.warn = (...args) => { addToFrontendLogs(formatLogMessageForFrontend('warn', args)); originalConsole.warn.apply(console, args); };
console.error = (...args) => { addToFrontendLogs(formatLogMessageForFrontend('error', args)); originalConsole.error.apply(console, args); };
console.info = (...args) => { addToFrontendLogs(formatLogMessageForFrontend('info', args)); originalConsole.info.apply(console, args); };
console.debug = (...args) => { addToFrontendLogs(formatLogMessageForFrontend('debug', args)); originalConsole.debug.apply(console, args); };

const adjustSearchLayout = () => {
  if (!appHeaderRef.value || !headerLeftElRef.value || !headerSearchWrapperRef.value || !headerSettingsIconRef.value || !searchInputRef.value?.$el) {
    return;
  }
  const headerContentEl = appHeaderRef.value;
  const headerLeftWidth = headerLeftElRef.value.offsetWidth;
  const settingsIconWidth = headerSettingsIconRef.value.offsetWidth;
  
  const headerContentStyle = window.getComputedStyle(headerContentEl);
  const headerPaddingHorizontal = (parseFloat(headerContentStyle.paddingLeft) || 0) + (parseFloat(headerContentStyle.paddingRight) || 0);
  
  const gapBetweenLeftAndSearch = 30; 
  const gapBetweenSearchAndSettings = 20; // 搜索框与设置图标的固定间距

  const availableWidthForSearch = headerContentEl.clientWidth - headerPaddingHorizontal - headerLeftWidth - settingsIconWidth - gapBetweenLeftAndSearch - gapBetweenSearchAndSettings;
  
  const minSearchWidth = 250; 
  const maxSearchWidth = 700; 
  
  let newSearchWidth = Math.max(minSearchWidth, Math.min(availableWidthForSearch, maxSearchWidth));
  searchInputStyle.width = `${newSearchWidth}px`;

  const searchInputEl = searchInputRef.value.$el;
  if (showSearchHistory.value && searchHistoryDropdownRef.value && searchInputEl) {
    const inputRect = searchInputEl.getBoundingClientRect();
    dropdownStyle.width = `${inputRect.width}px`; 
    dropdownStyle.left = `${searchInputEl.offsetLeft}px`; 
    dropdownStyle.top = `${searchInputEl.offsetHeight + 2}px`; 
  }
};
const adjustSearchLayoutDebounced = debounce(adjustSearchLayout, 50);

watch(showSearchHistory, (newValue) => { if (newValue) { nextTick(adjustSearchLayout); } });

const loadSearchHistory = () => { const history = localStorage.getItem("videoSearchHistory"); if (history) { searchHistory.value = JSON.parse(history); } };
const saveSearchHistory = () => { localStorage.setItem("videoSearchHistory", JSON.stringify(searchHistory.value)); };
const addSearchHistoryItem = (term) => { if (!term || term.trim() === "") return; const trimmedTerm = term.trim(); const existingIndex = searchHistory.value.indexOf(trimmedTerm); if (existingIndex > -1) { searchHistory.value.splice(existingIndex, 1); } searchHistory.value.unshift(trimmedTerm); if (searchHistory.value.length > MAX_HISTORY) { searchHistory.value.pop(); } saveSearchHistory(); };
const removeSearchHistoryItem = (item) => { searchHistory.value = searchHistory.value.filter((h) => h !== item); saveSearchHistory(); if (searchHistory.value.length > 0) { showSearchHistory.value = true; nextTick(adjustSearchLayout); } else { showSearchHistory.value = false; } };
const applySearchHistoryItem = (item) => { globalSearchTerm.value = item; handleGlobalSearch(); };
const handleGlobalSearch = () => { const searchTermValue = globalSearchTerm.value.trim(); addSearchHistoryItem(searchTermValue); showSearchHistory.value = false; const query = {}; if (searchTermValue) { query.search_term = searchTermValue; } router.push({ name: "VideoList", query: query }); };
const handleClearSearch = () => { globalSearchTerm.value = ""; showSearchHistory.value = false; router.push({ name: "VideoList", query: {} }); };
const handleSearchFocus = () => { if (blurTimeoutId) { clearTimeout(blurTimeoutId); blurTimeoutId = null; } if (searchHistory.value.length > 0) { showSearchHistory.value = true; nextTick(adjustSearchLayout); } };
const hideSearchHistoryWithDelay = () => { if (blurTimeoutId) { clearTimeout(blurTimeoutId); } blurTimeoutId = setTimeout(() => { showSearchHistory.value = false; blurTimeoutId = null; }, 250); };
const onDropdownInteraction = () => { if (blurTimeoutId) { clearTimeout(blurTimeoutId); blurTimeoutId = null; } };

onMounted(async () => {
  loadSearchHistory();
  if (route.query.search_term) { globalSearchTerm.value = String(route.query.search_term); }
  window.addEventListener("resize", adjustSearchLayoutDebounced);
  nextTick(adjustSearchLayout);
  if (window.electronApp && typeof window.electronApp.getAppConfig === 'function') {
      const config = await window.electronApp.getAppConfig();
      if (config && (!config.videoPaths || config.videoPaths.length === 0)) { router.push('/settings'); }
  }
});
onBeforeUnmount(() => {
  window.removeEventListener("resize", adjustSearchLayoutDebounced);
  if (blurTimeoutId) clearTimeout(blurTimeoutId);
  console.log = originalConsole.log; console.warn = originalConsole.warn;
  console.error = originalConsole.error; console.info = originalConsole.info;
  console.debug = originalConsole.debug;
});
watch(() => route.query.search_term, (newTerm) => { globalSearchTerm.value = newTerm || ""; });
watch(() => route.fullPath, () => { 
    if (showSearchHistory.value) { nextTick(adjustSearchLayout); }
    nextTick(adjustSearchLayoutDebounced);
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
  width: 100%;
  height: 56px;
  padding: 0 24px;
  box-sizing: border-box;
  border-bottom: 1px solid #e3e5e7;
}
.bili-header-left {
  display: flex;
  align-items: center;
  flex-shrink: 0; 
  margin-right: auto; 
}
.bili-logo-link { 
  display: flex; align-items: center; margin-right: 24px; 
  outline: none !important; -webkit-tap-highlight-color: transparent;
}
.bili-logo-link:focus, .bili-logo-link:focus-visible { outline: none !important; }
.bili-logo-img { height: 32px; outline: none !important; }
.bili-logo-img:focus, .bili-logo-img:focus-visible { outline: none !important; }

.bili-main-nav { display: flex; align-items: center; gap: 15px; }
.bili-nav-item { padding: 0 4px; font-size: 15px; color: #61666d; transition: color 0.2s; line-height: 56px; display: inline-block; font-weight: 500; white-space: nowrap; }
.bili-nav-item.is-active-nav, .bili-nav-item:hover:not(.disabled-nav) { color: #00a1d6; }
.disabled-nav { color: #aaa !important; cursor: not-allowed; }
.disabled-nav:hover { color: #aaa !important; }

.bili-header-right-combined {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}
.bili-header-center-search-wrapper {
  position: relative; 
  display: flex; 
  align-items: center;
  margin-right: 20px; /* 重点说明: 搜索框和设置图标之间的固定间距 */
}
.bili-search-input .el-input__wrapper { border-radius: 8px; background-color: #f1f2f3; box-shadow: none; }
.bili-search-input .el-input__wrapper:hover { background-color: #e7e8ea; }

.search-history-dropdown {
  position: absolute; background-color: white; border: 1px solid #e3e5e7;
  border-top: none; border-radius: 0 0 6px 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  padding: 8px; z-index: 900; display: flex; flex-direction: row; 
  flex-wrap: wrap; gap: 6px; box-sizing: border-box; top:35px 
}
.history-tag { cursor: pointer; }

.bili-header-right-settings {
  display: flex;
  align-items: center;
}
.bili-header-action-item {
  display: flex; align-items: center; justify-content: center;
  height: 32px; width: 32px; color: #61666d; cursor: pointer;
  border-radius: 50%; transition: background-color 0.2s;
}
.bili-header-action-item:hover { background-color: #f1f2f3; }
.bili-header-action-item .el-icon { font-size: 20px; }

.bili-main-wrapper { flex-grow: 1; display: flex; justify-content: center; padding-top: 16px; }
.bili-main-content { width: 100%; max-width: 1320px; }

:root { --el-color-primary: #00a1d6; --el-border-radius-base: 6px; }
.el-button--primary { background-color: var(--el-color-primary); border-color: var(--el-color-primary); }
.el-button--primary:hover, .el-button--primary:focus { background-color: #00b5e5; border-color: #00b5e5; }
.el-button.is-round { border-radius: 16px; }
.el-popover.el-popper { border-radius: var(--el-border-radius-base); box-shadow: 0 0 10px rgba(0, 0, 0, 0.1); }
</style>