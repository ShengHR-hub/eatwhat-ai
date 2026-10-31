import { fileURLToPath, URL } from 'node:url'
import os from 'node:os'

import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

/*
 * 多人房间的邀请二维码不能编码 localhost（另一台设备打不开）。
 * dev server 暴露本机非回环 IPv4，前端据此拼局域网邀请链接；
 * 这是开发辅助端点，不进入生产构建，也不碰业务后端。
 */
function lanAddressPlugin() {
  return {
    name: 'eatwhat-lan-addresses',
    configureServer(server) {
      server.middlewares.use('/__lan', (_req, res) => {
        const addresses = Object.values(os.networkInterfaces())
          .flat()
          .filter((item) => item && item.family === 'IPv4' && !item.internal)
          .map((item) => item.address)
        res.setHeader('Content-Type', 'application/json')
        res.end(JSON.stringify({ addresses }))
      })
    },
  }
}

// 移动端前台 + PC 后台共用一套构建产物；开发期把 /api/v1 代理到本机 FastAPI。
// 8000 被占用时可用 VITE_API_TARGET 指向备用端口，默认行为不变。
const API_TARGET = process.env.VITE_API_TARGET || 'http://127.0.0.1:8000'
const WS_TARGET = API_TARGET.replace(/^http/, 'ws')

export default defineConfig({
  plugins: [vue(), lanAddressPlugin()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    // 监听所有网卡：手机与 PC 同一 Wi-Fi 时直接访问 http://192.168.x.x:5173 看真机效果
    host: '0.0.0.0',
    port: 5173,
    // 编辑器/工具做原子写入时会在 src 下留临时目录，被 watcher 抓到时 Windows 会抛 EBUSY 直接把 dev server 打死。
    watch: {
      ignored: ['**/*.tmp', '**/.*.tmpdir/**', '**/.*.tmpdir'],
    },
    proxy: {
      '/api': {
        target: API_TARGET,
        changeOrigin: true,
      },
      // 用户上传的头像由后端静态目录提供，不代理会被 SPA 回退成 index.html
      '/uploads': {
        target: API_TARGET,
        changeOrigin: true,
      },
      // 多人房间的实时协议在根路径 /ws/room/...，单独代理并开 ws
      '/ws': {
        target: WS_TARGET,
        ws: true,
        changeOrigin: true,
      },
    },
  },
  build: {
    chunkSizeWarningLimit: 1200,
    rollupOptions: {
      output: {
        manualChunks: {
          echarts: ['echarts', 'vue-echarts'],
          motion: ['gsap', 'lottie-web', '@vueuse/motion'],
        },
      },
    },
  },
})
