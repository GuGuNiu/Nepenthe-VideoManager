<template>
  <div class="bili-videolist-page">
    <div class="sticky-controls-wrapper">
      <div class="sticky-controls-content">
        <div class="bili-channel-section bili-tags-section">
          <div class="bili-channel-header">
            <div class="left-channel-actions">
              <div class="channel-tags-wrapper" v-if="allAvailableTags.length > 0">
                <el-button
                  v-for="tag in allAvailableTags"
                  :key="tag.id"
                  :type="searchParams.tags.includes(tag.name) ? 'primary' : ''"
                  @click="toggleTagInSearch(tag.name)"
                  class="bili-channel-button"
                  text
                  size="small"
                >
                  {{ tag.name }}
                </el-button>
              </div>
              <div v-else-if="!isLoadingTags" class="no-tags-tip">暂无标签可筛选</div>
            </div>
            <div class="right-channel-actions">
              <el-button @click="resetSearchAndFetch" :icon="RefreshIcon" circle class="reset-btn-circle" title="重置筛选和排序"></el-button>
            </div>
          </div>
        </div>
        <hr class="section-separator" /> 
        <div class="bili-list-controls-container bili-sort-section">
          <div class="sort-by-field-group">
            <el-button
              v-for="option in sortByOptions" :key="option.value"
              @click="setSortByAndSearch(option.value)"
              :class="['sort-field-btn-direct', { 'is-active-sort': searchParams.sortBy === option.value }]"
              text
            >
              {{ option.label }}
            </el-button>
          </div>
          <div class="sort-order-and-reset-group">
            <el-button @click="setSortOrderAndSearch('asc')" :class="['sort-order-btn', { 'is-active-sort': searchParams.sortOrder === 'asc' }]">升序</el-button>
            <el-button @click="setSortOrderAndSearch('desc')" :class="['sort-order-btn', { 'is-active-sort': searchParams.sortOrder === 'desc' }]">降序</el-button>
          </div>
        </div>
      </div>
    </div>

    <div class="video-grid-scrollable-area">
      <el-skeleton :loading="isLoading" animated :rows="10">
        <template #default>
          <div v-if="videos.length > 0" class="bili-video-grid">
            <div 
              v-for="video in videos" :key="video.id" 
              class="bili-video-card"
              @mouseenter="startPreview(video.id)"
              @mouseleave="stopPreview(video.id)"
              @click="navigateToPlayer(video.id)"
            >
              <div class="bili-card-thumbnail-container">
                <video 
                  v-if="previewingVideoId === video.id"
                  :ref="el => { if (el) videoPlayerRefs[video.id] = el }"
                  muted loop playsinline
                  class="bili-card-preview-player"
                ></video> 
                <el-image :src="video.thumbnail_url" fit="cover" class="bili-card-thumbnail" v-show="previewingVideoId !== video.id">
                  <template #error><div class="bili-image-slot-error"><span>加载失败</span></div></template>
                  <template #placeholder><div class="bili-image-slot-placeholder"><span>加载中...</span></div></template>
                </el-image>
                <div class="bili-card-overlay-info">
                  <span class="bili-card-duration">{{ formatDuration(video.duration) }}</span>
                </div>
              </div>
              <div class="bili-card-info">
                <h3 class="bili-card-title" :title="video.name">{{ video.name }}</h3>
                <div class="bili-card-tags-persons">
                  <el-tag v-for="person in video.persons" :key="person.id" type="warning" size="small" class="info-tag person-tag" @click.stop="addPersonToSearch(person.name)">
                     <el-icon><UserFilled /></el-icon> {{ person.name }}
                  </el-tag>
                  <el-tag v-for="tag in video.tags" :key="tag.id" size="small" class="info-tag" @click.stop="addTagToSearch(tag.name)">{{ tag.name }}</el-tag>
                </div>
                <div class="bili-card-rating" v-if="video.rating !== null && video.rating !== undefined && video.rating >= 0">
                    <span>评分: {{ video.rating.toFixed(1) }} / 5</span>
                </div>
                <div class="bili-card-meta">
                  <span class="meta-item view-count">播放: {{ video.view_count || 0 }}</span>
                  <span class="meta-item added-date">{{ formatRelativeDate(video.added_date) }}</span>
                </div>
                <div class="bili-card-actions">
                    <el-dropdown @command="handleCardCommand" trigger="click" @click.stop>
                        <el-button :icon="MoreFilledIcon" circle class="bili-action-more-btn" @click.stop></el-button>
                        <template #dropdown>
                        <el-dropdown-menu>
                            <el-dropdown-item :command="{action: 'edit', video: video}" :icon="EditPenIcon">编辑</el-dropdown-item>
                            <el-dropdown-item :command="{action: 'delete', video: video}" :icon="DeleteIcon" class="delete-item">删除</el-dropdown-item>
                        </el-dropdown-menu>
                        </template>
                    </el-dropdown>
                </div>
              </div>
            </div>
          </div>
          <el-empty v-else-if="!isLoading" description="没有找到符合条件的视频" class="bili-empty-state"></el-empty>
        </template>
      </el-skeleton>
    </div>

    <div class="bili-pagination-container" v-if="totalVideos > 0 && !isLoading">
      <el-pagination
        background
        layout="prev, pager, next, jumper, ->, total, sizes"
        :total="totalVideos"
        :current-page="currentPage"
        :page-size="pageSize"
        :page-sizes="[10, 25, 50, 100]"
        @current-change="handleCurrentPageChange"
        @size-change="handlePageSizeChange"
      />
    </div>
    <VideoEditModal v-model:visible="editModalVisible" :video-data="currentVideoToEdit" @video-updated="handleVideoUpdated" />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick, onBeforeUnmount, watch } from 'vue';
