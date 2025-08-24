import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Requests to any path starting with /api will be sent to the backend
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      // Add this if you also use the /graph endpoint from the previous steps
      '/graph': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
})