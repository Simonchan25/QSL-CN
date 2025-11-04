import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import InteractiveKLineChart from './InteractiveKLineChart'

/**
 * 智能报告渲染器
 * 自动检测并提取HTML图表，用交互式ECharts替换
 */
export default function ReportRenderer({ text, prices, predictions, stockName, indicators }) {
  if (!text) return null

  // 检测是否有图表（静态SVG或HTML）
  const chartMatch = text.match(/<div class="chart-container">[\s\S]*?<\/div>/);

  if (chartMatch) {
    // 分割文本：图表前、图表、图表后
    const parts = text.split(chartMatch[0]);
    const beforeChart = parts[0];
    const afterChart = parts[1] || '';

    return (
      <>
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {beforeChart}
        </ReactMarkdown>

        {/* 用交互式K线图替换静态图表 */}
        {prices && prices.length > 0 && (() => {
          console.log('[ReportRenderer] Passing to KLine:', {
            prices: prices?.length,
            predictions: predictions,
            hasPredictions: !!predictions,
            historical: predictions?.historical?.length,
            future: predictions?.future?.length
          });
          return (
            <InteractiveKLineChart
              prices={prices}
              predictions={predictions || []}
              stockName={stockName || ''}
              indicators={indicators || {}}
            />
          );
        })()}

        {/* 如果没有price数据，降级显示原始图片 */}
        {(!prices || prices.length === 0) && (
          <div className="chart-container" style={{ margin: '20px 0' }}>
            <img
              src={chartMatch[0].match(/src="([^"]+)"/)?.[1] || ''}
              alt="K线图"
              style={{
                maxWidth: '100%',
                height: 'auto',
                borderRadius: '8px',
                boxShadow: '0 4px 12px rgba(0,0,0,0.3)'
              }}
            />
          </div>
        )}

        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {afterChart}
        </ReactMarkdown>
      </>
    );
  }

  // 没有图表，正常渲染
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]}>
      {text}
    </ReactMarkdown>
  );
}
