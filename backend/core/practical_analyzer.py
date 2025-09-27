"""
实用投资分析报告生成器 - 生成简洁、实用、基于最新数据的投资建议
"""
import datetime as dt
from typing import Dict, Any, Optional
import pandas as pd


def generate_practical_report(stock_data: Dict[str, Any], name: str) -> str:
    """
    生成简洁实用的投资报告
    
    重点关注：
    1. 当前价格和估值
    2. 技术趋势和买卖点
    3. 资金流向
    4. 明确的操作建议
    """
    report_lines = []
    
    # 初始化变量
    current_price = None
    pe = None
    rsi = None
    main_net = None
    total_score = 50
    
    # 报告标题
    today = dt.date.today().strftime("%Y-%m-%d")
    report_lines.append(f"# {name} 投资分析报告")
    report_lines.append(f"生成时间：{today}\n")
    
    # 1. 价格和估值
    report_lines.append("## 一、当前价格与估值")
    
    price = stock_data.get("price", {})
    if price:
        current_price = price.get("close", "N/A")
        change_pct = price.get("pct_chg", 0)
        volume = price.get("volume", 0)
        
        report_lines.append(f"- **当前价格**：{current_price}元")
        report_lines.append(f"- **今日涨跌**：{change_pct:+.2f}%")
        report_lines.append(f"- **成交量**：{volume/10000:.1f}万手")
    
    fundamentals = stock_data.get("fundamentals", {})
    if fundamentals:
        pe = fundamentals.get("pe_ttm", "N/A")
        pb = fundamentals.get("pb", "N/A")
        roe = fundamentals.get("roe", "N/A")
        
        report_lines.append(f"- **市盈率(PE)**：{pe}")
        report_lines.append(f"- **市净率(PB)**：{pb}")
        report_lines.append(f"- **ROE**：{roe}%")
        
        # 估值判断
        if isinstance(pe, (int, float)) and pe > 0:
            if pe < 15:
                report_lines.append("- **估值判断**：低估值区间，具有安全边际")
            elif pe < 30:
                report_lines.append("- **估值判断**：合理估值区间")
            else:
                report_lines.append("- **估值判断**：高估值区间，注意风险")
    
    report_lines.append("")
    
    # 2. 技术分析
    report_lines.append("## 二、技术趋势分析")
    
    indicators = stock_data.get("indicators", {})
    if indicators:
        tech_signal = stock_data.get("tech_signal", {})
        
        # MA趋势
        ma5 = indicators.get("MA5", 0)
        ma20 = indicators.get("MA20", 0)
        ma60 = indicators.get("MA60", 0)
        
        if current_price and ma5 and ma20:
            if current_price > ma5 > ma20:
                report_lines.append("- **均线趋势**：多头排列，趋势向上 ↗")
            elif current_price < ma5 < ma20:
                report_lines.append("- **均线趋势**：空头排列，趋势向下 ↘")
            else:
                report_lines.append("- **均线趋势**：震荡整理")
        
        # RSI
        rsi = indicators.get("RSI", 50)
        if rsi:
            if rsi > 70:
                report_lines.append(f"- **RSI指标**：{rsi:.1f} (超买区间，注意回调)")
            elif rsi < 30:
                report_lines.append(f"- **RSI指标**：{rsi:.1f} (超卖区间，可能反弹)")
            else:
                report_lines.append(f"- **RSI指标**：{rsi:.1f} (中性区间)")
        
        # MACD
        macd_signal = tech_signal.get("MACD", {}).get("signal", "中性")
        report_lines.append(f"- **MACD信号**：{macd_signal}")
        
        # 支撑压力位
        support = indicators.get("support_levels", [])
        resistance = indicators.get("resistance_levels", [])
        if support and resistance:
            report_lines.append(f"- **支撑位**：{support[0]:.2f}元")
            report_lines.append(f"- **压力位**：{resistance[0]:.2f}元")
    
    report_lines.append("")
    
    # 3. 资金流向
    report_lines.append("## 三、资金流向分析")
    
    capital_flow = stock_data.get("capital_flow", {})
    if capital_flow:
        # 主力资金
        main_net = capital_flow.get("main_net_amount", 0)
        if main_net:
            if main_net > 0:
                report_lines.append(f"- **主力资金**：净流入 {abs(main_net)/10000:.1f}万元 💰")
            else:
                report_lines.append(f"- **主力资金**：净流出 {abs(main_net)/10000:.1f}万元 💸")
        
        # 北向资金（如果有）
        north_flow = capital_flow.get("north_net", 0)
        if north_flow:
            if north_flow > 0:
                report_lines.append(f"- **北向资金**：净买入 {abs(north_flow)/10000:.1f}万元")
            else:
                report_lines.append(f"- **北向资金**：净卖出 {abs(north_flow)/10000:.1f}万元")
    
    # 龙虎榜
    dragon_tiger = stock_data.get("dragon_tiger", {})
    if dragon_tiger and dragon_tiger.get("on_list"):
        report_lines.append("- **龙虎榜**：今日上榜，游资关注度高")
    
    report_lines.append("")
    
    # 4. 综合评分
    report_lines.append("## 四、综合评分")
    
    scorecard = stock_data.get("scorecard", {})
    if scorecard:
        total_score = scorecard.get("总分", 50)
        tech_score = scorecard.get("技术", {}).get("score", 0)
        sentiment_score = scorecard.get("情绪", {}).get("score", 0)
        fundamental_score = scorecard.get("基本面", {}).get("score", 0)
        
        report_lines.append(f"- **综合评分**：{total_score}/100")
        report_lines.append(f"- **技术面**：{tech_score}/40")
        report_lines.append(f"- **市场情绪**：{sentiment_score}/35")
        report_lines.append(f"- **基本面**：{fundamental_score}/20")
        
        # 评分解读
        if total_score >= 70:
            report_lines.append("- **评级**：强烈推荐 ⭐⭐⭐⭐⭐")
        elif total_score >= 60:
            report_lines.append("- **评级**：推荐 ⭐⭐⭐⭐")
        elif total_score >= 50:
            report_lines.append("- **评级**：中性 ⭐⭐⭐")
        else:
            report_lines.append("- **评级**：谨慎 ⭐⭐")
    
    report_lines.append("")
    
    # 5. 操作建议
    report_lines.append("## 五、操作建议")
    
    # 基于数据生成操作建议
    suggestions = []
    
    # 根据技术信号
    if indicators and current_price:
        if current_price > ma20 and rsi < 70:
            suggestions.append("**趋势策略**：股价在均线上方，可持股待涨")
        elif current_price < ma20 and rsi > 30:
            suggestions.append("**趋势策略**：股价在均线下方，建议观望")
        
        if rsi and rsi < 30:
            suggestions.append("**抄底机会**：RSI进入超卖区，可考虑分批建仓")
        elif rsi and rsi > 70:
            suggestions.append("**获利了结**：RSI进入超买区，建议减仓锁利")
    
    # 根据资金流向
    if capital_flow and main_net:
        if main_net > 10000000:  # 主力净流入超1000万
            suggestions.append("**资金信号**：主力大幅流入，短期看涨")
        elif main_net < -10000000:
            suggestions.append("**资金信号**：主力大幅流出，注意风险")
    
    # 根据综合评分
    if scorecard:
        if total_score >= 65:
            suggestions.append("**综合建议**：各项指标向好，可积极操作")
        elif total_score <= 45:
            suggestions.append("**综合建议**：指标偏弱，建议降低仓位")
        else:
            suggestions.append("**综合建议**：指标中性，高抛低吸为主")
    
    # 输出建议
    if suggestions:
        for suggestion in suggestions:
            report_lines.append(f"- {suggestion}")
    else:
        report_lines.append("- **综合建议**：缺少足够数据，建议谨慎操作")
    
    # 风险提示
    report_lines.append("\n### 风险提示")
    if isinstance(pe, (int, float)) and pe > 50:
        report_lines.append("- ⚠️ 市盈率偏高，注意估值风险")
    if rsi and rsi > 80:
        report_lines.append("- ⚠️ 技术指标超买严重，防止追高")
    if main_net and main_net < -50000000:
        report_lines.append("- ⚠️ 主力资金大幅流出，注意下跌风险")
    
    report_lines.append("\n---")
    report_lines.append("*免责声明：本报告仅供参考，不构成投资建议。投资有风险，入市需谨慎。*")
    
    return "\n".join(report_lines)


