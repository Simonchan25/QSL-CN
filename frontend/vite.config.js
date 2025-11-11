import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react({ fastRefresh: false })],
  define: {
    global: 'globalThis',
  },
  server: {
    host: '0.0.0.0',
    port: 2345,
    strictPort: true,
    cors: true,
    hmr: {
      overlay: false,
      clientPort: 2345
    },
    watch: {
      ignored: ['**/node_modules/**', '**/.git/**']
    },
    proxy: {}
  },
  preview: {
    host: '0.0.0.0',
    port: 2345
  }
})