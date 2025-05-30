import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  base: './', // <--- 确保 base 是 './'，这对于 file:// 协议加载至关重要
  build: {
    outDir: 'dist' // 确保 Vue 构建输出到 'dist' 目录
  }
})