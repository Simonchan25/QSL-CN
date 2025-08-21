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
  const [llmAnalysis, setLlmAnalysis] = useState('')
  const [aiAnalysis, setAiAnalysis] = useState(null)
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
        
        // 生成LLM分析（如果还没有的话）
        if (!llmAnalysis && data.indices) {
          generateLLMAnalysis(data)
        }
        
        // 加载AI综合分析
        loadAIAnalysis()
        
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

  const loadAIAnalysis = async () => {
    try {
      const res = await fetch(getApiUrl('/market/ai-analysis'))
      if (res.ok) {
        const data = await res.json()
        setAiAnalysis(data.ai_analysis)
      }
    } catch (e) {
      console.error('Failed to load AI analysis:', e)
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

  const generateLLMAnalysis = async (marketData) => {
    setLoading(true)
    try {
      const validIndices = marketData.indices.filter(it => it.pct_chg !== null && it.pct_chg !== undefined)
      const avgChange = validIndices.length > 0 ? validIndices.reduce((sum, idx) => sum + (idx.pct_chg || 0), 0) / validIndices.length : 0
      
      // 生成详细的多维度分析
      let analysis = {}
      
      // 1. 整体趋势判断
      let trendAnalysis = ''
      const sh = marketData.indices[0]?.pct_chg || 0
      const sz = marketData.indices[1]?.pct_chg || 0
      const cyb = marketData.indices[2]?.pct_chg || 0
      
      if (avgChange > 1.5) {
        trendAnalysis = `📈 今日A股全面爆发，上证指数涨${sh.toFixed(2)}%，深成指涨${sz.toFixed(2)}%，创业板涨${cyb.toFixed(2)}%。多头强势主导，市场情绪高涨。`
      } else if (avgChange > 0.5) {
        trendAnalysis = `📊 市场温和上涨，主要指数${sh > 0 ? '上证领涨' : sz > 0 ? '深成指领涨' : '创业板领涨'}。结构性行情延续，赚钱效应尚可。`
      } else if (avgChange > -0.5) {
        trendAnalysis = `⚖️ 大盘横盘震荡，上证${sh > 0 ? '微涨' : '微跌'}${Math.abs(sh).toFixed(2)}%，市场分歧加大，观望情绪浓厚。`
      } else if (avgChange > -1.5) {
        trendAnalysis = `📉 市场小幅调整，${Math.min(sh, sz, cyb) === sh ? '上证领跌' : Math.min(sh, sz, cyb) === sz ? '深成指领跌' : '创业板领跌'}。短期承压，注意风险控制。`
      } else {
        trendAnalysis = `⚠️ 大盘大幅下挫，三大指数全线重挫超${Math.abs(avgChange).toFixed(1)}%。恐慌情绪蔓延，建议谨慎观望。`
      }
      analysis.trend = trendAnalysis
      
      // 2. 资金流向分析
      if (marketData.capital_flow) {
        const northFlow = marketData.capital_flow.hsgt_net_amount || 0
        let flowAnalysis = ''
        if (northFlow > 100) {
          flowAnalysis = `💰 北向资金大举流入${northFlow.toFixed(1)}亿，外资坚定看多A股，重点关注外资偏好的核心资产。`
        } else if (northFlow > 50) {
          flowAnalysis = `💵 北向资金净流入${northFlow.toFixed(1)}亿，外资温和加仓，市场信心有所恢复。`
        } else if (northFlow > 0) {
          flowAnalysis = `💱 北向资金小幅净流入${northFlow.toFixed(1)}亿，外资态度谨慎乐观。`
        } else if (northFlow > -50) {
          flowAnalysis = `💸 北向资金净流出${Math.abs(northFlow).toFixed(1)}亿，外资获利了结，短期需注意调整风险。`
        } else {
          flowAnalysis = `🚨 北向资金大幅流出${Math.abs(northFlow).toFixed(1)}亿，外资避险情绪升温，建议降低仓位。`
        }
        analysis.capital = flowAnalysis
      }
      
      // 3. 板块轮动分析
      if (marketData.sectors && marketData.sectors.length > 0) {
        const topSectors = marketData.sectors.slice(0, 3)
        const bottomSectors = marketData.sectors.slice(-3)
        let sectorAnalysis = `🎯 板块轮动：`
        
        if (topSectors[0]?.pct_chg > 3) {
          sectorAnalysis += `${topSectors.map(s => s.name).join('、')}板块领涨市场，涨幅超${topSectors[0].pct_chg.toFixed(1)}%，资金抱团明显。`
        } else if (topSectors[0]?.pct_chg > 0) {
          sectorAnalysis += `${topSectors[0].name}小幅领涨${topSectors[0].pct_chg.toFixed(1)}%，板块轮动较快，缺乏持续性热点。`
        }
        
        if (bottomSectors[0]?.pct_chg < -2) {
          sectorAnalysis += `${bottomSectors[0].name}领跌${Math.abs(bottomSectors[0].pct_chg).toFixed(1)}%，注意规避相关风险。`
        }
        analysis.sectors = sectorAnalysis
      }
      
      // 4. 市场情绪与热点
      if (marketData.market_breadth) {
        const upRatio = (marketData.market_breadth.up_count / marketData.market_breadth.total_count * 100).toFixed(1)
        let sentimentAnalysis = ''
        if (upRatio > 70) {
          sentimentAnalysis = `🔥 市场情绪火爆！${marketData.market_breadth.up_count}只个股上涨，涨停板众多，赚钱效应极佳。`
        } else if (upRatio > 50) {
          sentimentAnalysis = `😊 ${marketData.market_breadth.up_count}涨/${marketData.market_breadth.down_count}跌，多头占优，个股活跃度较高。`
        } else if (upRatio > 30) {
          sentimentAnalysis = `😐 涨跌比${marketData.market_breadth.up_count}:${marketData.market_breadth.down_count}，市场分化严重，操作难度加大。`
        } else {
          sentimentAnalysis = `😰 仅${marketData.market_breadth.up_count}只个股上涨，市场极度低迷，建议空仓观望。`
        }
        analysis.sentiment = sentimentAnalysis
      }
      
      // 5. 热门股票分析（同花顺热榜）
      if (marketData.hot_stocks && marketData.hot_stocks.length > 0) {
        const topHots = marketData.hot_stocks.slice(0, 5)
        let hotAnalysis = `🌟 同花顺热榜：${topHots.map(s => s.name).join('、')}等个股备受关注，`
        
        // 判断热门股类型
        const hotNames = topHots.map(s => s.name).join('')
        if (hotNames.includes('茅台') || hotNames.includes('五粮液')) {
          hotAnalysis += '白酒板块持续受到资金追捧。'
        } else if (hotNames.includes('宁德') || hotNames.includes('比亚迪')) {
          hotAnalysis += '新能源赛道依然是市场焦点。'
        } else if (hotNames.includes('银行') || hotNames.includes('保险')) {
          hotAnalysis += '大金融板块获得资金青睐。'
        } else {
          hotAnalysis += '题材股活跃，注意追高风险。'
        }
        analysis.hotStocks = hotAnalysis
      }
      
      // 6. 操作建议
      let suggestion = ''
      if (avgChange > 1 && marketData.capital_flow?.hsgt_net_amount > 50) {
        suggestion = `💡 操作建议：市场强势且北向资金流入，可适度加仓，重点关注${marketData.sectors?.[0]?.name || '领涨板块'}的龙头股。建议仓位控制在60-70%。`
      } else if (avgChange > 0) {
        suggestion = `💡 操作建议：市场震荡向上，可维持半仓操作，采取高抛低吸策略。关注${marketData.hot_stocks?.[0]?.name || '热门'}等市场热点。`
      } else if (avgChange > -1) {
        suggestion = `💡 操作建议：市场调整压力较大，建议降低仓位至30%以下，等待企稳信号。可适当关注防御性板块。`
      } else {
        suggestion = `💡 操作建议：市场风险释放中，建议空仓观望，等待超跌反弹机会。重点观察成交量和北向资金动向。`
      }
      analysis.suggestion = suggestion
      
      setLlmAnalysis(analysis)
    } catch (e) {
      console.error('Failed to generate analysis:', e)
      setLlmAnalysis({
        trend: '市场数据加载中，请稍后刷新查看分析...',
        suggestion: '建议等待数据更新后再做投资决策。'
      })
    } finally {
      setLoading(false)
    }
  }

  if (!market || !market.indices) {
    return (
      <div className={`market-overview-widget ${className}`}>
        <h3 className="widget-title">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style={{marginRight: '8px', verticalAlign: 'middle'}}>
            <path d="M3,13H7L10,17L13,13H17L22,6L19.5,7.5L16.5,4.5L12,9L10.5,7.5L3,14.5V13Z"/>
          </svg>
          今日大盘
        </h3>
        <div className="loading-state">加载中...</div>
      </div>
    )
  }

  const validIndices = market.indices.filter(it => it.pct_chg !== null && it.pct_chg !== undefined)
  const avgPct = validIndices.length > 0 
    ? validIndices.reduce((sum, it) => sum + it.pct_chg, 0) / validIndices.length 
    : 0
  const sentiment = avgPct > 1 ? '强势' : avgPct > 0 ? '偏强' : avgPct > -1 ? '偏弱' : '弱势'
  const sentimentClass = avgPct > 1 ? 'strong' : avgPct > 0 ? 'positive' : avgPct > -1 ? 'weak' : 'negative'

  return (
    <div className={`market-overview-widget ${className}`}>
      <h3 className="widget-title">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style={{marginRight: '8px', verticalAlign: 'middle'}}>
          <path d="M3,13H7L10,17L13,13H17L22,6L19.5,7.5L16.5,4.5L12,9L10.5,7.5L3,14.5V13Z"/>
        </svg>
        今日大盘
      </h3>
      
      {/* 1. 指数表现 */}
      <div className="market-section">
        <h4 className="section-title">指数表现</h4>
        <div className="indices-grid">
          {market.indices.slice(0, 3).map((idx, i) => {
            const name = idx.ts_code === "000001.SH" ? '上证指数' : 
                         idx.ts_code === "399001.SZ" ? '深证成指' : 
                         idx.ts_code === "399006.SZ" ? '创业板指' : idx.ts_code
            const cls = idx.pct_chg > 0 ? 'up' : idx.pct_chg < 0 ? 'down' : 'neutral'
            
            return (
              <div key={i} className={`index-card ${cls}`}>
                <div className="index-name">{name}</div>
                <div className="index-price">{idx.close?.toFixed(2) || 'N/A'}</div>
                <div className="index-change">
                  {idx.pct_chg !== null ? `${idx.pct_chg > 0 ? '+' : ''}${idx.pct_chg.toFixed(2)}%` : 'N/A'}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* 2. 市场情绪 & 热点 */}
      <div className="market-section">
        <h4 className="section-title">市场情绪</h4>
        <div className="market-sentiment-detailed">
          <div className="sentiment-item">
            <span className="sentiment-label">市场温度</span>
            <span className={`sentiment-value ${sentimentClass}`}>{sentiment}</span>
          </div>
          {market.market_breadth && (
            <div className="sentiment-item">
              <span className="sentiment-label">涨跌家数</span>
              <span className="sentiment-value">
                {market.market_breadth.up_count}↑ / {market.market_breadth.down_count}↓
              </span>
            </div>
          )}
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

      {/* 3. 行业板块 */}
      {market.sectors && market.sectors.length > 0 && (
        <div className="market-section">
          <h4 className="section-title">板块表现</h4>
          <div className="sectors-list">
            <div className="sectors-group">
              <span className="group-label">涨幅前三:</span>
              {market.sectors.slice(0, 3).map((sector, i) => (
                <span key={i} className="sector-item up">
                  {sector.name} {sector.pct_chg > 0 ? '+' : ''}{sector.pct_chg.toFixed(2)}%
                </span>
              ))}
            </div>
            <div className="sectors-group">
              <span className="group-label">跌幅前三:</span>
              {market.sectors.slice(-3).reverse().map((sector, i) => (
                <span key={i} className="sector-item down">
                  {sector.name} {sector.pct_chg > 0 ? '+' : ''}{sector.pct_chg.toFixed(2)}%
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 4. 宏观指标 */}
      {market.macro_indicators && (
        <div className="market-section">
          <h4 className="section-title">宏观指标</h4>
          <div className="macro-grid">
            <div className="macro-item">
              <span className="macro-label">USD/CNY</span>
              <span className="macro-value">{market.macro_indicators.usd_cny}</span>
            </div>
            <div className="macro-item">
              <span className="macro-label">原油</span>
              <span className={`macro-value ${market.macro_indicators.oil_change > 0 ? 'up' : 'down'}`}>
                ${market.macro_indicators.oil_price} ({market.macro_indicators.oil_change > 0 ? '+' : ''}{market.macro_indicators.oil_change}%)
              </span>
            </div>
            <div className="macro-item">
              <span className="macro-label">黄金</span>
              <span className={`macro-value ${market.macro_indicators.gold_change > 0 ? 'up' : 'down'}`}>
                ${market.macro_indicators.gold_price} ({market.macro_indicators.gold_change > 0 ? '+' : ''}{market.macro_indicators.gold_change}%)
              </span>
            </div>
          </div>
        </div>
      )}

      {/* 5. 同花顺热榜 */}
      {market.hot_stocks && market.hot_stocks.length > 0 && (
        <div className="market-section">
          <h4 className="section-title">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style={{marginRight: '4px', verticalAlign: 'middle'}}>
              <path d="M17.66 11.2C17.43 10.9 17.15 10.64 16.89 10.38C16.22 9.78 15.46 9.35 14.82 8.72C13.33 7.26 13 4.85 13.95 3C13 3.23 12.17 3.75 11.46 4.32C8.87 6.4 7.85 10.07 9.07 13.22C9.11 13.32 9.15 13.42 9.15 13.55C9.15 13.77 9 13.97 8.8 14.05C8.57 14.15 8.33 14.09 8.14 13.93C8.08 13.88 8.04 13.83 8 13.76C6.87 12.33 6.69 10.28 7.45 8.64C5.78 10 4.87 12.3 5 14.47C5.06 14.97 5.12 15.47 5.29 15.97C5.43 16.57 5.7 17.17 6 17.7C7.08 19.43 8.95 20.67 10.96 20.92C13.1 21.19 15.39 20.8 17.03 19.32C18.86 17.66 19.5 15 18.56 12.72L18.43 12.46C18.22 12 17.66 11.2 17.66 11.2M14.5 17.5C14.22 17.74 13.76 18 13.4 18.1C12.28 18.5 11.16 17.94 10.5 17.28C11.69 17 12.4 16.12 12.61 15.23C12.78 14.43 12.46 13.77 12.33 13C12.21 12.26 12.23 11.63 12.5 10.94C12.69 11.32 12.89 11.7 13.13 12C13.9 13 15.11 13.44 15.37 14.8C15.41 14.94 15.43 15.08 15.43 15.23C15.46 16.05 15.1 16.95 14.5 17.5H14.5Z"/>
            </svg>
            热门股票
          </h4>
          <div className="hot-stocks-list">
            {market.hot_stocks.slice(0, 8).map((stock, i) => (
              <div key={i} className="hot-stock-item">
                <span className="hot-rank">#{stock.hot_rank || i + 1}</span>
                <span className="hot-name">{stock.name}</span>
                <span className="hot-value">{stock.hot_value?.toFixed(1) || '0.0'}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 6. 新闻摘要 */}
      {market.major_news && market.major_news.length > 0 && (
        <div className="market-section">
          <h4 className="section-title">重要新闻</h4>
          <div className="news-list">
            {market.major_news.slice(0, 3).map((news, i) => (
              <div key={i} className="news-item">
                <span className="news-bullet">•</span>
                <span className="news-text">{news}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 恐慌贪婪指数 */}
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
      
      {/* 智能预警 */}
      {marketAlerts && marketAlerts.length > 0 && (
        <div className="market-section alerts-section">
          <h4 className="section-title">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style={{marginRight: '4px', verticalAlign: 'middle'}}>
              <path d="M13,14H11V10H13M13,18H11V16H13M1,21H23L12,2L1,21Z"/>
            </svg>
            预警 ({marketAlerts.length})
          </h4>
          <div className="alerts-container">
            {marketAlerts.slice(0, 2).map((alert, index) => (
              <div key={index} className={`alert-item alert-${alert.level}`}>
                <div className="alert-message">{alert.message}</div>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* 精简版AI分析 - 只显示核心信息 */}
      {aiAnalysis && (
        <div className="market-section ai-analysis-section">
          <h4 className="section-title">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style={{marginRight: '4px', verticalAlign: 'middle'}}>
              <path d="M12,2A2,2 0 0,1 14,4C14,4.74 13.6,5.39 13,5.73V7H14A7,7 0 0,1 21,14H22A1,1 0 0,1 23,15V18A1,1 0 0,1 22,19H21V20A2,2 0 0,1 19,22H5A2,2 0 0,1 3,20V19H2A1,1 0 0,1 1,18V15A1,1 0 0,1 2,14H3A7,7 0 0,1 10,7H11V5.73C10.4,5.39 10,4.74 10,4A2,2 0 0,1 12,2M7.5,13A2.5,2.5 0 0,0 5,15.5A2.5,2.5 0 0,0 7.5,18A2.5,2.5 0 0,0 10,15.5A2.5,2.5 0 0,0 7.5,13M16.5,13A2.5,2.5 0 0,0 14,15.5A2.5,2.5 0 0,0 16.5,18A2.5,2.5 0 0,0 19,15.5A2.5,2.5 0 0,0 16.5,13Z"/>
            </svg>
            QSL-AI五维度分析
          </h4>
          
          {/* 综合评分和市场状态 */}
          {aiAnalysis.summary && (
            <div className="ai-summary-section">
              <div className="market-score-card">
                <div className="score-display">
                  <span className="score-value">{aiAnalysis.summary.overall_score}</span>
                  <span className="score-max">/10</span>
                </div>
                <div className="market-state">
                  <span className="state-label">市场状态:</span>
                  <span className={`state-value ${aiAnalysis.summary.overall_score >= 6 ? 'positive' : aiAnalysis.summary.overall_score >= 4 ? 'neutral' : 'negative'}`}>
                    {aiAnalysis.summary.market_state}
                  </span>
                </div>
              </div>
            </div>
          )}
          
          {/* 1. 市场情绪解读 */}
          {aiAnalysis.sentiment && !aiAnalysis.sentiment.error && (
            <div className="analysis-dimension">
              <div className="dimension-header">
                <span className="dimension-icon">😊</span>
                <span className="dimension-title">市场情绪解读</span>
                {aiAnalysis.sentiment.emotion_score && (
                  <span className={`emotion-badge ${aiAnalysis.sentiment.emotion_score >= 6 ? 'positive' : aiAnalysis.sentiment.emotion_score >= 4 ? 'neutral' : 'negative'}`}>
                    {aiAnalysis.sentiment.overall_sentiment}
                  </span>
                )}
              </div>
              <div className="dimension-content">
                {aiAnalysis.sentiment.up_down_ratio && (
                  <div className="metric-item">
                    <span className="metric-label">涨跌比例:</span>
                    <span className="metric-value">{aiAnalysis.sentiment.up_down_ratio.up_count}↑/{aiAnalysis.sentiment.up_down_ratio.down_count}↓ ({aiAnalysis.sentiment.up_down_ratio.up_ratio}%)</span>
                    <div className="metric-analysis">{aiAnalysis.sentiment.up_down_ratio.analysis}</div>
                  </div>
                )}
                {aiAnalysis.sentiment.limit_analysis && (
                  <div className="metric-item">
                    <span className="metric-label">涨跌停:</span>
                    <span className="metric-value">涨停{aiAnalysis.sentiment.limit_analysis.limit_up}家 跌停{aiAnalysis.sentiment.limit_analysis.limit_down}家</span>
                    <div className="metric-analysis">{aiAnalysis.sentiment.limit_analysis.analysis}</div>
                  </div>
                )}
              </div>
            </div>
          )}
          
          {/* 2. 资金流向分析 */}
          {aiAnalysis.capital && !aiAnalysis.capital.error && (
            <div className="analysis-dimension">
              <div className="dimension-header">
                <span className="dimension-icon">💰</span>
                <span className="dimension-title">资金流向分析</span>
              </div>
              <div className="dimension-content">
                {aiAnalysis.capital.north_funds && (
                  <div className="metric-item">
                    <span className="metric-label">北向资金:</span>
                    <span className={`metric-value ${aiAnalysis.capital.north_funds.total_net_inflow > 0 ? 'positive' : 'negative'}`}>
                      {aiAnalysis.capital.north_funds.total_net_inflow > 0 ? '净流入' : '净流出'} {Math.abs(aiAnalysis.capital.north_funds.total_net_inflow)}亿
                    </span>
                    <div className="metric-analysis">{aiAnalysis.capital.north_funds.analysis}</div>
                  </div>
                )}
          {/* 精简版AI分析 - 只显示最重要的信息 */}
          <div className="analysis-summary">
            {/* 操作建议 */}
            {aiAnalysis.summary && aiAnalysis.summary.operation_advice && (
              <div className="advice-section">
                <div className="advice-title">💡 操作建议</div>
                <div className="advice-list">
                  {aiAnalysis.summary.operation_advice.slice(0, 2).map((advice, index) => (
                    <div key={index} className="advice-item">{advice}</div>
                  ))}
                </div>
              </div>
            )}
            
            {/* 风险提示 */}
            {aiAnalysis.summary && aiAnalysis.summary.risk_warnings && (
              <div className="risk-section">
                <div className="risk-title">⚠️ 风险提示</div>
                <div className="risk-list">
                  {aiAnalysis.summary.risk_warnings.slice(0, 1).map((warning, index) => (
                    <div key={index} className="risk-item">{warning}</div>
                  ))}
                </div>
              </div>
            )}
          </div>
          
          {/* 3. 指数板块结构 */}
          {aiAnalysis.structure && !aiAnalysis.structure.error && (
            <div className="analysis-dimension">
              <div className="dimension-header">
                <span className="dimension-icon">📊</span>
                <span className="dimension-title">指数板块结构</span>
              </div>
              <div className="dimension-content">
                {aiAnalysis.structure.index_performance && (
                  <div className="metric-item">
                    <span className="metric-label">指数表现:</span>
                    <div className="indices-mini-grid">
                      {aiAnalysis.structure.index_performance.indices.slice(0, 3).map((idx, i) => (
                        <span key={i} className={`mini-index ${idx.change > 0 ? 'up' : idx.change < 0 ? 'down' : 'neutral'}`}>
                          {idx.name} {idx.change > 0 ? '+' : ''}{idx.change?.toFixed(2)}%
                        </span>
                      ))}
                    </div>
                    <div className="metric-analysis">{aiAnalysis.structure.index_performance.analysis}</div>
                  </div>
                )}
                {aiAnalysis.structure.sector_rotation && (
                  <div className="metric-item">
                    <span className="metric-label">板块轮动:</span>
                    <div className="sector-leaders">
                      领涨: {aiAnalysis.structure.sector_rotation.leading_sectors.slice(0, 3).map(s => s.name).join('、')}
                    </div>
                    <div className="metric-analysis">{aiAnalysis.structure.sector_rotation.analysis}</div>
                  </div>
                )}
              </div>
            </div>
          )}
          
          {/* 4. 宏观环境 */}
          {aiAnalysis.macro && !aiAnalysis.macro.error && (
            <div className="analysis-dimension">
              <div className="dimension-header">
                <span className="dimension-icon">🌍</span>
                <span className="dimension-title">宏观外部环境</span>
              </div>
              <div className="dimension-content">
                {aiAnalysis.macro.forex && (
                  <div className="metric-item">
                    <span className="metric-label">汇率环境:</span>
                    <span className="metric-value">USD/CNY {aiAnalysis.macro.forex.usd_cny}</span>
                    <div className="metric-analysis">{aiAnalysis.macro.forex.analysis}</div>
                  </div>
                )}
                {aiAnalysis.macro.commodities && (
                  <div className="metric-item">
                    <span className="metric-label">大宗商品:</span>
                    <div className="commodities-row">
                      <span className={`commodity-item ${aiAnalysis.macro.commodities.oil.change > 0 ? 'up' : 'down'}`}>
                        原油 ${aiAnalysis.macro.commodities.oil.price} ({aiAnalysis.macro.commodities.oil.change > 0 ? '+' : ''}{aiAnalysis.macro.commodities.oil.change}%)
                      </span>
                      <span className={`commodity-item ${aiAnalysis.macro.commodities.gold.change > 0 ? 'up' : 'down'}`}>
                        黄金 ${aiAnalysis.macro.commodities.gold.price} ({aiAnalysis.macro.commodities.gold.change > 0 ? '+' : ''}{aiAnalysis.macro.commodities.gold.change}%)
                      </span>
                    </div>
                    <div className="metric-analysis">{aiAnalysis.macro.commodities.analysis}</div>
                  </div>
                )}
              </div>
            </div>
          )}
          
          {/* 5. 新闻政策解读 */}
          {aiAnalysis.news && !aiAnalysis.news.error && (
            <div className="analysis-dimension">
              <div className="dimension-header">
                <span className="dimension-icon">📰</span>
                <span className="dimension-title">新闻政策解读</span>
              </div>
              <div className="dimension-content">
                {aiAnalysis.news.important_announcements && (
                  <div className="metric-item">
                    <span className="metric-label">重要公告:</span>
                    <span className="metric-value">
                      {aiAnalysis.news.important_announcements.total_count}条 (利好{aiAnalysis.news.important_announcements.positive_count}条)
                    </span>
                    <div className="metric-analysis">{aiAnalysis.news.important_announcements.analysis}</div>
                  </div>
                )}
                {aiAnalysis.news.policy_news && (
                  <div className="metric-item">
                    <span className="metric-label">政策影响:</span>
                    <span className="metric-value">平均影响评分 {aiAnalysis.news.policy_news.average_impact}/10</span>
                    <div className="metric-analysis">{aiAnalysis.news.policy_news.analysis}</div>
                  </div>
                )}
              </div>
            </div>
          )}
          
          {/* 操作建议 */}
          {aiAnalysis.summary && aiAnalysis.summary.operation_advice && (
            <div className="ai-advice-section">
              <div className="advice-header">
                <span className="advice-icon">💡</span>
                <span className="advice-title">操作建议</span>
                <span className="confidence-badge">
                  置信度: {aiAnalysis.summary.confidence_level}
                </span>
              </div>
              <div className="advice-list">
                {aiAnalysis.summary.operation_advice.map((advice, i) => (
                  <div key={i} className="advice-item">{advice}</div>
                ))}
              </div>
              {aiAnalysis.summary.risk_warnings && (
                <div className="risk-warnings">
                  <div className="warning-header">⚠️ 风险提示</div>
                  {aiAnalysis.summary.risk_warnings.map((warning, i) => (
                    <div key={i} className="warning-item">{warning}</div>
                  ))}
                </div>
              )}
            </div>
          )}
          
          <div className="ai-analysis-footer">
            <span className="generated-time">
              分析时间: {aiAnalysis.generated_at ? new Date(aiAnalysis.generated_at).toLocaleString('zh-CN') : ''}
            </span>
          </div>
        </div>
      )}
      
      {/* 如果AI分析还没加载，显示简化版LLM分析 */}
      {!aiAnalysis && llmAnalysis && (
        <div className="market-section ai-analysis-section">
          <h4 className="section-title">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style={{marginRight: '4px', verticalAlign: 'middle'}}>
              <path d="M12,2A2,2 0 0,1 14,4C14,4.74 13.6,5.39 13,5.73V7H14A7,7 0 0,1 21,14H22A1,1 0 0,1 23,15V18A1,1 0 0,1 22,19H21V20A2,2 0 0,1 19,22H5A2,2 0 0,1 3,20V19H2A1,1 0 0,1 1,18V15A1,1 0 0,1 2,14H3A7,7 0 0,1 10,7H11V5.73C10.4,5.39 10,4.74 10,4A2,2 0 0,1 12,2M7.5,13A2.5,2.5 0 0,0 5,15.5A2.5,2.5 0 0,0 7.5,18A2.5,2.5 0 0,0 10,15.5A2.5,2.5 0 0,0 7.5,13M16.5,13A2.5,2.5 0 0,0 14,15.5A2.5,2.5 0 0,0 16.5,18A2.5,2.5 0 0,0 19,15.5A2.5,2.5 0 0,0 16.5,13Z"/>
            </svg>
            QSL-AI深度分析
          </h4>
          <div className="llm-analysis-detailed">
            {typeof llmAnalysis === 'string' ? (
              <div className="analysis-text">{llmAnalysis}</div>
            ) : (
              <>
                {llmAnalysis.trend && (
                  <div className="analysis-item">
                    <div className="analysis-subtitle">市场趋势</div>
                    <div className="analysis-content">{llmAnalysis.trend}</div>
                  </div>
                )}
                {llmAnalysis.capital && (
                  <div className="analysis-item">
                    <div className="analysis-subtitle">资金动向</div>
                    <div className="analysis-content">{llmAnalysis.capital}</div>
                  </div>
                )}
                {llmAnalysis.sectors && (
                  <div className="analysis-item">
                    <div className="analysis-subtitle">板块轮动</div>
                    <div className="analysis-content">{llmAnalysis.sectors}</div>
                  </div>
                )}
                {llmAnalysis.sentiment && (
                  <div className="analysis-item">
                    <div className="analysis-subtitle">市场情绪</div>
                    <div className="analysis-content">{llmAnalysis.sentiment}</div>
                  </div>
                )}
                {llmAnalysis.hotStocks && (
                  <div className="analysis-item">
                    <div className="analysis-subtitle">热门追踪</div>
                    <div className="analysis-content">{llmAnalysis.hotStocks}</div>
                  </div>
                )}
                {llmAnalysis.suggestion && (
                  <div className="analysis-item suggestion">
                    <div className="analysis-subtitle">投资策略</div>
                    <div className="analysis-content">{llmAnalysis.suggestion}</div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}

      {/* 恐慌贪婪指数 */}
      {fearGreedIndex && (
        <div className="market-section fear-greed-section">
          <h4 className="section-title">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style={{marginRight: '4px', verticalAlign: 'middle'}}>
              <path d="M12,2A2,2 0 0,1 14,4V5.5L15.5,7H17A2,2 0 0,1 19,9V10A2,2 0 0,1 17,12H15L13.5,13.5V19A2,2 0 0,1 11,21H9A2,2 0 0,1 7,19V13.5L5.5,12H4A2,2 0 0,1 2,10V9A2,2 0 0,1 4,7H5.5L7,5.5V4A2,2 0 0,1 9,2H12M12,4H9V6L7,8H4V10H7L9,12V19H11V12L13,10H17V8H13L12,6V4Z"/>
            </svg>
            恐慌贪婪指数
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
      
      {/* 智能预警 */}
      {marketAlerts && marketAlerts.length > 0 && (
        <div className="market-section alerts-section">
          <h4 className="section-title">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style={{marginRight: '4px', verticalAlign: 'middle'}}>
              <path d="M13,14H11V10H13M13,18H11V16H13M1,21H23L12,2L1,21Z"/>
            </svg>
            智能预警 ({marketAlerts.length})
          </h4>
          <div className="alerts-container">
            {marketAlerts.slice(0, 3).map((alert, index) => (
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
      
      {/* 增强版AI智能解读 */}
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