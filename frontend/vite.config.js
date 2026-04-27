import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  base: '/StockSelector/',
  publicDir: 'public',
  resolve: {
    alias: {
      /** @ 符号指向 src 目录 */
      "@": resolve(__dirname, "./src")
    }
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:5001',
        changeOrigin: true
      },
      '/StockSelector/api': {
        target: 'http://localhost:5001',
        changeOrigin: true
      },
      '/assets': {
        target: 'http://localhost:5001',
        changeOrigin: true
      }
    }
  }
})