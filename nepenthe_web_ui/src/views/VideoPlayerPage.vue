<template>
  <div class="video-player-page-container">
    <div class="player-wrapper" v-if="videoToPlay && !isLoadingInitialVideo && !videoToPlay.hasError">
      <PlyrPlayer 
        :key="videoToPlay.id"
        :player-id-unique="`plyr-instance-wrapper-${videoToPlay.id}`" 
        :player-id="`video-player-element-${videoToPlay.id}`"
        :video-src="getVideoStreamUrl(videoToPlay.id)"
        :options="plyrOptionsSingle"
        @ready="onSinglePlayerReady"
        @timeupdate="onSinglePlayerTimeUpdate"
        @ended="onSinglePlayerEnded"
        @error="onSinglePlayerError"
        @loadedmetadata="onSinglePlayerLoadedMetadata"
        class="actual-plyr-player"
      />
    </div>
    <div v-else-if="isLoadingInitialVideo" class="player-wrapper empty-state">
      <el-empty description="正在加载视频信息..."></el-empty>
    </div>
    <div v-else class="player-wrapper empty-state">
      <el-empty :description="videoToPlay && videoToPlay.hasError ? '视频加载失败' : '没有选择要播放的视频'"></el-empty>
    </div>

    <div class="simplified-controls" v-if="videoToPlay && !videoToPlay.hasError && playerInstance">
      <el-button @click="togglePlay" :icon="isPlaying ? PauseIcon : PlayIcon" circle title="播放/暂停"></el-button>
      <div class="progress-control">
        <span>{{ formatTime(currentTime) }}</span>
        <el-slider 
          v-model="progress" 
          :max="duration" 
          :format-tooltip="formatTimeSlider"
          @change="seekPlayer" 
          :disabled="duration === 0"
          style="flex-grow: 1; margin: 0 10px;"
        />
        <span>{{ formatTime(duration) }}</span>
      </div>
      <el-select v-model="currentSpeed" @change="setPlayerSpeed" placeholder="速度" style="width: 90px;" size="small">
        <el-option label="0.5x" :value="0.5"></el-option>
        <el-option label="1x" :value="1.0"></el-option>
        <el-option label="1.25x" :value="1.25"></el-option>
        <el-option label="1.5x" :value="1.5"></el-option>
        <el-option label="2x" :value="2.0"></el-option>
      </el-select>
      <el-tooltip :content="isMuted ? '取消静音' : '静音'" placement="top">
        <el-popover placement="top" :width="40" trigger="hover" :disabled="isMuted">
          <template #reference>
            <el-button :icon="isMuted ? MuteIcon : VolumeIcon" circle @click="toggleMute" style="margin-left: 10px;"></el-button>
          </template>
          <el-slider v-model="volume" vertical height="80px" :min="0" :max="1" :step="0.01" @input="setPlayerVolume" :disabled="isMuted"></el-slider>
        </el-popover>
      </el-tooltip>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue';
import PlyrPlayer from '../components/PlyrPlayer.vue';
import { useRoute, useRouter } from 'vue-router';
import axios from 'axios';
import { CaretRight as PlayIcon, VideoPause as PauseIcon, Bell as VolumeIcon, Mute as MuteIcon } from '@element-plus/icons-vue';

const route = useRoute();
const router = useRouter();
const API_BASE_URL = 'http://127.0.0.1:8000';

const videoToPlay = ref(null);
const playerInstance = ref(null);
const isLoadingInitialVideo = ref(true);
const isPlaying = ref(false);
const currentTime = ref(0);
const duration = ref(0);
const currentSpeed = ref(1.0);
const volume = ref(0.8);
const isMuted = ref(false);
const previousVolume = ref(0.8);