import axios from 'axios';
import { useRouter, useRoute } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Refresh as RefreshIcon, EditPen as EditPenIcon, MoreFilled as MoreFilledIcon, Delete as DeleteIcon, User as UserFilled } from '@element-plus/icons-vue';
import VideoEditModal from '../components/VideoEditModal.vue';
import { formatDistanceToNowStrict } from 'date-fns';
import { zhCN } from 'date-fns/locale';

const props = defineProps({ initialMinRating: { type: Number, default: null } });
const router = useRouter();
const route = useRoute();
const videos = ref([]);
const isLoading = ref(true);
const currentPage = ref(1);
const pageSize = ref(25);
const totalVideos = ref(0);
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
const searchParams = reactive({ searchTerm: '', tags: [], persons_search: '', min_rating: props.initialMinRating, sortBy: props.initialMinRating ? 'rating' : 'id', sortOrder: 'desc' });
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
  { label: '最近更新', value: 'updated_date' }
]);

watch(() => route.query, (newQuery, oldQuery) => {
    searchParams.searchTerm = newQuery.search_term || '';
    searchParams.tags = newQuery.tags ? String(newQuery.tags).split(',').map(t => t.trim()).filter(t => t) : [];
    searchParams.persons_search = newQuery.persons_search || '';
    if (route.name === 'FeaturedVideos' && props.initialMinRating !== null) {
        searchParams.min_rating = props.initialMinRating;
        searchParams.sortBy = 'rating';
        searchParams.sortOrder = 'desc';
    } else if (newQuery.min_rating) {
        searchParams.min_rating = parseFloat(newQuery.min_rating);
    } else {
        searchParams.min_rating = null;
    }
    if (newQuery.sort_by) {
        searchParams.sortBy = newQuery.sort_by;
    }
    if (newQuery.sort_order) {
        searchParams.sortOrder = newQuery.sort_order;
    }
    if (JSON.stringify(newQuery) !== JSON.stringify(oldQuery) && !isLoading.value) {
         triggerSearch();
    }
}, { immediate: true, deep: true });

watch(() => props.initialMinRating, (newVal) => {
    searchParams.min_rating = newVal;
    if (route.name === 'FeaturedVideos' && newVal !== null) {
        searchParams.sortBy = 'rating';
    } else if (searchParams.sortBy === 'rating' && newVal === null) { 
        searchParams.sortBy = sortByOptions.value[0]?.value || 'id';
    }
    searchParams.sortOrder = 'desc';
    triggerSearch();
});

