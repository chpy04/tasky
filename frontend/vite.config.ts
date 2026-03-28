import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const apiTarget = process.env.API_URL || 'http://localhost:7400'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 7401,
    host: true,
    proxy: {
      // Proxy API requests to the FastAPI backend during development
      '/api': {
        target: apiTarget,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
