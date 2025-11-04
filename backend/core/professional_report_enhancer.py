"""
专业报告增强模块
根据用户反馈，提升报告的专业性和深度
"""
from typing import Dict, Any, List, Tuple
import numpy as np


def enhance_technical_analysis(technical: Dict, prices: List[Dict], indicators: Dict) -> str:
    """
    增强技术面分析
    补充：成交量趋势、K线形态、支撑压力位、相对市场表现
    """
    parts = []

    if not prices or len(prices) < 5:
        return "技术数据不足，无法进行深度分析"

    current_price = prices[0].get('close', 0)
    prev_prices = [p.get('close', 0) for p in prices[1:6]]

    # 1. 成交量分析
    volumes = [p.get('amount', 0) for p in prices[:10]]
    if volumes and volumes[0] > 0:
        avg_volume = np.mean(volumes[1:6])
        vol_ratio = volumes[0] / avg_volume if avg_volume > 0 else 1

        if vol_ratio > 2:
            vol_desc = f"📈 **放量突破**: 今日成交额较5日均值放大{vol_ratio:.1f}倍，资金追捧明显"
        elif vol_ratio > 1.5:
            vol_desc = f"📊 **温和放量**: 成交额较均值增加{(vol_ratio-1)*100:.0f}%，关注度提升"
        elif vol_ratio < 0.5:
            vol_desc = f"📉 **成交萎缩**: 成交额仅为均值的{vol_ratio*100:.0f}%，市场观望情绪浓厚"
        else:
            vol_desc = f"📊 **量能平稳**: 成交额维持常态水平"

        parts.append(vol_desc)

    # 2. K线形态识别
    if len(prices) >= 3:
        p0, p1, p2 = prices[0], prices[1], prices[2]
        close0, close1, close2 = p0.get('close', 0), p1.get('close', 0), p2.get('close', 0)
        high0, low0 = p0.get('high', close0), p0.get('low', close0)

        # 判断趋势
        if close0 > close1 > close2:
            trend_desc = "🔺 **连续上涨**: 三连阳形态，多头气势如虹"
        elif close0 < close1 < close2:
            trend_desc = "🔻 **连续下跌**: 三连阴形态，空头压制明显"
        elif close0 > close1 and close1 < close2:
            trend_desc = "📈 **V型反转**: 快速回升，可能形成底部反弹"
        elif close0 < close1 and close1 > close2:
            trend_desc = "📉 **倒V反转**: 冲高回落，短期见顶风险"
        else:
            trend_desc = "📊 **震荡整理**: K线形态不明朗，等待方向选择"

        parts.append(trend_desc)

    # 3. 支撑压力位计算
    ma5 = indicators.get('MA5', 0)
    ma10 = indicators.get('MA10', 0)
    ma20 = indicators.get('MA20', 0)

    if ma5 > 0 and ma20 > 0:
        support_levels = []
        resistance_levels = []

        # 均线支撑/压力
        if current_price > ma5:
            support_levels.append(f"MA5({ma5:.2f}元)")
        else:
            resistance_levels.append(f"MA5({ma5:.2f}元)")

        if current_price > ma20:
            support_levels.append(f"MA20({ma20:.2f}元)")
        else:
            resistance_levels.append(f"MA20({ma20:.2f}元)")

        # 近期高低点
        if len(prices) >= 20:
            recent_highs = [p.get('high', 0) for p in prices[:20]]
            recent_lows = [p.get('low', 0) for p in prices[:20]]
            max_high = max(recent_highs)
            min_low = min(recent_lows)

            if current_price < max_high * 0.95:
                resistance_levels.append(f"近期高点({max_high:.2f}元)")
            if current_price > min_low * 1.05:
                support_levels.append(f"近期低点({min_low:.2f}元)")

        parts.append(f"🎯 **关键位置**: 支撑 {' / '.join(support_levels[:2])}，压力 {' / '.join(resistance_levels[:2])}")
        parts.append(f"⚠️ **风险提示**: 若跌破{support_levels[0] if support_levels else 'MA20'}，走势将转弱")

    # 4. 技术指标综合判断
    rsi = indicators.get('RSI', 50)
    macd = indicators.get('MACD', 0)
    dif = indicators.get('DIF', 0)
    dea = indicators.get('DEA', 0)

    signal_count = 0
    signals = []

    if rsi > 70:
        signals.append("RSI超买(警惕回调)")
        signal_count -= 1
    elif rsi < 30:
        signals.append("RSI超卖(关注反弹)")
        signal_count += 1

    if dif > dea and macd > 0:
        signals.append("MACD金叉+零轴上方(强势)")
        signal_count += 2
    elif dif < dea and macd < 0:
        signals.append("MACD死叉+零轴下方(弱势)")
        signal_count -= 2

    if ma5 > ma10 > ma20:
        signals.append("均线多头排列(趋势向上)")
        signal_count += 1
    elif ma5 < ma10 < ma20:
        signals.append("均线空头排列(趋势向下)")
        signal_count -= 1

    if signal_count >= 2:
        tech_verdict = "✅ **技术面偏强**: " + "、".join(signals)
    elif signal_count <= -2:
        tech_verdict = "❌ **技术面偏弱**: " + "、".join(signals)
    else:
        tech_verdict = "⚖️ **技术面中性**: " + "、".join(signals)

    parts.append(tech_verdict)

    return "\n".join(parts)


