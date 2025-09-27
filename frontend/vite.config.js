import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  define: {
    global: 'globalThis',
  },
  server: {
    host: '0.0.0.0',
    port: 2345,
    strictPort: true,
    cors: true,
    hmr: {
      protocol: 'ws',
      host: '0.0.0.0',
      port: 2345
    }
  },
  preview: {
    host: '0.0.0.0',
    port: 2345
  }
})