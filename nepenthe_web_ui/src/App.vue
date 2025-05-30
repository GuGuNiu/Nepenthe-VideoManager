<template>
  <div class="bili-app-container">
    <header class="bili-header">
      <div class="bili-header-content">
        <div class="bili-header-left">
          <router-link to="/" class="bili-logo-link">
            <img src="/vite.svg" alt="Logo" class="bili-logo-img" />
          </router-link>
          <nav class="bili-main-nav">
            <router-link to="/" class="bili-nav-item active">首页</router-link>
          </nav>
        </div>
        <div class="bili-header-center">
          <el-input
            placeholder="搜索感兴趣的视频内容..."
            class="bili-search-input"
            :prefix-icon="SearchIcon"
            v-model="globalSearchTerm"
            @keyup.enter="handleGlobalSearch"
          >
            <template #append>
              <el-button :icon="SearchIcon" @click="handleGlobalSearch" />
            </template>
          </el-input>
        </div>
        <div class="bili-header-right">
          <!-- 用户头像和投稿按钮已移除 -->
        </div>
      </div>
    </header>

    <main class="bili-main-wrapper">
      <div class="bili-main-content">
        <router-view />
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { Search as SearchIcon } from '@element-plus/icons-vue'; // 移除了 UserFilledIcon 和 UploadIcon
import { useRouter } from 'vue-router';

const router = useRouter();
const globalSearchTerm = ref('');

const handleGlobalSearch = () => {
  if (globalSearchTerm.value.trim()) {
    router.push({ name: 'VideoList', query: { search_term: globalSearchTerm.value.trim() } });
  } else {
    router.push({ name: 'VideoList', query: {} });
  }
};
</script>

<style>
body, html { margin: 0; padding: 0; height: 100%; font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", Helvetica, Arial, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif; background-color: #f1f2f3; color: #18191c;}
#app { height: 100%;}
a { text-decoration: none; color: inherit; }
ul, li { list-style: none; margin: 0; padding: 0; }

.bili-app-container { display: flex; flex-direction: column; min-height: 100vh; }

.bili-header { position: sticky; top: 0; z-index: 1000; background-color: #fff; }
.bili-header-content { display: flex; align-items: center; justify-content: space-between; height: 56px; padding: 0 24px; border-bottom: 1px solid #e3e5e7; }

.bili-header-left { display: flex; align-items: center; }
.bili-logo-link { display: flex; align-items: center; margin-right: 24px; }
.bili-logo-img { height: 32px; }
.bili-main-nav { display: flex; align-items: center; gap: 18px; }
.bili-nav-item { padding: 0 4px; font-size: 14px; color: #18191c; transition: color 0.2s; line-height: 56px; display: inline-block; }
.bili-nav-item:hover, .bili-nav-item.router-link-exact-active, .bili-nav-item.active { color: #00a1d6; }

.bili-header-center { flex-grow: 1; display: flex; justify-content: center; max-width: 550px; margin: 0 20px; }
.bili-search-input .el-input__wrapper { border-radius: 8px; background-color: #f1f2f3; box-shadow: none; }
.bili-search-input .el-input__wrapper:hover { background-color: #e7e8ea; }
.bili-search-input .el-input-group__append .el-button { background-color: #f1f2f3; border-left: none; border-radius: 0 8px 8px 0; color: #61666d; }
.bili-search-input .el-input-group__append .el-button:hover { background-color: #e7e8ea; color: #00a1d6;}

.bili-header-right { display: flex; align-items: center; min-width: 1px; /* 确保即使为空也占据空间，以保持布局 */ }
/* .bili-user-avatar 和 .bili-upload-btn 的样式可以保留或删除，因为元素本身已移除 */

.bili-main-wrapper { flex-grow: 1; display: flex; justify-content: center; padding-top: 16px; }
.bili-main-content { width: 100%; max-width: 1320px; }

:root { --el-color-primary: #00a1d6; --el-border-radius-base: 6px; }
.el-button--primary { background-color: var(--el-color-primary); border-color: var(--el-color-primary); }
.el-button--primary:hover, .el-button--primary:focus { background-color: #00b5e5; border-color: #00b5e5; }
.el-button.is-round { border-radius: 16px; }
.el-popover.el-popper { border-radius: var(--el-border-radius-base); box-shadow: 0 0 10px rgba(0,0,0,0.1); }
</style>