import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/health': 'http://127.0.0.1:8000',
      '/patients': 'http://127.0.0.1:8000',
      '/doctor': 'http://127.0.0.1:8000'
    }
  }
})
