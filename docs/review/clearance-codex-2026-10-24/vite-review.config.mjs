import { fileURLToPath } from 'node:url'
import original from '../../../frontend/vite.config.js'

export default {
  ...original,
  root: fileURLToPath(new URL('../../../frontend', import.meta.url)),
  server: {
    ...original.server,
    host: '127.0.0.1',
    port: 5174,
    strictPort: true,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8011', changeOrigin: true },
      '/ws': { target: 'ws://127.0.0.1:8011', ws: true, changeOrigin: true },
    },
  },
}