def enhance_fundamental_analysis(fundamental: Dict) -> str:
    """
    增强基本面分析
    补充：盈利质量、现金流、资产负债结构
    """
    parts = []

    # 财务指标
    latest_metrics = fundamental.get('fina_indicator_latest', {})
    income = fundamental.get('income_latest', {})
    balance = fundamental.get('balancesheet_latest', {})
    cashflow = fundamental.get('cashflow_latest', {})

    # 1. 盈利能力分析
    roe = latest_metrics.get('roe')
    net_margin = latest_metrics.get('netprofit_margin')
    gross_margin = latest_metrics.get('grossprofit_margin')

    if roe:
        parts.append(f"💰 **ROE**: {roe:.2f}% " + (
            "(优秀)" if roe > 15 else "(良好)" if roe > 10 else "(一般)" if roe > 5 else "(偏低)"
        ))

    if gross_margin:
        parts.append(f"📊 **毛利率**: {gross_margin:.2f}% " + (
            "(高毛利业务)" if gross_margin > 40 else "(中等水平)" if gross_margin > 20 else "(低毛利)"
        ))

    if net_margin:
        parts.append(f"💵 **净利率**: {net_margin:.2f}% " + (
            "(盈利能力强)" if net_margin > 15 else "(盈利能力中等)" if net_margin > 5 else "(盈利能力弱)"
        ))

    # 2. 现金流分析
    if income and cashflow:
        net_profit = income.get('n_income', 0)
        op_cashflow = cashflow.get('n_cashflow_act', 0)

        if net_profit > 0 and op_cashflow > 0:
            cash_quality = op_cashflow / net_profit
            parts.append(f"💸 **现金流质量**: 经营现金流/净利润 = {cash_quality:.2f} " + (
                "(优秀，现金回流充裕)" if cash_quality > 1.2 else
                "(良好)" if cash_quality > 0.8 else
                "(一般，需关注应收账款)" if cash_quality > 0.5 else
                "(警惕，盈利含金量低)"
            ))

    # 3. 资产负债分析
    if balance:
        total_assets = balance.get('total_assets', 0)
        total_liab = balance.get('total_liab', 0)

        if total_assets > 0:
            debt_ratio = (total_liab / total_assets) * 100
            parts.append(f"🏦 **资产负债率**: {debt_ratio:.1f}% " + (
                "(偏高，杠杆风险)" if debt_ratio > 70 else
                "(适中)" if debt_ratio > 30 else
                "(较低，财务稳健)"
            ))

            # 流动比率
            current_assets = balance.get('total_cur_assets', 0)
            current_liab = balance.get('total_cur_liab', 0)
            if current_liab > 0:
                current_ratio = current_assets / current_liab
                parts.append(f"💳 **流动比率**: {current_ratio:.2f} " + (
                    "(短期偿债能力强)" if current_ratio > 2 else
                    "(短期偿债能力一般)" if current_ratio > 1 else
                    "(短期偿债压力大)"
                ))

    # 4. 成长性分析
    revenue = income.get('revenue', 0)
    revenue_yoy = latest_metrics.get('or_yoy')  # 营收同比增长率

    if revenue_yoy is not None:
        parts.append(f"📈 **营收增速**: {revenue_yoy:.2f}% " + (
            "(高成长)" if revenue_yoy > 30 else
            "(稳健增长)" if revenue_yoy > 10 else
            "(低速增长)" if revenue_yoy > 0 else
            "(营收下滑)"
        ))

    return "\n\n".join(parts) if parts else "基本面数据不足"


