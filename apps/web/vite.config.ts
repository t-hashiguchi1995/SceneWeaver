import { TanStackRouterVite } from '@tanstack/router-plugin/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const apiProxy = process.env.SCENEWEAVER_API_PROXY ?? 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [TanStackRouterVite({ autoCodeSplitting: true }), react()],
  server: {
    host: '127.0.0.1',
    port: Number(process.env.SCENEWEAVER_WEB_PORT ?? 5173),
    proxy: {
      '/api': apiProxy,
      '/health': apiProxy,
    },
  },
})