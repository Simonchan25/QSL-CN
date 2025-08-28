import React, { useState, useEffect } from 'react'

// 动态获取API地址
const getApiUrl = (path) => {
  // 如果是本地开发环境，使用localhost
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return `http://localhost:8001${path}`
  }
  // 否则使用当前访问的主机地址
  return `http://${window.location.hostname}:8001${path}`
}

export default function MarketOverview({ className = '' }) {
  const [market, setMarket] = useState(null)
  const [enhancedAnalysis, setEnhancedAnalysis] = useState(null)
  const [fearGreedIndex, setFearGreedIndex] = useState(null)
  const [marketAlerts, setMarketAlerts] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadMarketData()
    const interval = setInterval(loadMarketData, 60000) // 每分钟刷新
    return () => clearInterval(interval)
  }, [])

  const loadMarketData = async () => {
    try {
      const res = await fetch(getApiUrl('/market'))
      if (res.ok) {
        const data = await res.json()
        setMarket(data)
        
        // 加载增强版分析
        loadEnhancedAnalysis()
        
        // 加载恐慌贪婪指数
        loadFearGreedIndex()
        
        // 加载市场预警
        loadMarketAlerts()
      }
    } catch (e) {
      console.error('Failed to load market data:', e)
    }
  }
  
  const loadEnhancedAnalysis = async () => {
    try {
      const res = await fetch(getApiUrl('/market/enhanced-analysis'))
      if (res.ok) {
        const data = await res.json()
        setEnhancedAnalysis(data.insight_report)
      }
    } catch (e) {
      console.error('Failed to load enhanced analysis:', e)
    }
  }
  
  const loadFearGreedIndex = async () => {
    try {
      const res = await fetch(getApiUrl('/market/fear-greed-index'))
      if (res.ok) {
        const data = await res.json()
        setFearGreedIndex(data.fear_greed_index)
      }
    } catch (e) {
      console.error('Failed to load fear greed index:', e)
    }
  }
  
  const loadMarketAlerts = async () => {
    try {
      const res = await fetch(getApiUrl('/market/alerts'))
      if (res.ok) {
        const data = await res.json()
        setMarketAlerts(data.alerts || [])
      }
    } catch (e) {
      console.error('Failed to load market alerts:', e)
    }
  }

  console.log('MarketOverview market data:', market)
  
  if (!market) {
    return <div className={`market-overview ${className}`}>加载中...</div>
  }

  return (
    <div className={`market-overview ${className}`}>
      {/* 1. 今日大盘 */}
      <div className="market-section">
        <h4 className="section-title">今日大盘</h4>
        <div className="indices-grid">
          {market.indices && market.indices.slice(0, 3).map((idx, i) => {
            console.log('Index item:', idx)
            return (
              <div key={i} className="index-item">
                <span className="index-name">{idx.name || '未知指数'}</span>
                <span className={`index-value ${idx.pct_chg > 0 ? 'up' : idx.pct_chg < 0 ? 'down' : 'neutral'}`}>
                  {idx.close || 'N/A'}
                </span>
                <span className={`index-change ${idx.pct_chg > 0 ? 'up' : idx.pct_chg < 0 ? 'down' : 'neutral'}`}>
                  {idx.pct_chg ? `${idx.pct_chg > 0 ? '+' : ''}${idx.pct_chg.toFixed(2)}%` : 'N/A'}
                </span>
              </div>
            )
          })}
        </div>
      </div>

      {/* 2. 市场情绪 */}
      <div className="market-section">
        <h4 className="section-title">市场情绪</h4>
        <div className="sentiment-grid">
          <div className="sentiment-item">
            <span className="sentiment-label">涨跌家数</span>
            <span className="sentiment-value">
              {market.market_breadth?.up_count || 0}↑ / {market.market_breadth?.down_count || 0}↓
            </span>
          </div>
          {market.capital_flow && (
            <div className="sentiment-item">
              <span className="sentiment-label">北向资金</span>
              <span className={`sentiment-value ${market.capital_flow.hsgt_net_amount > 0 ? 'up' : 'down'}`}>
                {market.capital_flow.hsgt_net_amount > 0 ? '净流入' : '净流出'} {Math.abs(market.capital_flow.hsgt_net_amount).toFixed(1)}亿
              </span>
            </div>
          )}
        </div>
      </div>

      {/* 3. 恐慌贪婪指数 */}
      {fearGreedIndex && (
        <div className="market-section fear-greed-section">
          <h4 className="section-title">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style={{marginRight: '4px', verticalAlign: 'middle'}}>
              <path d="M12,2A2,2 0 0,1 14,4V5.5L15.5,7H17A2,2 0 0,1 19,9V10A2,2 0 0,1 17,12H15L13.5,13.5V19A2,2 0 0,1 11,21H9A2,2 0 0,1 7,19V13.5L5.5,12H4A2,2 0 0,1 2,10V9A2,2 0 0,1 4,7H5.5L7,5.5V4A2,2 0 0,1 9,2H12M12,4H9V6L7,8H4V10H7L9,12V19H11V12L13,10H17V8H13L12,6V4Z"/>
            </svg>
            情绪指数
          </h4>
          <div className="fear-greed-display">
            <div className="fear-greed-score">
              <span className={`score-value ${fearGreedIndex.level}`}>{fearGreedIndex.score}</span>
              <span className="score-level">{fearGreedIndex.level}</span>
            </div>
            <div className="fear-greed-interpretation">
              {fearGreedIndex.interpretation}
            </div>
          </div>
        </div>
      )}
      
      {/* 4. 智能预警 */}
      {marketAlerts && marketAlerts.length > 0 && (
        <div className="market-section alerts-section">
          <h4 className="section-title">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style={{marginRight: '4px', verticalAlign: 'middle'}}>
              <path d="M13,14H11V10H13M13,18H11V16H13M1,21H23L12,2L1,21Z"/>
            </svg>
            智能预警 ({marketAlerts.length})
          </h4>
          <div className="alerts-container">
            {marketAlerts.slice(0, 2).map((alert, index) => (
              <div key={index} className={`alert-item alert-${alert.level}`}>
                <div className="alert-message">{alert.message}</div>
                {alert.action && (
                  <div className="alert-action">建议: {alert.action}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* 5. QSL-AI智能解读 */}
      {enhancedAnalysis && enhancedAnalysis.intelligent_narrative && (
        <div className="market-section enhanced-narrative-section">
          <h4 className="section-title">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style={{marginRight: '4px', verticalAlign: 'middle'}}>
              <path d="M9,2V8H7V2H9M17,2V8H15V2H17M3,10H5V22H3V10M7,18H9V22H7V18M15,18H17V22H15V18M19,10H21V22H19V10M8,10H16L15,12H13L12,14L11,12H9L8,10Z"/>
            </svg>
            QSL-AI 智能解读
          </h4>
          <div className="intelligent-narrative">
            <div 
              className="narrative-content" 
              dangerouslySetInnerHTML={{
                __html: enhancedAnalysis.intelligent_narrative.replace(/\n/g, '<br/>')
              }}
            />
          </div>
        </div>
      )}

      {/* 6. 操作建议（精简版） */}
      {enhancedAnalysis && enhancedAnalysis.summary && enhancedAnalysis.summary.operation_advice && (
        <div className="market-section advice-section">
          <h4 className="section-title">💡 操作建议</h4>
          <div className="advice-list">
            {enhancedAnalysis.summary.operation_advice.slice(0, 2).map((advice, index) => (
              <div key={index} className="advice-item">{advice}</div>
            ))}
          </div>
        </div>
      )}

      {/* Shibor利率 */}
      {market.shibor && (
        <div className="market-section">
          <h4 className="section-title">SHIBOR</h4>
          <div className="shibor-items">
            <span className="shibor-item">隔夜: {market.shibor.on || 'N/A'}</span>
            <span className="shibor-item">1周: {market.shibor['1w'] || 'N/A'}</span>
          </div>
        </div>
      )}
    </div>
  )
}