def enhance_valuation_analysis(fundamental: Dict, technical: Dict, industry: str = "") -> str:
    """
    增强估值分析
    补充：PE/PB/PS与行业对比
    """
    parts = []

    # 从daily_basic获取估值数据
    latest_price_info = technical.get('latest_price_info', {})
    latest_basic = technical.get('latest_basic', {})

    pe_ttm = latest_price_info.get('pe_ttm', 0) or latest_basic.get('pe_ttm', 0)
    pb = latest_price_info.get('pb', 0) or latest_basic.get('pb', 0)
    ps_ttm = latest_price_info.get('ps_ttm', 0) or latest_basic.get('ps_ttm', 0)

    # 如果还是没有，尝试从fundamental获取
    if not pe_ttm:
        fina_latest = fundamental.get('fina_indicator_latest', {})
        pe_ttm = fina_latest.get('pe_ttm', 0) or fina_latest.get('pe', 0)

    # 行业平均估值（简化版，实际应从数据库获取）
    industry_avg_pe = {
        '互联网': 35,
        '医药生物': 40,
        '电子': 45,
        '计算机': 50,
        '食品饮料': 30,
        '银行': 6,
        '房地产': 8,
        '汽车': 15,
    }

    avg_pe = industry_avg_pe.get(industry, 25)

    if pe_ttm and pe_ttm > 0:
        pe_vs_industry = ((pe_ttm - avg_pe) / avg_pe) * 100
        parts.append(f"📊 **市盈率(PE-TTM)**: {pe_ttm:.1f}倍")
        parts.append(f"   行业均值约{avg_pe}倍，当前" + (
            f"**高估{abs(pe_vs_industry):.0f}%**" if pe_vs_industry > 20 else
            f"**低估{abs(pe_vs_industry):.0f}%**" if pe_vs_industry < -20 else
            f"处于合理区间({pe_vs_industry:+.0f}%)"
        ))

    if pb and pb > 0:
        parts.append(f"📈 **市净率(PB)**: {pb:.2f}倍" + (
            " (破净，严重低估)" if pb < 1 else
            " (估值合理)" if pb < 3 else
            " (估值偏高)" if pb < 5 else
            " (估值泡沫)"
        ))

    if ps_ttm and ps_ttm > 0:
        parts.append(f"💹 **市销率(PS)**: {ps_ttm:.2f}倍")

    # 估值安全边际
    fundamental_data = fundamental.get('fina_indicator_latest', {})
    roe = fundamental_data.get('roe', 0)

    if pe_ttm > 0 and roe > 0:
        peg = pe_ttm / roe if roe > 0 else 999
        parts.append(f"🎯 **PEG指标**: {peg:.2f} " + (
            "(相对低估，成长性支撑估值)" if peg < 1 else
            "(估值合理)" if peg < 1.5 else
            "(相对高估，成长性不足以支撑估值)"
        ))

    return "\n".join(parts) if parts else "估值数据不足"


