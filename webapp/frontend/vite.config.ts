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
        // Must match the port the backend is actually started on - see
        // README.md's "Backend startup" (`uvicorn app.main:app --port 8000`).
        // This previously pointed at 8010, a stale/mismatched dev port that
        // would silently 404 every API call on a fresh `npm run dev` +
        // README-documented backend start.
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
