import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return {
    plugins: [react(), tailwindcss()],
    server: {
      port: 5173,
      // Same-origin proxy: the browser talks only to :5173, so the HttpOnly auth cookie
      // and the CSRF cookie work without cross-site cookie settings.
      proxy: { '/api': { target: env.VITE_BACKEND_URL || 'http://127.0.0.1:5000', changeOrigin: false } },
    },
    test: {
      environment: 'jsdom',
      setupFiles: ['./src/test/setup.js'],
      globals: true,
    },
  }
})
