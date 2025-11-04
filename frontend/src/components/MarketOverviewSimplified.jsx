import React, { useState, useEffect } from 'react'
import API_BASE_URL from '../config/api'

// 动态获取API地址
const getApiUrl = (path) => {
  return `${API_BASE_URL}${path}`
}

export default function MarketOverview({ className = '' }) {
  const [market, setMarket] = useState(null)
  const [enhancedAnalysis, setEnhancedAnalysis] = useState(null)
  const [fearGreedIndex, setFearGreedIndex] = useState(null)
  const [marketAlerts, setMarketAlerts] = useState([])
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)

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
        
        // 从市场数据中提取预警信息
        if (data.alerts && data.alerts.length > 0) {
          setMarketAlerts(data.alerts)
        } else {
          // 如果主API没有预警数据，尝试单独加载
          loadMarketAlerts()
        }
        
        // 加载增强版分析
        loadEnhancedAnalysis()
        
        // 加载恐慌贪婪指数
        loadFearGreedIndex()
      }
    } catch (e) {
      console.error('Failed to load market data:', e)
    }
  }

  const refreshMarketData = async () => {
    if (refreshing) return
    
    setRefreshing(true)
    try {
      // 调用后端刷新接口
      const refreshRes = await fetch(getApiUrl('/market/refresh'), {
        method: 'POST'
      })
      
      if (refreshRes.ok) {
        // 刷新成功后重新加载数据
        await loadMarketData()
      }
    } catch (e) {
      console.error('Failed to refresh market data:', e)
    } finally {
      setRefreshing(false)
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
      } else {
        console.error('Market alerts request failed:', res.status, res.statusText)
      }
    } catch (e) {
      console.error('Failed to load market alerts:', e)
    }
  }

  
  if (!market) {
    return <div className={`market-overview ${className}`}>加载中...</div>
  }

  return (
    <div className={`market-overview ${className}`}>
      {/* 1. 今日大盘 */}
      <div className="market-section">
        <h4 className="section-title">
          <span>
            {market.data_update_time?.includes('最近交易日') ? '市场行情' : '今日大盘'}
            {market.data_date && (
              <span className="data-date-info">
                {market.data_date.replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3')}
              </span>
            )}
            {market.data_update_time && (
              <span className={`data-type-badge ${market.is_realtime ? 'realtime' : 'historical'}`}>
                {market.data_update_time}
              </span>
            )}
          </span>
          <button 
            className={`refresh-btn ${refreshing ? 'refreshing' : ''}`}
            onClick={refreshMarketData}
            disabled={refreshing}
            title="刷新市场数据"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
              <path d="M17.65,6.35C16.2,4.9 14.21,4 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20C15.73,20 18.84,17.45 19.73,14H17.65C16.83,16.33 14.61,18 12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6C13.66,6 15.14,6.69 16.22,7.78L13,11H20V4L17.65,6.35Z"/>
            </svg>
            {refreshing ? '刷新中...' : ''}
          </button>
        </h4>
        <div className="indices-rows">
          {market.indices && market.indices.slice(0, 3).map((idx, i) => {
            const indexNames = ['上证指数', '深证成指', '创业板指'];
            const indexName = indexNames[i] || idx.name || '未知指数';
            
            return (
              <div key={i} className="index-row">
                <div className="index-name">{indexName}</div>
                <div className="index-values">
                  <span className={`index-value ${idx.pct_chg > 0 ? 'up' : idx.pct_chg < 0 ? 'down' : 'neutral'}`}>
                    {idx.close ? idx.close.toFixed(4) : 'N/A'}
                  </span>
                  <span className={`index-change ${idx.pct_chg > 0 ? 'up' : idx.pct_chg < 0 ? 'down' : 'neutral'}`}>
                    {idx.pct_chg ? `${idx.pct_chg > 0 ? '+' : ''}${idx.pct_chg.toFixed(2)}%` : 'N/A'}
                  </span>
                </div>
              </div>
            )
          })}
        </div>
        
        {/* 数据说明 */}
        <div className="data-info-panel">
          {market.data_update_time && (
            <div className="data-info-item">
              <svg className="info-icon" width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                <path d="M15,1H9V3H15M19,8H17V21H19M15,21H9A2,2 0 0,1 7,19V5A2,2 0 0,1 9,3A2,2 0 0,1 9,3V19H15V3A2,2 0 0,1 15,3M5,8H3V21H5M11,9H13V19H11V9Z"/>
              </svg>
              <span className="info-text">数据时效: {market.data_update_time}</span>
            </div>
          )}
          <div className="data-info-item">
            <svg className="info-icon" width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12,20A8,8 0 0,0 20,12A8,8 0 0,0 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20M12,2A10,10 0 0,1 22,12A10,10 0 0,1 12,22C6.47,22 2,17.5 2,12A10,10 0 0,1 12,2M12.5,7V12.25L17,14.92L16.25,16.15L11,13V7H12.5Z"/>
            </svg>
            <span className="info-text">获取时间: {market.timestamp ? new Date(market.timestamp).toLocaleTimeString('zh-CN') : '未知'}</span>
          </div>
          {!market.is_realtime && market.data_update_time && (
            <div className="data-info-item data-warning">
              <svg className="info-icon" width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                <path d="M13,9H11V7H13M13,17H11V11H13M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2Z"/>
              </svg>
              <span className="info-text">
                {market.data_update_time.includes('天前')
                  ? `显示最近交易日数据 (${market.data_update_time})`
                  : '提示: Tushare日线数据在收盘后更新'}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* 2. 市场情绪 */}
      <div className="market-section">
        <h4 className="section-title">市场情绪</h4>
        <div className="sentiment-grid">
          <div className="sentiment-item">
            <span className="sentiment-label">涨跌家数</span>
            <span className="sentiment-value">
              {(market.market_breadth?.up_count !== null && 
                market.market_breadth?.up_count !== undefined && 
                market.market_breadth?.down_count !== null && 
                market.market_breadth?.down_count !== undefined) ? 
                `${market.market_breadth.up_count}↑ / ${market.market_breadth.down_count}↓` : 
                '暂无数据'
              }
            </span>
          </div>
          {market.capital_flow && market.capital_flow.north_flow && (
            <div className="sentiment-item">
              <span className="sentiment-label">北向资金</span>
              <span className={`sentiment-value ${(market.capital_flow.north_flow.north_money || 0) > 0 ? 'up' : 'down'}`}>
                {(market.capital_flow.north_flow.north_money || 0) > 0 ? '净流入' : '净流出'} {Math.abs(market.capital_flow.north_flow.north_money || 0).toFixed(1)}亿
              </span>
            </div>
          )}
          {market.capital_flow && !market.capital_flow.north_flow && (
            <div className="sentiment-item">
              <span className="sentiment-label">北向资金</span>
              <span className="sentiment-value neutral">
                暂无数据
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
          <h4 className="section-title">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style={{marginRight: '4px', verticalAlign: 'middle'}}>
              <path d="M12,2A7,7 0 0,1 19,9C19,11.38 17.81,13.47 16,14.74V17A1,1 0 0,1 15,18H9A1,1 0 0,1 8,17V14.74C6.19,13.47 5,11.38 5,9A7,7 0 0,1 12,2M9,21A1,1 0 0,0 8,22A1,1 0 0,0 9,23H15A1,1 0 0,0 16,22A1,1 0 0,0 15,21V20H9V21Z"/>
            </svg>
            操作建议
          </h4>
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