const progress = computed({
  get: () => currentTime.value,
  set: (val) => { if (playerInstance.value) seekPlayer(val); }
});
const plyrOptionsSingle = ref({
  controls: [], autoplay: true, clickToPlay: true,
  keyboard: { focused: false, global: false },
  tooltips: { controls: false, seek: false },
});
const getVideoStreamUrl = (videoId) => videoId ? `${API_BASE_URL}/api/stream/${videoId}` : '';
const fetchVideoDetails = async (videoId) => {
  if (!videoId) { videoToPlay.value = null; isLoadingInitialVideo.value = false; return; }
  isLoadingInitialVideo.value = true;
  videoToPlay.value = { id: videoId, isLoading: true, hasError: false, name: `视频 ${videoId}`, duration: 0 };
  try {
    const response = await axios.get(`${API_BASE_URL}/api/videos/${videoId}`);
    let videoDataFromServer = { ...response.data, isLoading: false, hasError: false };
    if (videoDataFromServer.thumbnail_url && typeof videoDataFromServer.thumbnail_url === 'string' && videoDataFromServer.thumbnail_url.startsWith('/')) {
      videoDataFromServer.thumbnail_url = `${API_BASE_URL}${videoDataFromServer.thumbnail_url}`;
    } else if (videoDataFromServer.thumbnail_path) {
      videoDataFromServer.thumbnail_url = `${API_BASE_URL}/static/thumbnails/${videoDataFromServer.thumbnail_path}`;
    } else { videoDataFromServer.thumbnail_url = null; }
    videoToPlay.value = videoDataFromServer;
    if (videoToPlay.value && videoToPlay.value.duration) { duration.value = videoToPlay.value.duration; }
  } catch (error) {
    console.error(`[VideoPlayerPage] 获取视频 ${videoId} 详情失败:`, error);
    videoToPlay.value = { id: videoId, name: `视频 ${videoId} (加载失败)`, duration: 0, isLoading: false, hasError: true };
  } finally { isLoadingInitialVideo.value = false; }
};
const onSinglePlayerReady = async (player) => {
  if (videoToPlay.value && videoToPlay.value.hasError) return;
  playerInstance.value = player;
  player.volume = isMuted.value ? 0 : volume.value;
  player.speed = currentSpeed.value;
  if (player && player.media.paused && plyrOptionsSingle.value.autoplay) {
    player.play().then(() => { isPlaying.value = true;}).catch(e => console.warn("[VideoPlayerPage] 自动播放失败:", e));
  } else if (player && !player.media.paused) { isPlaying.value = true; }
};
const onSinglePlayerLoadedMetadata = (playerDuration) => {
  if (playerInstance.value) {
    const actualDuration = playerInstance.value.duration;
    if (actualDuration && isFinite(actualDuration) && actualDuration > 0) {
        duration.value = actualDuration;
    } else if (videoToPlay.value && videoToPlay.value.duration) {
        duration.value = videoToPlay.value.duration;
    }
  }
};
const onSinglePlayerTimeUpdate = (newTime) => { currentTime.value = newTime; };
const onSinglePlayerEnded = () => { isPlaying.value = false; };
const onSinglePlayerError = (event) => {
  if (videoToPlay.value) videoToPlay.value.hasError = true;
  isPlaying.value = false;
};
const togglePlay = () => {
  if (playerInstance.value) {
    if (playerInstance.value.playing) { playerInstance.value.pause(); isPlaying.value = false; }
    else { playerInstance.value.play().catch(e => console.warn("播放失败:", e)); isPlaying.value = true; }
  }
};
const seekPlayer = (timeInSeconds) => {
  if (playerInstance.value && playerInstance.value.readyState >= 1 && playerInstance.value.duration && Number.isFinite(playerInstance.value.duration)) {
    playerInstance.value.currentTime = Math.max(0, Math.min(timeInSeconds, playerInstance.value.duration));
  } else {
    console.warn("播放器尚未准备好或时长未知，无法跳转");
  }
};
const setPlayerSpeed = (speed) => { if (playerInstance.value) playerInstance.value.speed = speed; };
const setPlayerVolume = (newVolume) => {
  if (playerInstance.value) {
    playerInstance.value.volume = newVolume; volume.value = newVolume;
    isMuted.value = newVolume < 0.01;
  }
};
const toggleMute = () => {
  if (playerInstance.value) {
    if (isMuted.value) { setPlayerVolume(previousVolume.value > 0.01 ? previousVolume.value : 0.5); }
    else { previousVolume.value = volume.value; setPlayerVolume(0); }
  }
};
const formatTime = (seconds) => {
  if (isNaN(seconds) || seconds === null || seconds === undefined || !isFinite(seconds) || seconds < 0) return '00:00';
  const date = new Date(0); date.setSeconds(seconds); 
  const timeStr = date.toISOString();
  return seconds >= 3600 ? timeStr.substr(11, 8) : timeStr.substr(14, 5);
};
const formatTimeSlider = (val) => formatTime(val);
const loadVideoFromRoute = async (idsQueryParam) => {
  isLoadingInitialVideo.value = true; isPlaying.value = false;
  currentTime.value = 0; duration.value = 0;
  if (playerInstance.value && typeof playerInstance.value.destroy === 'function') {
    try { playerInstance.value.destroy(); } catch (e) { console.warn("销毁旧播放器实例时出错:", e); }
    playerInstance.value = null;
  }
  if (idsQueryParam) {
    const ids = idsQueryParam.split(',').map(idStr => parseInt(idStr.trim())).filter(id => !isNaN(id));
    if (ids.length > 0) { await fetchVideoDetails(ids[0]); }
    else { videoToPlay.value = null; isLoadingInitialVideo.value = false; }
  } else { videoToPlay.value = null; isLoadingInitialVideo.value = false; }
};
watch(() => route.query.ids, (newIds) => { loadVideoFromRoute(newIds); }, { immediate: true });
const handleKeyDown = (event) => {
  if (!videoToPlay.value || videoToPlay.value.hasError || !playerInstance.value) return;
  const targetTagName = event.target.tagName.toLowerCase();
  if (['input', 'textarea', 'select'].includes(targetTagName) || event.target.isContentEditable) return;
  switch (event.key) {
    case ' ': event.preventDefault(); togglePlay(); break;
    case 'ArrowLeft': event.preventDefault(); seekPlayer(currentTime.value - 5); break;
    case 'ArrowRight': event.preventDefault(); seekPlayer(currentTime.value + 5); break;
    case 'm': case 'M': event.preventDefault(); toggleMute(); break;
  }
};
onMounted(() => { document.addEventListener('keydown', handleKeyDown); });
onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyDown);
  if (playerInstance.value && typeof playerInstance.value.destroy === 'function') {
    try { playerInstance.value.destroy(); } catch (e) { console.warn("销毁播放器实例时出错:", e); }
  }
});
</script>

