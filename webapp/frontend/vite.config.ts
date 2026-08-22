import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Local-only prototype: dev server proxies /api to the FastAPI backend
// (webapp/backend) so the frontend never needs a hardcoded absolute URL.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8010',
        changeOrigin: true,
      },
    },
  },
})
