import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // /api/ へのリクエストを Django へ転送する（Docker では compose.yaml で backend:8000 を指定）
    proxy: {
      '/api': process.env.VITE_PROXY_TARGET ?? 'http://localhost:8000',
    },
  },
})
