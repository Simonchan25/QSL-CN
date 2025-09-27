"""
专业股票分析器 - 基于真实数据的智能评分和LLM深度分析
"""
from typing import Dict, Any, Optional
from datetime import datetime
import json

def calculate_professional_score(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    基于真实数据计算专业评分

    评分体系：
    - 技术面（40分）：基于RSI、MACD、均线、成交量等
    - 基本面（30分）：基于PE、PB、ROE、营收增长等
    - 市场情绪（20分）：基于新闻情绪、资金流向、市场热度
    - 行业地位（10分）：基于市值、行业排名、竞争优势
    """
    scores = {}
    details = {}

    # 1. 技术面评分（40分）
    tech_score = 40  # 默认中性
    tech_details = []

    if 'technical' in data and data['technical']:
        tech = data['technical']
        if 'indicators' in tech:
            indicators = tech['indicators']

            # RSI评分（10分）
            rsi = indicators.get('RSI', 50)
            if 30 <= rsi <= 70:
                rsi_score = 10  # 正常区间
                tech_details.append(f"RSI({rsi:.1f})处于正常区间")
            elif rsi < 30:
                rsi_score = 8  # 超卖，可能反弹
                tech_details.append(f"RSI({rsi:.1f})超卖，关注反弹机会")
            else:
                rsi_score = 5  # 超买，有回调风险
                tech_details.append(f"RSI({rsi:.1f})超买，注意回调风险")

            # MACD评分（10分）
            macd = indicators.get('MACD', 0)
            dif = indicators.get('DIF', 0)
            dea = indicators.get('DEA', 0)
            if dif > dea and macd > 0:
                macd_score = 10
                tech_details.append("MACD金叉向上，趋势良好")
            elif dif > dea:
                macd_score = 7
                tech_details.append("MACD金叉但处于零轴下方")
            else:
                macd_score = 4
                tech_details.append("MACD死叉，趋势偏弱")

            # 均线评分（10分）
            price = tech.get('price', {}).get('close', 0)
            ma5 = indicators.get('MA5', price)
            ma20 = indicators.get('MA20', price)
            if price > ma5 > ma20:
                ma_score = 10
                tech_details.append("价格在均线上方，多头排列")
            elif price > ma20:
                ma_score = 7
                tech_details.append("价格在MA20上方，中期趋势向好")
            else:
                ma_score = 4
                tech_details.append("价格在均线下方，趋势偏弱")

            # 成交量评分（10分）
            vol_score = 7  # 默认正常
            if 'trend' in tech:
                if tech['trend'] == '上升趋势':
                    vol_score = 10
                    tech_details.append("上升趋势确立")
                elif tech['trend'] == '下降趋势':
                    vol_score = 4
                    tech_details.append("下降趋势需谨慎")

            tech_score = rsi_score + macd_score + ma_score + vol_score

    scores['technical'] = tech_score
    details['technical'] = tech_details

    # 2. 基本面评分（30分）
    fundamental_score = 15  # 默认中性
    fundamental_details = []

    if 'fundamental' in data and data['fundamental']:
        fund = data['fundamental']

        # PE估值（10分）
        if 'valuation' in fund:
            val = fund['valuation']
            pe = val.get('pe_ttm', 0)
            if 0 < pe < 15:
                pe_score = 10
                fundamental_details.append(f"PE({pe:.1f})低估值")
            elif 15 <= pe < 30:
                pe_score = 7
                fundamental_details.append(f"PE({pe:.1f})合理估值")
            elif pe >= 30:
                pe_score = 4
                fundamental_details.append(f"PE({pe:.1f})高估值")
            else:
                pe_score = 5

            # PB估值（5分）
            pb = val.get('pb', 0)
            if 0 < pb < 1:
                pb_score = 5
                fundamental_details.append(f"PB({pb:.2f})破净股")
            elif 1 <= pb < 3:
                pb_score = 3
                fundamental_details.append(f"PB({pb:.2f})合理")
            else:
                pb_score = 1
                fundamental_details.append(f"PB({pb:.2f})偏高")
        else:
            pe_score = 5
            pb_score = 2

        # ROE盈利能力（10分）
        if 'fina_indicator_latest' in fund:
            fina = fund['fina_indicator_latest']
            roe = fina.get('roe', 0)
            if roe > 15:
                roe_score = 10
                fundamental_details.append(f"ROE({roe:.1f}%)优秀")
            elif roe > 8:
                roe_score = 7
                fundamental_details.append(f"ROE({roe:.1f}%)良好")
            else:
                roe_score = 4
                fundamental_details.append(f"ROE({roe:.1f}%)偏低")

            # 营收增长（5分）
            growth = fina.get('or_yoy', 0)
            if growth > 20:
                growth_score = 5
                fundamental_details.append(f"营收增长{growth:.1f}%")
            elif growth > 0:
                growth_score = 3
                fundamental_details.append(f"营收增长{growth:.1f}%")
            else:
                growth_score = 1
                fundamental_details.append(f"营收下滑{growth:.1f}%")
        else:
            roe_score = 5
            growth_score = 2

        fundamental_score = pe_score + pb_score + roe_score + growth_score

    scores['fundamental'] = fundamental_score
    details['fundamental'] = fundamental_details

    # 3. 市场情绪评分（20分）
    sentiment_score = 10  # 默认中性
    sentiment_details = []

    # 新闻情绪
    if 'news' in data and data['news']:
        news = data['news']
        if 'stats' in news:
            stats = news['stats']
            direct_news = stats.get('direct', 0)
            total_news = stats.get('total', 0)

            if direct_news > 10:
                news_score = 10
                sentiment_details.append(f"直接相关新闻{direct_news}条，市场关注度高")
            elif direct_news > 5:
                news_score = 7
                sentiment_details.append(f"直接相关新闻{direct_news}条，关注度中等")
            elif total_news > 20:
                news_score = 5
                sentiment_details.append(f"相关新闻{total_news}条")
            else:
                news_score = 3
                sentiment_details.append("新闻关注度较低")
        else:
            news_score = 5
    else:
        news_score = 5

    # 市场环境
    if 'market' in data and data['market']:
        market = data['market']
        sentiment = market.get('sentiment', '')
        if '乐观' in sentiment:
            market_score = 10
            sentiment_details.append("市场情绪乐观")
        elif '偏多' in sentiment:
            market_score = 7
            sentiment_details.append("市场情绪偏多")
        elif '偏空' in sentiment:
            market_score = 4
            sentiment_details.append("市场情绪偏空")
        else:
            market_score = 5
            sentiment_details.append("市场情绪中性")
    else:
        market_score = 5

    sentiment_score = news_score + market_score
    scores['sentiment'] = sentiment_score

    details['sentiment'] = sentiment_details

    # 4. 行业地位评分（10分）
    industry_score = 5  # 默认中等
    industry_details = []

    if 'fundamental' in data and 'valuation' in data['fundamental']:
        val = data['fundamental']['valuation']
        market_cap = val.get('total_mv', 0) / 10000  # 转换为亿
        if market_cap > 1000:
            industry_score = 10
            industry_details.append(f"大型龙头企业(市值{market_cap:.0f}亿)")
        elif market_cap > 100:
            industry_score = 7
            industry_details.append(f"中大型企业(市值{market_cap:.0f}亿)")
        else:
            industry_score = 5
            industry_details.append(f"中小型企业(市值{market_cap:.0f}亿)")

    scores['industry'] = industry_score
    details['industry'] = industry_details

    # 计算总分
    total_score = tech_score + fundamental_score + sentiment_score + industry_score

    # 评级
    if total_score >= 80:
        rating = "强烈推荐"
        rating_desc = "各项指标优秀，投资价值突出"
    elif total_score >= 65:
        rating = "推荐"
        rating_desc = "综合表现良好，值得关注"
    elif total_score >= 50:
        rating = "中性"
        rating_desc = "表现一般，谨慎观察"
    elif total_score >= 35:
        rating = "谨慎"
        rating_desc = "存在一定风险，不建议追高"
    else:
        rating = "回避"
        rating_desc = "风险较大，建议回避"

    return {
        'total': total_score,
        'scores': scores,
        'details': details,
        'rating': rating,
        'rating_desc': rating_desc
    }


def generate_llm_analysis(data: Dict[str, Any]) -> str:
    """
    生成LLM深度分析报告
    """
    try:
        from nlp.ollama_client import summarize

        # 准备分析数据
        stock_name = data.get('basic', {}).get('name', '股票')
        score_info = calculate_professional_score(data)

        # 构建分析prompt
        prompt = f"""
作为资深股票分析师，请对{stock_name}进行专业深度分析：

【基础信息】
- 股票代码：{data.get('basic', {}).get('ts_code', 'N/A')}
- 所属行业：{data.get('basic', {}).get('industry', 'N/A')}
- 总市值：{data.get('fundamental', {}).get('valuation', {}).get('total_mv', 0)/10000:.0f}亿元

【技术指标】
- RSI：{data.get('technical', {}).get('indicators', {}).get('RSI', 'N/A')}
- MACD：{data.get('technical', {}).get('indicators', {}).get('MACD', 'N/A')}
- 价格趋势：{data.get('technical', {}).get('trend', 'N/A')}
- 最新收盘：{data.get('technical', {}).get('price', {}).get('close', 'N/A')}

【基本面数据】
- PE(TTM)：{data.get('fundamental', {}).get('valuation', {}).get('pe_ttm', 'N/A')}
- PB：{data.get('fundamental', {}).get('valuation', {}).get('pb', 'N/A')}
- ROE：{data.get('fundamental', {}).get('fina_indicator_latest', {}).get('roe', 'N/A')}%
- 营收增长：{data.get('fundamental', {}).get('fina_indicator_latest', {}).get('or_yoy', 'N/A')}%

【市场情绪】
- 相关新闻：{data.get('news', {}).get('stats', {}).get('total', 0)}条
- 市场氛围：{data.get('market', {}).get('sentiment', 'N/A')}

【综合评分】
- 总分：{score_info['total']}/100
- 评级：{score_info['rating']}
- 技术面：{score_info['scores']['technical']}/40分
- 基本面：{score_info['scores']['fundamental']}/30分
- 市场情绪：{score_info['scores']['sentiment']}/20分
- 行业地位：{score_info['scores']['industry']}/10分

请提供：
1. 投资价值评估（结合估值、成长性、盈利能力）
2. 技术面分析（趋势、支撑阻力、买卖信号）
3. 风险提示（主要风险点、注意事项）
4. 操作建议（具体买卖点位、仓位管理）
5. 后市展望（短期、中期预期）

要求：
- 观点明确，有理有据
- 量化分析，给出具体数值
- 风险提示要充分
- 建议要可操作
"""

        # 调用LLM生成分析
        # 构建数据字典传入summarize函数
        analysis_data = {
            "prompt": prompt,
            "股票基本信息": data.get('basic', {}),
            "技术指标": data.get('technical', {}),
            "基本面数据": data.get('fundamental', {}),
            "新闻情绪": data.get('news', {}),
            "市场环境": data.get('market', {})
        }
        analysis = summarize(analysis_data)

        # 添加评分详情
        analysis += "\n\n### 📊 评分详情\n"
        for category, details_list in score_info['details'].items():
            if details_list:
                analysis += f"\n**{category}**\n"
                for detail in details_list:
                    analysis += f"- {detail}\n"

        return analysis

    except Exception as e:
        print(f"[LLM分析] 生成失败: {e}")
        # 返回基础分析
        return generate_basic_analysis(data, score_info)


def generate_basic_analysis(data: Dict[str, Any], score_info: Dict[str, Any]) -> str:
    """
    生成基础分析报告（不依赖LLM）
    """
    stock_name = data.get('basic', {}).get('name', '股票')

    analysis = f"""
## {stock_name} 专业投资分析报告

### 📈 综合评分：{score_info['total']}/100 【{score_info['rating']}】
{score_info['rating_desc']}

### 1️⃣ 技术面分析（{score_info['scores']['technical']}/40分）
"""
    for detail in score_info['details']['technical']:
        analysis += f"- {detail}\n"

    analysis += f"""

### 2️⃣ 基本面分析（{score_info['scores']['fundamental']}/30分）
"""
    for detail in score_info['details']['fundamental']:
        analysis += f"- {detail}\n"

    analysis += f"""

### 3️⃣ 市场情绪（{score_info['scores']['sentiment']}/20分）
"""
    for detail in score_info['details']['sentiment']:
        analysis += f"- {detail}\n"

    analysis += f"""

### 4️⃣ 行业地位（{score_info['scores']['industry']}/10分）
"""
    for detail in score_info['details']['industry']:
        analysis += f"- {detail}\n"

    # 添加操作建议
    if score_info['total'] >= 65:
        suggestion = "建议：可适当建仓，分批买入"
    elif score_info['total'] >= 50:
        suggestion = "建议：观望为主，等待更好机会"
    else:
        suggestion = "建议：暂时回避，控制风险"

    analysis += f"""

### 💡 操作建议
{suggestion}

---
*报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

    return analysis


def analyze_with_5000_points(ts_code: str) -> Dict[str, Any]:
    """
    使用5000积分接口获取高级数据
    """
    from .advanced_data_client import advanced_client

    try:
        # 获取高级数据
        advanced_data = advanced_client.get_full_professional_data(ts_code)

        # 返回所有数据，包括实时数据
        result = {
            'chip_analysis': advanced_data.get('chip_analysis', {}),
            'institution_data': advanced_data.get('institution_data', {}),
            'holders_analysis': advanced_data.get('holders_analysis', {}),
            'moneyflow': advanced_data.get('moneyflow', {}),
            'margin_detail': advanced_data.get('margin_detail', {}),
            'block_trade': advanced_data.get('block_trade', {}),
            'dividend': advanced_data.get('dividend', {})
        }

        # 添加实时数据
        realtime_quote = advanced_client.get_realtime_quote(ts_code)
        if realtime_quote:
            result['realtime_quote'] = realtime_quote

        realtime_indicators = advanced_client.calculate_realtime_indicators(ts_code)
        if realtime_indicators:
            result['realtime_indicators'] = realtime_indicators

        return result
    except Exception as e:
        print(f"[5000积分接口] 调用失败: {e}")
        return {}