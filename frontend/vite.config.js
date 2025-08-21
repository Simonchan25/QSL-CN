import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 1234,
    strictPort: true,
    cors: true,
    hmr: {
      protocol: 'ws',
      host: '0.0.0.0',
      port: 1234
    }
  },
  preview: {
    host: '0.0.0.0',
    port: 1234
  }
})