const fetchAllAvailableTags = async () => {
  isLoadingTags.value = true;
  try {
    const response = await axios.get(`${API_BASE_URL}/api/tags`, { params: { limit: 100 } }); 
    if (response.data && Array.isArray(response.data)) { allAvailableTags.value = response.data; }
  } catch (error) { console.error('获取所有可用标签失败:', error); allAvailableTags.value = []; }
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
    searchParams.persons_search = personName; 
    triggerSearch();
    ElMessage.info(`按人物 "${personName}" 筛选`);
};
const setSortByAndSearch = (sortByValue) => { 
    searchParams.sortBy = sortByValue; 
    if (sortByValue === 'name') {
        searchParams.sortOrder = 'asc';
    } else {
        searchParams.sortOrder = 'desc';
    }
    triggerSearch(); 
};
const setSortOrderAndSearch = (order) => { searchParams.sortOrder = order; triggerSearch(); };
const getVideoStreamUrl = (videoId) => videoId ? `${API_BASE_URL}/api/stream/${videoId}` : '';

const stopPreview = (videoIdToStop) => {
  if (previewTimeoutId) {
    clearTimeout(previewTimeoutId);
    previewTimeoutId = null;
  }
  if (previewingVideoId.value === videoIdToStop) {
    const player = videoPlayerRefs[videoIdToStop];
    if (player) {
      if (!player.paused) {
        player.pause();
      }
      player.removeAttribute('src'); 
      player.load(); 
    }
    previewingVideoId.value = null;
  }
};

const startPreview = (videoId) => {
  if (previewingVideoId.value && previewingVideoId.value !== videoId) {
    stopPreview(previewingVideoId.value);
  }
  if (previewTimeoutId) {
    clearTimeout(previewTimeoutId);
  }
  previewTimeoutId = setTimeout(async () => {
    if (previewingVideoId.value === videoId && videoPlayerRefs[videoId] && !videoPlayerRefs[videoId].paused) {
      return; 
    }
    previewingVideoId.value = videoId;
    await nextTick(); 
    const player = videoPlayerRefs[videoId];
    if (player) {
      const streamUrl = getVideoStreamUrl(videoId);
      player.src = streamUrl;
      const onCanPlay = () => {
        player.currentTime = 0;
        player.playbackRate = 5.0;
        player.play()
          .then(() => { 
            if (player.playbackRate !== 5.0) player.playbackRate = 5.0;
          })
          .catch(e => { 
            console.error(`视频ID: ${videoId} 预览播放Promise失败:`, e);
            if (previewingVideoId.value === videoId) stopPreview(videoId);
          });
        player.removeEventListener('canplay', onCanPlay);
        player.removeEventListener('error', onError);
      };
      const onError = (e) => {
        console.error(`视频ID: ${videoId} 加载或播放时发生错误事件:`, e);
        if (previewingVideoId.value === videoId) stopPreview(videoId);
        player.removeEventListener('canplay', onCanPlay);
        player.removeEventListener('error', onError);
      };
      player.addEventListener('canplay', onCanPlay);
      player.addEventListener('error', onError);
      player.load();
    } else {
      if (previewingVideoId.value === videoId) stopPreview(videoId);
    }
  }, 300); 
};

const fetchVideos = async (page = currentPage.value, size = pageSize.value) => {
  isLoading.value = true;
  try {
    const apiParams = { 
        skip: (page - 1) * size, limit: size, 
        search_term: searchParams.searchTerm || undefined, 
        tags: searchParams.tags.length > 0 ? searchParams.tags.join(',') : undefined, 
        persons_search: searchParams.persons_search || undefined,
        min_rating: searchParams.min_rating !== null ? searchParams.min_rating : undefined,
        sort_by: searchParams.sortBy, sort_order: searchParams.sortOrder 
    };
    const response = await axios.get(`${API_BASE_URL}/api/videos`, { params: apiParams });
    if (response.data && Array.isArray(response.data.videos)) {
      videos.value = response.data.videos.map(video => ({ ...video, thumbnail_url: video.thumbnail_url ? `${API_BASE_URL}${video.thumbnail_url}` : null, added_date: video.added_date ? new Date(video.added_date) : null }));
      totalVideos.value = response.data.total_count || 0;
      currentPage.value = page; pageSize.value = size;
    } else { 
      videos.value = []; totalVideos.value = 0; 
    }
  } catch (error) { 
    console.error('获取视频列表失败:', error.response || error); 
    videos.value = []; totalVideos.value = 0; 
    ElMessage.error('获取视频列表失败，请检查后端服务或网络连接。');
  } finally { 
    isLoading.value = false; 
  }
};

