import React, { useState, useEffect } from 'react'
import API_BASE_URL from '../config/api'

// 动态获取API地址
const getApiUrl = (path) => {
  return `${API_BASE_URL}${path}`
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
        setHistory(data.history || [])
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

  const deleteReport = async (item, e) => {
    e.stopPropagation() // 防止触发loadReport

    if (!confirm(`确定要删除 ${item.date} 的${getReportName(item.type)}吗？`)) {
      return
    }

    try {
      const res = await fetch(getApiUrl(`/reports/${item.type}?date=${item.date}`), {
        method: 'DELETE'
      })

      if (res.ok) {
        // 刷新历史记录
        loadHistory()
      } else {
        alert('删除失败')
      }
    } catch (e) {
      console.error('Failed to delete report:', e)
      alert('删除失败: ' + e.message)
    }
  }

  const refreshHistory = () => {
    loadHistory()
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
      case 'comprehensive_market':
      case 'professional_morning_report': return (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
          <path d="M3,13H7L10,17L13,13H17L22,6L19.5,7.5L16.5,4.5L12,9L10.5,7.5L3,14.5V13Z"/>
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
      case 'comprehensive_market': return '综合市场报告'
      case 'professional_morning_report': return '专业早报'
      default: return '市场报告'
    }
  }

  if (loading) {
    return <div className="report-history-loading">加载历史记录...</div>
  }

  return (
    <div className="report-history">
      <h3 className="history-title">
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style={{marginRight: '8px', verticalAlign: 'middle'}}>
            <path d="M4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm16-4H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-1 9H9V9h10v2zm-4 4H9v-2h6v2zm4-8H9V5h10v2z"/>
          </svg>
          <span>历史报告</span>
        </div>
        <button
          onClick={refreshHistory}
          style={{
            background: 'transparent',
            border: 'none',
            color: '#8b93a7',
            cursor: 'pointer',
            padding: '4px 8px',
            borderRadius: '4px',
            display: 'flex',
            alignItems: 'center',
            transition: 'all 0.2s'
          }}
          onMouseEnter={(e) => e.target.style.color = '#fff'}
          onMouseLeave={(e) => e.target.style.color = '#8b93a7'}
          title="刷新历史记录"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
            <path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/>
          </svg>
        </button>
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
                      {report.generated_at ? new Date(report.generated_at).toLocaleTimeString('zh-CN', {
                        hour: '2-digit',
                        minute: '2-digit'
                      }) : '未知'}
                    </span>
                    <button
                      className="delete-btn"
                      onClick={(e) => deleteReport(report, e)}
                      title="删除此报告"
                      style={{
                        background: 'transparent',
                        border: 'none',
                        color: '#ef5350',
                        cursor: 'pointer',
                        padding: '4px',
                        borderRadius: '4px',
                        display: 'flex',
                        alignItems: 'center',
                        opacity: 0.6,
                        transition: 'opacity 0.2s'
                      }}
                      onMouseEnter={(e) => e.target.style.opacity = '1'}
                      onMouseLeave={(e) => e.target.style.opacity = '0.6'}
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
                      </svg>
                    </button>
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