import React from 'react'
import { useState, useEffect } from 'react'

export default function App() {
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
  
  // 热点概念分析状态
  const [hotspotKeyword, setHotspotKeyword] = useState('脑机')
  const [hotspotLoading, setHotspotLoading] = useState(false)
  const [hotspotData, setHotspotData] = useState(null)
  const [hotspotError, setHotspotError] = useState('')
  const [showHotspot, setShowHotspot] = useState(false)

  // 报告系统状态
  const [showReports, setShowReports] = useState(false)
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

    const logs = new EventSource('http://localhost:8001/logs/stream')
    logs.addEventListener('log', (ev) => {
      try { const d = JSON.parse(ev.data || '{}'); if (d.line) setLogLines(ls => [...ls, d.line].slice(-300)) } catch {}
    })
    logs.addEventListener('error', () => { try { logs.close() } catch {} })

    const url = `http://localhost:8001/analyze/stream?name=${encodeURIComponent(name)}&force=${force}`
    const maxRetry = 3
    const retryDelay = 800
    let ended = false
    let captured = null

    const fallbackOnce = async () => {
      setProgress(p => [...p, '[warn] SSE 失败，改用一次性请求'])
      try {
        const res = await fetch('http://localhost:8001/analyze', {
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

  const [market, setMarket] = useState(null)
  useEffect(()=>{ (async()=>{
    try { const r = await fetch('http://localhost:8001/market'); if(r.ok){ setMarket(await r.json()) } } catch {}
  })() }, [])

  const analyzeHotspot = async () => {
    setHotspotError('')
    setHotspotLoading(true)
    setHotspotData(null)
    setShowHotspot(true)
    
    const url = `http://localhost:8001/hotspot/stream?keyword=${encodeURIComponent(hotspotKeyword)}&force=${force}`
    let ended = false
    let captured = null
    
    const fallback = async () => {
      try {
        const res = await fetch('http://localhost:8001/hotspot', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ keyword: hotspotKeyword, force })
        })
        if (!res.ok) throw new Error(await res.text())
        const j = await res.json()
        setHotspotData(j)
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
      const res = await fetch(`http://localhost:8001/reports/${type}`)
      if (res.ok) {
        const report = await res.json()
        setCurrentReport(report)
        setShowReports(true)
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
      const res = await fetch(`http://localhost:8001/reports/${type}/generate`, {
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
      if (h && h.data && Object.keys(h.data).length) {
        setData(h.data)
        return
      }
      setLoading(true)
      const res = await fetch('http://localhost:8001/analyze', {
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

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="header-content">
          <div className="logo-section">
            <img src="/logo.svg" alt="logo" className="logo-svg" />
            <div>
              <h1 className="app-title">QSL-A股分析助手</h1>
              <p className="app-subtitle">智能股票分析与决策支持系统</p>
            </div>
          </div>
          <div className="header-stats">
            <div className="stat-item">
              <span className="stat-label">历史查询</span>
              <span className="stat-value">{history.length}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">当前状态</span>
              <span className="stat-value">{loading ? '分析中' : '就绪'}</span>
            </div>
          </div>
        </div>
      </header>

      <div className="app-body">
        <aside className="sidebar">
          <div className="sidebar-section">
            <h3 className="sidebar-title">🔍 个股分析</h3>
            <div className="search-box">
              <input 
                type="text" 
                value={name} 
                onChange={e=>setName(e.target.value)} 
                placeholder="股票名称/代码" 
                onKeyDown={(e) => e.key === 'Enter' && !loading && analyze()}
              />
              <div className="search-options">
                <label className="checkbox-label">
                  <input type="checkbox" checked={force} onChange={e=>setForce(e.target.checked)} />
                  <span>强制刷新数据</span>
        </label>
              </div>
              <button className="search-button" onClick={analyze} disabled={loading}>
                {loading ? <><span className="spinner"></span> 分析中...</> : '开始分析'}
              </button>
            </div>
            {error && <div className="error-message">{error}</div>}
          </div>
          
          <div className="sidebar-section">
            <h3 className="sidebar-title">🔥 热点概念</h3>
            <div className="search-box">
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
            {hotspotError && <div className="error-message">{hotspotError}</div>}
          </div>

          <div className="sidebar-section">
            <h3 className="sidebar-title">📰 市场报告</h3>
            <div className="report-buttons">
              <button className="report-button morning" onClick={() => loadReport('morning')} disabled={reportLoading}>
                {reportLoading && reportType === 'morning' ? <span className="spinner"></span> : '📅'} 早报
              </button>
              <button className="report-button noon" onClick={() => loadReport('noon')} disabled={reportLoading}>
                {reportLoading && reportType === 'noon' ? <span className="spinner"></span> : '🌅'} 午报
              </button>
              <button className="report-button evening" onClick={() => loadReport('evening')} disabled={reportLoading}>
                {reportLoading && reportType === 'evening' ? <span className="spinner"></span> : '🌆'} 晚报
              </button>
            </div>
            <div className="report-generate">
              <select value={reportType} onChange={e => setReportType(e.target.value)} disabled={reportLoading}>
                <option value="morning">早报</option>
                <option value="noon">午报</option>
                <option value="evening">晚报</option>
              </select>
              <button className="generate-button" onClick={() => generateReport(reportType)} disabled={reportLoading}>
                生成报告
              </button>
            </div>
            {reportError && <div className="error-message">{reportError}</div>}
          </div>
          
          <div className="sidebar-section">
            <h3 className="sidebar-title">📝 历史记录</h3>
            <div className="history-list">
              {history.length > 0 ? (
                history.map((h,i)=> (
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

          <div className="sidebar-section market-overview">
            <h3 className="sidebar-title">📈 今日大盘</h3>
            {market && market.indices ? (
              <>
                {/* 市场情绪指标 */}
                <div className="market-sentiment">
                  <div className="sentiment-indicator">
                    {(() => {
                      const validIndices = (market.indices || []).filter(it => it.pct_chg !== null && it.pct_chg !== undefined)
                      if (validIndices.length === 0) {
                        return (
                          <>
                            <span className="sentiment-label">市场情绪</span>
                            <span className="sentiment-value neutral">数据获取中</span>
                          </>
                        )
                      }
                      const avgPct = validIndices.reduce((sum, it) => sum + it.pct_chg, 0) / validIndices.length
                      const sentiment = avgPct > 1 ? '强势' : avgPct > 0 ? '偏强' : avgPct > -1 ? '偏弱' : '弱势'
                      const sentimentClass = avgPct > 1 ? 'strong' : avgPct > 0 ? 'positive' : avgPct > -1 ? 'weak' : 'negative'
                      return (
                        <>
                          <span className="sentiment-label">市场情绪</span>
                          <span className={`sentiment-value ${sentimentClass}`}>{sentiment}</span>
                        </>
                      )
                    })()}
                  </div>
                </div>
                
                {/* 指数列表 */}
                <div className="market-content">
                  {(market.indices||[]).map((it,i)=>{
                    const pct = it.pct_chg
                    const cls = pct>0? 'up' : pct<0? 'down' : 'neutral'
                    const name = it.ts_code==="000001.SH"? '上证综指': it.ts_code==="399001.SZ"? '深证成指': it.ts_code==="399006.SZ"? '创业板指': it.ts_code==="000300.SH"? '沪深300': it.ts_code==="000016.SH"? '上证50' : it.ts_code
                    return (
                      <div key={i} className={`index-item ${cls}`}>
                        <div className="index-left">
                          <span className="index-name">{name}</span>
                          <span className="index-close">{it.close !== null && it.close !== undefined ? it.close.toFixed(2) : 'N/A'}</span>
                        </div>
                        <span className="index-value">
                          {pct === null || pct === undefined ? 'N/A' : (pct > 0 ? '+' : '') + pct.toFixed(2) + '%'}
                        </span>
                      </div>
                    )
                  })}
                </div>
                
                {/* Shibor */}
                {market.shibor && (
                  <div className="shibor-section">
                    <div className="shibor-title">Shibor利率</div>
                    <div className="shibor-content">
                      <div className="shibor-item">
                        <span>隔夜</span>
                        <span>{market.shibor.on !== null && market.shibor.on !== undefined ? market.shibor.on : 'N/A'}</span>
                      </div>
                      <div className="shibor-item">
                        <span>1周</span>
                        <span>{market.shibor['1w'] !== null && market.shibor['1w'] !== undefined ? market.shibor['1w'] : 'N/A'}</span>
                      </div>
                    </div>
                  </div>
                )}
                
                {/* 重大新闻 */}
                {market.major_news && market.major_news.length > 0 && (
                  <div className="news-section">
                    <div className="news-title">重大新闻</div>
                    <div className="news-list">
                      {market.major_news.slice(0, 5).map((news, i) => (
                        <div key={i} className="news-item">{news}</div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="loading-state">
                <div className="error-state">
                  <span>数据获取失败</span>
                  <span className="error-hint">可能是API权限未开通或网络问题</span>
                </div>
              </div>
            )}
          </div>
        </aside>

        <main className="main-content">
          {/* 默认占位卡片 */}
          {!data && !loading && (
            <div className="placeholder-container">
              <div className="placeholder-card">
                <h3 className="card-title">📋 基本信息</h3>
                <div className="placeholder-content">
                  <div className="placeholder-text">等待开始分析...</div>
                  <div className="placeholder-hint">输入股票名称或代码开始分析</div>
                </div>
              </div>
              
              <div className="placeholder-card">
                <h3 className="card-title">📊 技术分析</h3>
                <div className="placeholder-content">
                  <div className="placeholder-text">等待开始分析...</div>
                  <div className="placeholder-hint">将展示RSI、MACD等技术指标</div>
                </div>
      </div>

              <div className="placeholder-card">
                <h3 className="card-title">🤖 AI 智能分析</h3>
                <div className="placeholder-content">
                  <div className="placeholder-text">等待开始分析...</div>
                  <div className="placeholder-hint">AI将为您提供专业的投资建议</div>
                </div>
              </div>
              
              <div className="placeholder-card">
                <h3 className="card-title">📈 综合评分</h3>
                <div className="placeholder-content">
                  <div className="placeholder-text">等待开始分析...</div>
                  <div className="placeholder-hint">多维度综合评估股票价值</div>
                </div>
              </div>
            </div>
          )}
          
          {showTerminal && (
            <div className="terminal-card">
              <div className="terminal-header">
                <span className="terminal-title">🖥️ 实时分析进度</span>
                <button className="terminal-close" onClick={() => setShowTerminal(false)}>×</button>
              </div>
              <div className="terminal-body">
                {progress.map((ln, i)=> (
                  <div key={i} className="terminal-line progress-line">
                    <span className="line-prefix">▶</span>{ln}
                  </div>
                ))}
                {logLines.slice(-10).map((ln, i)=> (
                  <div key={i} className="terminal-line log-line">{ln}</div>
                ))}
              </div>
            </div>
          )}

          {showHotspot && hotspotData && (
            <div className="results-container hotspot-results">
              <div className="result-card hotspot-header">
                <h3 className="card-title">🔥 热点概念：{hotspotData.keyword}</h3>
                <div className="hotspot-stats">
                  <span>相关股票：{hotspotData.stock_count || 0}只</span>
                  <span>分析数量：{hotspotData.analyzed_count || 0}只</span>
                  <span>相关新闻：{hotspotData.news?.news_count || 0}条</span>
                </div>
              </div>
              
              {hotspotData.news_sentiment && (
                <div className="result-card sentiment-card">
                  <h3 className="card-title">📊 市场情绪</h3>
                  <div className="sentiment-grid">
                    <div className={`sentiment-item ${hotspotData.news_sentiment.overall}`}>
                      <span className="sentiment-label">整体情绪</span>
                      <span className="sentiment-value">{hotspotData.news_sentiment.overall === 'positive' ? '正面' : hotspotData.news_sentiment.overall === 'negative' ? '负面' : '中性'}</span>
                    </div>
                    <div className="sentiment-item">
                      <span className="sentiment-label">正面占比</span>
                      <span className="sentiment-value">{hotspotData.news_sentiment.percentages?.positive || 0}%</span>
                    </div>
                    <div className="sentiment-item">
                      <span className="sentiment-label">负面占比</span>
                      <span className="sentiment-value">{hotspotData.news_sentiment.percentages?.negative || 0}%</span>
                    </div>
                  </div>
                </div>
              )}
              
              {hotspotData.stocks && hotspotData.stocks.length > 0 && (
                <div className="result-card stocks-table">
                  <h3 className="card-title">📈 相关股票排名</h3>
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
                      {hotspotData.stocks.map((stock, i) => (
                        <tr key={i}>
                          <td>{i + 1}</td>
                          <td className="stock-name">{stock.name}</td>
                          <td>{stock.industry}</td>
                          <td>{stock.relevance_score}</td>
                          <td>{stock.tech_score}</td>
                          <td>{stock.fund_score}</td>
                          <td className="final-score">{stock.final_score}</td>
                          <td className={stock.price_change_pct > 0 ? 'up' : stock.price_change_pct < 0 ? 'down' : ''}>
                            {stock.price_change_pct ? `${stock.price_change_pct > 0 ? '+' : ''}${stock.price_change_pct}%` : '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              
              {hotspotData.industry_distribution && Object.keys(hotspotData.industry_distribution).length > 0 && (
                <div className="result-card industry-dist">
                  <h3 className="card-title">🏭 行业分布</h3>
                  <div className="industry-grid">
                    {Object.entries(hotspotData.industry_distribution).slice(0, 8).map(([industry, count], i) => (
                      <div key={i} className="industry-item">
                        <span className="industry-name">{industry}</span>
                        <span className="industry-count">{count}家</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {hotspotData.llm_summary && (
                <div className="result-card llm-summary">
                  <h3 className="card-title">🤖 AI 热点分析</h3>
                  <div className="llm-content">
                    <div className="llm-text">{hotspotData.llm_summary}</div>
                  </div>
                </div>
              )}
              
              {hotspotData.news?.news_list && hotspotData.news.news_list.length > 0 && (
                <div className="result-card news-list">
                  <h3 className="card-title">📰 相关新闻</h3>
                  <div className="news-items">
                    {hotspotData.news.news_list.slice(0, 10).map((news, i) => (
                      <div key={i} className="news-item">
                        <span className="news-source">[{news.source}]</span>
                        <span className="news-title">{news.title}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* 报告显示区域 */}
          {showReports && currentReport && (
            <div className="results-container report-results">
              <div className="result-card report-header">
                <h3 className="card-title">
                  📰 {currentReport.type === 'morning' ? '早报' : currentReport.type === 'noon' ? '午报' : '晚报'} - {currentReport.date}
                </h3>
                <div className="report-meta">
                  <span>生成时间：{new Date(currentReport.generated_at).toLocaleString()}</span>
                  <button className="close-report" onClick={() => setShowReports(false)}>×</button>
                </div>
              </div>

              {/* AI总结/专业总结 */}
              {(currentReport.ai_summary || currentReport.professional_summary) && (
                <div className="result-card ai-summary">
                  <h3 className="card-title">🤖 AI智能解读</h3>
                  <div className="summary-content">
                    {(currentReport.professional_summary || currentReport.ai_summary).split('\n').map((line, i) => (
                      <p key={i}>{line}</p>
                    ))}
                  </div>
                </div>
              )}

              {/* V2专业报告格式 - 根据报告类型显示不同内容 */}
              {currentReport.template_version === 'v2_professional' && currentReport.sections && (
                <>
                  {/* 早报内容 - 盘前热点事件 */}
                  {currentReport.sections.pre_market_hotspots && (
                    <>
                      {/* 昨日热点板块 */}
                      {currentReport.sections.pre_market_hotspots.yesterday_hot_sectors && (
                    <div className="result-card hot-sectors-v2">
                      <h3 className="card-title">📈 昨日热点板块</h3>
                      <div className="sectors-grid">
                        {currentReport.sections.pre_market_hotspots.yesterday_hot_sectors.map((sector, i) => (
                          <div key={i} className="sector-card">
                            <div className="sector-header">
                              <span className="sector-name">{sector.sector}</span>
                              <span className={`sector-performance ${sector.sector_performance?.startsWith('+') ? 'positive' : 'negative'}`}>
                                {sector.sector_performance}
                              </span>
                            </div>
                            <div className="sector-analysis">{sector.analysis}</div>
                            <div className="leading-stocks">
                              <h5>龙头股票：</h5>
                              {sector.leading_stocks?.map((stock, j) => (
                                <div key={j} className="stock-item-v2">
                                  <span className="stock-name">{stock.name}</span>
                                  <span className="stock-code">({stock.code})</span>
                                  <span className={`stock-change ${stock.change?.startsWith('+') ? 'positive' : 'negative'}`}>
                                    {stock.change}
                                  </span>
                                  <span className="volume-ratio">量比{stock.volume_ratio}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 重大事件 */}
                  {currentReport.sections.pre_market_hotspots.major_events && (
                    <div className="result-card major-events-v2">
                      <h3 className="card-title">📰 重大事件</h3>
                      {currentReport.sections.pre_market_hotspots.major_events.map((event, i) => (
                        <div key={i} className="event-card">
                          <h4 className="event-title">{event.title}</h4>
                          <div className="event-content">
                            {event.content && typeof event.content === 'object' && (
                              <>
                                {event.content.background && (
                                  <div className="event-section">
                                    <strong>背景：</strong>
                                    <p>{event.content.background}</p>
                                  </div>
                                )}
                                {event.content.current_status && (
                                  <div className="event-section">
                                    <strong>现状：</strong>
                                    <p>{event.content.current_status}</p>
                                  </div>
                                )}
                                {event.content.policy_background && (
                                  <div className="event-section">
                                    <strong>政策背景：</strong>
                                    <p>{event.content.policy_background}</p>
                                  </div>
                                )}
                                {event.content.industry_development && (
                                  <div className="event-section">
                                    <strong>产业发展：</strong>
                                    <p>{event.content.industry_development}</p>
                                  </div>
                                )}
                                {event.content.future_plans && (
                                  <div className="event-section">
                                    <strong>未来规划：</strong>
                                    {Object.entries(event.content.future_plans).map(([year, plan]) => (
                                      <div key={year} className="future-plan">
                                        <strong>{year}年：</strong>{plan}
                                      </div>
                                    ))}
                                  </div>
                                )}
                                {event.content.industry_impact && (
                                  <div className="event-section">
                                    <strong>产业影响：</strong>
                                    <p>{event.content.industry_impact}</p>
                                  </div>
                                )}
                                {event.content.domestic_development && (
                                  <div className="event-section">
                                    <strong>国内发展：</strong>
                                    <p>{event.content.domestic_development}</p>
                                  </div>
                                )}
                              </>
                            )}
                          </div>
                          
                          {/* 相关股票 */}
                          {event.related_stocks && (
                            <div className="related-stocks">
                              <h5>📊 相关股票</h5>
                              {Object.entries(event.related_stocks).map(([category, stocks]) => (
                                <div key={category} className="stock-category">
                                  <h6>{
                                    category === 'main_concept' ? '主要概念股：' :
                                    category === 'extended_concept' ? '扩展概念股：' :
                                    category === 'rwa_concept' ? 'RWA概念股：' :
                                    category === 'stablecoin_concept' ? '稳定币概念股：' :
                                    category === 'bse_stablecoin' ? '北交所稳定币：' :
                                    category.replace(/_/g, ' ') + '：'
                                  }</h6>
                                  {Array.isArray(stocks) && (
                                    <div className="stocks-list-v2">
                                      {stocks.map((stock, j) => (
                                        <div key={j} className="stock-tag">
                                          <span className="stock-name">{stock.name}</span>
                                          <span className="stock-code">({stock.code})</span>
                                          {stock.concept && <span className="stock-concept">{stock.concept}</span>}
                                        </div>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          )}
                          
                          {/* 投资逻辑和风险提示 */}
                          <div className="investment-analysis">
                            {event.investment_logic && (
                              <div className="logic-section">
                                <strong>💡 投资逻辑：</strong>
                                <p>{event.investment_logic}</p>
                              </div>
                            )}
                            {event.risk_warning && (
                              <div className="risk-section">
                                <strong>⚠️ 风险提示：</strong>
                                <p>{event.risk_warning}</p>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* 行业要闻 */}
                  {currentReport.sections.pre_market_hotspots.industry_news && (
                    <div className="result-card industry-news-v2">
                      <h3 className="card-title">🏭 行业要闻</h3>
                      {currentReport.sections.pre_market_hotspots.industry_news.map((news, i) => (
                        <div key={i} className="news-card-v2">
                          <h4 className="news-title">{news.title}</h4>
                          <div className="news-content">
                            {typeof news.content === 'object' ? (
                              Object.entries(news.content).map(([key, value]) => (
                                <div key={key} className="news-detail">
                                  <strong>{key}：</strong>
                                  <p>{value}</p>
                                </div>
                              ))
                            ) : (
                              news.content
                            )}
                          </div>
                          <div className="news-impact">
                            <strong>市场影响：</strong>{news.supply_impact || news.market_impact}
                          </div>
                          <div className="news-logic">
                            <strong>投资逻辑：</strong>{news.investment_logic}
                          </div>
                          {news.related_stocks && (
                            <div className="news-stocks">
                              <strong>相关股票：</strong>
                              {Object.entries(news.related_stocks).map(([category, stocks]) => (
                                <div key={category} className="stock-category-inline">
                                  <span className="category-name">{category}：</span>
                                  {stocks.map((stock, j) => (
                                    <span key={j} className="stock-tag-inline">
                                      {stock.name}({stock.code})
                                    </span>
                                  ))}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                    </>
                  )}

                  {/* 外围市场 */}
                  {currentReport.sections.overseas_markets && (
                    <div className="result-card overseas-markets-v2">
                      <h3 className="card-title">🌍 外围市场</h3>
                      {currentReport.sections.overseas_markets.us_markets && (
                        <div className="market-section">
                          <h4>🇺🇸 美股市场</h4>
                          <p className="market-overview">{currentReport.sections.overseas_markets.us_markets.overview}</p>
                          <div className="indices-grid-v2">
                            {Object.entries(currentReport.sections.overseas_markets.us_markets.indices || {}).map(([key, index]) => (
                              <div key={key} className="index-item-v2">
                                <span className="index-name">{key.toUpperCase()}</span>
                                <span className="index-close">{index.close}</span>
                                <span className={`index-change ${index.pct_change >= 0 ? 'positive' : 'negative'}`}>
                                  {index.pct_change >= 0 ? '+' : ''}{index.pct_change}%
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* 公告精选 */}
                  {currentReport.sections.announcement_highlights && (
                    <div className="result-card announcements-v2">
                      <h3 className="card-title">📢 公告精选</h3>
                      {currentReport.sections.announcement_highlights.performance_forecasts && (
                        <div className="announcement-section">
                          <h4>📊 业绩预告</h4>
                          {currentReport.sections.announcement_highlights.performance_forecasts.map((forecast, i) => (
                            <div key={i} className="forecast-item">
                              <div className="forecast-header">
                                <span className="company-name">{forecast.company}</span>
                                <span className="forecast-type">{forecast.forecast_type}</span>
                              </div>
                              <div className="forecast-details">
                                <span>净利润：{forecast.net_profit_range}</span>
                                <span>增长：{forecast.growth_range}</span>
                              </div>
                              <div className="forecast-reasons">
                                <strong>主要原因：</strong>
                                <ul>
                                  {forecast.main_reasons?.map((reason, j) => (
                                    <li key={j}>{reason}</li>
                                  ))}
                                </ul>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* 午报内容 */}
                  {currentReport.sections.morning_summary && (
                    <div className="result-card morning-summary-v2">
                      <h3 className="card-title">📊 上午市场总结</h3>
                      <div className="summary-grid">
                        <div className="summary-item">
                          <strong>指数表现：</strong>
                          {currentReport.sections.morning_summary.indices_performance && Object.entries(currentReport.sections.morning_summary.indices_performance).map(([key, index]) => (
                            <div key={key} className="index-row">
                              <span>{key === 'shanghai' ? '上证' : key === 'shenzhen' ? '深证' : '创业板'}</span>
                              <span className={index.change >= 0 ? 'positive' : 'negative'}>
                                {index.change >= 0 ? '+' : ''}{index.change}%
                              </span>
                            </div>
                          ))}
                        </div>
                        <div className="summary-item">
                          <strong>成交额：</strong>{currentReport.sections.morning_summary.turnover?.total_turnover}亿元
                        </div>
                        <div className="summary-item">
                          <strong>涨跌比：</strong>{currentReport.sections.morning_summary.advance_decline_ratio?.ratio}
                        </div>
                        <div className="summary-item">
                          <strong>市场情绪：</strong>{currentReport.sections.morning_summary.market_sentiment}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* 晚报内容 - 市场总结 */}
                  {currentReport.sections.market_summary && (
                    <div className="result-card market-summary-v2">
                      <h3 className="card-title">📈 全日市场总结</h3>
                      <div className="daily-performance">
                        {currentReport.sections.market_summary.daily_performance && Object.entries(currentReport.sections.market_summary.daily_performance).map(([key, index]) => (
                          <div key={key} className="index-card">
                            <span className="index-name">{key === 'shanghai' ? '上证指数' : key === 'shenzhen' ? '深证成指' : '创业板指'}</span>
                            <span className="index-close">{index.close}</span>
                            <span className={`index-change ${index.change >= 0 ? 'positive' : 'negative'}`}>
                              {index.change >= 0 ? '+' : ''}{index.change}%
                            </span>
                            <span className="index-volume">成交{index.volume}亿</span>
                          </div>
                        ))}
                      </div>
                      <p>{currentReport.sections.market_summary.market_characteristics}</p>
                      <p>{currentReport.sections.market_summary.volume_analysis}</p>
                    </div>
                  )}

                  {/* 板块复盘 */}
                  {currentReport.sections.sector_review && (
                    <div className="result-card sector-review-v2">
                      <h3 className="card-title">📊 板块复盘</h3>
                      <div className="sector-lists">
                        <div className="top-sectors">
                          <h4>领涨板块</h4>
                          {currentReport.sections.sector_review.top_sectors?.map((sector, i) => (
                            <div key={i} className="sector-item">
                              <span>{sector.sector}</span>
                              <span className="positive">+{sector.change}%</span>
                              <span className="leader">龙头：{sector.leading_stock}</span>
                            </div>
                          ))}
                        </div>
                        {currentReport.sections.sector_review.weak_sectors && (
                          <div className="weak-sectors">
                            <h4>弱势板块</h4>
                            {currentReport.sections.sector_review.weak_sectors.map((sector, i) => (
                              <div key={i} className="sector-item">
                                <span>{sector.sector}</span>
                                <span className="negative">{sector.change}%</span>
                                <span className="reason">{sector.reason}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </>
              )}

              {/* 市场概况 */}
              {currentReport.sections?.market_overview && (
                <div className="result-card market-overview">
                  <h3 className="card-title">📈 市场概况</h3>
                  {currentReport.sections.market_overview.indices && (
                    <div className="indices-grid">
                      {currentReport.sections.market_overview.indices.map((index, i) => (
                        <div key={i} className="index-item">
                          <span className="index-name">{index.name}</span>
                          <span className="index-price">{index.close}</span>
                          <span className={`index-change ${index.pct_chg >= 0 ? 'positive' : 'negative'}`}>
                            {index.pct_chg >= 0 ? '+' : ''}{index.pct_chg}%
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                  <div className="market-sentiment">
                    <span>市场情绪：{currentReport.sections.market_overview.market_sentiment || '中性'}</span>
                  </div>
                </div>
              )}

              {/* 热点概念 */}
              {currentReport.sections?.hot_concepts && (
                <div className="result-card hot-concepts">
                  <h3 className="card-title">🔥 热点概念</h3>
                  <div className="concepts-grid">
                    {currentReport.sections.hot_concepts.slice(0, 6).map((concept, i) => (
                      <div key={i} className="concept-item">
                        <span className="concept-name">{concept.name}</span>
                        <span className="concept-stocks">{concept.stock_count}只</span>
                        <span className={`concept-change ${concept.avg_change >= 0 ? 'positive' : 'negative'}`}>
                          {concept.avg_change >= 0 ? '+' : ''}{concept.avg_change?.toFixed(1)}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 重点关注股票 */}
              {currentReport.sections?.focus_stocks && (
                <div className="result-card focus-stocks">
                  <h3 className="card-title">⭐ 重点关注</h3>
                  <div className="stocks-list">
                    {currentReport.sections.focus_stocks.map((stock, i) => (
                      <div key={i} className="stock-item">
                        <span className="stock-code">{stock.code}</span>
                        <span className="stock-name">{stock.name}</span>
                        <span className="stock-reason">{stock.reason}</span>
                        {stock.pct_chg !== undefined && (
                          <span className={`stock-change ${stock.pct_chg >= 0 ? 'positive' : 'negative'}`}>
                            {stock.pct_chg >= 0 ? '+' : ''}{stock.pct_chg}%
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 宏观数据 */}
              {currentReport.sections?.macro_data && (
                <div className="result-card macro-data">
                  <h3 className="card-title">📊 宏观数据</h3>
                  <div className="macro-grid">
                    {currentReport.sections.macro_data.cpi && (
                      <div className="macro-item">
                        <span className="macro-label">CPI</span>
                        <span className="macro-value">{currentReport.sections.macro_data.cpi.cpi_yoy}%</span>
                      </div>
                    )}
                    {currentReport.sections.macro_data.pmi && (
                      <div className="macro-item">
                        <span className="macro-label">PMI</span>
                        <span className="macro-value">{currentReport.sections.macro_data.pmi.pmi}</span>
                      </div>
                    )}
                    {currentReport.sections.macro_data.m2 && (
                      <div className="macro-item">
                        <span className="macro-label">M2增速</span>
                        <span className="macro-value">{currentReport.sections.macro_data.m2.m2_yoy}%</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* 今日看点/风险提示 */}
              {(currentReport.sections?.today_highlights || currentReport.sections?.risk_alerts) && (
                <div className="result-card highlights-risks">
                  {currentReport.sections.today_highlights && (
                    <div className="highlights">
                      <h4>📍 今日看点</h4>
                      <ul>
                        {currentReport.sections.today_highlights.map((item, i) => (
                          <li key={i}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {currentReport.sections.risk_alerts && (
                    <div className="risks">
                      <h4>⚠️ 风险提示</h4>
                      <ul>
                        {currentReport.sections.risk_alerts.map((item, i) => (
                          <li key={i}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
          
          {data && (
            <div className="results-container">
              <div className="result-card basic-info">
                <h3 className="card-title">📋 基本信息</h3>
                <div className="info-grid">
                  <div className="info-item">
                    <span className="info-label">股票名称</span>
                    <span className="info-value">{data.basic?.name || '-'}</span>
                  </div>
                  <div className="info-item">
                    <span className="info-label">股票代码</span>
                    <span className="info-value">{data.basic?.ts_code || data.basic?.symbol || '-'}</span>
                  </div>
                  <div className="info-item">
                    <span className="info-label">上市市场</span>
                    <span className="info-value">{data.basic?.market || '-'}</span>
                  </div>
                  <div className="info-item">
                    <span className="info-label">上市状态</span>
                    <span className="info-value">{data.basic?.list_status || '-'}</span>
                  </div>
                </div>
              </div>

              <div className="result-card technical-info">
                <h3 className="card-title">📊 技术分析</h3>
                <div className="tech-grid">
                  <div className="tech-item">
                    <span className="tech-label">最新收盘</span>
                    <span className="tech-value large">{data.technical?.tech_last_close ?? '-'}</span>
                  </div>
                  <div className="tech-item">
                    <span className="tech-label">RSI(14)</span>
                    <span className="tech-value">{data.technical?.tech_last_rsi ?? '-'}</span>
                  </div>
                  <div className="tech-item">
                    <span className="tech-label">MACD</span>
                    <span className="tech-value">{data.technical?.tech_last_macd ?? '-'}</span>
                  </div>
                  <div className="tech-item">
                    <span className="tech-label">DIF/DEA</span>
                    <span className="tech-value">{(data.technical?.tech_last_dif ?? '-') + ' / ' + (data.technical?.tech_last_dea ?? '-')}</span>
                  </div>
                </div>
                <div className="signal-badge">
                  <span className="signal-label">交易信号</span>
                  <span className={`signal-value ${data.technical?.tech_signal?.toLowerCase()}`}>
                    {data.technical?.tech_signal || '中性'}
                  </span>
                </div>
              </div>

              <div className="result-card llm-summary">
                <h3 className="card-title">🤖 AI 智能分析</h3>
                <div className="llm-content">
                  <div className="llm-text">{data.llm_summary || '暂无AI分析'}</div>
                </div>
              </div>

              <div className="result-card scorecard">
                <h3 className="card-title">📈 综合评分</h3>
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
                  <div className="score-item">
                    <span className="score-label">情绪</span>
                    <span className="score-value">{data.scorecard?.score_sentiment ?? '-'}</span>
                  </div>
                  <div className="score-item">
                    <span className="score-label">宏观</span>
                    <span className="score-value">{data.scorecard?.score_macro ?? '-'}</span>
                  </div>
                </div>
              </div>

              <div className="result-card news-section">
                <h3 className="card-title">📰 新闻资讯</h3>
                <div className="news-stats">
                  <div className="stat">快讯: {data.news?.summary?.flash_news_count ?? 0}</div>
                  <div className="stat">重大: {data.news?.summary?.major_news_count ?? 0}</div>
                  <div className="stat">联播: {data.news?.summary?.cctv_news_count ?? 0}</div>
                  <div className="stat">个股: {data.news?.summary?.stock_news_count ?? 0}</div>
                </div>
                {data.news?.stock_news && data.news.stock_news.length > 0 && (
                  <div className="news-list">
                    {data.news.stock_news.slice(0, 5).map((item, i) => (
                      <div key={i} className="news-item">{item.title}</div>
                    ))}
                  </div>
                )}
              </div>

              {data.announcements && data.announcements.length > 0 && (
                <div className="result-card announcements">
                  <h3 className="card-title">📢 最新公告</h3>
                  <div className="announcement-list">
                    {data.announcements.slice(0, 5).map((ann, i) => (
                      <div key={i} className="announcement-item">
                        <span className="ann-date">{ann.ann_date}</span>
                        <span className="ann-title">{ann.title}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {data.fundamental && Object.keys(data.fundamental).length > 0 && (
                <div className="result-card fundamental">
                  <h3 className="card-title">💼 基本面数据</h3>
                  <div className="json-viewer">
                    <pre>{JSON.stringify(data.fundamental, null, 2)}</pre>
                  </div>
                </div>
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  )
}