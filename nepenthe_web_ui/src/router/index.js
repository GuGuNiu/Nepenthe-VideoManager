import { createRouter, createWebHashHistory } from 'vue-router'; 
import VideoListView from '../views/VideoListView.vue';

const routes = [
  {
    path: '/',
    name: 'VideoList',
    component: VideoListView,
  },
  // VideoPlayerPage 相关的路由已移除，因为我们调用本地播放器
];

const router = createRouter({
  history: createWebHashHistory(), // 使用 Hash 模式
  routes,
});

export default router;