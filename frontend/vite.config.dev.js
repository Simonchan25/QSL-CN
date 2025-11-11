import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Polyfill plugin
const cryptoPolyfillPlugin = () => ({
  name: 'crypto-polyfill',
  transform(code, id) {
    if (id.includes('node_modules') && code.includes('crypto.randomUUID')) {
      const polyfillCode = '(function(){return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g,function(c){var r=Math.random()*16|0,v=c==="x"?r:(r&0x3|0x8);return v.toString(16)})})';
      const transformed = code.replace(/crypto\.randomUUID/g, polyfillCode);
      if (transformed !== code) {
        console.log('[crypto-polyfill] Transformed:', id);
        return { code: transformed, map: null };
      }
    }
    return null;
  }
});

// 开发环境配置 - 启用HMR
export default defineConfig({
  plugins: [cryptoPolyfillPlugin(), react()],
  define: {
    global: 'globalThis',
  },
  server: {
    host: '0.0.0.0',
    port: 2345,
    strictPort: true,
    cors: true,
    hmr: true,  // 开发环境启用HMR
    proxy: {
      // 可选：代理API请求到后端
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      }
    }
  }
})