<style scoped>
.video-player-page-container { display: flex; flex-direction: column; height: calc(100vh - 60px); background-color: #000; color: white; overflow: hidden; }
.player-wrapper { flex-grow: 1; display: flex; justify-content: center; align-items: center; background-color: #000; position: relative; overflow: hidden; }
.player-wrapper.empty-state { /* Styles for empty state already handled by el-empty */ }
.actual-plyr-player { width: 100%; height: 100%; }
:deep(.plyr-player-wrapper), :deep(.plyr--video), :deep(video) { width: 100% !important; height: 100% !important; object-fit: contain; display: block; }
.simplified-controls { display: flex; align-items: center; padding: 8px 15px; background-color: #181818; border-top: 1px solid #282828; flex-shrink: 0; z-index: 20; }
.progress-control { display: flex; align-items: center; flex-grow: 1; margin: 0 15px; }
.progress-control span { font-size: 0.85em; min-width: 45px; text-align: center; color: #ccc; }
.el-button { background-color: transparent !important; border-color: transparent !important; color: white !important; }
.el-button:hover, .el-button:focus { background-color: #383838 !important; color: white !important; }
.el-button :deep(.el-icon) { font-size: 20px; }
:deep(.el-slider__bar) { background-color: #409EFF; }
:deep(.el-slider__button) { border-color: #409EFF; background-color: #409EFF; width:14px; height:14px; } 
:deep(.el-select .el-input__wrapper) { background-color: #333 !important; box-shadow: none !important; border: 1px solid #555 !important; height: 30px; line-height:30px;}
:deep(.el-select .el-input__inner) { color: white !important; height: 28px; line-height:28px;}
:deep(.el-select .el-input .el-select__caret) { color: #888 !important; }
:deep(.el-popover.el-popper) { min-width: 40px !important; padding: 10px 5px !important; background-color: #1f1f1f !important; border-color: #383838 !important;}
</style>