def enhance_news_analysis(news_data: Dict) -> str:
    """
    深化新闻分析
    补充：具体事件、情绪风险提示
    """
    parts = []

    sentiment = news_data.get('sentiment', {})
    overall = sentiment.get('overall', 'neutral')
    percentages = sentiment.get('percentages', {})
    news_count = sentiment.get('news_count', 0)

    # 新闻数量判断
    if news_count == 0:
        parts.append(f"📰 **媒体关注度**: 暂无相关新闻")
        parts.append(f"📊 **情绪分布**: 数据不足，无法分析")
        return "\n".join(parts)
    elif news_count >= 10:
        parts.append(f"📰 **媒体关注度**: 高 ({news_count}条相关新闻)")
    elif news_count >= 5:
        parts.append(f"📰 **媒体关注度**: 中等 ({news_count}条)")
    else:
        parts.append(f"📰 **媒体关注度**: 较低 ({news_count}条)")

    # 情绪分布
    pos_pct = percentages.get('positive', 0)
    neg_pct = percentages.get('negative', 0)

    parts.append(f"📊 **情绪分布**: 正面{pos_pct:.0f}% / 中性{percentages.get('neutral', 0):.0f}% / 负面{neg_pct:.0f}%")

    # 情绪风险提示
    if pos_pct >= 80:
        parts.append("⚠️ **情绪风险**: 市场情绪过度一致，警惕情绪反转形成短期顶部")
    elif neg_pct >= 60:
        parts.append("💡 **反向机会**: 负面情绪集中释放，可能形成超跌反弹机会")

    # 具体新闻事件（如果有）
    matched_news = news_data.get('matched_news', [])
    if matched_news:
        top_news = matched_news[:3]
        parts.append("\n📌 **重点新闻**:")
        for i, news in enumerate(top_news, 1):
            title = news.get('title', '')
            if title:
                parts.append(f"   {i}. {title[:50]}...")

    return "\n".join(parts)


def enhance_risk_assessment(result: Dict) -> str:
    """
    细化风险评估
    补充：行业风险、政策风险、公司治理风险、流动性风险
    """
    parts = []

    basic = result.get('basic', {})
    technical = result.get('technical', {})
    fundamental = result.get('fundamental', {})
    score = result.get('score', {})

    industry = basic.get('industry', '')

    # 1. 行业风险
    industry_risks = {
        '互联网': "受宏观经济波动影响较大，用户增长见顶风险",
        '医药生物': "政策集采降价风险，研发失败风险",
        '房地产': "政策调控风险，债务风险",
        '银行': "经济下行导致不良贷款上升风险",
        '化工': "原材料价格波动风险，环保政策风险",
        '电子': "技术迭代快，产品更新换代风险",
    }

    if industry in industry_risks:
        parts.append(f"🏭 **行业风险**: {industry_risks[industry]}")

    # 2. 估值风险
    latest_price_info = technical.get('latest_price_info', {})
    pe = latest_price_info.get('pe_ttm', 0)

    if pe > 50:
        parts.append(f"💰 **估值风险**: PE {pe:.1f}倍处于高位，存在估值回归风险")

    # 3. 流动性风险
    volume = technical.get('latest_price_info', {}).get('amount', 0)
    if volume > 0 and volume < 100000000:  # 成交额小于1亿
        parts.append(f"💧 **流动性风险**: 日成交额{volume/100000000:.2f}亿，筹码集中，容易大幅波动")

    # 4. 财务风险
    balance = fundamental.get('balancesheet_latest', {})
    if balance:
        total_assets = balance.get('total_assets', 0)
        total_liab = balance.get('total_liab', 0)
        if total_assets > 0:
            debt_ratio = (total_liab / total_assets) * 100
            if debt_ratio > 70:
                parts.append(f"⚠️ **财务风险**: 资产负债率{debt_ratio:.1f}%偏高，杠杆风险需关注")

    # 5. 综合风险评级
    total_score = score.get('total', 50)
    if total_score >= 70:
        risk_level = "较低"
        risk_color = "🟢"
    elif total_score >= 50:
        risk_level = "中等"
        risk_color = "🟡"
    else:
        risk_level = "较高"
        risk_color = "🔴"

    parts.append(f"\n{risk_color} **综合风险等级**: {risk_level}")

    return "\n".join(parts)