def generate_quick_summary(stock_data: Dict[str, Any], name: str) -> Dict[str, Any]:
    """生成快速摘要（JSON格式）"""
    
    price = stock_data.get("price", {})
    indicators = stock_data.get("indicators", {})
    scorecard = stock_data.get("scorecard", {})
    capital_flow = stock_data.get("capital_flow", {})
    
    # 判断买卖信号
    signal = "持有"
    if scorecard.get("总分", 50) >= 65:
        signal = "买入"
    elif scorecard.get("总分", 50) <= 40:
        signal = "卖出"
    
    # 计算目标价
    current_price = price.get("close", 0)
    resistance = indicators.get("resistance_levels", [current_price * 1.1])
    support = indicators.get("support_levels", [current_price * 0.9])
    
    return {
        "stock_name": name,
        "current_price": current_price,
        "change_pct": price.get("pct_chg", 0),
        "signal": signal,
        "score": scorecard.get("总分", 50),
        "target_price": resistance[0] if resistance else current_price * 1.1,
        "stop_loss": support[0] if support else current_price * 0.95,
        "main_flow": capital_flow.get("main_net_amount", 0),
        "recommendation": signal,
        "risk_level": "高" if scorecard.get("总分", 50) < 40 else "中" if scorecard.get("总分", 50) < 60 else "低",
        "update_time": dt.datetime.now().isoformat()
    }