import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import './theme.css'  // 统一深色主题
import './chat.css'

// crypto.randomUUID polyfill for older browsers
if (!globalThis.crypto) {
  globalThis.crypto = {}
}
if (!globalThis.crypto.randomUUID) {
  globalThis.crypto.randomUUID = function() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      const r = Math.random() * 16 | 0
      const v = c === 'x' ? r : (r & 0x3 | 0x8)
      return v.toString(16)
    })
  }
}

const rootEl = document.getElementById('root')
createRoot(rootEl).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)


