import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

/**
 * ECharts报告图表组件
 * 根据后端生成的图表配置渲染交互式图表
 */
const ReportChart = ({ chartConfig }) => {
  const chartRef = useRef(null);
  const chartInstance = useRef(null);

  useEffect(() => {
    if (!chartRef.current || !chartConfig || !chartConfig.config) {
      return;
    }

    // 初始化图表实例
    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current, 'dark');
    }

    // 设置图表配置
    try {
      const option = buildEChartsOption(chartConfig);
      chartInstance.current.setOption(option, true);
    } catch (error) {
      console.error('设置图表配置失败:', error);
    }

    // 响应式处理
    const handleResize = () => {
      chartInstance.current?.resize();
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [chartConfig]);

  // 组件卸载时销毁图表
  useEffect(() => {
    return () => {
      chartInstance.current?.dispose();
      chartInstance.current = null;
    };
  }, []);

  // 处理数据缺失情况
  if (!chartConfig) {
    return (
      <div className="chart-empty" style={styles.empty}>
        <p>图表配置缺失</p>
      </div>
    );
  }

  if (!chartConfig.config) {
    return (
      <div className="chart-empty" style={styles.empty}>
        <p>{chartConfig.data?.message || '暂无数据'}</p>
      </div>
    );
  }

  return (
    <div
      ref={chartRef}
      style={styles.chartContainer}
      className="report-chart"
    />
  );
};

/**
 * 构建ECharts配置对象
 * 将后端的配置转换为前端可用的格式
 */
function buildEChartsOption(chartConfig) {
  if (!chartConfig || !chartConfig.config) {
    return {};
  }

  const config = chartConfig.config;

  // 处理formatter函数（后端返回的是字符串，需要转换为函数）
  const processedConfig = JSON.parse(JSON.stringify(config));

  // 处理tooltip formatter
  if (processedConfig.tooltip && processedConfig.tooltip.formatter) {
    const formatterStr = processedConfig.tooltip.formatter;

    if (chartConfig.type === 'bar') {
      // 柱状图tooltip - 显示涨停跌停数据
      processedConfig.tooltip.formatter = function(params) {
        if (!Array.isArray(params)) {
          params = [params];
        }
        let result = params[0].axisValue + '<br/>';
        params.forEach(param => {
          const value = Math.abs(param.value);
          result += `${param.marker}${param.seriesName}: ${value}只<br/>`;
        });
        return result;
      };
    } else if (chartConfig.type === 'line') {
      // 折线图tooltip - 显示资金流向
      processedConfig.tooltip.formatter = function(params) {
        if (!Array.isArray(params)) {
          params = [params];
        }
        if (params.length > 0 && params[0].value !== null && params[0].value !== undefined) {
          const value = params[0].value ?? 0;
          const sign = value >= 0 ? '+' : '';
          return `${params[0].axisValue}<br/>净流入: ${sign}${value.toFixed(2)}亿元`;
        }
        return '';
      };
    }
  }

  // 处理yAxis label formatter
  if (processedConfig.yAxis && processedConfig.yAxis.axisLabel) {
    if (chartConfig.type === 'bar') {
      processedConfig.yAxis.axisLabel.formatter = function(value) {
        return Math.abs(value).toString();
      };
    } else if (chartConfig.type === 'line') {
      processedConfig.yAxis.axisLabel.formatter = function(value) {
        return value + '亿';
      };
    } else if (chartConfig.type === 'scatter') {
      processedConfig.yAxis.axisLabel.formatter = function(value) {
        return value + '%';
      };
    }
  }

  // 处理scatter symbolSize函数
  if (chartConfig.type === 'scatter' && processedConfig.series && processedConfig.series[0]) {
    const series = processedConfig.series[0];
    series.symbolSize = function(dataItem) {
      // dataItem是[x, y]数组，我们需要从原始data中获取成交额
      const index = dataItem[0];
      const originalData = chartConfig.data?.sectors || [];
      if (originalData[index]) {
        const turnover = originalData[index].turnover || 0;
        return Math.max(10, Math.min(80, turnover / 20));
      }
      return 20;
    };

    // 处理scatter颜色函数
    series.itemStyle = {
      ...series.itemStyle,
      color: function(params) {
        const originalData = chartConfig.data?.sectors || [];
        if (originalData[params.dataIndex]) {
          const pctChg = originalData[params.dataIndex].pct_chg || 0;
          return pctChg >= 0 ? '#66bb6a' : '#ef5350';
        }
        return '#8b93a7';
      },
      opacity: 0.8
    };

    // 添加scatter tooltip
    series.tooltip = {
      formatter: function(params) {
        const originalData = chartConfig.data?.sectors || [];
        if (originalData[params.dataIndex]) {
          const sector = originalData[params.dataIndex];
          const pctChg = sector.pct_chg ?? 0;
          const turnover = sector.turnover ?? 0;
          return `${sector.name}<br/>涨跌幅: ${pctChg >= 0 ? '+' : ''}${pctChg.toFixed(2)}%<br/>成交额: ${turnover.toFixed(0)}亿`;
        }
        return '';
      }
    };
  }

  return processedConfig;
}

// 样式定义
const styles = {
  chartContainer: {
    width: '100%',
    height: '400px',
    minHeight: '400px'
  },
  empty: {
    width: '100%',
    height: '400px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#1a1d29',
    borderRadius: '8px',
    color: '#8b93a7',
    fontSize: '14px'
  }
};

export default ReportChart;
export { buildEChartsOption };
