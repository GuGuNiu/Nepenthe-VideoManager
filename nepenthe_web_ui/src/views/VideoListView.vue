<template>
  <div class="bili-videolist-page">
    <div class="bili-channel-section">
      <div class="bili-channel-header">
        <div class="left-channel-actions">
        </div>
        <div class="channel-tags-wrapper">
          <el-button
            v-for="tag in allAvailableTags"
            :key="tag.id"
            :type="searchParams.tags.includes(tag.name) ? 'primary' : 'default'"
            text 
            size="small" 
            class="bili-channel-button" 
            @click="toggleTagInSearch(tag.name)"
            :round="false"
          >
            {{ tag.name }}
          </el-button>
          <el-skeleton :rows="1" animated v-if="isLoadingTags && allAvailableTags.length === 0" style="width: 300px;"/>
          <span v-if="!isLoadingTags && allAvailableTags.length === 0" class="no-tags-tip">暂无频道分类</span>
        </div>
        <div class="right-channel-actions">
        </div>
      </div>
    </div>

    <div class="bili-list-controls-container">
      <div class="sort-by-field-group">
        <el-button 
            v-for="option in sortByOptions"
            :key="option.value"
            text 
            @click="setSortByAndSearch(option.value)" 
            :class="{'is-active-sort': searchParams.sortBy === option.value}"
            class="sort-field-btn-direct"
        >
            {{ option.label }}
        </el-button>
      </div>
      
      <div class="sort-order-and-reset-group">
        <el-button 
            text 
            @click="setSortOrderAndSearch('desc')" 
            :class="{'is-active-sort': searchParams.sortOrder === 'desc'}"
            class="sort-order-btn"
        >
            热门优先
        </el-button>
        <el-button 
            text 
            @click="setSortOrderAndSearch('asc')" 
            :class="{'is-active-sort': searchParams.sortOrder === 'asc'}"
            class="sort-order-btn"
        >
            最新发布
        </el-button>
        <el-tooltip content="重置筛选和排序" placement="top">
            <el-button @click="resetSearchAndFetch" :icon="RefreshIcon" circle text class="reset-btn-circle"></el-button>
        </el-tooltip>
      </div>
    </div>

    <div v-if="isLoading" class="bili-loading-state">
      <el-skeleton :rows="12" animated />
    </div>
    <div v-else-if="videos.length > 0" class="bili-video-grid">
      <div
        v-for="video in videos"
        :key="video.id"
        class="bili-video-card"
        @mouseenter="startPreview(video.id)"
        @mouseleave="stopPreview(video.id)"
        @click="navigateToPlayer(video.id)"
      >
        <div class="bili-card-thumbnail-container">
          <video
            v-if="previewingVideoId === video.id && video.id"
            :ref="el => videoPlayerRefs[video.id] = el"
            :src="getVideoStreamUrl(video.id)"
            class="bili-card-preview-player"
            autoplay muted loop playsinline preload="metadata" 
            @loadedmetadata="setPlaybackRate($event, 5.0)"
          ></video>
          <el-image
            v-show="previewingVideoId !== video.id" 
            class="bili-card-thumbnail"
            :src="video.thumbnail_url"
            fit="cover" lazy
          >
            <template #error><div class="bili-image-slot-error"><span>无封面</span></div></template>
            <template #placeholder><div class="bili-image-slot-placeholder"><span>载入中</span></div></template>
          </el-image>
          <div class="bili-card-overlay-info" v-show="previewingVideoId !== video.id">
            <span class="bili-card-duration">{{ formatDuration(video.duration) }}</span>
          </div>
        </div>
        <div class="bili-card-info">
          <h3 class="bili-card-title" :title="video.name">{{ video.name }}</h3>
          
          <div class="bili-card-tags-persons" v-if="video.tags && video.tags.length">
            <el-tag 
                v-for="tag in video.tags.slice(0, 3)" 
                :key="`tag-${video.id}-${tag.id}`" 
                size="small" effect="plain" type="info" class="info-tag"
                @click.stop="addTagToSearch(tag.name)"
            >
                {{ tag.name }}
            </el-tag>
            <el-tag v-if="video.tags.length > 3" size="small" effect="plain" type="info" class="info-tag">...</el-tag>
          </div>

          <div class="bili-card-tags-persons" v-if="video.persons && video.persons.length">
            <el-tag 
                v-for="person in video.persons.slice(0, 3)" 
                :key="`person-${video.id}-${person.id}`" 
                size="small" effect="plain" type="warning" class="info-tag person-tag"
                @click.stop="addPersonToSearch(person.name)"
            >
              <el-icon style="margin-right: 2px;"><UserFilled /></el-icon> {{ person.name }}
            </el-tag>
            <el-tag v-if="video.persons.length > 3" size="small" effect="plain" type="warning" class="info-tag person-tag">...</el-tag>
          </div>

          <div class="bili-card-meta">
            <span class="bili-card-views">{{ video.view_count }} 播放</span>
            <span class="bili-card-date" v-if="video.added_date"> • {{ formatRelativeDate(video.added_date) }}</span>
          </div>
          <div class="bili-card-actions">
             <el-dropdown trigger="hover" @command="handleCardCommand" @click.stop placement="bottom-end">
                <el-button :icon="MoreFilledIcon" text circle class="bili-action-more-btn" @click.stop/>
                <template #dropdown>
                    <el-dropdown-menu>
                    <el-dropdown-item :command="{action: 'edit', video: video}" :icon="EditPenIcon">编辑信息</el-dropdown-item>
                    <el-dropdown-item :command="{action: 'delete', video: video}" :icon="DeleteIcon" divided class="delete-item">移至回收站</el-dropdown-item>
                    </el-dropdown-menu>
                </template>
            </el-dropdown>
          </div>
        </div>
      </div>
    </div>
    <el-empty v-else description="什么也没有找到~" class="bili-empty-state"></el-empty>

    <div v-if="totalVideos > pageSize && videos.length > 0" class="bili-pagination-container">
      <el-pagination
        background
        layout="prev, pager, next, total, sizes" 
        :total="totalVideos"
        :page-sizes="[25, 50, 75, 100]"
        :page-size="pageSize"
        :current-page="currentPage"
        @current-change="handleCurrentPageChange"
        @size-change="handlePageSizeChange"
        :pager-count="7"
      />
    </div>

    <VideoEditModal
      v-if="editModalVisible"
      v-model:visible="editModalVisible"
      :video-data="currentVideoToEdit"
      @video-updated="handleVideoUpdated"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick, onBeforeUnmount, watch, computed } from 'vue';
