import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

// https://vite.dev/config/
export default defineConfig(({ command }) => ({
  plugins: [vue()],
  // Khi build: base = /assets/ct_datalake/frontend/
  // → Frappe phục vụ tại: /assets/ct_datalake/frontend/index.html
  base: command === 'serve' ? '/' : '/assets/ct_datalake/frontend/',
  build: {
    // Output vào ct_datalake/ct_datalake/public/frontend/
    outDir: path.resolve(__dirname, '../ct_datalake/public/frontend'),
    emptyOutDir: true,
  },
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/files': 'http://127.0.0.1:8000',
      '/private': 'http://127.0.0.1:8000',
      '/assets': 'http://127.0.0.1:8000',
    }
  }
}))
