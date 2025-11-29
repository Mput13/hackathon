import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true,
    proxy: {
      '/api': {
        target: 'http://172.29.8.236:8000',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path
      }
    }
  }
})