import axios from 'axios';
import { useRouter, useRoute } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { 
    Search as SearchIcon, Refresh as RefreshIcon, 
    PriceTag as PriceTagIcon, EditPen as EditPenIcon, Sort as SortIcon, MoreFilled as MoreFilledIcon, Delete as DeleteIcon,
    UserFilled,
} from '@element-plus/icons-vue';
import VideoEditModal from '../components/VideoEditModal.vue';
import { formatDistanceToNowStrict } from 'date-fns';
import { zhCN } from 'date-fns/locale';

const router = useRouter();
const route = useRoute();
const videos = ref([]);
const isLoading = ref(true);
const currentPage = ref(1);
const pageSize = ref(25);
const totalVideos = ref(0);
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
const searchParams = reactive({ searchTerm: route.query.search_term || '', tags: [], persons_search: '', sortBy: 'id', sortOrder: 'desc' });
const editModalVisible = ref(false);
const currentVideoToEdit = ref(null);
const previewingVideoId = ref(null);
const videoPlayerRefs = reactive({});
let previewTimeoutId = null;
const allAvailableTags = ref([]);
const isLoadingTags = ref(false);

const sortByOptions = ref([
    { label: '默认推荐', value: 'id' },
    { label: '视频名称', value: 'name' },
    { label: '视频时长', value: 'duration' },
    { label: '播放数量', value: 'view_count' },
    { label: '添加时间', value: 'added_date' },
]);

watch(() => route.query.search_term, (newSearchTerm) => {
  searchParams.searchTerm = newSearchTerm || '';
  if (!isLoading.value) { 
    triggerSearch();
  }
});

