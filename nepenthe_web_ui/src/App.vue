<template>
  <div class="bili-app-container">
    <header class="bili-header">
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
        <div class="bili-header-center">
          <el-input
            placeholder="搜索名称、标签 (空格分隔多标签)"
            class="bili-search-input"
            :prefix-icon="SearchIcon"
            v-model="globalSearchTerm"
            @keyup.enter="handleGlobalSearch"
            clearable
            @clear="handleClearSearch"
            @focus="showSearchHistory = true"
            @blur="hideSearchHistoryWithDelay"
          >
            <template #append>
              <el-button :icon="SearchIcon" @click="handleGlobalSearch" />
            </template>
          </el-input>
          <div v-if="showSearchHistory && searchHistory.length > 0" class="search-history-dropdown">
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
        <div class="bili-header-right">
        </div>
      </div>
    </header>
    <main class="bili-main-wrapper">
      <div class="bili-main-content">
        <router-view :key="route.fullPath" />
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, computed } from 'vue';
import { Search as SearchIcon } from '@element-plus/icons-vue';
import { useRouter, useRoute } from 'vue-router';

const router = useRouter();
const route = useRoute();
const globalSearchTerm = ref('');
const searchHistory = ref([]);
const MAX_HISTORY = 5;
const showSearchHistory = ref(false);

const isGalleryDisabled = computed(() => route.matched.some(record => record.meta.disabled));

const loadSearchHistory = () => {
  const history = localStorage.getItem('videoSearchHistory');
  if (history) {
    searchHistory.value = JSON.parse(history);
  }
};
const saveSearchHistory = () => {
  localStorage.setItem('videoSearchHistory', JSON.stringify(searchHistory.value));
};
const addSearchHistoryItem = (term) => {
  if (!term || term.trim() === '') return;
  const trimmedTerm = term.trim();
  const existingIndex = searchHistory.value.indexOf(trimmedTerm);
  if (existingIndex > -1) {
    searchHistory.value.splice(existingIndex, 1);
  }
  searchHistory.value.unshift(trimmedTerm);
  if (searchHistory.value.length > MAX_HISTORY) {
    searchHistory.value.pop();
  }
  saveSearchHistory();
};
const removeSearchHistoryItem = (item) => {
  searchHistory.value = searchHistory.value.filter(h => h !== item);
  saveSearchHistory();
};
const applySearchHistoryItem = (item) => {
  globalSearchTerm.value = item;
  showSearchHistory.value = false;
  handleGlobalSearch();
};
const handleGlobalSearch = () => {
  const searchTermValue = globalSearchTerm.value.trim();
  addSearchHistoryItem(searchTermValue);
  showSearchHistory.value = false;
  const query = {};
  if (searchTermValue) {
    query.search_term = searchTermValue;
  }
  router.push({ name: 'VideoList', query: query });
};
const handleClearSearch = () => {
    globalSearchTerm.value = '';
    showSearchHistory.value = false;
    router.push({ name: 'VideoList', query: {} });
};
const hideSearchHistoryWithDelay = () => {
  setTimeout(() => {
    showSearchHistory.value = false;
  }, 150);
};

onMounted(() => {
  loadSearchHistory();
  if (route.query.search_term) {
    globalSearchTerm.value = String(route.query.search_term);
  }
});
watch(() => route.query.search_term, (newTerm) => {
    globalSearchTerm.value = newTerm || '';
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
}
.bili-logo-link { display: flex; align-items: center; margin-right: 24px; }
.bili-logo-img { height: 32px; }
.bili-main-nav { display: flex; align-items: center; gap: 20px; margin-left: 20px;}
.bili-nav-item { padding: 0 8px; font-size: 15px; color: #61666d; transition: color 0.2s; line-height: 56px; display: inline-block; font-weight: 500; }
.bili-nav-item.is-active-nav, .bili-nav-item:hover:not(.disabled-nav) { color: #00a1d6; }
.disabled-nav { color: #aaa !important; cursor: not-allowed; }

.bili-header-center {
  position: relative; 
  flex-grow: 1; 
  display: flex;
  justify-content: center; 
  align-items: center; 
}

.bili-search-input {
  max-width: 550px; 
  width: 100%; 
}

.bili-search-input .el-input__wrapper { background-color: #f1f2f3; box-shadow: none; }
.bili-search-input .el-input__wrapper:hover { background-color: #e7e8ea; }
.bili-search-input .el-input-group__append .el-button { background-color: #f1f2f3; border-left: none; border-radius: 0 8px 8px 0; color: #61666d; }
.bili-search-input .el-input-group__append .el-button:hover { background-color: #e7e8ea; color: #00a1d6;}
.search-history-dropdown { position: absolute; top: calc(100% + 2px); width: 100%; max-width: 550px; background-color: white; border: 1px solid #e3e5e7; border-top: none; border-radius: 0 0 6px 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); padding: 8px; z-index: 900; display: flex; flex-direction: column; gap: 6px; }
.history-tag { cursor: pointer; align-self: flex-start; }

.bili-header-right {
  display: flex;
  align-items: center;
  min-width: 1px; 
  flex-shrink: 0; 
  width:350px;
}

.bili-main-wrapper { flex-grow: 1; display: flex; justify-content: center; padding-top: 16px; }
.bili-main-content { width: 100%; max-width: 1320px; }
:root { --el-color-primary: #00a1d6; --el-border-radius-base: 6px; }
.el-button--primary { background-color: var(--el-color-primary); border-color: var(--el-color-primary); }
.el-button--primary:hover, .el-button--primary:focus { background-color: #00b5e5; border-color: #00b5e5; }
.el-button.is-round { border-radius: 16px; }
.el-popover.el-popper { border-radius: var(--el-border-radius-base); box-shadow: 0 0 10px rgba(0,0,0,0.1); }
</style>