def generate_investment_strategy(score: Dict, technical: Dict, fundamental: Dict) -> str:
    """
    优化投资策略
    按投资者类型分类，明确止损止盈
    """
    total_score = score.get('total', 50)
    tech_score = score.get('details', {}).get('technical', 50)
    fund_score = score.get('details', {}).get('fundamental', 50)

    current_price = technical.get('latest_price', 0)
    ma20 = technical.get('indicators', {}).get('MA20', 0)

    parts = []

    # 1. 短线交易者策略
    parts.append("### 📈 短线交易者 (1-7天)")
    if tech_score >= 70:
        parts.append("- **操作建议**: 技术面强势，可适度参与")
        parts.append(f"- **止损位**: {current_price * 0.95:.2f}元 (-5%)")
        parts.append(f"- **止盈位**: {current_price * 1.08:.2f}元 (+8%)")
        parts.append("- **关注**: 成交量是否持续放大，RSI是否超买")
    else:
        parts.append("- **操作建议**: 技术面偏弱，暂时观望")
        parts.append("- **等待信号**: 放量突破关键均线")

    # 2. 波段投资者策略
    parts.append("\n### 📊 波段投资者 (1-3个月)")
    if total_score >= 60:
        parts.append("- **操作建议**: 综合面良好，可分批建仓")
        parts.append(f"- **止损位**: {ma20:.2f}元 (跌破MA20)")
        parts.append(f"- **目标位**: {current_price * 1.15:.2f}-{current_price * 1.25:.2f}元")
        parts.append("- **仓位**: 10-20%试探性建仓")
    else:
        parts.append("- **操作建议**: 等待更好的介入时机")
        parts.append("- **关注**: 基本面改善或技术面企稳")

    # 3. 价值投资者策略
    parts.append("\n### 💎 价值投资者 (6个月+)")
    if fund_score >= 60:
        parts.append("- **操作建议**: 基本面优秀，适合长期配置")
        parts.append("- **建仓策略**: 分3-5次定投，降低成本")
        parts.append(f"- **长期目标**: {current_price * 1.5:.2f}元 (+50%)")
        parts.append("- **持有周期**: 1-3年")
    else:
        parts.append("- **操作建议**: 基本面偏弱，不适合长期持有")
        parts.append("- **等待条件**: ROE提升至15%+，营收增速转正")

    return "\n".join(parts)


def generate_enhanced_summary(result: Dict) -> str:
    """
    生成三句话总结 + 前瞻观测点
    """
    score = result.get('score', {})
    details = score.get('details', {})

    total_score = score.get('total', 50)
    tech_score = details.get('technical', 50)
    fund_score = details.get('fundamental', 50)
    news_score = details.get('news', 50)

    # 三句话总结
    # 第一句：亮点
    if tech_score >= 70 and news_score >= 70:
        highlight = "**技术面与情绪面共振向上**，短期资金追捧明显，趋势强势"
    elif fund_score >= 70:
        highlight = "**基本面扎实**，盈利能力优秀，具备长期投资价值"
    elif tech_score >= 60:
        highlight = "**技术面偏强**，存在短线交易机会"
    else:
        highlight = "**综合面偏弱**，暂无明显亮点"

    # 第二句：风险
    if fund_score < 40:
        risk = "但**基本面偏弱**，ROE不足，盈利能力有待提升，长期价值存疑"
    elif tech_score < 40:
        risk = "但**技术面走弱**，短期承压明显，需等待企稳信号"
    elif total_score < 50:
        risk = "**综合评分偏低**，多维度风险并存，需谨慎对待"
    else:
        risk = "**风险相对可控**，但仍需关注市场环境变化"

    # 第三句：策略
    if total_score >= 70:
        strategy = "**建议积极关注**，短线可参与，中长线需跟踪基本面改善"
    elif total_score >= 60:
        strategy = "**建议谨慎参与**，适合波段操作，严格止损"
    elif total_score >= 50:
        strategy = "**建议观望为主**，等待更明确的趋势信号"
    else:
        strategy = "**建议暂时回避**，等待基本面改善或技术面企稳后再介入"

    summary = f"""
### 🎯 三句话总结

1. {highlight}
2. {risk}
3. {strategy}

### 🔮 未来关键观测点

- **下次财报发布** (季报/年报)：关注营收增速、ROE变化
- **技术面观测**：是否有效突破/跌破关键均线(MA20/MA60)
- **情绪面观测**：北向资金流向、机构调研频次
- **宏观环境**：货币政策、行业政策变化
- **公司动态**：大股东增减持、重大合同签订、产品发布
"""

    return summary


