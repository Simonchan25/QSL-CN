import React, { useState, useEffect } from 'react'
import MarketOverview from './components/MarketOverviewSimplified'
import ReportHistory from './components/ReportHistory'
import './App.css'
import FloatingChat from './components/FloatingChat'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

// 动态获取API地址
const getApiUrl = (path) => {
  // 如果是本地开发环境，使用localhost
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return `http://localhost:8001${path}`
  }
  // 否则使用当前访问的主机地址
  return `http://${window.location.hostname}:8001${path}`
}

export default function App() {
  // 页面导航状态
  const [activeTab, setActiveTab] = useState('stock') // 'stock', 'hotspot', 'reports'
  // 移动端菜单状态
  const [sidebarOpen, setSidebarOpen] = useState(false)
  // 移动端市场概览状态
  const [marketOverviewOpen, setMarketOverviewOpen] = useState(false)
  
  // 个股分析状态
  const [name, setName] = useState('贵州茅台')
  const [force, setForce] = useState(false)
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [progress, setProgress] = useState([])
  const [showTerminal, setShowTerminal] = useState(false)
  const [logLines, setLogLines] = useState([])
  const [history, setHistory] = useState(() => {
    try { return JSON.parse(localStorage.getItem('qsl_history')||'[]') } catch { return [] }
  })
  
  // 热点概念历史记录
  const [hotspotHistory, setHotspotHistory] = useState(() => {
    try { return JSON.parse(localStorage.getItem('qsl_hotspot_history')||'[]') } catch { return [] }
  })
  
  // 热点概念分析状态
  const [hotspotKeyword, setHotspotKeyword] = useState('脑机')
  const [hotspotLoading, setHotspotLoading] = useState(false)
  const [hotspotData, setHotspotData] = useState(null)
  const [hotspotError, setHotspotError] = useState('')

  // 报告系统状态
  const [currentReport, setCurrentReport] = useState(null)
  const [reportType, setReportType] = useState('morning')
  const [reportLoading, setReportLoading] = useState(false)
  const [reportError, setReportError] = useState('')

  const formatProgress = (d) => {
    const s = d?.step || ''
    const p = d?.payload || {}
    if (s === 'resolve:start') return `开始解析：${p.input || ''}`
    if (s === 'resolve:done') return `解析成功：${p.base?.name || ''}${p.base?.ts_code ? `（${p.base.ts_code}）` : ''}`
    if (s === 'fetch:parallel:start') return `开始抓取：${p.ts_code || ''}`
    if (s === 'fetch:parallel:done') return `抓取完成：价格${p.px_rows ?? 0}行，基本面${(p.fundamental_keys||[]).length}项，宏观${(p.macro_keys||[]).length}项`
    if (s === 'compute:technical') return `技术面：收盘${p.tech_last_close ?? '-'}，RSI${p.tech_last_rsi ?? '-'}，MACD${p.tech_last_macd ?? '-'}，信号${p.tech_signal || '-'}`
    if (s === 'fetch:announcements') return `公告条数：${p.count ?? 0}`
    if (s === 'compute:news_sentiment') return `新闻情绪：正面${p.percentages?.positive ?? 0}% 中性${p.percentages?.neutral ?? 0}% 负面${p.percentages?.negative ?? 0}%（整体${p.overall || '-' }）`
    if (s === 'compute:scorecard') return `评分：总分${p.score_total ?? '-'}（基本面${p.score_fundamental ?? '-'} 技术${p.score_technical ?? '-'} 宏观${p.score_macro ?? '-' }）`
    if (s === 'llm:summary:start') return '生成 LLM 总结...'
    if (s === 'llm:summary:done') return `LLM 总结完成（长度 ${p.length ?? 0}）`
    return s ? `步骤：${s}` : ''
  }

  const analyze = async () => {
    setError(''); setLoading(true); setData(null)
    setProgress([]); setLogLines([]); setShowTerminal(true)

    const logs = new EventSource(getApiUrl('/logs/stream'))
    logs.addEventListener('log', (ev) => {
      try { const d = JSON.parse(ev.data || '{}'); if (d.line) setLogLines(ls => [...ls, d.line].slice(-300)) } catch {}
    })
    logs.addEventListener('error', () => { try { logs.close() } catch {} })

    const url = getApiUrl(`/analyze/stream?name=${encodeURIComponent(name)}&force=${force}`)
    const maxRetry = 3
    const retryDelay = 800
    let ended = false
    let captured = null

    const fallbackOnce = async () => {
      setProgress(p => [...p, '[warn] SSE 失败，改用一次性请求'])
      try {
        const res = await fetch(getApiUrl('/analyze'), {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, force })
        })
        if (!res.ok) throw new Error(await res.text())
        const j = await res.json(); captured = j; setData(j)
        try {
          const item = { name, at: Date.now(), data: j }
          const filtered = history.filter(h => h.name !== name)
          const next = [item, ...filtered].slice(0,50)
          setHistory(next)
          localStorage.setItem('qsl_history', JSON.stringify(next))
        } catch {}
      } catch (e) {
        const msg = String(e)
        setError(msg.includes('TypeError') ? '网络/后端暂不可达（可能在重启），请稍后重试' : msg)
      } finally {
        setLoading(false)
      }
    }

    const startSse = (attempt = 0) => {
      const es = new EventSource(url)
      es.addEventListener('progress', (ev) => {
        try { const d = JSON.parse(ev.data || '{}'); const line = formatProgress(d); if (line) setProgress(p => [...p, line].slice(-200)) } catch {}
      })
      es.addEventListener('result', (ev) => {
        try { const d = JSON.parse(ev.data || '{}'); if (d && Object.keys(d).length){ setData(d); captured = d } } catch {}
      })
      es.addEventListener('end', () => {
        ended = true
        try { es.close() } catch {}
        setLoading(false)
        setTimeout(()=> setShowTerminal(false), 1500)
        try {
          const item = { name, at: Date.now(), data: captured }
          const filtered = history.filter(h => h.name !== name)
          const next = [item, ...filtered].slice(0,50)
          setHistory(next)
          localStorage.setItem('qsl_history', JSON.stringify(next))
        } catch {}
      })
      es.addEventListener('error', () => {
        if (ended) return
        try { es.close() } catch {}
        if (attempt + 1 <= maxRetry) {
          const nextAttempt = attempt + 1
          setProgress(p => [...p, `[info] SSE 重试 #${nextAttempt}`])
          setTimeout(()=> startSse(nextAttempt), retryDelay * nextAttempt)
        } else {
          fallbackOnce()
        }
      })
    }

    startSse(0)
  }

  const analyzeHotspot = async () => {
    setHotspotError('')
    setHotspotLoading(true)
    setHotspotData(null)
    
    const url = getApiUrl(`/hotspot/stream?keyword=${encodeURIComponent(hotspotKeyword)}&force=${force}`)
    let ended = false
    let captured = null
    
    const fallback = async () => {
      try {
        const res = await fetch(getApiUrl('/hotspot'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ keyword: hotspotKeyword, force })
        })
        if (!res.ok) throw new Error(await res.text())
        const j = await res.json()
        setHotspotData(j)
        // 保存到历史记录
        try {
          const item = { keyword: hotspotKeyword, at: Date.now(), data: j }
          const filtered = hotspotHistory.filter(h => h.keyword !== hotspotKeyword)
          const next = [item, ...filtered].slice(0, 50)
          setHotspotHistory(next)
          localStorage.setItem('qsl_hotspot_history', JSON.stringify(next))
        } catch {}
      } catch (e) {
        setHotspotError(String(e))
      } finally {
        setHotspotLoading(false)
      }
    }
    
    const es = new EventSource(url)
    es.addEventListener('result', (ev) => {
      try {
        const d = JSON.parse(ev.data || '{}')
        if (d && Object.keys(d).length) {
          setHotspotData(d)
          captured = d
        }
      } catch {}
    })
    es.addEventListener('end', () => {
      ended = true
      try { es.close() } catch {}
      setHotspotLoading(false)
      // 保存到历史记录
      if (captured) {
        try {
          const item = { keyword: hotspotKeyword, at: Date.now(), data: captured }
          const filtered = hotspotHistory.filter(h => h.keyword !== hotspotKeyword)
          const next = [item, ...filtered].slice(0, 50)
          setHotspotHistory(next)
          localStorage.setItem('qsl_hotspot_history', JSON.stringify(next))
        } catch {}
      }
    })
    es.addEventListener('error', () => {
      if (ended) return
      try { es.close() } catch {}
      fallback()
    })
  }

  // 报告相关函数
  const loadReport = async (type) => {
    setReportLoading(true)
    setReportError('')
    setReportType(type)
    
    try {
      const res = await fetch(getApiUrl(`/reports/${type}`))
      if (res.ok) {
        const report = await res.json()
        setCurrentReport(report)
        setActiveTab('reports')
      } else if (res.status === 404) {
        setReportError(`暂无${type === 'morning' ? '早' : type === 'noon' ? '午' : '晚'}报`)
      } else {
        setReportError('加载报告失败')
      }
    } catch (e) {
      setReportError('网络错误')
    } finally {
      setReportLoading(false)
    }
  }

  const generateReport = async (type) => {
    setReportLoading(true)
    setReportError('')
    
    try {
      const res = await fetch(getApiUrl(`/reports/${type}/generate`), {
        method: 'POST'
      })
      if (res.ok) {
        // 等待3秒后自动加载
        setTimeout(() => loadReport(type), 3000)
        setReportError('报告生成中，请稍候...')
      } else {
        setReportError('生成报告失败')
      }
    } catch (e) {
      setReportError('网络错误')
    } finally {
      setReportLoading(false)
    }
  }
  
  const loadHistory = async (h) => {
    try {
      setError('')
      setShowTerminal(false)
      setProgress([]); setLogLines([])
      setName(h.name)
      setSidebarOpen(false) // 选择历史记录后关闭侦边栏
      if (h && h.data && Object.keys(h.data).length) {
        setData(h.data)
        return
      }
      setLoading(true)
      const res = await fetch(getApiUrl('/analyze'), {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: h.name, force: false })
      })
      if (!res.ok) throw new Error(await res.text())
      const j = await res.json()
      setData(j)
      try {
        const updated = (history||[]).map(x => x.name===h.name ? { ...x, data: j } : x)
        setHistory(updated)
        localStorage.setItem('qsl_history', JSON.stringify(updated))
      } catch {}
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  const loadHotspotHistory = async (h) => {
    try {
      setHotspotError('')
      setHotspotKeyword(h.keyword)
      setSidebarOpen(false) // 选择历史记录后关闭侦边栏
      if (h && h.data && Object.keys(h.data).length) {
        setHotspotData(h.data)
        return
      }
      setHotspotLoading(true)
      const res = await fetch(getApiUrl('/hotspot'), {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ keyword: h.keyword, force: false })
      })
      if (!res.ok) throw new Error(await res.text())
      const j = await res.json()
      setHotspotData(j)
      try {
        const updated = (hotspotHistory||[]).map(x => x.keyword===h.keyword ? { ...x, data: j } : x)
        setHotspotHistory(updated)
        localStorage.setItem('qsl_hotspot_history', JSON.stringify(updated))
      } catch {}
    } catch (e) {
      setHotspotError(String(e))
    } finally {
      setHotspotLoading(false)
    }
  }

  return (
    <div className="app-container" role="application">
      <header className="app-header">
        <div className="header-content">
          {/* 移动端菜单按钮 */}
          <button className="mobile-menu-button" onClick={() => setSidebarOpen(!sidebarOpen)} aria-label="Toggle menu">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
              <path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z"/>
            </svg>
          </button>
          
          <div className="logo-section">
            <svg className="logo-svg" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
              <rect x="10" y="20" width="15" height="60" fill="currentColor" opacity="0.8"/>
              <rect x="30" y="35" width="15" height="45" fill="currentColor" opacity="0.9"/>
              <rect x="50" y="15" width="15" height="65" fill="currentColor"/>
              <rect x="70" y="40" width="15" height="40" fill="currentColor" opacity="0.7"/>
            </svg>
            <div>
              <h1 className="app-title">QSL-A股分析助手</h1>
              <p className="app-subtitle">智能股票分析与决策支持系统</p>
            </div>
          </div>
          
          {/* 移动端市场概览按钮 */}
          <button className="mobile-market-button" onClick={() => {
            console.log('Market button clicked, current state:', marketOverviewOpen)
            setMarketOverviewOpen(!marketOverviewOpen)
          }} aria-label="市场概览">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
              <path d="M3,13H7L10,17L13,13H17L22,6L19.5,7.5L16.5,4.5L12,9L10.5,7.5L3,14.5V13Z"/>
            </svg>
          </button>
          
          {/* 导航标签 */}
          <nav className="header-nav">
            <button 
              className={`nav-tab ${activeTab === 'stock' ? 'active' : ''}`}
              onClick={() => setActiveTab('stock')}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M3 3v18h18v-2H5V3H3zm4 14h2v-6H7v6zm4 0h2V9h-2v8zm4 0h2v-4h-2v4z"/></svg> 个股分析
            </button>
            <button 
              className={`nav-tab ${activeTab === 'hotspot' ? 'active' : ''}`}
              onClick={() => setActiveTab('hotspot')}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M13.5.67s.74 2.65.74 4.8c0 2.06-1.35 3.73-3.41 3.73-2.07 0-3.63-1.67-3.63-3.73l.03-.36C5.21 7.51 4 10.62 4 14c0 4.42 3.58 8 8 8s8-3.58 8-8C20 8.61 17.41 3.8 13.5.67zM11.71 19c-1.78 0-3.22-1.4-3.22-3.14 0-1.62 1.05-2.76 2.81-3.12 1.77-.36 3.6-1.21 4.62-2.58.39 1.29.28 2.97-.2 4.18-.72 1.83-2.33 3.04-4.01 3.66z"/></svg> 热点概念
            </button>
            <button 
              className={`nav-tab ${activeTab === 'reports' ? 'active' : ''}`}
              onClick={() => setActiveTab('reports')}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm16-4H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-1 9H9V9h10v2zm-4 4H9v-2h6v2zm4-8H9V5h10v2z"/></svg> 市场报告
            </button>
          </nav>
        </div>
      </header>

      <div className="app-body">
        {/* 移动端侧边栏遮罩 */}
        <div className={`sidebar-overlay ${sidebarOpen ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}></div>
        {/* 移动端市场概览遮罩 */}
        <div className={`sidebar-overlay market-overlay ${marketOverviewOpen ? 'active' : ''}`} onClick={() => setMarketOverviewOpen(false)}></div>
        
        <div className={`main-layout ${activeTab}`}>
          {/* 个股分析页面 */}
          {activeTab === 'stock' && (
            <>
              {/* 左侧栏 - 桌面端显示，移动端作为抽屉 */}
              <aside className={`left-sidebar ${sidebarOpen ? 'active' : ''}`}>
                <div className="sidebar-section">
                  <h3 className="sidebar-title"><svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg> 个股分析</h3>
                  <div className="search-box">
                    <input 
                      type="text" 
                      id="stock-search"
                      name="stock-search"
                      value={name} 
                      onChange={e=>setName(e.target.value)} 
                      placeholder="股票名称/代码" 
                      onKeyDown={(e) => e.key === 'Enter' && !loading && analyze()}
                    />
                    <div className="search-options">
                      <label className="checkbox-label" htmlFor="force-refresh-stock">
                        <input type="checkbox" id="force-refresh-stock" name="force-refresh-stock" checked={force} onChange={e=>setForce(e.target.checked)} />
                        <span>强制刷新</span>
                      </label>
                    </div>
                    <button className="search-button" onClick={analyze} disabled={loading}>
                      {loading ? <><span className="spinner"></span> 分析中...</> : '开始分析'}
                    </button>
                    {loading && (
                      <div className="progress-bar-container">
                        <div className="progress-bar">
                          <div className="progress-bar-fill"></div>
                        </div>
                        <div className="progress-text">正在分析，请稍候...</div>
                      </div>
                    )}
                  </div>
                  {error && <div className="error-message">{error}</div>}
                </div>
                
                <div className="sidebar-section">
                  <h3 className="sidebar-title"><svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/></svg> 历史记录</h3>
                  <div className="history-list">
                    {history.length > 0 ? (
                      history.slice(0, 10).map((h,i)=> (
                        <div key={i} className="history-item" onClick={()=>loadHistory(h)}>
                          <span className="history-name">{h.name}</span>
                          <span className="history-time">{new Date(h.at).toLocaleDateString()}</span>
                        </div>
                      ))
                    ) : (
                      <div className="empty-state">暂无历史记录</div>
                    )}
                  </div>
                </div>
              </aside>

              {/* 中间内容区 */}
              <main className="content-area">
                {/* 移动端搜索框 - 仅在小屏幕显示 */}
                <div className="mobile-search-container">
                  <div className="search-box mobile-only">
                    <input 
                      type="text"
                      value={name} 
                      onChange={e=>setName(e.target.value)} 
                      placeholder="输入股票名称或代码" 
                      onKeyDown={(e) => e.key === 'Enter' && !loading && analyze()}
                    />
                    <button className="search-button" onClick={analyze} disabled={loading}>
                      {loading ? <><span className="spinner"></span> 分析中...</> : '开始分析'}
                    </button>
                  </div>
                </div>
                
                {!data && !loading && !showTerminal && (
                  <div className="empty-analysis">
                    <h3><svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M16,6L18.29,8.29L13.41,13.17L9.41,9.17L2,16.59L3.41,18L9.41,12L13.41,16L19.71,9.71L22,12V6H16Z"/></svg> 等待分析</h3>
                    <p>请在左侧输入股票名称或代码，点击"开始分析"</p>
                  </div>
                )}

                {showTerminal && (
                  <div className="terminal-card">
                    <div className="terminal-header">
                      <span className="terminal-title"><svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M20,3H4A1,1 0 0,0 3,4V20A1,1 0 0,0 4,21H20A1,1 0 0,0 21,20V4A1,1 0 0,0 20,3M20,20H4V5H20V20Z"/><path d="M6 7H8V9H6V7M10 7H18V9H10V7M6 11H8V13H6V11M10 11H18V13H10V11M6 15H8V17H6V15M10 15H18V17H10V15Z"/></svg> 实时分析进度</span>
                      <button className="terminal-close" onClick={() => setShowTerminal(false)}>×</button>
                    </div>
                    <div className="terminal-body">
                      {progress.map((ln, i)=> (
                        <div key={i} className="terminal-line progress-line">
                          <span className="line-prefix">▶</span>{ln}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {data && (
                  <div className="results-container">
                    <div className="result-card basic-info">
                      <h3 className="card-title"><svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M19,3H5A2,2 0 0,0 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V5A2,2 0 0,0 19,3M9,17H7V10H9V17M13,17H11V7H13V17M17,17H15V13H17V17Z"/></svg> 基本信息</h3>
                      <div className="info-grid">
                        <div className="info-item">
                          <span className="info-label">股票名称</span>
                          <span className="info-value">{data.basic?.name || '-'}</span>
                        </div>
                        <div className="info-item">
                          <span className="info-label">股票代码</span>
                          <span className="info-value">{data.basic?.ts_code || data.basic?.symbol || '-'}</span>
                        </div>
                      </div>
                    </div>

                    <div className="result-card llm-summary">
                      <h3 className="card-title"><svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12,2A2,2 0 0,1 14,4C14,4.74 13.6,5.39 13,5.73V7H14A7,7 0 0,1 21,14H22A1,1 0 0,1 23,15V18A1,1 0 0,1 22,19H21V20A2,2 0 0,1 19,22H5A2,2 0 0,1 3,20V19H2A1,1 0 0,1 1,18V15A1,1 0 0,1 2,14H3A7,7 0 0,1 10,7H11V5.73C10.4,5.39 10,4.74 10,4A2,2 0 0,1 12,2M7.5,13A2.5,2.5 0 0,0 5,15.5A2.5,2.5 0 0,0 7.5,18A2.5,2.5 0 0,0 10,15.5A2.5,2.5 0 0,0 7.5,13M16.5,13A2.5,2.5 0 0,0 14,15.5A2.5,2.5 0 0,0 16.5,18A2.5,2.5 0 0,0 19,15.5A2.5,2.5 0 0,0 16.5,13Z"/></svg> QSL-AI 智能分析</h3>
                      <div className="llm-content markdown-content">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {data.llm_summary || '暂无QSL-AI分析'}
                        </ReactMarkdown>
                      </div>
                    </div>

                    <div className="result-card scorecard">
                      <h3 className="card-title"><svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M22,21H2V3H4V19H6V17H10V19H12V16H16V19H18V17H22V21M18,14H22V16H18V14M12,6H16V15H12V6M6,10H10V16H6V10M4,13H2V15H4V13Z"/></svg> 综合评分</h3>
                      <div className="score-grid">
                        <div className="score-item total">
                          <span className="score-label">总分</span>
                          <span className="score-value">{data.scorecard?.score_total ?? '-'}</span>
                        </div>
                        <div className="score-item">
                          <span className="score-label">基本面</span>
                          <span className="score-value">{data.scorecard?.score_fundamental ?? '-'}</span>
                        </div>
                        <div className="score-item">
                          <span className="score-label">技术面</span>
                          <span className="score-value">{data.scorecard?.score_technical ?? '-'}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </main>
            </>
          )}

          {/* 热点概念页面 */}
          {activeTab === 'hotspot' && (
            <>
              {/* 左侧栏 */}
              <aside className={`left-sidebar ${sidebarOpen ? 'active' : ''}`}>
                <div className="sidebar-section">
                  <h3 className="sidebar-title">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style={{marginRight: '8px', verticalAlign: 'middle'}}>
                      <path d="M17.66 11.2C17.43 10.9 17.15 10.64 16.89 10.38C16.22 9.78 15.46 9.35 14.82 8.72C13.33 7.26 13 4.85 13.95 3C13 3.23 12.17 3.75 11.46 4.32C8.87 6.4 7.85 10.07 9.07 13.22C9.11 13.32 9.15 13.42 9.15 13.55C9.15 13.77 9 13.97 8.8 14.05C8.57 14.15 8.33 14.09 8.14 13.93C8.08 13.88 8.04 13.83 8 13.76C6.87 12.33 6.69 10.28 7.45 8.64C5.78 10 4.87 12.3 5 14.47C5.06 14.97 5.12 15.47 5.29 15.97C5.43 16.57 5.7 17.17 6 17.7C7.08 19.43 8.95 20.67 10.96 20.92C13.1 21.19 15.39 20.8 17.03 19.32C18.86 17.66 19.5 15 18.56 12.72L18.43 12.46C18.22 12 17.66 11.2 17.66 11.2M14.5 17.5C14.22 17.74 13.76 18 13.4 18.1C12.28 18.5 11.16 17.94 10.5 17.28C11.69 17 12.4 16.12 12.61 15.23C12.78 14.43 12.46 13.77 12.33 13C12.21 12.26 12.23 11.63 12.5 10.94C12.69 11.32 12.89 11.7 13.13 12C13.9 13 15.11 13.44 15.37 14.8C15.41 14.94 15.43 15.08 15.43 15.23C15.46 16.05 15.1 16.95 14.5 17.5H14.5Z"/>
                    </svg>
                    热点概念分析
                  </h3>
                  <div className="search-box">
                    <input 
                      type="text" 
                      id="hotspot-search"
                      name="hotspot-search"
                      value={hotspotKeyword} 
                      onChange={e=>setHotspotKeyword(e.target.value)} 
                      placeholder="输入概念关键词" 
                      onKeyDown={(e) => e.key === 'Enter' && !hotspotLoading && analyzeHotspot()}
                    />
                    <div className="search-options">
                      <label className="checkbox-label" htmlFor="force-refresh-hotspot">
                        <input type="checkbox" id="force-refresh-hotspot" name="force-refresh-hotspot" checked={force} onChange={e=>setForce(e.target.checked)} />
                        <span>强制刷新</span>
                      </label>
                    </div>
                    <button className="search-button" onClick={analyzeHotspot} disabled={hotspotLoading}>
                      {hotspotLoading ? <><span className="spinner"></span> 分析中...</> : '分析热点'}
                    </button>
                    {hotspotLoading && (
                      <div className="progress-bar-container">
                        <div className="progress-bar">
                          <div className="progress-bar-fill"></div>
                        </div>
                        <div className="progress-text">正在分析热点，请稍候...</div>
                      </div>
                    )}
                  </div>
                  {hotspotError && <div className="error-message">{hotspotError}</div>}
                </div>
                
                <div className="sidebar-section">
                  <h3 className="sidebar-title">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/>
                    </svg>
                    历史记录
                  </h3>
                  <div className="history-list">
                    {hotspotHistory.length > 0 ? (
                      hotspotHistory.slice(0, 10).map((h,i)=> (
                        <div key={i} className="history-item" onClick={()=>loadHotspotHistory(h)}>
                          <span className="history-name">{h.keyword}</span>
                          <span className="history-time">{new Date(h.at).toLocaleDateString()}</span>
                        </div>
                      ))
                    ) : (
                      <div className="empty-state">暂无历史记录</div>
                    )}
                  </div>
                </div>
              </aside>

              {/* 中间内容区 */}
              <main className="content-area">
                {/* 移动端搜索框 - 仅在小屏幕显示 */}
                <div className="mobile-search-container">
                  <div className="search-box mobile-only">
                    <input 
                      type="text"
                      value={hotspotKeyword} 
                      onChange={e=>setHotspotKeyword(e.target.value)} 
                      placeholder="输入概念关键词" 
                      onKeyDown={(e) => e.key === 'Enter' && !hotspotLoading && analyzeHotspot()}
                    />
                    <button className="search-button" onClick={analyzeHotspot} disabled={hotspotLoading}>
                      {hotspotLoading ? <><span className="spinner"></span> 分析中...</> : '分析热点'}
                    </button>
                  </div>
                </div>
                
                {!hotspotData && !hotspotLoading && (
                  <div className="empty-analysis">
                    <h3>
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style={{marginRight: '8px', verticalAlign: 'middle'}}>
                        <path d="M17.66 11.2C17.43 10.9 17.15 10.64 16.89 10.38C16.22 9.78 15.46 9.35 14.82 8.72C13.33 7.26 13 4.85 13.95 3C13 3.23 12.17 3.75 11.46 4.32C8.87 6.4 7.85 10.07 9.07 13.22C9.11 13.32 9.15 13.42 9.15 13.55C9.15 13.77 9 13.97 8.8 14.05C8.57 14.15 8.33 14.09 8.14 13.93C8.08 13.88 8.04 13.83 8 13.76C6.87 12.33 6.69 10.28 7.45 8.64C5.78 10 4.87 12.3 5 14.47C5.06 14.97 5.12 15.47 5.29 15.97C5.43 16.57 5.7 17.17 6 17.7C7.08 19.43 8.95 20.67 10.96 20.92C13.1 21.19 15.39 20.8 17.03 19.32C18.86 17.66 19.5 15 18.56 12.72L18.43 12.46C18.22 12 17.66 11.2 17.66 11.2M14.5 17.5C14.22 17.74 13.76 18 13.4 18.1C12.28 18.5 11.16 17.94 10.5 17.28C11.69 17 12.4 16.12 12.61 15.23C12.78 14.43 12.46 13.77 12.33 13C12.21 12.26 12.23 11.63 12.5 10.94C12.69 11.32 12.89 11.7 13.13 12C13.9 13 15.11 13.44 15.37 14.8C15.41 14.94 15.43 15.08 15.43 15.23C15.46 16.05 15.1 16.95 14.5 17.5H14.5Z"/>
                      </svg>
                      等待分析
                    </h3>
                    <p>请在左侧输入概念关键词，点击"分析热点"</p>
                  </div>
                )}

                {hotspotData && (
                  <div className="results-container hotspot-results">
                    <div className="result-card hotspot-header">
                      <h3 className="card-title">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style={{marginRight: '8px', verticalAlign: 'middle'}}>
                          <path d="M17.66 11.2C17.43 10.9 17.15 10.64 16.89 10.38C16.22 9.78 15.46 9.35 14.82 8.72C13.33 7.26 13 4.85 13.95 3C13 3.23 12.17 3.75 11.46 4.32C8.87 6.4 7.85 10.07 9.07 13.22C9.11 13.32 9.15 13.42 9.15 13.55C9.15 13.77 9 13.97 8.8 14.05C8.57 14.15 8.33 14.09 8.14 13.93C8.08 13.88 8.04 13.83 8 13.76C6.87 12.33 6.69 10.28 7.45 8.64C5.78 10 4.87 12.3 5 14.47C5.06 14.97 5.12 15.47 5.29 15.97C5.43 16.57 5.7 17.17 6 17.7C7.08 19.43 8.95 20.67 10.96 20.92C13.1 21.19 15.39 20.8 17.03 19.32C18.86 17.66 19.5 15 18.56 12.72L18.43 12.46C18.22 12 17.66 11.2 17.66 11.2M14.5 17.5C14.22 17.74 13.76 18 13.4 18.1C12.28 18.5 11.16 17.94 10.5 17.28C11.69 17 12.4 16.12 12.61 15.23C12.78 14.43 12.46 13.77 12.33 13C12.21 12.26 12.23 11.63 12.5 10.94C12.69 11.32 12.89 11.7 13.13 12C13.9 13 15.11 13.44 15.37 14.8C15.41 14.94 15.43 15.08 15.43 15.23C15.46 16.05 15.1 16.95 14.5 17.5H14.5Z"/>
                        </svg>
                        热点概念：{hotspotData.keyword}
                      </h3>
                      <div className="hotspot-stats">
                        <div className="stat-item">
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M3,13H7L10,17L13,13H17L22,6L19.5,7.5L16.5,4.5L12,9L10.5,7.5L3,14.5V13Z"/>
                          </svg>
                          <span className="stat-value">{hotspotData?.stock_count || 0}</span>
                          <span className="stat-label">相关股票</span>
                        </div>
                        <div className="stat-item">
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M19,3H5A2,2 0 0,0 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V5A2,2 0 0,0 19,3M9,17H7V10H9V17M13,17H11V7H13V17M17,17H15V13H17V17Z"/>
                          </svg>
                          <span className="stat-value">{hotspotData?.analyzed_count || 0}</span>
                          <span className="stat-label">分析数量</span>
                        </div>
                        <div className="stat-item">
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M20 5L20 19L4 19L4 5H20M20 3H4C2.89 3 2 3.89 2 5V19C2 20.11 2.89 21 4 21H20C21.11 21 22 20.11 22 19V5C22 3.89 21.11 3 20 3M18 15H6V17H18V15M10 7H6V13H10V7M12 9H18V7H12V9M18 11H12V13H18V11Z"/>
                          </svg>
                          <span className="stat-value">{hotspotData?.news?.news_count || 0}</span>
                          <span className="stat-label">相关新闻</span>
                        </div>
                      </div>
                    </div>
                    
                    {hotspotData?.llm_summary && (
                      <div className="result-card llm-summary">
                        <h3 className="card-title">
                          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style={{marginRight: '8px', verticalAlign: 'middle'}}>
                            <path d="M12,2A2,2 0 0,1 14,4C14,4.74 13.6,5.39 13,5.73V7H14A7,7 0 0,1 21,14H22A1,1 0 0,1 23,15V18A1,1 0 0,1 22,19H21V20A2,2 0 0,1 19,22H5A2,2 0 0,1 3,20V19H2A1,1 0 0,1 1,18V15A1,1 0 0,1 2,14H3A7,7 0 0,1 10,7H11V5.73C10.4,5.39 10,4.74 10,4A2,2 0 0,1 12,2M7.5,13A2.5,2.5 0 0,0 5,15.5A2.5,2.5 0 0,0 7.5,18A2.5,2.5 0 0,0 10,15.5A2.5,2.5 0 0,0 7.5,13M16.5,13A2.5,2.5 0 0,0 14,15.5A2.5,2.5 0 0,0 16.5,18A2.5,2.5 0 0,0 19,15.5A2.5,2.5 0 0,0 16.5,13Z"/>
                          </svg>
                          QSL-AI 热点分析
                        </h3>
                        <div className="llm-content markdown-content">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {hotspotData.llm_summary}
                          </ReactMarkdown>
                        </div>
                      </div>
                    )}
                    
                    {hotspotData.stocks && hotspotData.stocks.length > 0 && (
                      <div className="result-card">
                        <h3 className="card-title">
                          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style={{marginRight: '8px', verticalAlign: 'middle'}}>
                            <path d="M3,13H7L10,17L13,13H17L22,6L19.5,7.5L16.5,4.5L12,9L10.5,7.5L3,14.5V13Z"/>
                          </svg>
                          相关股票排名
                        </h3>
                        <div className="stocks-table-container">
                          {/* 桌面端表格 */}
                          <table className="hotspot-table">
                            <thead>
                              <tr>
                                <th>排名</th>
                                <th>股票</th>
                                <th>行业</th>
                                <th>相关度</th>
                                <th>技术分</th>
                                <th>基本分</th>
                                <th>综合分</th>
                                <th>涨跌幅</th>
                              </tr>
                            </thead>
                            <tbody>
                              {(hotspotData?.stocks || []).map((stock, i) => (
                                <tr key={i}>
                                  <td>{i + 1}</td>
                                  <td className="stock-name">{stock?.name || '-'}</td>
                                  <td>{stock?.industry || '-'}</td>
                                  <td>{stock?.relevance_score || '-'}</td>
                                  <td>{stock?.tech_score || '-'}</td>
                                  <td>{stock?.fund_score || '-'}</td>
                                  <td className="final-score">{stock?.final_score || '-'}</td>
                                  <td className={stock?.price_change_pct > 0 ? 'up' : stock?.price_change_pct < 0 ? 'down' : ''}>
                                    {stock?.price_change_pct ? `${stock.price_change_pct > 0 ? '+' : ''}${stock.price_change_pct}%` : '-'}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                          
                          {/* 移动端卡片列表 */}
                          <div className="mobile-stock-cards" style={{display: 'none'}}>
                            {(hotspotData?.stocks || []).map((stock, i) => (
                              <div key={i} className="mobile-stock-card">
                                <span className="stock-rank">#{i + 1}</span>
                                <div className="stock-info">
                                  <span className="stock-name">{stock?.name || '-'}</span>
                                  <span className={`stock-change ${stock?.price_change_pct > 0 ? 'up' : stock?.price_change_pct < 0 ? 'down' : ''}`}>
                                    {stock?.price_change_pct ? `${stock.price_change_pct > 0 ? '+' : ''}${stock.price_change_pct}%` : '-'}
                                  </span>
                                </div>
                                <div className="stock-scores">
                                  <span className="score-item">{stock?.industry || '-'}</span>
                                  <span className="score-item">相关度: {stock?.relevance_score || '-'}</span>
                                  <span className="score-item">技术: {stock?.tech_score || '-'}</span>
                                  <span className="score-item">基本: {stock?.fund_score || '-'}</span>
                                  <span className="score-item" style={{fontWeight: 'bold'}}>综合: {stock?.final_score || '-'}</span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </main>
            </>
          )}

          {/* 报告页面 */}
          {activeTab === 'reports' && (
            <>
              {/* 左侧报告历史 */}
              <aside className="left-sidebar">
                <div className="sidebar-section">
                  <h3 className="sidebar-title">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style={{marginRight: '8px', verticalAlign: 'middle'}}>
                      <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20M10,19L12,15H9V10H15V15L13,19H10Z"/>
                    </svg>
                    报告管理
                  </h3>
                  <div className="report-buttons">
                    <button className="report-button morning" onClick={() => loadReport('morning')} disabled={reportLoading}>
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style={{marginRight: '6px', verticalAlign: 'middle'}}>
                        <path d="M9,10H7V12H9V10M13,10H11V12H13V10M17,10H15V12H17V10M19,3H18V1H16V3H8V1H6V3H5C3.89,3 3,3.9 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V5A2,2 0 0,0 19,3M19,19H5V8H19V19Z"/>
                      </svg>
                      查看早报
                    </button>
                    <button className="report-button noon" onClick={() => loadReport('noon')} disabled={reportLoading}>
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style={{marginRight: '6px', verticalAlign: 'middle'}}>
                        <path d="M3,12H7A5,5 0 0,1 12,7A5,5 0 0,1 17,12H21A1,1 0 0,1 22,13A1,1 0 0,1 21,14H3A1,1 0 0,1 2,13A1,1 0 0,1 3,12M5,16H19A1,1 0 0,1 20,17A1,1 0 0,1 19,18H5A1,1 0 0,1 4,17A1,1 0 0,1 5,16M17,20A1,1 0 0,1 18,21A1,1 0 0,1 17,22H7A1,1 0 0,1 6,21A1,1 0 0,1 7,20H17Z"/>
                      </svg>
                      查看午报
                    </button>
                    <button className="report-button evening" onClick={() => loadReport('evening')} disabled={reportLoading}>
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style={{marginRight: '6px', verticalAlign: 'middle'}}>
                        <path d="M17.75,4.09L15.22,6.03L16.13,9.09L13.5,7.28L10.87,9.09L11.78,6.03L9.25,4.09L12.44,4L13.5,1L14.56,4L17.75,4.09M21.25,11L19.61,12.25L20.2,14.23L18.5,13.06L16.8,14.23L17.39,12.25L15.75,11L17.81,10.95L18.5,9L19.19,10.95L21.25,11M18.97,15.95C19.8,15.87 20.69,17.05 20.16,17.8C19.84,18.25 19.5,18.67 19.08,19.07C15.17,23 8.84,23 4.94,19.07C1.03,15.17 1.03,8.83 4.94,4.93C5.34,4.53 5.76,4.17 6.21,3.85C6.96,3.32 8.14,4.21 8.06,5.04C7.79,7.9 8.75,10.87 10.95,13.06C13.14,15.26 16.1,16.22 18.97,15.95M17.33,17.97C14.5,17.81 11.7,16.64 9.53,14.5C7.36,12.31 6.2,9.5 6.04,6.68C3.23,9.82 3.34,14.64 6.35,17.66C9.37,20.67 14.19,20.78 17.33,17.97Z"/>
                      </svg>
                      查看晚报
                    </button>
                  </div>
                  <div className="report-generate">
                    <div className="report-type-selector">
                      <span className="selector-label">选择报告类型：</span>
                      <div className="type-buttons">
                        <button 
                          className={`type-button ${reportType === 'morning' ? 'active' : ''}`}
                          onClick={() => setReportType('morning')}
                          disabled={reportLoading}
                        >
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M12 7c-2.76 0-5 2.24-5 5s2.24 5 5 5 5-2.24 5-5-2.24-5-5-5zM2 13h2c.55 0 1-.45 1-1s-.45-1-1-1H2c-.55 0-1 .45-1 1s.45 1 1 1zm18 0h2c.55 0 1-.45 1-1s-.45-1-1-1h-2c-.55 0-1 .45-1 1s.45 1 1 1zM11 2v2c0 .55.45 1 1 1s1-.45 1-1V2c0-.55-.45-1-1-1s-1 .45-1 1zm0 18v2c0 .55.45 1 1 1s1-.45 1-1v-2c0-.55-.45-1-1-1s-1 .45-1 1zM5.99 4.58c-.39-.39-1.03-.39-1.41 0-.39.39-.39 1.03 0 1.41l1.06 1.06c.39.39 1.03.39 1.41 0s.39-1.03 0-1.41L5.99 4.58zm12.37 12.37c-.39-.39-1.03-.39-1.41 0-.39.39-.39 1.03 0 1.41l1.06 1.06c.39.39 1.03.39 1.41 0 .39-.39.39-1.03 0-1.41l-1.06-1.06zm1.06-10.96c.39-.39.39-1.03 0-1.41-.39-.39-1.03-.39-1.41 0l-1.06 1.06c-.39.39-.39 1.03 0 1.41s1.03.39 1.41 0l1.06-1.06zM7.05 18.36c.39-.39.39-1.03 0-1.41-.39-.39-1.03-.39-1.41 0l-1.06 1.06c-.39.39-.39 1.03 0 1.41s1.03.39 1.41 0l1.06-1.06z"/>
                          </svg>
                          早报
                        </button>
                        <button 
                          className={`type-button ${reportType === 'noon' ? 'active' : ''}`}
                          onClick={() => setReportType('noon')}
                          disabled={reportLoading}
                        >
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M3,12H7A5,5 0 0,1 12,7A5,5 0 0,1 17,12H21A1,1 0 0,1 22,13A1,1 0 0,1 21,14H3A1,1 0 0,1 2,13A1,1 0 0,1 3,12M5,16H19A1,1 0 0,1 20,17A1,1 0 0,1 19,18H5A1,1 0 0,1 4,17A1,1 0 0,1 5,16M17,20A1,1 0 0,1 18,21A1,1 0 0,1 17,22H7A1,1 0 0,1 6,21A1,1 0 0,1 7,20H17Z"/>
                          </svg>
                          午报
                        </button>
                        <button 
                          className={`type-button ${reportType === 'evening' ? 'active' : ''}`}
                          onClick={() => setReportType('evening')}
                          disabled={reportLoading}
                        >
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M17.75,4.09L15.22,6.03L16.13,9.09L13.5,7.28L10.87,9.09L11.78,6.03L9.25,4.09L12.44,4L13.5,1L14.56,4L17.75,4.09M21.25,11L19.61,12.25L20.2,14.23L18.5,13.06L16.8,14.23L17.39,12.25L15.75,11L17.81,10.95L18.5,9L19.19,10.95L21.25,11M18.97,15.95C19.8,15.87 20.69,17.05 20.16,17.8C19.84,18.25 19.5,18.67 19.08,19.07C15.17,23 8.84,23 4.94,19.07C1.03,15.17 1.03,8.83 4.94,4.93C5.34,4.53 5.76,4.17 6.21,3.85C6.96,3.32 8.14,4.21 8.06,5.04C7.79,7.9 8.75,10.87 10.95,13.06C13.14,15.26 16.1,16.22 18.97,15.95M17.33,17.97C14.5,17.81 11.7,16.64 9.53,14.5C7.36,12.31 6.2,9.5 6.04,6.68C3.23,9.82 3.34,14.64 6.35,17.66C9.37,20.67 14.19,20.78 17.33,17.97Z"/>
                          </svg>
                          晚报
                        </button>
                      </div>
                    </div>
                    <button className="generate-button" onClick={() => generateReport(reportType)} disabled={reportLoading}>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" style={{marginRight: '6px'}}>
                        <path d="M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z"/>
                      </svg>
                      生成{reportType === 'morning' ? '早' : reportType === 'noon' ? '午' : '晚'}报
                    </button>
                  </div>
                  {reportError && <div className="error-message">{reportError}</div>}
                </div>
                
                <ReportHistory onSelectReport={setCurrentReport} />
              </aside>

              {/* 中间报告内容 */}
              <main className="content-area">
                {currentReport ? (
                  <div className="report-container">
                    <div className="report-header">
                      <h2>
                        {currentReport.type === 'morning' ? (
                          <>
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style={{marginRight: '8px', verticalAlign: 'middle'}}>
                              <path d="M9,10H7V12H9V10M13,10H11V12H13V10M17,10H15V12H17V10M19,3H18V1H16V3H8V1H6V3H5C3.89,3 3,3.9 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V5A2,2 0 0,0 19,3M19,19H5V8H19V19Z"/>
                            </svg>
                            早报
                          </>
                        ) : currentReport.type === 'noon' ? (
                          <>
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style={{marginRight: '8px', verticalAlign: 'middle'}}>
                              <path d="M3,12H7A5,5 0 0,1 12,7A5,5 0 0,1 17,12H21A1,1 0 0,1 22,13A1,1 0 0,1 21,14H3A1,1 0 0,1 2,13A1,1 0 0,1 3,12M5,16H19A1,1 0 0,1 20,17A1,1 0 0,1 19,18H5A1,1 0 0,1 4,17A1,1 0 0,1 5,16M17,20A1,1 0 0,1 18,21A1,1 0 0,1 17,22H7A1,1 0 0,1 6,21A1,1 0 0,1 7,20H17Z"/>
                            </svg>
                            午报
                          </>
                        ) : (
                          <>
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style={{marginRight: '8px', verticalAlign: 'middle'}}>
                              <path d="M17.75,4.09L15.22,6.03L16.13,9.09L13.5,7.28L10.87,9.09L11.78,6.03L9.25,4.09L12.44,4L13.5,1L14.56,4L17.75,4.09M21.25,11L19.61,12.25L20.2,14.23L18.5,13.06L16.8,14.23L17.39,12.25L15.75,11L17.81,10.95L18.5,9L19.19,10.95L21.25,11M18.97,15.95C19.8,15.87 20.69,17.05 20.16,17.8C19.84,18.25 19.5,18.67 19.08,19.07C15.17,23 8.84,23 4.94,19.07C1.03,15.17 1.03,8.83 4.94,4.93C5.34,4.53 5.76,4.17 6.21,3.85C6.96,3.32 8.14,4.21 8.06,5.04C7.79,7.9 8.75,10.87 10.95,13.06C13.14,15.26 16.1,16.22 18.97,15.95M17.33,17.97C14.5,17.81 11.7,16.64 9.53,14.5C7.36,12.31 6.2,9.5 6.04,6.68C3.23,9.82 3.34,14.64 6.35,17.66C9.37,20.67 14.19,20.78 17.33,17.97Z"/>
                            </svg>
                            晚报
                          </>
                        )} - {currentReport.date}
                      </h2>
                      <span className="report-time">
                        生成时间：{new Date(currentReport.generated_at).toLocaleString()}
                      </span>
                    </div>

                    {/* 专业总结 */}
                    {currentReport.professional_summary && (
                      <div className="report-section">
                        <h3>
                          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style={{marginRight: '8px', verticalAlign: 'middle'}}>
                            <path d="M22,21H2V3H4V19H6V10H10V19H12V6H16V19H18V14H22V21Z"/>
                          </svg>
                          专业总结
                        </h3>
                        <div className="summary-content">
                          {currentReport.professional_summary.split('\n').map((line, i) => (
                            <p key={i}>{line}</p>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* V2报告内容渲染 */}
                    {currentReport.template_version === 'v2_professional' && currentReport.sections && (
                      <>
                        {/* 渲染盘前热点 */}
                        {currentReport.sections.pre_market_hotspots && (
                          <div className="report-section">
                            <h3>
                              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style={{marginRight: '8px', verticalAlign: 'middle'}}>
                                <path d="M3,13H7L10,17L13,13H17L22,6L19.5,7.5L16.5,4.5L12,9L10.5,7.5L3,14.5V13Z"/>
                              </svg>
                              盘前热点
                            </h3>
                            {currentReport.sections.pre_market_hotspots.yesterday_hot_sectors && (
                              <div className="hot-sectors">
                                <h4>昨日热门板块</h4>
                                {currentReport.sections.pre_market_hotspots.yesterday_hot_sectors.map((sector, i) => (
                                  <div key={i} className="sector-item">
                                    <h5>{sector.sector} (涨幅: {sector.sector_performance})</h5>
                                    <p className="sector-analysis">{sector.analysis}</p>
                                    <div className="leading-stocks">
                                      <span className="stock-label">领涨个股：</span>
                                      {sector.leading_stocks.map((stock, j) => (
                                        <span key={j} className="stock-chip">
                                          {stock.name}({stock.code}) {stock.change}
                                        </span>
                                      ))}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            )}

                            {currentReport.sections.pre_market_hotspots.major_events && (
                              <div className="major-events">
                                <h4>重大事件</h4>
                                {currentReport.sections.pre_market_hotspots.major_events.map((event, i) => (
                                  <div key={i} className="event-item">
                                    <h5>{event.title}</h5>
                                    {event.content && (
                                      <div className="event-content">
                                        {event.content.background && (
                                          <p><strong>背景：</strong>{event.content.background}</p>
                                        )}
                                        {event.content.current_status && (
                                          <p><strong>现状：</strong>{event.content.current_status}</p>
                                        )}
                                        {event.content.future_plans && (
                                          <div className="future-plans">
                                            <p><strong>未来规划：</strong></p>
                                            <ul>
                                              {Object.entries(event.content.future_plans).map(([year, plan]) => (
                                                <li key={year}><strong>{year}年：</strong>{plan}</li>
                                              ))}
                                            </ul>
                                          </div>
                                        )}
                                        {event.content.industry_impact && (
                                          <p><strong>行业影响：</strong>{event.content.industry_impact}</p>
                                        )}
                                        {event.content.domestic_development && (
                                          <p><strong>国内发展：</strong>{event.content.domestic_development}</p>
                                        )}
                                        {event.content.policy_background && (
                                          <p><strong>政策背景：</strong>{event.content.policy_background}</p>
                                        )}
                                        {event.content.industry_development && (
                                          <p><strong>行业发展：</strong>{event.content.industry_development}</p>
                                        )}
                                      </div>
                                    )}
                                    
                                    {event.related_stocks && (
                                      <div className="related-stocks">
                                        {event.related_stocks.main_concept && (
                                          <div className="stock-group">
                                            <span className="stock-group-label">主要概念股：</span>
                                            {event.related_stocks.main_concept.map((stock, j) => (
                                              <span key={j} className="stock-item">
                                                {stock.name}({stock.code}) - {stock.concept}
                                              </span>
                                            ))}
                                          </div>
                                        )}
                                        {event.related_stocks.extended_concept && (
                                          <div className="stock-group">
                                            <span className="stock-group-label">延伸概念股：</span>
                                            {event.related_stocks.extended_concept.map((stock, j) => (
                                              <span key={j} className="stock-item">
                                                {stock.name}({stock.code}) - {stock.concept}
                                              </span>
                                            ))}
                                          </div>
                                        )}
                                        {event.related_stocks.rwa_concept && (
                                          <div className="stock-group">
                                            <span className="stock-group-label">RWA概念：</span>
                                            {event.related_stocks.rwa_concept.map((stock, j) => (
                                              <span key={j} className="stock-item">
                                                {stock.name}({stock.code}) - {stock.concept}
                                              </span>
                                            ))}
                                          </div>
                                        )}
                                        {event.related_stocks.stablecoin_concept && (
                                          <div className="stock-group">
                                            <span className="stock-group-label">稳定币概念：</span>
                                            {event.related_stocks.stablecoin_concept.map((stock, j) => (
                                              <span key={j} className="stock-item">
                                                {stock.name}({stock.code}) - {stock.concept}
                                              </span>
                                            ))}
                                          </div>
                                        )}
                                      </div>
                                    )}
                                    
                                    {event.investment_logic && (
                                      <p className="investment-logic"><strong>投资逻辑：</strong>{event.investment_logic}</p>
                                    )}
                                    {event.risk_warning && (
                                      <p className="risk-warning"><strong>风险提示：</strong>{event.risk_warning}</p>
                                    )}
                                    {event.market_impact && (
                                      <p><strong>市场影响：</strong>{event.market_impact}</p>
                                    )}
                                  </div>
                                ))}
                              </div>
                            )}

                            {currentReport.sections.pre_market_hotspots.industry_news && (
                              <div className="industry-news">
                                <h4>行业新闻</h4>
                                {currentReport.sections.pre_market_hotspots.industry_news.map((news, i) => (
                                  <div key={i} className="news-item">
                                    <h5>{news.title}</h5>
                                    {news.content && typeof news.content === 'object' && (
                                      <div className="news-content">
                                        {Object.entries(news.content).map(([key, value]) => (
                                          <p key={key}><strong>{key}：</strong>{value}</p>
                                        ))}
                                      </div>
                                    )}
                                    {news.content && typeof news.content === 'string' && (
                                      <p>{news.content}</p>
                                    )}
                                    {news.supply_impact && (
                                      <p><strong>供给影响：</strong>{news.supply_impact}</p>
                                    )}
                                    {news.investment_logic && (
                                      <p><strong>投资逻辑：</strong>{news.investment_logic}</p>
                                    )}
                                    {news.industry_trend && (
                                      <p><strong>行业趋势：</strong>{news.industry_trend}</p>
                                    )}
                                    {news.background && (
                                      <p><strong>背景：</strong>{news.background}</p>
                                    )}
                                    {news.market_impact && (
                                      <p><strong>市场影响：</strong>{news.market_impact}</p>
                                    )}
                                  </div>
                                ))}
                              </div>
                            )}

                            {currentReport.sections.pre_market_hotspots.policy_updates && (
                              <div className="policy-updates">
                                <h4>政策动态</h4>
                                {currentReport.sections.pre_market_hotspots.policy_updates.map((policy, i) => (
                                  <div key={i} className="policy-item">
                                    <h5>{policy.title}</h5>
                                    <p className="policy-date">日期：{policy.date}</p>
                                    <p>{policy.content}</p>
                                    <p><strong>影响：</strong>{policy.impact}</p>
                                    {policy.affected_sectors && (
                                      <p><strong>影响板块：</strong>{policy.affected_sectors.join('、')}</p>
                                    )}
                                    {policy.related_stocks && (
                                      <p><strong>相关个股：</strong>{policy.related_stocks.join('、')}</p>
                                    )}
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </>
                    )}
                  </div>
                ) : (
                  <div className="empty-report">
                    <h3>请选择或生成一份报告</h3>
                    <p>点击左侧按钮查看或生成市场报告</p>
                  </div>
                )}
              </main>
            </>
          )}

          {/* 右侧今日大盘 - 桌面端固定显示，移动端模态框 */}
          <aside className={`right-sidebar ${marketOverviewOpen ? 'mobile-active' : ''}`} style={{
            border: marketOverviewOpen ? '2px solid red' : '2px solid blue'
          }}>
            {/* 移动端关闭按钮 */}
            <button className="mobile-close-button" onClick={() => setMarketOverviewOpen(false)}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                <path d="M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z"/>
              </svg>
            </button>
            <MarketOverview />
          </aside>
        </div>
      </div>
      <FloatingChat />
    </div>
  )
}