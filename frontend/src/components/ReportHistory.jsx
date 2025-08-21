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

export default function ReportHistory({ onSelectReport }) {
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [selectedDate, setSelectedDate] = useState('')

  useEffect(() => {
    loadHistory()
  }, [])

  const loadHistory = async () => {
    setLoading(true)
    try {
      const res = await fetch(getApiUrl('/reports/history?days=30'))
      if (res.ok) {
        const data = await res.json()
        setHistory(data)
      }
    } catch (e) {
      console.error('Failed to load report history:', e)
    } finally {
      setLoading(false)
    }
  }

  const loadReport = async (item) => {
    try {
      const res = await fetch(getApiUrl(`/reports/${item.type}?date=${item.date}`))
      if (res.ok) {
        const report = await res.json()
        onSelectReport(report)
      }
    } catch (e) {
      console.error('Failed to load report:', e)
    }
  }

  // 按日期分组
  const groupedHistory = history.reduce((acc, item) => {
    const date = item.date
    if (!acc[date]) acc[date] = []
    acc[date].push(item)
    return acc
  }, {})

  const getReportIcon = (type) => {
    switch(type) {
      case 'morning': return (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
          <path d="M9,10H7V12H9V10M13,10H11V12H13V10M17,10H15V12H17V10M19,3H18V1H16V3H8V1H6V3H5C3.89,3 3,3.9 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V5A2,2 0 0,0 19,3M19,19H5V8H19V19Z"/>
        </svg>
      )
      case 'noon': return (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 7c-2.76 0-5 2.24-5 5s2.24 5 5 5 5-2.24 5-5-2.24-5-5-5zM2 13h2c.55 0 1-.45 1-1s-.45-1-1-1H2c-.55 0-1 .45-1 1s.45 1 1 1zm18 0h2c.55 0 1-.45 1-1s-.45-1-1-1h-2c-.55 0-1 .45-1 1s.45 1 1 1zM11 2v2c0 .55.45 1 1 1s1-.45 1-1V2c0-.55-.45-1-1-1s-1 .45-1 1zm0 18v2c0 .55.45 1 1 1s1-.45 1-1v-2c0-.55-.45-1-1-1s-1 .45-1 1z"/>
        </svg>
      )
      case 'evening': return (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
          <path d="M17.75,4.09L15.22,6.03L16.13,9.09L13.5,7.28L10.87,9.09L11.78,6.03L9.25,4.09L12.44,4L13.5,1L14.56,4L17.75,4.09M21.25,11L19.61,12.25L20.2,14.23L18.5,13.06L16.8,14.23L17.39,12.25L15.75,11L17.81,10.95L18.5,9L19.19,10.95L21.25,11M18.97,15.95C19.8,15.87 20.69,17.05 20.16,17.8C19.84,18.25 19.5,18.67 19.08,19.07C15.17,23 8.84,23 4.94,19.07C1.03,15.17 1.03,8.83 4.94,4.93C5.34,4.53 5.76,4.17 6.21,3.85C6.96,3.32 8.14,4.21 8.06,5.04C7.79,7.9 8.75,10.87 10.95,13.06C13.14,15.26 16.1,16.22 18.97,15.95Z"/>
        </svg>
      )
      default: return (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
          <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/>
        </svg>
      )
    }
  }

  const getReportName = (type) => {
    switch(type) {
      case 'morning': return '早报'
      case 'noon': return '午报'
      case 'evening': return '晚报'
      default: return '报告'
    }
  }

  if (loading) {
    return <div className="report-history-loading">加载历史记录...</div>
  }

  return (
    <div className="report-history">
      <h3 className="history-title">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style={{marginRight: '8px', verticalAlign: 'middle'}}>
          <path d="M4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm16-4H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-1 9H9V9h10v2zm-4 4H9v-2h6v2zm4-8H9V5h10v2z"/>
        </svg>
        历史报告
      </h3>
      
      {Object.keys(groupedHistory).length === 0 ? (
        <div className="empty-history">暂无历史报告</div>
      ) : (
        <div className="history-list">
          {Object.entries(groupedHistory).sort((a, b) => b[0].localeCompare(a[0])).map(([date, reports]) => (
            <div key={date} className="history-date-group">
              <div className="date-header">{date}</div>
              <div className="date-reports">
                {reports.map((report, i) => (
                  <div 
                    key={i} 
                    className={`history-item ${selectedDate === `${date}-${report.type}` ? 'selected' : ''}`}
                    onClick={() => {
                      setSelectedDate(`${date}-${report.type}`)
                      loadReport(report)
                    }}
                  >
                    <span className="report-icon">{getReportIcon(report.type)}</span>
                    <span className="report-name">{getReportName(report.type)}</span>
                    <span className="report-time">
                      {new Date(report.generated_at).toLocaleTimeString('zh-CN', { 
                        hour: '2-digit', 
                        minute: '2-digit' 
                      })}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}