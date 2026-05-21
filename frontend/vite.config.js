import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3005,
    proxy: {
      '/api/v1': {
        target: 'http://209.38.239.83:8000',
        changeOrigin: true,
      },
    },
  },
})