const triggerSearch = () => { 
    currentPage.value = 1; 
    const query = { }; 
    if (searchParams.searchTerm) query.search_term = searchParams.searchTerm;
    if (searchParams.tags.length > 0) query.tags = searchParams.tags.join(',');
    if (searchParams.persons_search) query.persons_search = searchParams.persons_search;
    if (searchParams.min_rating !== null) query.min_rating = searchParams.min_rating.toString();
    if (searchParams.sortBy && searchParams.sortBy !== (props.initialMinRating && route.name === 'FeaturedVideos' ? 'rating' : (sortByOptions.value[0]?.value || 'id'))) {
        query.sort_by = searchParams.sortBy;
    }
    if (searchParams.sortOrder && searchParams.sortOrder !== 'desc') {
         query.sort_order = searchParams.sortOrder;
    }

    if (Object.keys(query).length > 0 || route.name === 'VideoList') {
         if(JSON.stringify(query) !== JSON.stringify(route.query)) { 
            router.replace({ name: route.name || 'VideoList', query: query }); 
         } else { 
             fetchVideos();
         }
    } else if (Object.keys(route.query).length > 0 && route.name !== 'FeaturedVideos') {
        router.replace({ name: route.name || 'VideoList', query: {} });
    } else { 
        fetchVideos();
    }
};

const resetSearchAndFetch = () => { 
    searchParams.searchTerm = ''; searchParams.tags = []; searchParams.persons_search = ''; 
    const isFeaturedPage = route.name === 'FeaturedVideos';
    searchParams.min_rating = isFeaturedPage ? props.initialMinRating : null; 
    searchParams.sortBy = isFeaturedPage ? 'rating' : (sortByOptions.value[0]?.value || 'id'); 
    searchParams.sortOrder = 'desc'; 
    const query = {}; 
    if (isFeaturedPage && props.initialMinRating !== null) {
        query.min_rating = props.initialMinRating.toString();
    }
    router.replace({ name: route.name || 'VideoList', query: query }); 
    fetchVideos(); 
}; 

const formatDuration = (seconds) => { if (seconds === null || seconds === undefined || isNaN(seconds) || seconds < 0) return '0:00'; const h = Math.floor(seconds / 3600); const m = Math.floor((seconds % 3600) / 60); const s = Math.round(seconds % 60); if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`; return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`; };
const formatRelativeDate = (date) => { if (!date) return ''; try { return formatDistanceToNowStrict(date, { addSuffix: true, locale: zhCN }); } catch (e) { return '日期未知'; } };

