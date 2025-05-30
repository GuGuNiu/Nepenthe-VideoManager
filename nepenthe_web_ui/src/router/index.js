import { createRouter, createWebHashHistory } from 'vue-router';
import VideoListView from '../views/VideoListView.vue';

const routes = [
  { path: '/', name: 'VideoList', component: VideoListView, alias: '/home' },
  { path: '/featured', name: 'FeaturedVideos', component: VideoListView, props: { initialMinRating: 4.0 } },
  { path: '/gallery', name: 'GalleryView', component: VideoListView, meta: { disabled: true }, beforeEnter: (to, from, next) => { console.log('[路由守卫] 图集页面导航被阻止'); next(false); } },
];

const router = createRouter({
  history: createWebHashHistory(),
  routes,
  linkExactActiveClass: 'is-active-nav',
});

router.beforeEach((to, from, next) => {
  console.log(`[路由导航] 从: ${String(from.name)} (${from.fullPath}) 到: ${String(to.name)} (${to.fullPath})`);
  if (to.matched.some(record => record.meta.disabled)) {
    console.warn(`[路由导航] 到 ${String(to.name)} 的导航被 meta.disabled 阻止。`);
    if (from.name) { // 避免在初始加载时无限循环或导航到 undefined
      next(false); // 阻止导航
    } else {
      next('/'); // 如果没有来源（可能是直接访问），重定向到首页
    }
    return;
  }
  next();
});

export default router;