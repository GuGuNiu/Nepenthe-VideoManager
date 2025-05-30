<template>
  <div :id="playerIdUnique" class="plyr-player-wrapper">
    <video :id="playerId" playsinline controls>
      <source :src="videoSrc" type="video/mp4" />
    </video>
    <div v-if="isLoading" class="status-overlay loading-overlay">加载中...</div>
    <div v-if="hasError" class="status-overlay error-overlay">视频加载失败</div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue';
import Plyr from 'plyr';
import 'plyr/dist/plyr.css';

const props = defineProps({
  playerIdUnique: { type: String, required: true },
  playerId: { type: String, required: true },
  videoSrc: { type: String, required: true },
  options: { type: Object, default: () => ({}) },
  isLoading: { type: Boolean, default: false },
  hasError: { type: Boolean, default: false },
});

const emit = defineEmits([
    'ready', 'timeupdate', 'play', 'pause', 'ended', 
    'volumechange', 'ratechange', 'error', 'loadedmetadata' // 添加 loadedmetadata
]);

const playerInstance = ref(null);

onMounted(async () => {
  await nextTick(); // 确保 DOM 元素已渲染
  const videoElement = document.getElementById(props.playerId);
  if (videoElement) {
    if (props.videoSrc) { // 只有在 videoSrc 有效时才初始化
        try {
            playerInstance.value = new Plyr(videoElement, props.options);
            
            emit('ready', playerInstance.value);

            playerInstance.value.on('loadedmetadata', () => {
                if(playerInstance.value) emit('loadedmetadata', playerInstance.value.duration);
            });
            playerInstance.value.on('timeupdate', () => {
                if(playerInstance.value) emit('timeupdate', playerInstance.value.currentTime);
            });
            playerInstance.value.on('play', () => emit('play'));
            playerInstance.value.on('pause', () => emit('pause'));
            playerInstance.value.on('ended', () => emit('ended'));
            playerInstance.value.on('volumechange', () => {
                if(playerInstance.value) emit('volumechange', playerInstance.value.volume);
            });
            playerInstance.value.on('ratechange', () => {
                if(playerInstance.value) emit('ratechange', playerInstance.value.speed);
            });
            playerInstance.value.on('error', (event) => {
                console.error(`Plyr error on player ${props.playerId}:`, event);
                emit('error', event);
            });

        } catch (error) {
            console.error(`Error initializing Plyr for player ${props.playerId}:`, error);
            emit('error', error);
        }
    } else {
        console.warn(`PlyrPlayer ${props.playerId}: videoSrc is empty, Plyr not initialized.`);
    }
  } else {
    console.error(`PlyrPlayer: Video element with id #${props.playerId} not found.`);
    emit('error', new Error(`Video element #${props.playerId} not found`));
  }
});

onBeforeUnmount(() => {
  if (playerInstance.value) {
    try { playerInstance.value.destroy(); } 
    catch (e) { console.warn(`Error destroying Plyr instance ${props.playerId}:`, e); }
    playerInstance.value = null;
  }
});

watch(() => props.videoSrc, (newSrc, oldSrc) => {
  if (newSrc && newSrc !== oldSrc) {
    console.log(`PlyrPlayer ${props.playerId}: Source changed from ${oldSrc} to ${newSrc}`);
    if (playerInstance.value) {
        playerInstance.value.source = {
            type: 'video',
            sources: [{ src: newSrc, type: 'video/mp4' }],
        };
    } else {
        // 如果播放器还未初始化（例如初始 videoSrc 为空），则在 onMounted 中处理
        console.log(`PlyrPlayer ${props.playerId}: Player not yet initialized, will use new source on mount.`);
    }
  }
});
</script>

<style scoped>
.plyr-player-wrapper {
  width: 100%;
  height: 100%;
  position: relative; /* 用于定位覆盖层 */
}
/* 确保 video 元素充满其容器 */
:deep(video), :deep(.plyr) {
  width: 100% !important;
  height: 100% !important;
  display: block; /* 移除可能的底部空白 */
}
.status-overlay {
  position: absolute;
  top: 0; left: 0; width: 100%; height: 100%;
  display: flex; justify-content: center; align-items: center;
  background-color: rgba(0,0,0,0.6);
  color: white;
  font-size: 1.1em;
  z-index: 10; /* 确保在视频元素之上 */
  pointer-events: none; /* 允许点击穿透到视频 */
}
.error-overlay {
  color: #ff4d4f; /* 醒目的错误颜色 */
  /* background-color: rgba(50,0,0,0.7); */
}
</style>