const fetchAllAvailableTags = async () => {
  isLoadingTags.value = true;
  try {
    const response = await axios.get(`${API_BASE_URL}/api/tags`, { params: { limit: 100 } }); 
    if (response.data && Array.isArray(response.data)) { allAvailableTags.value = response.data; }
  } catch (error) { console.error('[BiliView] 获取所有标签失败:', error); allAvailableTags.value = []; }
  finally { isLoadingTags.value = false; }
};
const toggleTagInSearch = (tagName) => {
  const index = searchParams.tags.indexOf(tagName);
  if (index > -1) { searchParams.tags.splice(index, 1); } else { searchParams.tags = [tagName]; }
  triggerSearch();
};
const addTagToSearch = (tagName) => {
    if (!searchParams.tags.includes(tagName)) { searchParams.tags = [tagName]; triggerSearch(); }
    else if (searchParams.tags.length === 1 && searchParams.tags[0] === tagName) { searchParams.tags = []; triggerSearch(); }
};
const addPersonToSearch = (personName) => {
    searchParams.persons_search = personName; // 后端 persons_search 参数
    triggerSearch();
    ElMessage.info(`按人物 "${personName}" 筛选`);
};

const setSortByAndSearch = (sortByValue) => { searchParams.sortBy = sortByValue; triggerSearch(); };
const setSortOrderAndSearch = (order) => { searchParams.sortOrder = order; triggerSearch(); };
const getVideoStreamUrl = (videoId) => videoId ? `${API_BASE_URL}/api/stream/${videoId}` : '';
const startPreview = (videoId) => {
  if (previewTimeoutId) clearTimeout(previewTimeoutId);
  previewTimeoutId = setTimeout(() => {
    previewingVideoId.value = videoId;
    nextTick(() => {
      const player = videoPlayerRefs[videoId];
      if (player) { player.currentTime = 0; player.playbackRate = 5.0; player.play().catch(e => {}); }
    });
  }, 300);
};
const stopPreview = (videoId) => {
  if (previewTimeoutId) clearTimeout(previewTimeoutId);
  if (previewingVideoId.value === videoId) {
    const player = videoPlayerRefs[videoId];
    if (player) player.pause();
    previewingVideoId.value = null;
  }
};
const setPlaybackRate = (event, rate) => { if (event.target) event.target.playbackRate = rate; };
const fetchVideos = async (page = currentPage.value, size = pageSize.value) => {
  isLoading.value = true;
  try {
    const apiParams = { 
        skip: (page - 1) * size, limit: size, 
        search_term: searchParams.searchTerm || undefined, 
        tags: searchParams.tags.length > 0 ? searchParams.tags.join(',') : undefined, 
        persons_search: searchParams.persons_search || undefined,
        sort_by: searchParams.sortBy, sort_order: searchParams.sortOrder 
    };
    const response = await axios.get(`${API_BASE_URL}/api/videos`, { params: apiParams });
    if (response.data && Array.isArray(response.data.videos)) {
      videos.value = response.data.videos.map(video => ({ ...video, thumbnail_url: video.thumbnail_url ? `${API_BASE_URL}${video.thumbnail_url}` : null, added_date: video.added_date ? new Date(video.added_date) : null }));
      totalVideos.value = response.data.total_count || 0;
      currentPage.value = page; pageSize.value = size;
    } else { videos.value = []; totalVideos.value = 0; ElMessage.error('视频数据格式错误');}
  } catch (error) { console.error('[BiliView] 获取视频列表失败:', error); videos.value = []; totalVideos.value = 0; ElMessage.error('获取视频列表失败');}
  finally { isLoading.value = false; }
};
const triggerSearch = () => { currentPage.value = 1; fetchVideos(); };
const resetSearchAndFetch = () => { searchParams.searchTerm = ''; searchParams.tags = []; searchParams.persons_search = ''; searchParams.sortBy = 'id'; searchParams.sortOrder = 'desc'; router.replace({ query: {} }); triggerSearch(); }; 
const formatDuration = (seconds) => { if (seconds === null || seconds === undefined || isNaN(seconds) || seconds < 0) return '0:00'; const h = Math.floor(seconds / 3600); const m = Math.floor((seconds % 3600) / 60); const s = Math.round(seconds % 60); if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`; return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`; };
const formatRelativeDate = (date) => { if (!date) return ''; try { return formatDistanceToNowStrict(date, { addSuffix: true, locale: zhCN }); } catch (e) { return '日期未知'; } };
const navigateToPlayer = (videoId) => { if (!videoId) return; if (previewingVideoId.value) stopPreview(previewingVideoId.value); 
    const videoToPlay = videos.value.find(v => v.id === videoId);
    if (videoToPlay && videoToPlay.path) {
        if (window.electronAPI && typeof window.electronAPI.playVideoLocally === 'function') {
            window.electronAPI.playVideoLocally(videoToPlay.path);
            axios.post(`${API_BASE_URL}/api/videos/${videoId}/view`).catch(error => {});
        } else { ElMessage.error('无法调用本地播放器，桌面环境API未找到。'); }
    } else { ElMessage.error('未找到视频文件路径，无法播放。'); }
};
const handleCurrentPageChange = (newPage) => { fetchVideos(newPage, pageSize.value); };
const handlePageSizeChange = (newSize) => { fetchVideos(1, newSize); };
const openEditModal = (video) => { currentVideoToEdit.value = JSON.parse(JSON.stringify(video)); editModalVisible.value = true; };
const handleVideoUpdated = (updatedVideo) => { ElMessage.success('视频信息更新！'); fetchVideos(currentPage.value, pageSize.value); fetchAllAvailableTags(); };
const handleDeleteVideo = async (videoToDelete) => {
    try {
        await ElMessageBox.confirm( `确定将 "${videoToDelete.name}" 移至回收站吗?`, '删除确认', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning', draggable: true, });
        isLoading.value = true; 
        await axios.delete(`${API_BASE_URL}/api/videos/${videoToDelete.id}/to-trash`);
        ElMessage.success(`"${videoToDelete.name}" 已移至回收站`);
        videos.value = videos.value.filter(v => v.id !== videoToDelete.id);
        totalVideos.value = Math.max(0, totalVideos.value -1); 
        fetchAllAvailableTags();
    } catch (error) { if (error !== 'cancel') { console.error('删除视频失败:', error); ElMessage.error(error.response?.data?.detail || '删除视频失败'); } }
    finally { isLoading.value = false; }
};
const handleCardCommand = (command) => { if (command.action === 'edit') { openEditModal(command.video); } else if (command.action === 'delete') { handleDeleteVideo(command.video); } };

onMounted(() => { 
    fetchAllAvailableTags(); 
    if (route.query.search_term) { searchParams.searchTerm = String(route.query.search_term); }
    if (route.query.tags) { searchParams.tags = String(route.query.tags).split(',').map(t => t.trim()).filter(t => t); }
    if (route.query.persons_search) { searchParams.persons_search = String(route.query.persons_search); }
    fetchVideos(); 
});
onBeforeUnmount(() => { if (previewTimeoutId) clearTimeout(previewTimeoutId); Object.keys(videoPlayerRefs).forEach(vidId => { const player = videoPlayerRefs[vidId]; if (player && typeof player.pause === 'function') player.pause(); }); });
</script>

<style scoped>
.bili-videolist-page { padding: 0; }
.bili-channel-section { background-color: #fff; padding: 10px 0; margin-bottom: 16px; border-bottom: 1px solid #e3e5e7;}
.bili-channel-header { display: flex; align-items: center; justify-content: space-between; max-width: 1320px; margin: 0 auto; padding: 0 20px; }
.left-channel-actions, .right-channel-actions { flex-shrink: 0; }
.channel-tags-wrapper { display: flex; flex-wrap: wrap; gap: 6px 8px; justify-content: flex-start; flex-grow: 1; overflow-x: auto; padding: 2px 0; }
.bili-channel-button { font-size: 13px; padding: 0 10px; height: 26px; border-color: transparent; background-color: #f1f2f3; color: #61666d; border-radius: 4px; }
.bili-channel-button.el-button.is-text:hover,
.bili-channel-button.el-button:not(.is-text):not(.is-link):hover { color: #00a1d6; background-color: #e2f3fa; border-color: transparent; }
.bili-channel-button.el-button--primary, 
.bili-channel-button.el-button--primary.is-text { color: #fff; background-color: #00a1d6; border-color: #00a1d6; }
.bili-channel-button.el-button--primary:hover,
.bili-channel-button.el-button--primary.is-text:hover,
.bili-channel-button.el-button--primary:focus,
.bili-channel-button.el-button--primary.is-text:focus { background-color: #00b5e5; border-color: #00b5e5; }
.no-tags-tip { font-size: 13px; color: #999; padding: 5px 0; }
.bili-list-controls-container { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding: 0 20px; height: 32px; }
.sort-by-field-group { display: flex; align-items: center; gap: 6px; }
.sort-order-and-reset-group { display: flex; align-items: center; gap: 6px; }
.sort-field-btn-direct, .sort-order-btn { font-size: 13px; color: #61666d; padding: 0 10px; height: 28px; border-radius: 4px; line-height: 28px; }
.sort-field-btn-direct.is-active-sort, .sort-order-btn.is-active-sort { color: #00a1d6; font-weight: 500; background-color: #e2f3fa; }
.reset-btn-circle { font-size: 16px; color: #9499a0; padding: 6px; height: 28px; width: 28px; }
.reset-btn-circle:hover { color: #00a1d6; background-color: #f0f2f5; }
.bili-loading-state { padding: 20px; }
.bili-empty-state { margin-top: 40px; }
.bili-video-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 24px 16px; padding: 0 20px; }
.bili-video-card { background-color: transparent; cursor: pointer; display: flex; flex-direction: column; }
.bili-card-thumbnail-container { position: relative; width: 100%; padding-bottom: 56.25%; background-color: #e7e7e7; border-radius: 6px; overflow: hidden; margin-bottom: 8px; }
.bili-card-thumbnail, .bili-card-preview-player { position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; border-radius: 6px; }
.bili-card-preview-player { z-index: 1; }
.bili-image-slot-error, .bili-image-slot-placeholder { display: flex; justify-content: center; align-items: center; width: 100%; height: 100%; background: #f0f0f0; color: #aaa; font-size: 12px; }
.bili-card-overlay-info { position: absolute; bottom: 0; left: 0; right: 0; padding: 4px 6px; display: flex; justify-content: flex-end; align-items: center; background: linear-gradient(to top, rgba(0,0,0,0.6) 0%, rgba(0,0,0,0) 100%); }
.bili-card-duration { color: white; font-size: 11px; background-color: rgba(0,0,0,0.7); padding: 1px 4px; border-radius: 3px; }
.bili-card-info { padding-right: 20px; position: relative; }
.bili-card-title { font-size: 14px; font-weight: 500; color: #18191c; margin: 0 0 6px 0; line-height: 1.4; max-height: 2.8em; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
.bili-card-tags-persons { margin-top: 4px; margin-bottom: 6px; display: flex; flex-wrap: wrap; gap: 4px; }
.info-tag { cursor: pointer; }
.person-tag .el-icon { vertical-align: middle; }
.bili-card-meta { font-size: 12px; color: #9499a0; line-height: 1.3; display: flex; align-items: center; gap: 6px; }
.bili-card-actions { position: absolute; top: -5px; right: -5px; opacity: 0; transition: opacity 0.2s; }
.bili-video-card:hover .bili-card-actions { opacity: 1; }
.bili-action-more-btn { padding: 4px; font-size: 16px; color: #9499a0; }
.bili-action-more-btn:hover { color: #00a1d6; background-color: #e3e5e7; }
.bili-pagination-container { margin-top: 30px; display: flex; justify-content: center; padding: 0 20px; }
.bili-pagination-container :deep(.el-pagination.is-background .el-pager li:not(.is-disabled).is-active) { background-color: var(--el-color-primary) !important; }
.bili-pagination-container :deep(.el-pagination.is-background .el-pager li:not(.is-disabled):hover) { color: var(--el-color-primary) !important; }
.delete-item { color: var(--el-color-danger); }
.delete-item:hover { background-color: var(--el-color-danger-light-9); color: var(--el-color-danger); }
</style>