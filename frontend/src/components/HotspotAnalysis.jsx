import React, { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import API_BASE_URL from '../config/api'

// 动态获取API地址
const getApiUrl = (path) => {
  return `${API_BASE_URL}${path}`
}

export default function HotspotAnalysis() {
  const [keyword, setKeyword] = useState('AI')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [data, setData] = useState(null)
  const [progress, setProgress] = useState(0)
  const [progressMsg, setProgressMsg] = useState('')
  const [trendingConcepts, setTrendingConcepts] = useState([])

  // 加载热门概念
  useEffect(() => {
    loadTrendingConcepts()
  }, [])

  const loadTrendingConcepts = async () => {
    try {
      const res = await fetch(getApiUrl('/hotspot/trending'))
      if (res.ok) {
        const data = await res.json()
        setTrendingConcepts(data.trending_concepts || [])
      }
    } catch (e) {
      console.error('加载热门概念失败:', e)
    }
  }

  const analyzeHotspot = async () => {
    if (!keyword.trim()) {
      setError('请输入概念关键词')
      return
    }

    setLoading(true)
    setError('')
    setData(null)
    setProgress(0)
    setProgressMsg('初始化分析...')

    try {
      const url = getApiUrl(`/hotspot/stream?keyword=${encodeURIComponent(keyword.trim())}&force=false`)
      const eventSource = new EventSource(url)

      eventSource.addEventListener('start', (e) => {
        const data = JSON.parse(e.data)
        setProgressMsg(`开始分析概念: ${data.keyword}`)
      })

      eventSource.addEventListener('progress', (e) => {
        const data = JSON.parse(e.data)
        if (data.progress !== undefined) {
          setProgress(data.progress)
        }
        if (data.message) {
          setProgressMsg(data.message)
        }
      })

      eventSource.addEventListener('result', (e) => {
        const result = JSON.parse(e.data)
        if (result && Object.keys(result).length > 0) {
          setData(result)
          setProgressMsg('分析完成')
        }
      })

      eventSource.addEventListener('error', (e) => {
        const data = JSON.parse(e.data)
        setError(data.message || '分析失败')
        setLoading(false)
        eventSource.close()
      })

      eventSource.addEventListener('end', () => {
        setLoading(false)
        setProgress(100)
        eventSource.close()
      })

      eventSource.onerror = () => {
        setError('连接失败，请重试')
        setLoading(false)
        eventSource.close()
      }

    } catch (e) {
      setError(e.message || '分析失败')
      setLoading(false)
    }
  }

  return (
    <div style={{ width: '100%', maxWidth: '100%', padding: '0' }}>
      {/* 搜索区域 - 使用与个股分析相同的样式 */}
      <div className="sidebar-section" style={{ marginBottom: '24px' }}>
        <h3 className="sidebar-title">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
            <path d="M13.5.67s.74 2.65.74 4.8c0 2.06-1.35 3.73-3.41 3.73-2.07 0-3.63-1.67-3.63-3.73l.03-.36C5.21 7.51 4 10.62 4 14c0 4.42 3.58 8 8 8s8-3.58 8-8C20 8.61 17.41 3.8 13.5.67zM11.71 19c-1.78 0-3.22-1.4-3.22-3.14 0-1.62 1.05-2.76 2.81-3.12 1.77-.36 3.6-1.21 4.62-2.58.39 1.29.59 2.65.59 4.04 0 2.65-2.15 4.8-4.8 4.8z"/>
          </svg>
          热点概念分析
        </h3>
        <p style={{ color: 'var(--dark-text-secondary)', fontSize: '14px', marginBottom: '16px' }}>
          专业级多维度热点概念深度分析
        </p>

        <div className="search-box">
          <input
            type="text"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder="输入概念关键词，如：AI、新能源、半导体..."
            onKeyDown={(e) => e.key === 'Enter' && !loading && analyzeHotspot()}
            disabled={loading}
          />
          <button
            className="search-button"
            onClick={analyzeHotspot}
            disabled={loading || !keyword.trim()}
          >
            {loading ? <><span className="spinner"></span> 分析中...</> : '开始分析'}
          </button>

          {/* 进度条 */}
          {loading && (
            <div className="progress-bar-container">
              <div className="progress-bar">
                <div
                  className="progress-bar-fill"
                  style={{ width: `${progress}%` }}
                ></div>
                <span className="progress-percent">{progress}%</span>
              </div>
              <div className="progress-text">{progressMsg}</div>
            </div>
          )}
        </div>

        {/* 热门概念快速选择 */}
        {trendingConcepts.length > 0 && (
          <div style={{ marginTop: '16px' }}>
            <span style={{ color: 'var(--dark-text-secondary)', fontSize: '14px', marginRight: '12px' }}>
              热门概念:
            </span>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '8px' }}>
              {trendingConcepts.map((concept, i) => (
                <button
                  key={i}
                  style={{
                    padding: '6px 12px',
                    background: 'var(--dark-bg-secondary)',
                    border: '1px solid var(--dark-border)',
                    borderRadius: '20px',
                    color: 'var(--dark-text-secondary)',
                    cursor: 'pointer',
                    fontSize: '13px',
                    transition: 'all 0.2s'
                  }}
                  onClick={() => setKeyword(concept.concept)}
                  disabled={loading}
                  onMouseEnter={(e) => {
                    e.target.style.background = 'var(--dark-bg-hover)'
                    e.target.style.borderColor = 'var(--dark-border-hover)'
                  }}
                  onMouseLeave={(e) => {
                    e.target.style.background = 'var(--dark-bg-secondary)'
                    e.target.style.borderColor = 'var(--dark-border)'
                  }}
                >
                  {concept.concept}
                  <span style={{ marginLeft: '8px', color: '#4fc3f7', fontWeight: '600' }}>{concept.heat_score}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {error && <div className="error-message">{error}</div>}
      </div>

      {/* 分析结果 - 使用result-card样式 */}
      {data && (
        <div>
          {/* 综合评分 */}
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
                  {data.comprehensive_score}
                </div>
                <div style={{ fontSize: '16px', color: 'var(--dark-text-secondary)', marginTop: '8px' }}>
                  综合评分
                </div>
              </div>
              <div style={{ textAlign: 'right', color: 'var(--dark-text-secondary)' }}>
                <div style={{ marginBottom: '8px' }}>
                  <span style={{ opacity: 0.7 }}>分析时间:</span>{' '}
                  <span style={{ color: 'var(--dark-text-primary)' }}>
                    {data.analysis_time ? new Date(data.analysis_time).toLocaleString('zh-CN') : ''}
                  </span>
                </div>
                <div>
                  <span style={{ opacity: 0.7 }}>概念:</span>{' '}
                  <span style={{ color: 'var(--dark-text-primary)' }}>{data.keyword}</span>
                </div>
              </div>
            </div>
          </div>

          {/* 投资建议 */}
          {data.investment_advice && (
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
                    {data.investment_advice.recommendation_level}
                  </span>
                </div>
                <div style={{ display: 'flex', gap: '12px' }}>
                  <span style={{ fontWeight: 600, color: 'var(--dark-text-secondary)', minWidth: '100px' }}>
                    投资策略:
                  </span>
                  <span style={{ color: 'var(--dark-text-primary)' }}>
                    {data.investment_advice.investment_strategy}
                  </span>
                </div>
                <div style={{ display: 'flex', gap: '12px' }}>
                  <span style={{ fontWeight: 600, color: 'var(--dark-text-secondary)', minWidth: '100px' }}>
                    建议仓位:
                  </span>
                  <span style={{ color: 'var(--dark-text-primary)' }}>
                    {data.investment_advice.suggested_allocation}
                  </span>
                </div>
                <div style={{ display: 'flex', gap: '12px' }}>
                  <span style={{ fontWeight: 600, color: 'var(--dark-text-secondary)', minWidth: '100px' }}>
                    持有周期:
                  </span>
                  <span style={{ color: 'var(--dark-text-primary)' }}>
                    {data.investment_advice.time_horizon}
                  </span>
                </div>
                {data.investment_advice.key_risks && data.investment_advice.key_risks.length > 0 && (
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
                      {data.investment_advice.key_risks.map((risk, i) => (
                        <li key={i}>{risk}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* LLM总结 */}
          {data.llm_summary && (
            <div className="result-card llm-summary">
              <h3 className="card-title">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style={{marginRight: '8px'}}>
                  <path d="M4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm16-4H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-1 9H9V9h10v2z"/>
                </svg>
                AI智能总结
              </h3>
              <div className="llm-content markdown-content">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {data.llm_summary}
                </ReactMarkdown>
              </div>
            </div>
          )}

          {/* 相关个股 */}
          {data.basic_analysis && data.basic_analysis.stocks && (
            <div className="result-card">
              <h3 className="card-title">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style={{marginRight: '8px'}}>
                  <path d="M19,3H5C3.89,3 3,3.89 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V5C21,3.89 20.1,3 19,3M9,17H7V10H9V17M13,17H11V7H13V17M17,17H15V13H17V17Z"/>
                </svg>
                相关个股 ({data.basic_analysis.stocks.length})
              </h3>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr>
                      <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid var(--dark-border)', background: 'var(--dark-bg-secondary)', fontWeight: 600, color: 'var(--dark-text-primary)' }}>股票名称</th>
                      <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid var(--dark-border)', background: 'var(--dark-bg-secondary)', fontWeight: 600, color: 'var(--dark-text-primary)' }}>代码</th>
                      <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid var(--dark-border)', background: 'var(--dark-bg-secondary)', fontWeight: 600, color: 'var(--dark-text-primary)' }}>行业</th>
                      <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid var(--dark-border)', background: 'var(--dark-bg-secondary)', fontWeight: 600, color: 'var(--dark-text-primary)' }}>相关度</th>
                      <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid var(--dark-border)', background: 'var(--dark-bg-secondary)', fontWeight: 600, color: 'var(--dark-text-primary)' }}>综合评分</th>
                      <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid var(--dark-border)', background: 'var(--dark-bg-secondary)', fontWeight: 600, color: 'var(--dark-text-primary)' }}>涨跌幅</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.basic_analysis.stocks.map((stock, i) => (
                      <tr key={i} style={{ transition: 'background 0.2s' }}
                        onMouseEnter={(e) => e.currentTarget.style.background = 'var(--dark-bg-hover)'}
                        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                      >
                        <td style={{ padding: '12px', borderBottom: '1px solid var(--dark-border)', color: 'var(--dark-text-secondary)' }}>{stock.name}</td>
                        <td style={{ padding: '12px', borderBottom: '1px solid var(--dark-border)', color: 'var(--dark-text-secondary)' }}>{stock.ts_code}</td>
                        <td style={{ padding: '12px', borderBottom: '1px solid var(--dark-border)', color: 'var(--dark-text-secondary)' }}>{stock.industry}</td>
                        <td style={{ padding: '12px', borderBottom: '1px solid var(--dark-border)', color: 'var(--dark-text-secondary)' }}>{stock.relevance_score}</td>
                        <td style={{ padding: '12px', borderBottom: '1px solid var(--dark-border)', fontWeight: 600, color: '#4fc3f7' }}>{stock.final_score?.toFixed(1)}</td>
                        <td style={{
                          padding: '12px',
                          borderBottom: '1px solid var(--dark-border)',
                          color: stock.price_change_pct > 0 ? '#f87171' : stock.price_change_pct < 0 ? '#4ade80' : 'var(--dark-text-muted)'
                        }}>
                          {stock.price_change_pct !== null ? `${stock.price_change_pct > 0 ? '+' : ''}${stock.price_change_pct.toFixed(2)}%` : 'N/A'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
