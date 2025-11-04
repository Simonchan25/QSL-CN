import React, { useMemo } from 'react';

/**
 * 股票K线图组件
 * 包含：K线图 + 均线 + 成交量
 */
const StockChart = ({ prices = [], indicators = {}, stockName = '' }) => {
  // 计算图表数据
  const chartData = useMemo(() => {
    if (!prices || prices.length === 0) {
      return null;
    }

    // 只显示最近60天的数据
    const displayPrices = prices.slice(0, 60).reverse();

    // 计算价格范围
    const allPrices = displayPrices.flatMap(p => [p.high, p.low]);
    const maxPrice = Math.max(...allPrices);
    const minPrice = Math.min(...allPrices);
    const priceRange = maxPrice - minPrice;
    const pricePadding = priceRange * 0.1;

    // 计算成交量范围
    const volumes = displayPrices.map(p => p.amount || 0);
    const maxVolume = Math.max(...volumes);

    return {
      displayPrices,
      maxPrice: maxPrice + pricePadding,
      minPrice: minPrice - pricePadding,
      maxVolume,
      priceRange: priceRange + 2 * pricePadding
    };
  }, [prices]);

  if (!chartData) {
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

  const { displayPrices, maxPrice, minPrice, maxVolume, priceRange } = chartData;

  // 图表尺寸
  const width = 1000;
  const height = 500;
  const volumeHeight = 100;
  const padding = { top: 20, right: 80, bottom: 30, left: 10 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom - volumeHeight;
  const candleWidth = Math.max(3, Math.min(12, chartWidth / displayPrices.length - 2));

  // 坐标转换函数
  const priceToY = (price) => {
    return padding.top + ((maxPrice - price) / priceRange) * chartHeight;
  };

  const volumeToHeight = (volume) => {
    return (volume / maxVolume) * volumeHeight * 0.8;
  };

  // 格式化日期
  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    const str = String(dateStr);
    return `${str.slice(4, 6)}/${str.slice(6, 8)}`;
  };

  // 格式化价格
  const formatPrice = (price) => {
    return price.toFixed(2);
  };

  return (
    <div style={{
      background: 'linear-gradient(135deg, #1a1d29 0%, #252836 100%)',
      borderRadius: '12px',
      padding: '20px',
      marginBottom: '20px',
      boxShadow: '0 4px 20px rgba(0,0,0,0.3)'
    }}>
      {/* 标题 */}
      <div style={{
        color: '#fff',
        fontSize: '18px',
        fontWeight: '600',
        marginBottom: '15px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
            <path d="M16,11.78L20.24,4.45L21.97,5.45L16.74,14.5L10.23,10.75L5.46,19H22V21H2V3H4V17.54L9.5,8L16,11.78Z"/>
          </svg>
          {stockName} - 日K线图 (最近60天)
        </span>
        <div style={{ fontSize: '14px', color: '#8b93a7' }}>
          <span style={{ marginRight: '15px' }}>
            <span style={{ color: '#ef5350' }}>━</span> 涨
          </span>
          <span style={{ marginRight: '15px' }}>
            <span style={{ color: '#26a69a' }}>━</span> 跌
          </span>
          <span>
            <span style={{ color: '#ffb74d' }}>━</span> MA5
          </span>
        </div>
      </div>

      {/* K线图SVG */}
      <svg
        width={width}
        height={height}
        style={{
          background: '#1e2130',
          borderRadius: '8px',
          display: 'block'
        }}
      >
        {/* 网格线 */}
        {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
          const y = padding.top + chartHeight * ratio;
          const price = maxPrice - priceRange * ratio;
          return (
            <g key={ratio}>
              <line
                x1={padding.left}
                y1={y}
                x2={width - padding.right}
                y2={y}
                stroke="#2a2e3f"
                strokeWidth="1"
                strokeDasharray="4,4"
              />
              <text
                x={width - padding.right + 10}
                y={y + 4}
                fill="#6b7280"
                fontSize="12"
              >
                {formatPrice(price)}
              </text>
            </g>
          );
        })}

        {/* K线 */}
        {displayPrices.map((price, index) => {
          const x = padding.left + (index * (chartWidth / displayPrices.length)) + candleWidth;
          const openY = priceToY(price.open);
          const closeY = priceToY(price.close);
          const highY = priceToY(price.high);
          const lowY = priceToY(price.low);

          const isRise = price.close >= price.open;
          const color = isRise ? '#ef5350' : '#26a69a';
          const bodyTop = Math.min(openY, closeY);
          const bodyHeight = Math.abs(closeY - openY) || 1;

          return (
            <g key={index}>
              {/* 上下影线 */}
              <line
                x1={x + candleWidth / 2}
                y1={highY}
                x2={x + candleWidth / 2}
                y2={lowY}
                stroke={color}
                strokeWidth="1"
              />
              {/* K线实体 */}
              <rect
                x={x}
                y={bodyTop}
                width={candleWidth}
                height={bodyHeight}
                fill={isRise ? color : '#1e2130'}
                stroke={color}
                strokeWidth="1"
              />

              {/* 日期标签 (每10天显示一次) */}
              {index % 10 === 0 && (
                <text
                  x={x + candleWidth / 2}
                  y={height - volumeHeight - 5}
                  fill="#6b7280"
                  fontSize="10"
                  textAnchor="middle"
                >
                  {formatDate(price.trade_date)}
                </text>
              )}
            </g>
          );
        })}

        {/* MA5均线 */}
        {displayPrices.length > 5 && (
          <polyline
            points={displayPrices
              .map((price, index) => {
                if (index < 4) return null;
                const ma5 = displayPrices
                  .slice(index - 4, index + 1)
                  .reduce((sum, p) => sum + p.close, 0) / 5;
                const x = padding.left + (index * (chartWidth / displayPrices.length)) + candleWidth + candleWidth / 2;
                const y = priceToY(ma5);
                return `${x},${y}`;
              })
              .filter(Boolean)
              .join(' ')}
            fill="none"
            stroke="#ffb74d"
            strokeWidth="1.5"
            opacity="0.8"
          />
        )}

        {/* 成交量 */}
        {displayPrices.map((price, index) => {
          const x = padding.left + (index * (chartWidth / displayPrices.length)) + candleWidth;
          const volHeight = volumeToHeight(price.amount || 0);
          const y = height - volumeHeight + (volumeHeight * 0.2) + (volumeHeight * 0.8 - volHeight);
          const isRise = price.close >= price.open;
          const color = isRise ? '#ef5350' : '#26a69a';

          return (
            <rect
              key={`vol-${index}`}
              x={x}
              y={y}
              width={candleWidth}
              height={volHeight}
              fill={color}
              opacity="0.6"
            />
          );
        })}

        {/* 成交量标签 */}
        <text
          x={padding.left}
          y={height - volumeHeight + 15}
          fill="#6b7280"
          fontSize="12"
        >
          成交量
        </text>

        {/* 最新价格标签 */}
        {displayPrices.length > 0 && (
          <g>
            <rect
              x={width - padding.right}
              y={priceToY(displayPrices[displayPrices.length - 1].close) - 12}
              width={70}
              height={24}
              fill={displayPrices[displayPrices.length - 1].close >= displayPrices[displayPrices.length - 2]?.close ? '#ef5350' : '#26a69a'}
              rx="4"
            />
            <text
              x={width - padding.right + 35}
              y={priceToY(displayPrices[displayPrices.length - 1].close) + 4}
              fill="#fff"
              fontSize="12"
              fontWeight="bold"
              textAnchor="middle"
            >
              {formatPrice(displayPrices[displayPrices.length - 1].close)}
            </text>
          </g>
        )}
      </svg>

      {/* 图表说明 */}
      <div style={{
        marginTop: '15px',
        padding: '12px',
        background: '#252836',
        borderRadius: '8px',
        color: '#8b93a7',
        fontSize: '13px',
        display: 'flex',
        justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
            <path d="M19,3H5C3.89,3 3,3.89 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V5C21,3.89 20.1,3 19,3M9,17H7V10H9V17M13,17H11V7H13V17M17,17H15V13H17V17Z"/>
          </svg>
          显示最近 {displayPrices.length} 个交易日
        </div>
        <div>
          {displayPrices.length > 0 && (
            <>
              最高: <span style={{ color: '#ef5350', fontWeight: '600' }}>
                {formatPrice(Math.max(...displayPrices.map(p => p.high)))}
              </span>
              {' | '}
              最低: <span style={{ color: '#26a69a', fontWeight: '600' }}>
                {formatPrice(Math.min(...displayPrices.map(p => p.low)))}
              </span>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default StockChart;