def analyze_kronos_predictions(predictions: Dict, current_price: float, stock_name: str) -> str:
    """
    分析Kronos AI预测结果，生成专业解读

    Args:
        predictions: 包含historical和future的预测数据
        current_price: 当前价格
        stock_name: 股票名称

    Returns:
        Kronos预测分析报告文本
    """
    if not predictions:
        return ""

    historical = predictions.get('historical', [])
    future = predictions.get('future', [])

    parts = []
    parts.append("\n## 🤖 Kronos AI深度预测分析\n")

    # 初始化accuracy变量（如果没有历史数据，默认为0）
    accuracy = 0
    avg_error_rate = 0

    # 1. 历史验证准确率分析
    if historical and len(historical) > 0:
        total_error = 0
        valid_count = 0
        max_error_rate = 0

        for pred in historical:
            actual = pred.get('actual_price')
            predicted = pred.get('predicted_price')
            if actual and predicted and actual > 0:
                error_rate = abs(predicted - actual) / actual * 100
                total_error += error_rate
                valid_count += 1
                max_error_rate = max(max_error_rate, error_rate)

        if valid_count > 0:
            avg_error_rate = total_error / valid_count

            # 计算真实准确率：误差<2%的天数比例
            accurate_days = sum(1 for pred in historical
                              if pred.get('actual_price') and pred.get('predicted_price')
                              and pred.get('actual_price') > 0
                              and abs(pred.get('predicted_price') - pred.get('actual_price')) / pred.get('actual_price') * 100 < 2.0)
            accuracy_rate = accurate_days / valid_count * 100

            # 基于平均误差率的评级（更诚实的标准）
            if avg_error_rate <= 1.5:
                rating = "🌟 **卓越**"
                confidence = "极高"
            elif avg_error_rate <= 3.0:
                rating = "✨ **优秀**"
                confidence = "高"
            elif avg_error_rate <= 5.0:
                rating = "✅ **良好**"
                confidence = "较高"
            elif avg_error_rate <= 8.0:
                rating = "📊 **一般**"
                confidence = "中等"
            else:
                rating = "⚠️ **偏低**"
                confidence = "较低"

            parts.append(f"### 📊 模型验证（过去{valid_count}天回测）\n")
            parts.append(f"**Kronos深度学习模型**基于Transformer架构，使用时间序列预测算法，对{stock_name}进行了{valid_count}天的历史回测验证：\n")
            parts.append(f"- **平均预测误差**: ±{avg_error_rate:.2f}% {rating}")
            parts.append(f"- **最大单日误差**: {max_error_rate:.2f}%")
            parts.append(f"- **精准预测天数**: {accurate_days}/{valid_count}天 (误差<2%)")
            parts.append(f"- **误差金额**: 平均约±{total_error/valid_count*current_price/100:.2f}元/股")
            parts.append(f"- **模型可信度**: {confidence}")
            parts.append(f"- **回测样本量**: {valid_count}个交易日")

            # 添加诚实的模型表现说明
            if avg_error_rate <= 3.0:
                parts.append(f"\n💡 **模型表现**：平均误差{avg_error_rate:.2f}%，表明Kronos模型对{stock_name}的短期价格预测能力优秀，可作为重要参考依据。")
            elif avg_error_rate <= 5.0:
                parts.append(f"\n💡 **模型表现**：平均误差{avg_error_rate:.2f}%，模型预测具有较高参考价值，建议配合其他技术指标综合判断。")
            elif avg_error_rate <= 8.0:
                parts.append(f"\n💡 **模型表现**：平均误差{avg_error_rate:.2f}%，预测精度一般，建议作为辅助参考，不宜单独作为决策依据。")
            else:
                parts.append(f"\n💡 **模型表现**：平均误差{avg_error_rate:.2f}%，当前市场波动较大，建议谨慎参考AI预测，以基本面和技术面分析为主。")
            parts.append("")

    # 2. 未来趋势预测分析
    if future and len(future) > 0:
        parts.append(f"### 🔮 未来{len(future)}日AI预测\n")

        first_pred = future[0].get('predicted_price', current_price)
        last_pred = future[-1].get('predicted_price', current_price)

        # 计算预测趋势
        pred_change = (last_pred - current_price) / current_price * 100
        pred_direction = "上涨" if pred_change > 0 else "下跌" if pred_change < 0 else "横盘"

        # 计算预测波动率
        pred_prices = [p.get('predicted_price', 0) for p in future]
        if pred_prices:
            pred_volatility = (max(pred_prices) - min(pred_prices)) / current_price * 100
        else:
            pred_volatility = 0

        # 趋势描述
        if abs(pred_change) < 2:
            trend_desc = f"📊 **窄幅震荡**: 预计未来{len(future)}天在{current_price:.2f}元附近{pred_change:+.2f}%窄幅波动"
        elif pred_change > 5:
            trend_desc = f"🚀 **强势上涨**: Kronos预测{len(future)}日内上涨{pred_change:.2f}%，目标位{last_pred:.2f}元"
        elif pred_change > 2:
            trend_desc = f"📈 **温和上涨**: 预计未来{len(future)}天上涨{pred_change:.2f}%至{last_pred:.2f}元"
        elif pred_change < -5:
            trend_desc = f"⚠️ **明显回调**: AI预测{len(future)}日内下跌{abs(pred_change):.2f}%，支撑位{last_pred:.2f}元"
        elif pred_change < -2:
            trend_desc = f"📉 **小幅回调**: 预计短期回调{abs(pred_change):.2f}%至{last_pred:.2f}元"
        else:
            trend_desc = f"➡️ **维持震荡**: 预计未来几日在当前价位{pred_change:+.2f}%范围内波动"

        parts.append(f"**AI预测趋势**: {trend_desc}\n")

        # 波动率分析
        if pred_volatility < 3:
            vol_desc = "低波动"
            risk_level = "低"
        elif pred_volatility < 5:
            vol_desc = "正常波动"
            risk_level = "中"
        elif pred_volatility < 8:
            vol_desc = "较高波动"
            risk_level = "偏高"
        else:
            vol_desc = "高度波动"
            risk_level = "高"

        parts.append(f"**预期波动率**: {pred_volatility:.2f}% ({vol_desc}，风险{risk_level})\n")

        # 计算支撑位和压力位
        pred_prices = [p.get('predicted_price', 0) for p in future]
        support_level = min(pred_prices) if pred_prices else current_price
        resistance_level = max(pred_prices) if pred_prices else current_price

        parts.append(f"**关键价位区间**:")
        parts.append(f"  - 📉 **预测支撑位**: ¥{support_level:.2f} ({(support_level-current_price)/current_price*100:+.2f}%)")
        parts.append(f"  - 📈 **预测压力位**: ¥{resistance_level:.2f} ({(resistance_level-current_price)/current_price*100:+.2f}%)")
        parts.append(f"  - 📊 **价格区间**: ¥{support_level:.2f} ~ ¥{resistance_level:.2f}\n")

        # 具体预测点位（显示所有天数，最多10天）
        parts.append("**每日价格预测路径**:")
        for i, pred in enumerate(future[:min(10, len(future))], 1):
            pred_price = pred.get('predicted_price', 0)
            pred_date = pred.get('date', '')
            change_from_now = (pred_price - current_price) / current_price * 100

            # 使用数字emoji
            emoji_map = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
            emoji = emoji_map[i-1] if i <= 10 else f"{i}️⃣"

            # 添加趋势箭头
            if change_from_now > 1:
                arrow = "⬆️"
            elif change_from_now < -1:
                arrow = "⬇️"
            else:
                arrow = "➡️"

            parts.append(f"  {emoji} {pred_date}: ¥{pred_price:.2f} ({change_from_now:+.2f}%) {arrow}")

        parts.append("")

        # 3. 投资建议（基于AI预测）
        parts.append("### 💡 基于AI预测的交易策略\n")

        # 根据预测涨幅和准确率制定策略
        if pred_change > 5 and accuracy >= 95:
            parts.append("**策略评级**: ✅ **强烈看多（5星推荐）**\n")
            parts.append(f"**核心逻辑**: Kronos模型预测未来{len(future)}个交易日强势上涨{pred_change:.2f}%，且历史回测准确率高达{accuracy:.1f}%，AI信号与技术面共振。\n")
            parts.append("**操作建议**:")
            parts.append(f"  - 📈 **建仓策略**: 分2-3批建仓，控制单批仓位30%-40%")
            parts.append(f"  - 🎯 **目标价位**: 第一目标{last_pred:.2f}元（{pred_change:+.2f}%），第二目标{resistance_level:.2f}元")
            parts.append(f"  - 🛡️ **止损位置**: {current_price * 0.97:.2f}元（-3%），跌破立即离场")
            parts.append(f"  - ⏰ **持仓周期**: {len(future)}个交易日内，达到目标价分批止盈")
            parts.append(f"  - 📊 **仓位管理**: 建议配置30%-50%仓位，不宜重仓")

        elif pred_change > 2 and accuracy >= 90:
            parts.append("**策略评级**: 📊 **适度看多（3星推荐）**\n")
            parts.append(f"**核心逻辑**: AI预测温和上涨{pred_change:.2f}%，准确率{accuracy:.1f}%，具有一定参考价值。\n")
            parts.append("**操作建议**:")
            parts.append(f"  - 📈 **建仓策略**: 轻仓试探，单批仓位20%-30%")
            parts.append(f"  - 🎯 **目标价位**: {last_pred:.2f}元（{pred_change:+.2f}%）")
            parts.append(f"  - 🛡️ **止损位置**: {current_price * 0.95:.2f}元（-5%）")
            parts.append(f"  - 📊 **仓位管理**: 建议配置10%-30%仓位，见好就收")

        elif pred_change < -5:
            parts.append("**策略评级**: ⚠️ **看空回避（谨慎）**\n")
            parts.append(f"**核心逻辑**: Kronos模型预测{len(future)}日内下跌{abs(pred_change):.2f}%，AI发出风险预警信号。\n")
            parts.append("**操作建议**:")
            parts.append(f"  - ⛔ **持仓策略**: 建议减仓或清仓观望，避开调整风险")
            parts.append(f"  - 📉 **关注价位**: {support_level:.2f}元附近可能形成支撑")
            parts.append(f"  - 🔄 **反弹机会**: 若跌至{last_pred:.2f}元企稳，可轻仓博反弹")
            parts.append(f"  - 📊 **仓位管理**: 空仓为主，最多保留10%底仓观察")

        elif pred_change < -2:
            parts.append("**策略评级**: 📉 **中性偏空（观望）**\n")
            parts.append(f"**核心逻辑**: AI预测小幅回调{abs(pred_change):.2f}%，短期调整压力较大。\n")
            parts.append("**操作建议**:")
            parts.append(f"  - ⏸️ **持仓策略**: 暂时观望，等待回调到位")
            parts.append(f"  - 📍 **买入价位**: {last_pred:.2f}元附近可考虑低吸")
            parts.append(f"  - 📊 **仓位管理**: 暂不建仓，待企稳后再介入")

        else:
            parts.append("**策略评级**: ➡️ **中性震荡（持币）**\n")
            parts.append(f"**核心逻辑**: AI预测横盘震荡（{pred_change:+.2f}%），短期缺乏明确方向。\n")
            parts.append("**操作建议**:")
            parts.append(f"  - 💤 **持仓策略**: 持币观望，等待方向突破")
            parts.append(f"  - 📊 **关键位置**: 向上突破{resistance_level:.2f}元看多，向下跌破{support_level:.2f}元看空")
            parts.append(f"  - ⚡ **交易策略**: 可小仓位高抛低吸，赚取波段差价")

        # 添加风险管理和注意事项
        parts.append("\n### ⚠️ 重要提示\n")
        parts.append("**AI预测使用说明**:")
        parts.append(f"  - 🤖 Kronos模型基于深度学习，擅长捕捉短期价格波动规律")
        parts.append(f"  - 📊 历史准确率{accuracy:.2f}%，但不保证未来预测100%准确")
        parts.append(f"  - 📰 突发消息、政策变化、市场环境等因素可能影响预测效果")
        parts.append(f"  - 💡 建议将AI预测作为辅助工具，结合基本面、技术面综合判断")
        parts.append(f"\n**风险控制原则**:")
        parts.append(f"  - 严格执行止损，避免单次亏损超过本金5%")
        parts.append(f"  - 合理控制仓位，单票持仓不超过总资金50%")
        parts.append(f"  - 保持独立思考，不盲目跟随AI信号操作")
        parts.append(f"  - 定期复盘，总结AI预测成功率和失败案例\n")

    return "\n".join(parts)
