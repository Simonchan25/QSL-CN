import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';

/**
 * 交互式K线图组件（ECharts）
 * 功能：
 * - 可缩放、拖拽
 * - 鼠标悬停显示详情
 * - 显示AI预测数据及准确率
 */
const InteractiveKLineChart = ({ prices = [], predictions = [], stockName = '', indicators = {} }) => {
  // 处理历史预测和未来预测（在组件级别）
  const historical = useMemo(() => {
    const result = Array.isArray(predictions)
      ? predictions.filter(p => p.actual_price !== null && p.actual_price !== undefined)
      : (predictions?.historical || []);
    console.log('[KLine] Historical predictions:', result.length, 'items');
    return result;
  }, [predictions]);

  const future = useMemo(() => {
    const result = Array.isArray(predictions)
      ? predictions.filter(p => p.actual_price === null || p.actual_price === undefined)
      : (predictions?.future || []);
    console.log('[KLine] Future predictions:', result.length, 'items');
    return result;
  }, [predictions]);

  const option = useMemo(() => {
    if (!prices || prices.length === 0) {
      return null;
    }

    // 最近60天数据
    const displayPrices = prices.slice(0, 60).reverse();

    // 准备K线数据: [open, close, low, high]
    const klineData = displayPrices.map(p => [p.open, p.close, p.low, p.high]);

    // 准备日期数据（兼容trade_date和date两种字段名）
    const dates = displayPrices.map(p => {
      const dateStr = String(p.trade_date || p.date || '');
      return `${dateStr.slice(0,4)}-${dateStr.slice(4,6)}-${dateStr.slice(6,8)}`;
    });

    // 准备成交量数据
    const volumes = displayPrices.map((p, idx) => {
      const isRise = p.close >= p.open;
      return {
        value: p.amount || 0,
        itemStyle: {
          color: isRise ? '#ef5350' : '#26a69a'
        }
      };
    });

    // 计算MA5
    const ma5 = displayPrices.map((p, idx) => {
      if (idx < 4) return null;
      const sum = displayPrices.slice(idx - 4, idx + 1).reduce((acc, item) => acc + item.close, 0);
      return (sum / 5).toFixed(2);
    });

    // 计算MA10
    const ma10 = displayPrices.map((p, idx) => {
      if (idx < 9) return null;
      const sum = displayPrices.slice(idx - 9, idx + 1).reduce((acc, item) => acc + item.close, 0);
      return (sum / 10).toFixed(2);
    });

    // 准备预测数据 (区分历史和未来)
    let predictionSeries = [];

    // 历史预测点（紫色菱形）
    if (historical && historical.length > 0) {
      console.log('[KLine] Processing historical predictions:', historical);
      const historicalPoints = historical.map(pred => {
        const predDate = pred.date.replace(/-/g, '');
        // 兼容trade_date和date两种字段名
        const idx = displayPrices.findIndex(p => String(p.trade_date || p.date) === predDate);
        console.log('[KLine] Historical pred:', pred.date, '-> index:', idx);
        if (idx === -1) return null;

        return {
          coord: [idx, pred.predicted_price],
          actualPrice: pred.actual_price,
          error: pred.error,
          errorPct: pred.error_pct
        };
      }).filter(Boolean);
      console.log('[KLine] Filtered historical points:', historicalPoints.length);

      if (historicalPoints.length > 0) {
        predictionSeries.push({
          name: 'AI验证(过去7天)',
          type: 'scatter',
          symbol: 'diamond',
          symbolSize: 10,
          xAxisIndex: 0,
          yAxisIndex: 0,
          data: historicalPoints.map(p => ({
            value: p.coord,
            actualPrice: p.actualPrice,
            error: p.error,
            errorPct: p.errorPct
          })),
          itemStyle: {
            color: '#9c27b0',
            borderColor: '#fff',
            borderWidth: 2
          },
          z: 10,
          tooltip: {
            formatter: (params) => {
              const data = params.data;
              return `
                <div style="padding: 5px;">
                  <div style="font-weight: bold; margin-bottom: 5px;">AI历史验证</div>
                  <div>预测价格: ${params.value[1]}</div>
                  <div>实际价格: ${data.actualPrice}</div>
                  <div>误差: ${data.error} (${data.errorPct}%)</div>
                </div>
              `;
            }
          }
        });
      }
    }

    // 未来预测点（橙色圆圈）
    if (future && future.length > 0 && displayPrices.length > 0) {
      try {
        const lastPrice = displayPrices[displayPrices.length - 1];
        // 兼容trade_date和date两种字段名
        const lastDate = lastPrice?.trade_date || lastPrice?.date;

        // 检查日期字段是否存在
        if (!lastDate) {
          console.warn('No trade_date or date in last price:', lastPrice);
        } else {
          const lastDateObj = new Date(
            String(lastDate).slice(0, 4),
            parseInt(String(lastDate).slice(4, 6)) - 1,
            String(lastDate).slice(6, 8)
          );

          // 验证日期是否有效
          if (isNaN(lastDateObj.getTime())) {
            console.warn('Invalid lastDate:', lastDate);
          } else {
          const futurePoints = future.map((pred, i) => {
            const futureDate = new Date(lastDateObj);
            futureDate.setDate(futureDate.getDate() + i + 1);

            // 安全地调用toISOString
            let futureDateStr;
            try {
              futureDateStr = futureDate.toISOString().slice(0, 10);
            } catch (e) {
              console.warn('Invalid futureDate:', futureDate);
              futureDateStr = '';
            }

            return {
              coord: [displayPrices.length + i, pred.predicted_price],
              date: futureDateStr
            };
          });

          if (futurePoints.length > 0) {
            predictionSeries.push({
              name: 'Kronos AI预测(未来5天)',
              type: 'scatter',
              symbol: 'circle',
              symbolSize: 12,
              xAxisIndex: 0,
              yAxisIndex: 0,
              data: futurePoints.map(p => ({
                value: p.coord,
                date: p.date
              })),
              itemStyle: {
                color: '#ff9800',
                borderColor: '#fff',
                borderWidth: 2
              },
              z: 10,
              tooltip: {
                formatter: (params) => {
                  const data = params.data;
                  return `
                    <div style="padding: 5px;">
                      <div style="font-weight: bold; margin-bottom: 5px;">AI未来预测</div>
                      <div>日期: ${data.date}</div>
                      <div>预测价格: ${params.value[1]}</div>
                    </div>
                  `;
                }
              }
            });
          }
        }
      }
      } catch (e) {
        console.error('处理未来预测数据时出错:', e);
      }
    }

    return {
      backgroundColor: '#1e2130',
      title: {
        text: `${stockName} - Kronos AI深度预测 K线图`,
        left: 'center',
        top: 10,
        textStyle: {
          color: '#fff',
          fontSize: 16,
          fontWeight: 600
        }
      },
      legend: {
        top: 40,
        left: 'center',
        textStyle: {
          color: '#8b93a7'
        },
        data: ['日K', 'MA5', 'MA10', ...predictionSeries.map(s => s.name)]
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross'
        },
        backgroundColor: 'rgba(30, 33, 48, 0.95)',
        borderColor: '#3a3f51',
        textStyle: {
          color: '#fff'
        },
        formatter: (params) => {
          const dataIndex = params[0].dataIndex;
          const kline = klineData[dataIndex];
          const date = dates[dataIndex];

          let html = `
            <div style="padding: 5px;">
              <div style="font-weight: bold; margin-bottom: 5px;">${date}</div>
              <div>开盘: ${kline[0]}</div>
              <div>收盘: ${kline[1]}</div>
              <div>最低: ${kline[2]}</div>
              <div>最高: ${kline[3]}</div>
              <div>成交额: ${(volumes[dataIndex].value / 100000000).toFixed(2)}亿</div>
          `;

          params.forEach(param => {
            if (param.seriesName === 'MA5' && param.value) {
              html += `<div style="color: #ffb74d;">MA5: ${param.value}</div>`;
            }
            if (param.seriesName === 'MA10' && param.value) {
              html += `<div style="color: #42a5f5;">MA10: ${param.value}</div>`;
            }
          });

          html += '</div>';
          return html;
        }
      },
      axisPointer: {
        link: [{ xAxisIndex: 'all' }],
        label: {
          backgroundColor: '#777'
        }
      },
      grid: [
        {
          left: '3%',
          right: '3%',
          top: 90,
          height: '55%'
        },
        {
          left: '3%',
          right: '3%',
          top: '70%',
          height: '18%'
        }
      ],
      xAxis: [
        {
          type: 'category',
          data: dates,
          scale: true,
          boundaryGap: true,
          axisLine: {
            lineStyle: {
              color: '#3a3f51'
            }
          },
          axisLabel: {
            color: '#8b93a7',
            formatter: (value) => {
              return value.slice(5); // 只显示MM-DD
            }
          },
          splitLine: {
            show: false
          },
          min: 'dataMin',
          max: 'dataMax',
          axisPointer: {
            show: true
          }
        },
        {
          type: 'category',
          gridIndex: 1,
          data: dates,
          scale: true,
          boundaryGap: true,
          axisLine: {
            lineStyle: {
              color: '#3a3f51'
            }
          },
          axisLabel: {
            show: false
          },
          splitLine: {
            show: false
          },
          min: 'dataMin',
          max: 'dataMax'
        }
      ],
      yAxis: [
        {
          scale: true,
          splitArea: {
            show: false
          },
          axisLine: {
            lineStyle: {
              color: '#3a3f51'
            }
          },
          axisLabel: {
            color: '#8b93a7'
          },
          splitLine: {
            lineStyle: {
              color: '#2a2e3f',
              type: 'dashed'
            }
          }
        },
        {
          scale: true,
          gridIndex: 1,
          splitNumber: 2,
          axisLabel: {
            show: false
          },
          axisLine: {
            show: false
          },
          axisTick: {
            show: false
          },
          splitLine: {
            show: false
          }
        }
      ],
      dataZoom: [
        {
          type: 'inside',
          xAxisIndex: [0, 1],
          start: 0,
          end: 100
        },
        {
          show: true,
          xAxisIndex: [0, 1],
          type: 'slider',
          top: '92%',
          start: 0,
          end: 100,
          backgroundColor: '#252836',
          fillerColor: 'rgba(156, 39, 176, 0.2)',
          borderColor: '#3a3f51',
          textStyle: {
            color: '#8b93a7'
          }
        }
      ],
      series: [
        {
          name: '日K',
          type: 'candlestick',
          data: klineData,
          itemStyle: {
            color: '#ef5350',    // 涨
            color0: '#26a69a',   // 跌
            borderColor: '#ef5350',
            borderColor0: '#26a69a'
          },
          xAxisIndex: 0,
          yAxisIndex: 0
        },
        {
          name: 'MA5',
          type: 'line',
          data: ma5,
          smooth: true,
          lineStyle: {
            width: 1.5,
            color: '#ffb74d'
          },
          showSymbol: false,
          xAxisIndex: 0,
          yAxisIndex: 0
        },
        {
          name: 'MA10',
          type: 'line',
          data: ma10,
          smooth: true,
          lineStyle: {
            width: 1.5,
            color: '#42a5f5'
          },
          showSymbol: false,
          xAxisIndex: 0,
          yAxisIndex: 0
        },
        ...predictionSeries,
        {
          name: '成交量',
          type: 'bar',
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: volumes
        }
      ]
    };
  }, [prices, historical, future, stockName]);

  if (!option) {
    return (
      <div style={{
        padding: '40px',
        textAlign: 'center',
        background: '#1a1d29',
        borderRadius: '8px',
        color: '#8b93a7'
      }}>
        暂无K线数据
      </div>
    );
  }

  return (
    <div style={{
      background: 'linear-gradient(135deg, #1a1d29 0%, #252836 100%)',
      borderRadius: '12px',
      padding: '20px',
      marginBottom: '20px',
      boxShadow: '0 4px 20px rgba(0,0,0,0.3)'
    }}>
      <ReactECharts
        option={option}
        style={{ height: '600px', width: '100%' }}
        theme="dark"
      />

      {/* 说明文字 */}
      <div style={{
        marginTop: '15px',
        padding: '12px',
        background: '#252836',
        borderRadius: '8px',
        color: '#8b93a7',
        fontSize: '13px'
      }}>
        <div style={{ marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12,2A7,7 0 0,1 19,9C19,11.38 17.81,13.47 16,14.74V17A1,1 0 0,1 15,18H9A1,1 0 0,1 8,17V14.74C6.19,13.47 5,11.38 5,9A7,7 0 0,1 12,2M9,21A1,1 0 0,0 8,22A1,1 0 0,0 9,23H15A1,1 0 0,0 16,22A1,1 0 0,0 15,21V20H9V21Z"/>
          </svg>
          <strong>操作提示：</strong>
        </div>
        <ul style={{ margin: 0, paddingLeft: '20px' }}>
          <li>鼠标滚轮：缩放图表</li>
          <li>鼠标拖拽：移动查看历史数据</li>
          <li>悬停：查看详细数据</li>
          {historical && historical.length > 0 && (
            <li>💎 紫色菱形：AI历史验证（预测过去14天，对比实际价格验证准确率）</li>
          )}
          {future && future.length > 0 && (
            <li>🔮 橙色圆圈：AI未来预测（预测未来10个交易日趋势）</li>
          )}
        </ul>
      </div>

      {/* 历史预测准确率统计 */}
      {historical && historical.length > 0 && (
        <div style={{
          marginTop: '15px',
          padding: '12px',
          background: '#252836',
          borderRadius: '8px',
          color: '#fff',
          fontSize: '13px'
        }}>
          <div style={{ marginBottom: '8px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <path d="M19,3H5C3.89,3 3,3.89 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V5C21,3.89 20.1,3 19,3M9,17H7V10H9V17M13,17H11V7H13V17M17,17H15V13H17V17Z"/>
            </svg>
            Kronos AI历史验证准确率统计（过去14天）：
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '10px' }}>
            {historical.map((pred, idx) => {
              const accuracyColor = pred.error_pct < 1 ? '#4caf50' : pred.error_pct < 2 ? '#ffb74d' : '#ef5350';
              return (
                <div key={idx} style={{
                  padding: '8px',
                  background: '#1e2130',
                  borderRadius: '6px',
                  borderLeft: `3px solid ${accuracyColor}`
                }}>
                  <div style={{ fontSize: '11px', color: '#8b93a7', marginBottom: '4px' }}>
                    {pred.date}
                  </div>
                  <div style={{ fontSize: '12px' }}>
                    预测: {pred.predicted_price} | 实际: {pred.actual_price}
                  </div>
                  <div style={{ fontSize: '12px', color: accuracyColor, fontWeight: 600 }}>
                    误差: {pred.error_pct}%
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 未来预测展示 */}
      {future && future.length > 0 && (
        <div style={{
          marginTop: '15px',
          padding: '12px',
          background: '#252836',
          borderRadius: '8px',
          color: '#fff',
          fontSize: '13px'
        }}>
          <div style={{ marginBottom: '8px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12,2A2,2 0 0,1 14,4C14,4.74 13.6,5.39 13,5.73V7H14A7,7 0 0,1 21,14H22A1,1 0 0,1 23,15V18A1,1 0 0,1 22,19H21V20A2,2 0 0,1 19,22H5A2,2 0 0,1 3,20V19H2A1,1 0 0,1 1,18V15A1,1 0 0,1 2,14H3A7,7 0 0,1 10,7H11V5.73C10.4,5.39 10,4.74 10,4A2,2 0 0,1 12,2M7.5,13A0.5,0.5 0 0,0 7,13.5A0.5,0.5 0 0,0 7.5,14A0.5,0.5 0 0,0 8,13.5A0.5,0.5 0 0,0 7.5,13M16.5,13A0.5,0.5 0 0,0 16,13.5A0.5,0.5 0 0,0 16.5,14A0.5,0.5 0 0,0 17,13.5A0.5,0.5 0 0,0 16.5,13Z"/>
            </svg>
            AI未来预测（未来10个交易日）：
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '10px' }}>
            {future.map((pred, idx) => (
              <div key={idx} style={{
                padding: '8px',
                background: '#1e2130',
                borderRadius: '6px',
                borderLeft: '3px solid #ff9800'
              }}>
                <div style={{ fontSize: '11px', color: '#8b93a7', marginBottom: '4px' }}>
                  {pred.date}
                </div>
                <div style={{ fontSize: '14px', fontWeight: 600, color: '#ff9800' }}>
                  预测: ¥{pred.predicted_price}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default InteractiveKLineChart;
