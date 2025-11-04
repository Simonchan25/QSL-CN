import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import './App.css'

console.log('[Main] Starting app...')

// Error Boundary Component
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null, errorInfo: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true }
  }

  componentDidCatch(error, errorInfo) {
    console.error('[ErrorBoundary] Caught error:', error, errorInfo)
    this.setState({ error, errorInfo })
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          background: '#0f1419',
          color: 'white',
          padding: '20px',
          fontFamily: 'monospace'
        }}>
          <h1>⚠️ 应用加载错误</h1>
          <h2>错误详情:</h2>
          <pre style={{
            background: '#1a1f2e',
            padding: '15px',
            borderRadius: '5px',
            overflow: 'auto'
          }}>
            {this.state.error?.toString()}
          </pre>
          <h3>Stack Trace:</h3>
          <pre style={{
            background: '#1a1f2e',
            padding: '15px',
            borderRadius: '5px',
            overflow: 'auto',
            fontSize: '12px'
          }}>
            {this.state.errorInfo?.componentStack}
          </pre>
          <button
            onClick={() => window.location.reload()}
            style={{
              marginTop: '20px',
              padding: '10px 20px',
              background: '#4fc3f7',
              color: 'white',
              border: 'none',
              borderRadius: '5px',
              cursor: 'pointer'
            }}
          >
            刷新页面
          </button>
        </div>
      )
    }

    return this.props.children
  }
}

try {
  console.log('[Main] Getting root element...')
  const rootEl = document.getElementById('root')

  if (!rootEl) {
    throw new Error('Root element not found!')
  }

  console.log('[Main] Creating React root...')
  const root = createRoot(rootEl)

  console.log('[Main] Rendering app...')
  root.render(
    <React.StrictMode>
      <ErrorBoundary>
        <App />
      </ErrorBoundary>
    </React.StrictMode>
  )

  console.log('[Main] App rendered successfully!')
} catch (error) {
  console.error('[Main] Fatal error during app initialization:', error)
  document.body.innerHTML = `
    <div style="background: #0f1419; color: white; padding: 20px; font-family: monospace;">
      <h1>⚠️ 初始化错误</h1>
      <p>无法启动应用。请检查浏览器控制台获取详细信息。</p>
      <pre style="background: #1a1f2e; padding: 15px; border-radius: 5px;">${error.toString()}</pre>
    </div>
  `
}


