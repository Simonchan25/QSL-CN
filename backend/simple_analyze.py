#!/usr/bin/env python3
"""
简化版本的股票分析 - 只获取核心数据，速度优先
"""
from fastapi import FastAPI, HTTPException
import uvicorn
from datetime import datetime, timedelta
import os

# 创建独立的轻量级应用
app = FastAPI(title="快速股票分析服务", version="1.0")

@app.get("/")
def root():
    return {"message": "快速股票分析服务运行中", "version": "1.0"}

@app.get("/analyze")
def analyze_stock(name: str):
    """超快速股票分析 - 3秒内返回"""
    if not name:
        raise HTTPException(400, detail="name 不能为空")

    try:
        # 1. 解析股票基本信息（本地操作，很快）
        from core.analyze import resolve_by_name
        stock_info = resolve_by_name(name)
        if not stock_info:
            return {"error": f"未找到股票: {name}"}

        ts_code = stock_info['ts_code']
        stock_name = stock_info['name']

        # 2. 只获取最新价格数据（最少量数据）
        from core.tushare_client import daily
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=5)).strftime('%Y%m%d')

        df = daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
        if df is None or df.empty:
            return {"error": "无法获取价格数据"}

        # 3. 简单技术分析（本地计算，不调用外部API）
        latest = df.iloc[0]
        current_price = float(latest['close'])
        change_pct = float(latest.get('pct_chg', 0))
        volume = float(latest.get('vol', 0))

        # 计算简单均线
        if len(df) >= 5:
            ma5 = df['close'].head(5).mean()
            trend = "上涨趋势" if current_price > ma5 else "下跌趋势" if current_price < ma5 * 0.98 else "震荡"
        else:
            ma5 = current_price
            trend = "数据不足"

        # 4. 简单评分（基于价格和成交量）
        score = 50  # 基础分
        if change_pct > 3:
            score += 20
        elif change_pct > 0:
            score += 10
        elif change_pct < -3:
            score -= 20
        elif change_pct < 0:
            score -= 10

        if current_price > ma5:
            score += 10

        # 限制评分范围
        score = max(0, min(100, score))

        # 5. 生成快速报告（模板生成，不调用LLM）
        rating = "强烈推荐" if score >= 70 else "推荐" if score >= 60 else "中性" if score >= 50 else "谨慎" if score >= 40 else "回避"

        report_text = f"""# {stock_name} 快速分析报告

**基本信息**
- 股票代码：{ts_code}
- 最新价格：{current_price:.2f}元
- 今日涨跌：{change_pct:+.2f}%
- 成交量：{volume/10000:.1f}万手

**技术分析**
- 价格趋势：{trend}
- 5日均线：{ma5:.2f}元
- 相对位置：{'上方' if current_price > ma5 else '下方'}

**综合评价**
- 综合评分：{score}/100
- 投资建议：{rating}

**操作建议**
{_generate_suggestion(change_pct, current_price, ma5, volume)}

---
*快速分析 - 更新时间: {datetime.now().strftime('%H:%M:%S')}*
*数据来源: {latest.get('trade_date', '')} 交易数据*
"""

        # 构建返回结果
        result = {
            "basic": stock_info,
            "timestamp": datetime.now().isoformat(),
            "price": current_price,
            "change": change_pct,
            "volume": volume,
            "trend": trend,
            "score": {
                "total": score,
                "rating": rating
            },
            "text": report_text,
            "report_type": "fast",
            "data_source": "实时",
            "analysis_time": datetime.now().strftime('%H:%M:%S')
        }

        return result

    except Exception as e:
        print(f"快速分析错误: {e}")
        return {"error": f"分析失败: {str(e)}"}

def _generate_suggestion(change_pct: float, current_price: float, ma5: float, volume: float) -> str:
    """生成操作建议"""
    suggestions = []

    if change_pct > 5:
        suggestions.append("- ⚠️ 涨幅较大，注意获利了结风险")
    elif change_pct > 2:
        suggestions.append("- ✅ 表现良好，可适当关注")
    elif change_pct < -5:
        suggestions.append("- 📉 跌幅较大，可关注反弹机会")
    elif change_pct < -2:
        suggestions.append("- ⚠️ 走势偏弱，谨慎操作")
    else:
        suggestions.append("- 📊 走势平稳，等待明确信号")

    if current_price > ma5:
        suggestions.append("- 📈 价格在均线上方，短期趋势较好")
    else:
        suggestions.append("- 📉 价格在均线下方，需要耐心等待")

    if volume > 50000:  # 5万手以上
        suggestions.append("- 💰 成交活跃，关注度较高")
    else:
        suggestions.append("- 💤 成交平淡，关注度一般")

    return "\n".join(suggestions)

if __name__ == "__main__":
    # 运行在独立端口
    port = int(os.getenv("FAST_PORT", 9001))
    uvicorn.run(app, host="0.0.0.0", port=port)