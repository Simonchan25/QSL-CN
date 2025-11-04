import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Polyfill plugin to replace crypto.randomUUID calls in dependencies
const cryptoPolyfillPlugin = () => ({
  name: 'crypto-polyfill',
  transform(code, id) {
    // Only transform node_modules files that contain crypto.randomUUID
    if (id.includes('node_modules') && code.includes('crypto.randomUUID')) {
      // Replace crypto.randomUUID() with our polyfill
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

export default defineConfig({
  plugins: [cryptoPolyfillPlugin(), react()],
  define: {
    global: 'globalThis',
  },
  server: {
    host: '0.0.0.0',
    port: 2345,  // 使用2345端口
    strictPort: true,
    cors: true,
    allowedHosts: [
      'gp.simon-dd.life',
      '.simon-dd.life',
      'localhost',
      '127.0.0.1'
    ],
    hmr: false,  // 禁用HMR以支持HTTPS域名访问
    proxy: {
      // 不使用代理，直接访问远程API
    }
  },
  preview: {
    host: '0.0.0.0',
    port: 2345
  }
})