const navigateToPlayer = (videoId) => { 
    if (!videoId) return; 
    if (previewingVideoId.value) stopPreview(previewingVideoId.value); 
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
const handleVideoUpdated = (updatedVideo) => { ElMessage.success('视频信息更新成功！'); fetchVideos(currentPage.value, pageSize.value); fetchAllAvailableTags(); };

const handleDeleteVideo = async (videoToDelete) => {
    try {
        await ElMessageBox.confirm( `确定将视频 "${videoToDelete.name}" 发送到回收站吗？`, '删除确认', { confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'warning', draggable: true, });
        isLoading.value = true; 
        await axios.delete(`${API_BASE_URL}/api/videos/${videoToDelete.id}/to-trash`);
        ElMessage.success(`视频 "${videoToDelete.name}" 已发送到回收站。`);
        videos.value = videos.value.filter(v => v.id !== videoToDelete.id);
        totalVideos.value = Math.max(0, totalVideos.value -1); 
        fetchAllAvailableTags();
    } catch (error) { if (error !== 'cancel') { ElMessage.error(error.response?.data?.detail || '删除视频失败，请稍后再试。'); } }
    finally { isLoading.value = false; }
};
const handleCardCommand = (command) => { if (command.action === 'edit') { openEditModal(command.video); } else if (command.action === 'delete') { handleDeleteVideo(command.video); } };

onMounted(() => { 
    fetchAllAvailableTags(); 
    triggerSearch();
});
onBeforeUnmount(() => { 
    if (previewTimeoutId) clearTimeout(previewTimeoutId); 
    if (previewingVideoId.value) {
      stopPreview(previewingVideoId.value); 
    }
    Object.keys(videoPlayerRefs).forEach(vidId => { 
        const player = videoPlayerRefs[vidId]; 
        if (player && typeof player.pause === 'function') {
            try { player.pause(); player.removeAttribute('src'); player.load(); } catch(e){}
        }
        delete videoPlayerRefs[vidId];
    }); 
});
</script>

<style scoped>
.bili-videolist-page { padding-top: 0; }
.sticky-controls-wrapper { position: sticky; top: 0; background-color: #f1f2f3; z-index: 10; padding-bottom: 1px; margin-bottom: -1px; }
.sticky-controls-content { max-width: 1550px; margin: 0 auto; background-color: #fff; border-bottom: 1px solid #e3e5e7; }
.bili-channel-section { margin-bottom: 0; border-bottom: none; padding: 10px 0 0 0; }
.bili-channel-header { display: flex; align-items: center; justify-content: space-between; max-width: 1550px; margin: 0 auto; padding: 0 20px; }
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
.bili-list-controls-container { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0; padding: 8px 20px 10px 20px; }
.sort-by-field-group { display: flex; align-items: center; gap: 6px; }
.sort-order-and-reset-group { display: flex; align-items: center; gap: 6px; }
.sort-field-btn-direct, .sort-order-btn { font-size: 13px; color: #61666d; padding: 0 10px; height: 28px; border-radius: 4px; line-height: 28px; }
.sort-field-btn-direct.is-active-sort, .sort-order-btn.is-active-sort { color: #00a1d6; font-weight: 500; background-color: #e2f3fa; }
.reset-btn-circle { font-size: 16px; color: #9499a0; padding: 6px; height: 28px; width: 28px; }
.reset-btn-circle:hover { color: #00a1d6; background-color: #f0f2f5; }
.video-grid-scrollable-area { padding-top: 10px; }
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
.person-tag .el-icon { vertical-align: middle; margin-right: 2px;}
.bili-card-rating { margin-bottom: 10px; font-size: 12px; color: #61666d; }
.bili-card-meta { font-size: 12px; color: #9499a0; line-height: 1.3; display: flex; justify-content: space-between; align-items: center; }
.meta-item { } 
.bili-card-actions { position: absolute; top: -5px; right: -5px; opacity: 0; transition: opacity 0.2s; }
.bili-video-card:hover .bili-card-actions { opacity: 1; }
.bili-action-more-btn { padding: 4px; font-size: 16px; color: #9499a0; background-color: transparent !important; border: none !important; box-shadow: none !important; }
.bili-action-more-btn:hover { background-color: #e3e5e7 !important; }
.bili-pagination-container { margin-top: 30px; display: flex; justify-content: center; padding: 0 20px; }
.bili-pagination-container :deep(.el-pagination.is-background .el-pager li:not(.is-disabled).is-active) { background-color: var(--el-color-primary) !important; }
.bili-pagination-container :deep(.el-pagination.is-background .el-pager li:not(.is-disabled):hover) { color: var(--el-color-primary) !important; }
.delete-item { color: var(--el-color-danger); }
.delete-item:hover { background-color: var(--el-color-danger-light-9); color: var(--el-color-danger); }
.section-separator { border: none; border-top: 1px solid #e9e9eb; margin: 8px 20px; }
</style>