import React, { useState, useEffect } from 'react'
import MarketOverview from './components/MarketOverviewSimplified'
import ReportHistory from './components/ReportHistory'
import StockChart from './components/StockChart'
import InteractiveKLineChart from './components/InteractiveKLineChart'
import ReportRenderer from './components/ReportRenderer'
import ReportChart from './components/ReportCharts'
import DataTable from './components/DataTable'
import './App.css'
import FloatingChat from './components/FloatingChat'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'

// 动态获取API地址
const getApiUrl = (path) => {
  const hostname = window.location.hostname
  const protocol = window.location.protocol // 'http:' 或 'https:'

  // 生产环境：gp.simon-dd.life - 使用相对路径（通过Nginx代理）
  if (hostname === 'gp.simon-dd.life') {
    return path // Nginx会将请求代理到后端8001端口
  }

  // 本地开发环境，使用localhost
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return `http://localhost:8001${path}`
  }

  // 局域网访问：使用当前协议
  return `${protocol}//${hostname}:8001${path}`
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
  const [force, setForce] = useState(true)  // 默认强制刷新，获取最新数据
  // 专业版报告状态
  const [proLoading, setProLoading] = useState(false)
  const [proError, setProError] = useState('')
  const [proReport, setProReport] = useState(null)
  const [analyzeProgress, setAnalyzeProgress] = useState('')  // 新增：分析进度
  const [analyzePercent, setAnalyzePercent] = useState(0)  // 新增：进度百分比
  const [dataFetchDetails, setDataFetchDetails] = useState([])  // 新增：数据抓取详情
  const [history, setHistory] = useState(() => {
    try {
      const data = JSON.parse(localStorage.getItem('qsl_history')||'[]')
      // 验证并清理数据
      return data.filter(item => {
        try {
          // 验证必需字段存在
          if (!item.name) return false
          // 验证日期字段（如果存在）
          if (item.at && isNaN(new Date(item.at).getTime())) return false
          return true
        } catch {
          return false
        }
      })
    } catch { return [] }
  })

  // 热点概念历史记录
  const [hotspotHistory, setHotspotHistory] = useState(() => {
    try {
      const data = JSON.parse(localStorage.getItem('qsl_hotspot_history')||'[]')
      // 验证并清理数据
      return data.filter(item => {
        try {
          // 验证必需字段存在
          if (!item.keyword) return false
          // 验证日期字段（如果存在）
          if (item.at && isNaN(new Date(item.at).getTime())) return false
          return true
        } catch {
          return false
        }
      })
    } catch { return [] }
  })

  // 热点概念分析状态
  const [hotspotKeyword, setHotspotKeyword] = useState('脑机')
  const [hotspotLoading, setHotspotLoading] = useState(false)
  const [hotspotData, setHotspotData] = useState(null)
  const [hotspotError, setHotspotError] = useState('')
  const [hotspotProgress, setHotspotProgress] = useState(0)  // 进度百分比
  const [hotspotProgressMsg, setHotspotProgressMsg] = useState('')  // 进度消息
  const [trendingConcepts, setTrendingConcepts] = useState([])  // 热门概念

  // 报告系统状态
  const [currentReport, setCurrentReport] = useState(null)
  // 移除reportType状态，简化为固定的morning类型
  const [reportLoading, setReportLoading] = useState(false)
  const [reportError, setReportError] = useState('')
  const [reportProgress, setReportProgress] = useState(0)
  const [reportProgressText, setReportProgressText] = useState('')

  // 调试用：监控currentReport变化
  useEffect(() => {
    console.log('[DEBUG] currentReport状态变化:', {
      hasReport: !!currentReport,
      reportType: currentReport?.type,
      reportDate: currentReport?.date,
      hasSections: !!currentReport?.sections,
      hasSummary: !!(currentReport?.professional_summary || currentReport?.ai_summary),
      reportKeys: currentReport ? Object.keys(currentReport) : []
    })
  }, [currentReport])

  // 加载热门概念
  useEffect(() => {
    loadTrendingConcepts()
  }, [])

  const loadTrendingConcepts = async () => {
    try {
      // 添加10秒超时控制
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 10000)

      const res = await fetch(getApiUrl('/hotspot/trending'), {
        signal: controller.signal
      })
      clearTimeout(timeoutId)

      if (res.ok) {
        const data = await res.json()
        setTrendingConcepts(data.trending_concepts || [])
      }
    } catch (e) {
      // 只在非超时错误时输出错误信息
      if (e.name !== 'AbortError') {
        console.error('加载热门概念失败:', e)
      }
      // 失败不影响页面加载，静默处理
      setTrendingConcepts([])
    }
  }

  const formatProgress = (d) => {
    const s = d?.step || ''
    const p = d?.payload || {}

    // 创建详细的数据对象
    const detail = {
      step: s,
      timestamp: new Date().toLocaleTimeString(),
      data: null,
      type: 'info' // info, success, data
    }

    // 如果有进度百分比，优先使用描述
    if (p.progress_desc) {
      detail.message = p.progress_desc
      return detail
    }

    // 根据不同步骤返回详细信息
    if (s === 'resolve:start') {
      detail.message = `开始解析：${p.input || ''}`
      detail.type = 'info'
    } else if (s === 'resolve:done') {
      detail.message = `解析成功：${p.base?.name || ''}（${p.base?.ts_code || ''}）`
      detail.type = 'success'
      detail.data = { name: p.base?.name, code: p.base?.ts_code }
    } else if (s === 'fetch:parallel:start') {
      detail.message = `开始抓取数据：${p.ts_code || ''}`
      detail.type = 'info'
    } else if (s === 'fetch:parallel:done') {
      detail.message = `数据抓取完成`
      detail.type = 'data'
      detail.data = {
        prices: `价格数据 ${p.px_rows ?? 0} 条`,
        fundamental: `基本面 ${(p.fundamental_keys||[]).length} 项`,
        macro: `宏观数据 ${(p.macro_keys||[]).length} 项`
      }
    } else if (s === 'compute:technical') {
      detail.message = `技术指标计算完成`
      detail.type = 'data'
      detail.data = {
        close: `收盘价 ${p.tech_last_close ?? '-'}`,
        rsi: `RSI ${p.tech_last_rsi ?? '-'}`,
        macd: `MACD ${p.tech_last_macd ?? '-'}`,
        signal: p.tech_signal || '-'
      }
    } else if (s === 'fetch:announcements') {
      detail.message = `📢 公告获取完成：${p.count ?? 0} 条`
      detail.type = 'data'
      detail.data = { count: p.count }
    } else if (s === 'compute:news_sentiment') {
      detail.message = `📰 新闻情绪分析完成`
      detail.type = 'data'
      detail.data = {
        positive: `正面 ${p.percentages?.positive ?? 0}%`,
        neutral: `中性 ${p.percentages?.neutral ?? 0}%`,
        negative: `负面 ${p.percentages?.negative ?? 0}%`,
        overall: p.overall || '-'
      }
    } else if (s === 'compute:scorecard') {
      detail.message = `💯 综合评分计算完成`
      detail.type = 'data'
      detail.data = {
        total: `总分 ${p.score_total ?? '-'}/100`,
        fundamental: `基本面 ${p.score_fundamental ?? '-'}`,
        technical: `技术面 ${p.score_technical ?? '-'}`,
        macro: `宏观 ${p.score_macro ?? '-'}`
      }
    } else if (s === 'llm:summary:start') {
      detail.message = 'AI正在生成分析报告...'
      detail.type = 'info'
    } else if (s === 'llm:summary:done') {
      detail.message = `AI分析报告生成完成`
      detail.type = 'success'
      detail.data = { length: p.length ?? 0 }
    } else if (s === 'complete') {
      detail.message = '分析完成！'
      detail.type = 'success'
    } else {
      detail.message = s || ''
      detail.type = 'info'
    }

    return detail
  }

  const analyze = async () => {
    setProError('')
    setProLoading(true)
    setProReport(null)
    setAnalyzeProgress('')  // 清空进度
    setAnalyzePercent(0)  // 重置进度百分比
    setDataFetchDetails([])  // 清空数据抓取详情
    
    const url = getApiUrl(`/analyze/stream?name=${encodeURIComponent(name)}&force=${force}`)
    let ended = false
    let captured = null
    
    // 降级到非流式接口的函数
    const fallback = async () => {
      console.log('Fallback to HTTP API called')
      try {
        const fallbackUrl = getApiUrl(`/analyze/professional?name=${encodeURIComponent(name)}&force=${force}`)
        console.log('Fallback URL:', fallbackUrl)
        const res = await fetch(fallbackUrl)
        if (!res.ok) {
          const errorText = await res.text()
          console.log('Fallback API error:', res.status, errorText)
          throw new Error(errorText || '获取专业报告失败')
        }
        const reportData = await res.json()
        console.log('Fallback API success, data keys:', Object.keys(reportData))
        setProReport(reportData)

        // Save to history
        try {
          const item = { name, at: Date.now(), data: reportData }
          const filtered = history.filter(h => h.name !== name)
          const next = [item, ...filtered].slice(0, 50)
          setHistory(next)
          localStorage.setItem('qsl_history', JSON.stringify(next))
          console.log('Saved to history')
        } catch {}
      } catch (e) {
        console.log('Fallback failed:', e)
        setProError(String(e))
      } finally {
        setProLoading(false)
      }
    }
    
    try {
      console.log('Starting SSE connection to:', url)

      // 立即显示初始进度，避免卡顿感
      setAnalyzeProgress('🔄 正在连接服务器...')
      setAnalyzePercent(5)

      const es = new EventSource(url)

      // 处理开始事件 - 连接成功后立即更新进度
      es.addEventListener('start', (ev) => {
        try {
          setAnalyzeProgress('连接成功，开始分析...')
          setAnalyzePercent(10)
        } catch {}
      })

      // 处理进度事件
      es.addEventListener('progress', (ev) => {
        try {
          const d = JSON.parse(ev.data || '{}')
          const progressDetail = formatProgress(d)

          if (progressDetail && progressDetail.message) {
            setAnalyzeProgress(progressDetail.message)

            // 添加到数据抓取详情列表
            setDataFetchDetails(prev => {
              const newDetails = [...prev, progressDetail]
              // 最多保留最近20条记录
              return newDetails.slice(-20)
            })
          }

          // 更新进度百分比
          if (d?.payload?.progress_percent !== undefined) {
            setAnalyzePercent(d.payload.progress_percent)
          }
        } catch {}
      })
      
      // 处理结果事件
      es.addEventListener('result', (ev) => {
        try {
          const d = JSON.parse(ev.data || '{}')
          if (d && Object.keys(d).length) {
            console.log('[Debug] Received report, top keys:', Object.keys(d));
            console.log('[Debug] predictions:', d.predictions ? `exists (type: ${typeof d.predictions})` : 'missing');
            if (d.predictions) {
              console.log('[Debug] predictions keys:', Object.keys(d.predictions));
              console.log('[Debug] historical:', d.predictions.historical?.length || 0, 'items');
              console.log('[Debug] future:', d.predictions.future?.length || 0, 'items');
            }
            setProReport(d)
            captured = d

            // 收到结果后，显示100%进度并在短暂延迟后关闭loading
            setAnalyzeProgress('分析完成！')
            setAnalyzePercent(100)

            // 让用户看到100%进度，然后关闭loading状态显示报告
            setTimeout(() => {
              setProLoading(false)
            }, 500)

            // Save to history
            try {
              const item = { name, at: Date.now(), data: d }
              const filtered = history.filter(h => h.name !== name)
              const next = [item, ...filtered].slice(0, 50)
              setHistory(next)
              localStorage.setItem('qsl_history', JSON.stringify(next))
            } catch {}
          }
        } catch {}
      })
      
      // 处理错误事件
      es.addEventListener('error', (ev) => {
        console.log('SSE Error Event:', ev)
        if (!ended) {
          es.close()
          ended = true
          console.log('SSE failed, falling back to HTTP API')
          if (!captured) {
            fallback()
          } else {
            setProLoading(false)
          }
        }
      })
      
      // 处理结束事件
      es.addEventListener('end', () => {
        es.close()
        ended = true
        setProLoading(false)
      })
      
      // 超时保护
      setTimeout(() => {
        if (!ended) {
          es.close()
          ended = true
          if (!captured) {
            fallback()
          } else {
            setProLoading(false)
          }
        }
      }, 120000) // 2分钟超时
      
    } catch (e) {
      // EventSource 不支持时降级
      console.log('EventSource initialization failed:', e)
      fallback()
    }
  }

  

  const analyzeHotspot = async () => {
    setHotspotError('')
    setHotspotLoading(true)
    setHotspotData(null)
    setHotspotProgress(0)
    setHotspotProgressMsg('开始分析...')
    
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

    // 立即显示初始进度，避免卡顿感
    setHotspotProgressMsg('🔄 正在连接服务器...')
    setHotspotProgress(5)

    const es = new EventSource(url)

    // 处理开始事件 - 连接成功后立即更新进度
    es.addEventListener('start', (ev) => {
      try {
        setHotspotProgressMsg('连接成功，开始分析...')
        setHotspotProgress(10)
      } catch {}
    })

    // 处理进度事件
    es.addEventListener('progress', (ev) => {
      try {
        const d = JSON.parse(ev.data || '{}')
        if (d.progress !== undefined) {
          setHotspotProgress(d.progress)
        }
        if (d.message) {
          setHotspotProgressMsg(d.message)
        }
      } catch {}
    })

    es.addEventListener('result', (ev) => {
      try {
        const d = JSON.parse(ev.data || '{}')
        if (d && Object.keys(d).length) {
          setHotspotData(d)
          captured = d

          // 收到结果后，显示100%进度并在短暂延迟后关闭loading
          setHotspotProgressMsg('分析完成！')
          setHotspotProgress(100)

          // 让用户看到100%进度，然后关闭loading状态显示报告
          setTimeout(() => {
            setHotspotLoading(false)
          }, 500)

          // 保存到历史记录
          try {
            const item = { keyword: hotspotKeyword, at: Date.now(), data: d }
            const filtered = hotspotHistory.filter(h => h.keyword !== hotspotKeyword)
            const next = [item, ...filtered].slice(0, 50)
            setHotspotHistory(next)
            localStorage.setItem('qsl_hotspot_history', JSON.stringify(next))
          } catch {}
        }
      } catch {}
    })
    es.addEventListener('end', () => {
      ended = true
      try { es.close() } catch {}
      // 确保loading状态关闭（防御性编程，result事件已经处理了）
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
    
    try {
      const res = await fetch(getApiUrl(`/reports/${type}`))
      if (res.ok) {
        const data = await res.json()
        setCurrentReport(data.report)
        setActiveTab('reports')
      } else if (res.status === 404) {
        setReportError('暂无报告')
      } else {
        setReportError('加载报告失败')
      }
    } catch (e) {
      setReportError('网络错误')
    } finally {
      setReportLoading(false)
    }
  }

  const generateReport = async (type = 'morning') => {
    setReportLoading(true)
    setReportError('')
    setReportProgress(0)
    setReportProgressText('开始生成报告...')

    let pollInterval = null

    try {
      console.log(`开始生成${type}报告...`)

      // 第1步：创建异步任务
      const createRes = await fetch(getApiUrl(`/reports/${type}`), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      })

      if (!createRes.ok) {
        const errorData = await createRes.json().catch(() => ({}))
        throw new Error(errorData.detail || `创建任务失败(${createRes.status})`)
      }

      const createData = await createRes.json()

      if (!createData.success || !createData.task_id) {
        throw new Error('任务创建失败')
      }

      const taskId = createData.task_id
      console.log('任务已创建:', taskId)

      // 第2步：轮询任务状态
      const pollTask = async () => {
        try {
          const statusRes = await fetch(getApiUrl(`/reports/task/${taskId}`))

          if (!statusRes.ok) {
            throw new Error('查询任务状态失败')
          }

          const statusData = await statusRes.json()

          // 更新进度
          const progress = statusData.progress || 0
          setReportProgress(progress)

          // 根据进度更新文案
          if (progress < 30) {
            setReportProgressText('正在获取市场数据...')
          } else if (progress < 60) {
            setReportProgressText('分析热门板块和事件...')
          } else if (progress < 90) {
            setReportProgressText('生成AI智能总结...')
          } else {
            setReportProgressText('报告即将完成...')
          }

          console.log('任务状态:', statusData.status, '进度:', progress + '%')

          // 检查任务状态
          if (statusData.status === 'completed') {
            clearInterval(pollInterval)

            if (statusData.report) {
              setReportProgress(100)
              setReportProgressText('报告生成完成！')

              console.log('报告生成成功，准备显示')

              setTimeout(() => {
                setCurrentReport(statusData.report)
                setReportProgress(0)
                setReportProgressText('')
                setReportLoading(false)
              }, 500)
            } else {
              throw new Error('报告数据为空')
            }
          } else if (statusData.status === 'failed') {
            clearInterval(pollInterval)
            throw new Error(statusData.error || '报告生成失败')
          }
          // status === 'pending' 或 'processing' 继续轮询

        } catch (pollError) {
          console.error('轮询错误:', pollError)
          clearInterval(pollInterval)
          throw pollError
        }
      }

      // 立即执行一次，然后每2秒轮询
      await pollTask()
      pollInterval = setInterval(pollTask, 2000)

      // 设置60秒超时
      setTimeout(() => {
        if (pollInterval) {
          clearInterval(pollInterval)
          setReportError('报告生成超时，请重试')
          setReportLoading(false)
        }
      }, 60000)

    } catch (e) {
      console.error('生成报告错误:', e)
      if (pollInterval) clearInterval(pollInterval)
      setReportProgress(0)
      setReportProgressText('')
      setReportError(e.message || '生成报告失败，请重试')
      setReportLoading(false)
    }
  }
  
  const loadHistory = async (h) => {
    try {
      setProError('')
      setName(h.name)
      setSidebarOpen(false)
      if (h && h.data && Object.keys(h.data).length) {
        setProReport(h.data)
        return
      }
      // If history item has no data, re-analyze
      await analyze()
    } catch (e) {
      setProError(String(e))
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
                    <button className="search-button" onClick={analyze} disabled={proLoading}>
                      {proLoading ? <><span className="spinner"></span> 分析中...</> : '开始分析'}
                    </button>
                    {proLoading && (
                      <div className="progress-bar-container">
                        <div className="progress-bar">
                          <div 
                            className="progress-bar-fill" 
                            style={{ width: `${analyzePercent}%` }}
                          ></div>
                          <span className="progress-percent">{analyzePercent}%</span>
                        </div>
                        <div className="progress-text">{analyzeProgress || '正在生成专业报告，请稍候...'}</div>
                      </div>
                    )}
                  </div>
                  {proError && <div className="error-message">{proError}</div>}
                </div>
                
                <div className="sidebar-section">
                  <h3 className="sidebar-title"><svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/></svg> 历史记录</h3>
                  <div className="history-list">
                    {history.length > 0 ? (
                      history.slice(0, 10).map((h,i)=> (
                        <div key={i} className="history-item" onClick={()=>loadHistory(h)}>
                          <span className="history-name">{h.name}</span>
                          <span className="history-time">{(() => {
                            try {
                              return h.at ? new Date(h.at).toLocaleDateString() : '未知'
                            } catch {
                              return '未知'
                            }
                          })()}</span>
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
                    <button className="search-button" onClick={analyze} disabled={proLoading}>
                      {proLoading ? <><span className="spinner"></span> 分析中...</> : '开始分析'}
                    </button>
                  </div>
                </div>
                
                {/* 显示数据抓取进度 */}
                {proLoading && dataFetchDetails.length > 0 && (
                  <div className="data-fetch-progress">
                    <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M19,3H5C3.89,3 3,3.89 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V5C21,3.89 20.1,3 19,3M9,17H7V10H9V17M13,17H11V7H13V17M17,17H15V13H17V17Z"/>
                      </svg>
                      数据抓取进度
                    </h3>
                    <div className="fetch-details-container">
                      {dataFetchDetails.map((detail, index) => (
                        <div key={index} className={`fetch-detail-item ${detail.type}`}>
                          <span className="fetch-time">{detail.timestamp}</span>
                          <span className="fetch-message">{detail.message}</span>
                          {detail.data && (
                            <div className="fetch-data">
                              {typeof detail.data === 'object' ? (
                                Object.entries(detail.data).map(([key, value]) => (
                                  <span key={key} className="data-item">
                                    {typeof value === 'string' ? value : `${key}: ${value}`}
                                  </span>
                                ))
                              ) : (
                                <span>{detail.data}</span>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {!proReport && !proLoading && (
                  <div className="empty-analysis">
                    <h3><svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M16,6L18.29,8.29L13.41,13.17L9.41,9.17L2,16.59L3.41,18L9.41,12L13.41,16L19.71,9.71L22,12V6H16Z"/></svg> 等待分析</h3>
                    <p>请在左侧输入股票名称或代码，点击"开始分析"</p>
                  </div>
                )}

                

                

                {/* 专业版报告展示 */}
                {/* K线图表已移到ReportRenderer中,避免重复渲染 */}

                {proReport?.text && (
                  <div className="result-card llm-summary">
                    <h3 className="card-title">
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style={{marginRight: '8px', verticalAlign: 'middle'}}>
                        <path d="M4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm16-4H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-1 9H9V9h10v2z"/>
                      </svg>
                      单股专业报告
                    </h3>
                    <div className="llm-content markdown-content">
                      <ReportRenderer
                        text={proReport.text}
                        prices={proReport.technical?.prices || proReport.json?.technical?.prices}
                        predictions={proReport.predictions}
                        stockName={proReport.basic?.name || proReport.json?.basic?.name || name}
                        indicators={proReport.technical?.indicators || proReport.json?.technical?.indicators}
                      />
                    </div>
                  </div>
                )}

                {/* 专业版评分快照 */}
                {proReport?.json?.scoring && (
                  <div className="result-card">
                    <h3 className="card-title">
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style={{marginRight: '8px', verticalAlign: 'middle'}}>
                        <path d="M12 2L2 7v6c0 5 3.8 9.7 10 13 6.2-3.3 10-8 10-13V7l-10-5zM12 20.7C7.6 18.2 5 14.7 5 11.5V8.3l7-3.5 7 3.5v3.2c0 3.2-2.6 6.7-7 9.2z"/>
                      </svg>
                      专业评分（可解释）
                    </h3>
                    <div className="scores-grid">
                      <div className="score-item total"><span className="score-label">总分</span><span className="score-value">{proReport.score?.total ?? '-'}/100</span></div>
                      <div className="score-item"><span className="score-label">技术(40分)</span><span className="score-value">{proReport.score?.details?.technical ? Math.round(proReport.score.details.technical * 0.4) : '-'}/40</span></div>
                      <div className="score-item"><span className="score-label">新闻(35分)</span><span className="score-value">{proReport.score?.details?.news ? Math.round(proReport.score.details.news * 0.35) : '-'}/35</span></div>
                      <div className="score-item"><span className="score-label">基本面(20分)</span><span className="score-value">{proReport.score?.details?.fundamental ? Math.round(proReport.score.details.fundamental * 0.2) : '-'}/20</span></div>
                      <div className="score-item"><span className="score-label">市场(5分)</span><span className="score-value">{proReport.score?.details?.market ? Math.round(proReport.score.details.market * 0.05) : '-'}/5</span></div>
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
                          <div
                            className="progress-bar-fill"
                            style={{ width: `${hotspotProgress}%` }}
                          ></div>
                          <span className="progress-percent">{hotspotProgress}%</span>
                        </div>
                        <div className="progress-text">{hotspotProgressMsg || '正在分析热点，请稍候...'}</div>
                      </div>
                    )}
                  </div>
                  {hotspotError && <div className="error-message">{hotspotError}</div>}

                  {/* 热门概念快速选择 */}
                  {trendingConcepts.length > 0 && (
                    <div style={{ marginTop: '16px' }}>
                      <div style={{ color: 'var(--dark-text-secondary)', fontSize: '14px', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                          <path d="M13.5.67s.74 2.65.74 4.8c0 2.06-1.35 3.73-3.41 3.73-2.07 0-3.63-1.67-3.63-3.73l.03-.36C5.21 7.51 4 10.62 4 14c0 4.42 3.58 8 8 8s8-3.58 8-8C20 8.61 17.41 3.8 13.5.67zM11.71 19c-1.78 0-3.22-1.4-3.22-3.14 0-1.62 1.05-2.76 2.81-3.12 1.77-.36 3.6-1.21 4.62-2.58.39 1.29.59 2.65.59 4.04 0 2.65-2.15 4.8-4.8 4.8z"/>
                        </svg>
                        热门概念
                      </div>
                      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                        {trendingConcepts.slice(0, 6).map((concept, i) => (
                          <button
                            key={i}
                            className="concept-tag"
                            onClick={() => setHotspotKeyword(concept.concept)}
                            disabled={hotspotLoading}
                          >
                            {concept.concept}
                            <span style={{ marginLeft: '4px', color: '#4fc3f7', fontSize: '12px' }}>
                              {concept.heat_score}
                            </span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
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
                          <span className="history-time">{(() => {
                            try {
                              return h.at ? new Date(h.at).toLocaleDateString() : '未知'
                            } catch {
                              return '未知'
                            }
                          })()}</span>
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
                      id="hotspot-search-mobile"
                      name="hotspot-search-mobile"
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
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M13.5.67s.74 2.65.74 4.8c0 2.06-1.35 3.73-3.41 3.73-2.07 0-3.63-1.67-3.63-3.73l.03-.36C5.21 7.51 4 10.62 4 14c0 4.42 3.58 8 8 8s8-3.58 8-8C20 8.61 17.41 3.8 13.5.67zM11.71 19c-1.78 0-3.22-1.4-3.22-3.14 0-1.62 1.05-2.76 2.81-3.12 1.77-.36 3.6-1.21 4.62-2.58.39 1.29.59 2.65.59 4.04 0 2.65-2.15 4.8-4.8 4.8z"/>
                      </svg>
                      {' '}等待分析
                    </h3>
                    <p>请在左侧输入概念关键词，点击"分析热点"</p>
                  </div>
                )}

                {hotspotData && (
                  <div className="results-container hotspot-results">
                    {/* 综合评分 */}
                    {hotspotData.comprehensive_score && (
                      <div className="result-card">
                        <h3 className="card-title">
                          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style={{marginRight: '8px'}}>
                            <path d="M12 2L2 7v6c0 5 3.8 9.7 10 13 6.2-3.3 10-8 10-13V7l-10-5zM12 20.7C7.6 18.2 5 14.7 5 11.5V8.3l7-3.5 7 3.5v3.2c0 3.2-2.6 6.7-7 9.2z"/>
                          </svg>
                          综合评分
                        </h3>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '20px 0' }}>
                          <div style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: '64px', fontWeight: '700', color: '#4fc3f7' }}>
                              {hotspotData.comprehensive_score}
                            </div>
                            <div style={{ fontSize: '16px', color: 'var(--dark-text-secondary)', marginTop: '8px' }}>
                              综合评分
                            </div>
                          </div>
                          <div style={{ textAlign: 'right', color: 'var(--dark-text-secondary)' }}>
                            <div style={{ marginBottom: '8px' }}>
                              <span style={{ opacity: 0.7 }}>分析时间:</span>{' '}
                              <span style={{ color: 'var(--dark-text-primary)' }}>
                                {(() => {
                                  try {
                                    return hotspotData.analysis_time ? new Date(hotspotData.analysis_time).toLocaleString('zh-CN') : ''
                                  } catch {
                                    return '解析失败'
                                  }
                                })()}
                              </span>
                            </div>
                            <div>
                              <span style={{ opacity: 0.7 }}>概念:</span>{' '}
                              <span style={{ color: 'var(--dark-text-primary)' }}>{hotspotData.keyword}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* 投资建议 */}
                    {hotspotData.investment_advice && (
                      <div className="result-card">
                        <h3 className="card-title">
                          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style={{marginRight: '8px'}}>
                            <path d="M12,2A7,7 0 0,1 19,9C19,11.38 17.81,13.47 16,14.74V17A1,1 0 0,1 15,18H9A1,1 0 0,1 8,17V14.74C6.19,13.47 5,11.38 5,9A7,7 0 0,1 12,2M9,21A1,1 0 0,0 8,22A1,1 0 0,0 9,23H15A1,1 0 0,0 16,22A1,1 0 0,0 15,21V20H9V21Z"/>
                          </svg>
                          投资建议
                        </h3>
                        <div style={{ display: 'grid', gap: '16px' }}>
                          <div style={{ display: 'flex', gap: '12px' }}>
                            <span style={{ fontWeight: 600, color: 'var(--dark-text-secondary)', minWidth: '100px' }}>
                              推荐等级:
                            </span>
                            <span style={{
                              padding: '4px 12px',
                              borderRadius: '20px',
                              background: 'rgba(79, 195, 247, 0.2)',
                              color: '#4fc3f7',
                              fontSize: '14px',
                              fontWeight: 600
                            }}>
                              {hotspotData.investment_advice.recommendation_level}
                            </span>
                          </div>
                          <div style={{ display: 'flex', gap: '12px' }}>
                            <span style={{ fontWeight: 600, color: 'var(--dark-text-secondary)', minWidth: '100px' }}>
                              投资策略:
                            </span>
                            <span style={{ color: 'var(--dark-text-primary)' }}>
                              {hotspotData.investment_advice.investment_strategy}
                            </span>
                          </div>
                          <div style={{ display: 'flex', gap: '12px' }}>
                            <span style={{ fontWeight: 600, color: 'var(--dark-text-secondary)', minWidth: '100px' }}>
                              建议仓位:
                            </span>
                            <span style={{ color: 'var(--dark-text-primary)' }}>
                              {hotspotData.investment_advice.suggested_allocation}
                            </span>
                          </div>
                          <div style={{ display: 'flex', gap: '12px' }}>
                            <span style={{ fontWeight: 600, color: 'var(--dark-text-secondary)', minWidth: '100px' }}>
                              持有周期:
                            </span>
                            <span style={{ color: 'var(--dark-text-primary)' }}>
                              {hotspotData.investment_advice.time_horizon}
                            </span>
                          </div>
                          {hotspotData.investment_advice.key_risks && hotspotData.investment_advice.key_risks.length > 0 && (
                            <div style={{
                              padding: '16px',
                              background: 'rgba(251, 191, 36, 0.1)',
                              border: '1px solid rgba(251, 191, 36, 0.3)',
                              borderRadius: '8px'
                            }}>
                              <div style={{ fontWeight: 600, color: 'var(--dark-text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                                  <path d="M13,14H11V10H13M13,18H11V16H13M1,21H23L12,2L1,21Z"/>
                                </svg>
                                关键风险:
                              </div>
                              <ul style={{ margin: '8px 0 0 0', paddingLeft: '20px', color: 'var(--dark-text-secondary)' }}>
                                {hotspotData.investment_advice.key_risks.map((risk, i) => (
                                  <li key={i}>{risk}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {hotspotData?.llm_summary && hotspotData.llm_summary !== '系统缺失' && (
                      <div className="result-card llm-summary">
                        <h3 className="card-title">
                          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style={{marginRight: '8px', verticalAlign: 'middle'}}>
                            <path d="M12,2A2,2 0 0,1 14,4C14,4.74 13.6,5.39 13,5.73V7H14A7,7 0 0,1 21,14H22A1,1 0 0,1 23,15V18A1,1 0 0,1 22,19H21V20A2,2 0 0,1 19,22H5A2,2 0 0,1 3,20V19H2A1,1 0 0,1 1,18V15A1,1 0 0,1 2,14H3A7,7 0 0,1 10,7H11V5.73C10.4,5.39 10,4.74 10,4A2,2 0 0,1 12,2M7.5,13A2.5,2.5 0 0,0 5,15.5A2.5,2.5 0 0,0 7.5,18A2.5,2.5 0 0,0 10,15.5A2.5,2.5 0 0,0 7.5,13M16.5,13A2.5,2.5 0 0,0 14,15.5A2.5,2.5 0 0,0 16.5,18A2.5,2.5 0 0,0 19,15.5A2.5,2.5 0 0,0 16.5,13Z"/>
                          </svg>
                          QSL-AI 热点分析
                        </h3>
                        <div className="llm-content markdown-content">
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            rehypePlugins={[rehypeRaw]}
                          >
                            {hotspotData.llm_summary}
                          </ReactMarkdown>
                        </div>
                      </div>
                    )}

                    {/* 相关个股 - 兼容新旧数据结构 */}
                    {((hotspotData.stocks && hotspotData.stocks.length > 0) ||
                      (hotspotData.basic_analysis?.stocks && hotspotData.basic_analysis.stocks.length > 0)) && (
                      <div className="result-card">
                        <h3 className="card-title">
                          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style={{marginRight: '8px', verticalAlign: 'middle'}}>
                            <path d="M3,13H7L10,17L13,13H17L22,6L19.5,7.5L16.5,4.5L12,9L10.5,7.5L3,14.5V13Z"/>
                          </svg>
                          相关股票排名 ({(hotspotData.stocks || hotspotData.basic_analysis?.stocks || []).length})
                        </h3>
                        <div className="stocks-table-container">
                          {/* 桌面端表格 */}
                          <table className="hotspot-table">
                            <thead>
                              <tr>
                                <th>排名</th>
                                <th>股票</th>
                                <th>代码</th>
                                <th>行业</th>
                                <th>相关度</th>
                                <th>综合分</th>
                                <th>涨跌幅</th>
                              </tr>
                            </thead>
                            <tbody>
                              {(hotspotData.stocks || hotspotData.basic_analysis?.stocks || []).map((stock, i) => (
                                <tr key={i}>
                                  <td>{i + 1}</td>
                                  <td className="stock-name">{stock?.name || '-'}</td>
                                  <td>{stock?.ts_code || stock?.code || '-'}</td>
                                  <td>{stock?.industry || '-'}</td>
                                  <td>{stock?.relevance_score || '-'}</td>
                                  <td className="final-score">{stock?.final_score?.toFixed(1) || stock?.final_score || '-'}</td>
                                  <td className={stock?.price_change_pct > 0 ? 'up' : stock?.price_change_pct < 0 ? 'down' : ''}>
                                    {stock?.price_change_pct !== null && stock?.price_change_pct !== undefined ?
                                      `${stock.price_change_pct > 0 ? '+' : ''}${stock.price_change_pct.toFixed(2)}%` : '-'}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>

                          {/* 移动端卡片列表 */}
                          <div className="mobile-stock-cards">
                            {(hotspotData.stocks || hotspotData.basic_analysis?.stocks || []).map((stock, i) => (
                              <div key={i} className="mobile-stock-card">
                                <span className="stock-rank">#{i + 1}</span>
                                <div className="stock-info">
                                  <span className="stock-name">{stock?.name || '-'}</span>
                                  <span className={`stock-change ${stock?.price_change_pct > 0 ? 'up' : stock?.price_change_pct < 0 ? 'down' : ''}`}>
                                    {stock?.price_change_pct !== null && stock?.price_change_pct !== undefined ?
                                      `${stock.price_change_pct > 0 ? '+' : ''}${stock.price_change_pct.toFixed(2)}%` : '-'}
                                  </span>
                                </div>
                                <div className="stock-scores">
                                  <span className="score-item">{stock?.ts_code || stock?.code || '-'}</span>
                                  <span className="score-item">{stock?.industry || '-'}</span>
                                  <span className="score-item">相关度: {stock?.relevance_score || '-'}</span>
                                  <span className="score-item" style={{fontWeight: 'bold'}}>综合: {stock?.final_score?.toFixed(1) || stock?.final_score || '-'}</span>
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
                  <div className="report-generate">
                    <button className="generate-button" onClick={() => generateReport('morning')} disabled={reportLoading}>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" style={{marginRight: '6px'}}>
                        <path d="M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z"/>
                      </svg>
                      生成市场报告
                    </button>
                  </div>

                  {/* 进度条组件 */}
                  {reportLoading && reportProgress > 0 && (
                    <div className="report-progress-container">
                      <div className="progress-text-header">{reportProgressText}</div>
                      <div className="progress-bar-container">
                        <div className="progress-bar">
                          <div
                            className="progress-bar-fill"
                            style={{width: `${reportProgress}%`}}
                          ></div>
                        </div>
                        <div className="progress-percentage">{reportProgress}%</div>
                      </div>
                    </div>
                  )}

                  {reportError && <div className="error-message">{reportError}</div>}
                </div>
                
                <ReportHistory onSelectReport={setCurrentReport} />
              </aside>

              {/* 中间报告内容 */}
              <main className="content-area">
                {/* DEBUG信息 */}
                {console.log('[DEBUG] 渲染报告区域, currentReport:', currentReport ? '存在' : 'null')}
                {currentReport ? (
                  <div className="report-container">{console.log('[DEBUG] 渲染报告容器')}
                    <div className="report-header">
                      <h2>
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor" style={{marginRight: '8px', verticalAlign: 'middle'}}>
                          <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/>
                        </svg>
                        市场报告 - {currentReport.date}
                      </h2>
                      <span className="report-time">
                        生成时间：{(() => {
                          if (!currentReport?.generated_at) return '未知'
                          try {
                            return new Date(currentReport.generated_at).toLocaleString('zh-CN', {
                              year: 'numeric',
                              month: '2-digit',
                              day: '2-digit',
                              hour: '2-digit',
                              minute: '2-digit',
                              second: '2-digit'
                            })
                          } catch (e) {
                            console.error('Date parsing error:', e)
                            return '日期格式错误'
                          }
                        })()}
                      </span>
                    </div>

                    {/* 专业总结 */}
                    {(currentReport.professional_summary || currentReport.ai_summary) && (
                      <div className="report-section">
                        <h3>
                          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style={{marginRight: '8px', verticalAlign: 'middle'}}>
                            <path d="M22,21H2V3H4V19H6V10H10V19H12V6H16V19H18V14H22V21Z"/>
                          </svg>
                          {currentReport.type === 'comprehensive_market' ? 'AI智能分析' : '专业总结'}
                        </h3>
                        <div className="summary-content">
                          {(currentReport.professional_summary || currentReport.ai_summary || '').split('\n').map((line, i) => (
                            <p key={i}>{line}</p>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* V2报告内容渲染 */}
                    {currentReport.template_version === 'v2_professional' && currentReport.sections && (
                      <>
                        {/* 数据可视化图表 */}
                        {currentReport.charts && Object.keys(currentReport.charts).length > 0 && (
                          <div className="report-section">
                            <h3>
                              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style={{marginRight: '8px', verticalAlign: 'middle'}}>
                                <path d="M3,3H5V13H9V7H13V11H17V15H21V21H3V3Z"/>
                              </svg>
                              数据可视化
                            </h3>
                            <div className="charts-grid" style={{
                              display: 'grid',
                              gridTemplateColumns: 'repeat(auto-fit, minmax(500px, 1fr))',
                              gap: '1.5rem',
                              marginTop: '1rem'
                            }}>
                              {Object.entries(currentReport.charts).map(([key, config]) => (
                                <div key={key} className="chart-container" style={{
                                  backgroundColor: '#1a1d29',
                                  borderRadius: '8px',
                                  padding: '1rem',
                                  boxShadow: '0 2px 8px rgba(0,0,0,0.2)'
                                }}>
                                  <ReportChart chartConfig={config} />
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

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
                                <DataTable
                                  columns={[
                                    {
                                      title: '板块名称',
                                      key: 'sector',
                                      className: 'sector-tag',
                                      render: (val) => <span className="sector-tag">{val}</span>
                                    },
                                    {
                                      title: '涨跌幅',
                                      key: 'sector_performance',
                                      align: 'center',
                                      render: (val) => {
                                        const isUp = val && val.toString().startsWith('+')
                                        const isDown = val && val.toString().startsWith('-')
                                        return (
                                          <span className={isUp ? 'price-up' : isDown ? 'price-down' : ''}>
                                            {val || '-'}
                                          </span>
                                        )
                                      }
                                    },
                                    {
                                      title: '领涨个股',
                                      key: 'leading_stocks',
                                      render: (stocks) => (
                                        <div style={{display: 'flex', flexWrap: 'wrap', gap: '0.25rem'}}>
                                          {stocks && stocks.length > 0 ? stocks.map((s, idx) => (
                                            <span key={idx} className="stock-chip" style={{fontSize: '0.75rem', padding: '0.25rem 0.5rem'}}>
                                              {s.name}({s.code}) {s.change}
                                            </span>
                                          )) : '-'}
                                        </div>
                                      )
                                    },
                                    {
                                      title: '分析',
                                      key: 'analysis',
                                      render: (val) => (
                                        <div style={{maxWidth: '400px', whiteSpace: 'normal', lineHeight: '1.5'}}>
                                          {val || '-'}
                                        </div>
                                      )
                                    }
                                  ]}
                                  data={currentReport.sections.pre_market_hotspots.yesterday_hot_sectors}
                                  striped={true}
                                  hoverable={true}
                                />

                                {/* 保留原有的卡片式展示作为备选 */}
                                <div className="hot-sectors-cards" style={{display: 'none'}}>
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
                    <svg width="64" height="64" viewBox="0 0 24 24" fill="currentColor" style={{opacity: 0.3, marginBottom: '16px'}}>
                      <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/>
                    </svg>
                    <h3>暂无报告</h3>
                    <p>点击左侧"生成市场报告"按钮生成新报告</p>
                    <p style={{fontSize: '12px', color: '#8b93a7', marginTop: '8px'}}>或从历史记录中选择已生成的报告</p>
                  </div>
                )}
              </main>
            </>
          )}

          {/* 右侧今日大盘 - 桌面端固定显示，移动端模态框 */}
          <aside className={`right-sidebar ${marketOverviewOpen ? 'mobile-active' : ''}`}>
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
      {/* 移动端底部导航 */}
      <nav className="bottom-nav" aria-label="主导航">
        <button
          className={`bottom-nav-item ${activeTab === 'stock' ? 'active' : ''}`}
          onClick={() => setActiveTab('stock')}
          aria-label="个股分析"
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M3 3v18h18v-2H5V3H3zm4 14h2v-6H7v6zm4 0h2V9h-2v8zm4 0h2v-4h-2v4z"/></svg>
          <span>个股</span>
        </button>
        <button
          className={`bottom-nav-item ${activeTab === 'hotspot' ? 'active' : ''}`}
          onClick={() => setActiveTab('hotspot')}
          aria-label="热点概念"
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M13.5.67s.74 2.65.74 4.8c0 2.06-1.35 3.73-3.41 3.73-2.07 0-3.63-1.67-3.63-3.73l.03-.36C5.21 7.51 4 10.62 4 14c0 4.42 3.58 8 8 8s8-3.58 8-8C20 8.61 17.41 3.8 13.5.67zM11.71 19c-1.78 0-3.22-1.4-3.22-3.14 0-1.62 1.05-2.76 2.81-3.12 1.77-.36 3.6-1.21 4.62-2.58.39 1.29.28 2.97-.2 4.18-.72 1.83-2.33 3.04-4.01 3.66z"/></svg>
          <span>热点</span>
        </button>
        <button
          className={`bottom-nav-item ${activeTab === 'reports' ? 'active' : ''}`}
          onClick={() => setActiveTab('reports')}
          aria-label="市场报告"
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm16-4H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-1 9H9V9h10v2zm-4 4H9v-2h6v2zm4-8H9V5h10v2z"/></svg>
          <span>报告</span>
        </button>
      </nav>
      <FloatingChat />
    </div>
  )
}
// Force reload
