"""
量化指标收集和分析模块
为专业报告生成系统提供量化数据支持
"""
from typing import Dict
from .market import fetch_market_overview


def collect_quantitative_metrics(date: str) -> Dict:
    """收集量化指标数据"""
    try:
        print("[指标] 开始收集量化指标...")
        metrics = {}

        # 1. 获取市场概览数据
        market_data = fetch_market_overview()

        # 2. 市场宽度指标
        market_breadth = market_data.get("market_breadth", {})
        metrics["market_breadth"] = {
            "up_count": market_breadth.get("up_count", 0) or 0,
            "down_count": market_breadth.get("down_count", 0) or 0,
            "total_count": market_breadth.get("total_count", 0) or 0,
            "limit_up": market_breadth.get("limit_up", 0) or 0,
            "limit_down": market_breadth.get("limit_down", 0) or 0,
            "limit_break": market_breadth.get("limit_break", 0) or 0,
            "up_ratio": market_breadth.get("up_ratio", 0) or 0
        }

        # 3. 资金流向指标
        capital_flow = market_data.get("capital_flow", {})
        north_flow = capital_flow.get("north_flow", {})
        metrics["capital_flow"] = {
            "hsgt_net_amount": capital_flow.get("hsgt_net_amount", 0) or 0,
            "north_money": north_flow.get("north_money", 0) if north_flow else 0,
            "hgt": north_flow.get("hgt", 0) if north_flow else 0,
            "sgt": north_flow.get("sgt", 0) if north_flow else 0
        }

        # 融资融券（单位转换：元 → 亿元）
        margin = capital_flow.get("margin", {})
        if margin:
            # Tushare返回的融资数据单位是元，需要除以100000000（1亿）转为亿元
            rzye_raw = margin.get("rzye", 0) or 0
            rzmre_raw = margin.get("rzmre", 0) or 0
            metrics["capital_flow"]["margin_balance"] = round(rzye_raw / 100000000, 2) if rzye_raw else 0
            metrics["capital_flow"]["margin_buy"] = round(rzmre_raw / 100000000, 2) if rzmre_raw else 0

        # 4. 板块表现TOP5
        sectors = market_data.get("sectors", [])
        top_sectors = []
        if sectors:
            for sector in sectors[:5]:
                top_sectors.append({
                    "name": sector.get("name", ""),
                    "pct_chg": sector.get("pct_chg", 0) or 0,
                    "close": sector.get("close", 0) or 0
                })
        metrics["sector_performance"] = top_sectors

        # 5. 涨停分析
        limit_up_count = metrics["market_breadth"]["limit_up"]
        limit_down_count = metrics["market_breadth"]["limit_down"]
        total_stocks = metrics["market_breadth"]["total_count"]

        limit_up_ratio = (limit_up_count / total_stocks * 100) if total_stocks > 0 else 0

        metrics["limit_analysis"] = {
            "limit_up_count": limit_up_count,
            "limit_down_count": limit_down_count,
            "limit_up_ratio": round(limit_up_ratio, 2),
            "limit_break": metrics["market_breadth"]["limit_break"]
        }

        # 6. 市场情绪指标（基于量化数据计算）
        emotion_data = calculate_emotion_score(metrics)
        metrics["emotion_indicators"] = emotion_data

        print(f"[指标] 收集完成: 涨跌比{metrics['market_breadth']['up_ratio']:.1f}%, 涨停{limit_up_count}家, 情绪{emotion_data['emotion_score']}分")

        return metrics

    except Exception as e:
        print(f"[错误] 收集量化指标失败: {e}")
        # 返回基本结构，避免后续代码出错
        return {
            "market_breadth": {"up_count": 0, "down_count": 0, "total_count": 0, "limit_up": 0, "limit_down": 0, "limit_break": 0, "up_ratio": 0},
            "capital_flow": {"hsgt_net_amount": 0, "north_money": 0, "hgt": 0, "sgt": 0, "margin_balance": 0, "margin_buy": 0},
            "sector_performance": [],
            "limit_analysis": {"limit_up_count": 0, "limit_down_count": 0, "limit_up_ratio": 0, "limit_break": 0},
            "emotion_indicators": {"emotion_score": 5, "emotion_level": "中性"}
        }


def calculate_emotion_score(metrics: Dict) -> Dict:
    """根据量化指标计算市场情绪评分"""
    try:
        breadth = metrics.get("market_breadth", {})
        up_ratio = breadth.get("up_ratio", 0) or 0
        limit_up = breadth.get("limit_up", 0) or 0
        limit_down = breadth.get("limit_down", 0) or 0

        # 情绪评分逻辑
        if up_ratio >= 70 and limit_up >= 30:
            return {"emotion_score": 9, "emotion_level": "极度乐观"}
        elif up_ratio >= 60 and limit_up >= 15:
            return {"emotion_score": 7, "emotion_level": "偏暖"}
        elif up_ratio >= 50:
            return {"emotion_score": 6, "emotion_level": "中性偏强"}
        elif up_ratio >= 40:
            return {"emotion_score": 4, "emotion_level": "偏谨慎"}
        else:
            return {"emotion_score": 2, "emotion_level": "低迷"}

    except Exception as e:
        print(f"[错误] 计算情绪评分失败: {e}")
        return {"emotion_score": 5, "emotion_level": "中性"}


def generate_enhanced_fallback_summary(metrics: Dict, date: str) -> str:
    """生成增强的Fallback分析 - 基于量化指标"""
    try:
        # 提取量化数据
        breadth = metrics.get("market_breadth", {})
        capital = metrics.get("capital_flow", {})
        sectors = metrics.get("sector_performance", [])
        limit_info = metrics.get("limit_analysis", {})
        emotion = metrics.get("emotion_indicators", {})

        # 一、市场概况与情绪研判
        up_ratio = breadth.get("up_ratio", 0)
        limit_up = limit_info.get("limit_up_count", 0)
        limit_down = limit_info.get("limit_down_count", 0)
        emotion_score = emotion.get("emotion_score", 5)
        emotion_level = emotion.get("emotion_level", "中性")

        section1 = f"""一、市场概况与情绪研判
市场涨跌比为{up_ratio:.1f}%，共{limit_up}家涨停、{limit_down}家跌停。基于量化指标，当前市场情绪评分为{emotion_score}/10分，情绪等级：{emotion_level}。
评分依据：涨跌比反映多空力量对比，涨停数量体现赚钱效应强度，综合判断市场参与者情绪处于{emotion_level}状态。"""

        # 二、资金流向与博弈分析
        hsgt = capital.get("hsgt_net_amount", 0)
        margin_balance = capital.get("margin_balance", 0)
        margin_buy = capital.get("margin_buy", 0)

        if hsgt > 0:
            capital_desc = f"北向资金净流入{hsgt:.1f}亿元，外资态度积极，增强市场信心。"
        elif hsgt < 0:
            capital_desc = f"北向资金净流出{abs(hsgt):.1f}亿元，外资谨慎，需关注风险。"
        else:
            capital_desc = "北向资金数据暂缺，建议关注盘面资金流向。"

        section2 = f"""二、资金流向与博弈分析
{capital_desc}融资余额{margin_balance:.1f}亿元，当日融资买入{margin_buy:.1f}亿元，反映场内杠杆资金的配置意愿。主力资金整体呈现{"流入" if hsgt > 0 else "流出" if hsgt < 0 else "观望"}态势。"""

        # 三、板块轮动与热点挖掘
        if sectors:
            top3 = sectors[:3]
            sector_names = [f"{s['name']}({s['pct_chg']:+.1f}%)" for s in top3]
            section3 = f"""三、板块轮动与热点挖掘
市场热点集中在{', '.join(sector_names)}等板块。基于TOP5板块数据分析，当前主线明确，建议重点关注龙头个股，把握板块轮动节奏，短线操作窗口为1-3个交易日。"""
        else:
            section3 = """三、板块轮动与热点挖掘
板块数据暂缺，建议关注政策导向和突发事件驱动的投资机会，等待明确主线形成后再介入。"""

        # 四、投资策略与仓位建议
        if emotion_score >= 7:
            strategy = f"""激进策略：仓位70-80%，重点参与热点板块龙头股，追涨强势品种。
稳健策略：仓位50-60%，关注业绩确定性品种，高抛低吸操作。
保守策略：仓位30-40%，配置防御性板块，控制回撤风险。"""
        elif emotion_score >= 5:
            strategy = f"""激进策略：仓位50-60%，择优参与结构性机会，注意止盈止损。
稳健策略：仓位40-50%，以波段操作为主，规避追高风险。
保守策略：仓位20-30%，观望为主，等待更好介入时机。"""
        else:
            strategy = f"""激进策略：仓位30-40%，严格控制回撤，寻找超跌反弹机会。
稳健策略：仓位20-30%，以防守为主，保留资金等待转机。
保守策略：仓位10-20%或空仓观望，规避系统性风险。"""

        section4 = f"""四、投资策略与仓位建议
基于情绪评分{emotion_score}/10分，给出以下三类策略：
{strategy}
策略与当前市场情绪匹配度高，建议根据自身风险偏好选择执行。"""

        # 五、风险提示与预警
        risks = []
        if limit_down > 30:
            risks.append(f"系统性风险：{limit_down}家跌停，市场恐慌情绪严重，建议降低仓位")
        elif limit_up > 100:
            risks.append(f"过热风险：{limit_up}家涨停，市场情绪过于亢奋，注意高位回调风险")

        if hsgt < -100:
            risks.append(f"外资流出风险：北向资金大幅流出{abs(hsgt):.1f}亿，需防范外资减仓冲击")

        if not risks:
            risks.append("当前市场风险可控，建议保持正常仓位配置，关注个股基本面")

        section5 = f"""五、风险提示与预警
{'; '.join(risks)}。
风控措施：1) 设置止损点位，严格执行止损纪律；2) 分散持仓，单只个股仓位不超过10%；3) 关注政策面和资金面变化。"""

        # 整合报告
        report = f"""【{date} A股市场专业分析报告】

{section1}

{section2}

{section3}

{section4}

{section5}

【数据来源】基于{date}真实市场数据：涨跌比{up_ratio:.1f}%、涨停{limit_up}家、北向资金{hsgt:.1f}亿元等量化指标综合分析。

风险提示：股市有风险，投资需谨慎。以上分析仅供参考，不构成投资建议。"""

        return report

    except Exception as e:
        print(f"[错误] 生成增强fallback分析失败: {e}")
        return f"""【{date} A股市场分析】

市场概况：数据获取异常，建议谨慎操作。

投资建议：
1. 控制仓位风险，保持谨慎态度
2. 关注市场变化，等待明确信号
3. 优选优质个股，规避高风险标的

风险提示：股市有风险，投资需谨慎。"""


def generate_optimized_prompt(metrics: Dict, date: str, hotspots_data: Dict, board_data: Dict) -> str:
    """生成优化的AI分析提示词 - 包含量化数据"""
    import json

    prompt = f"""
请基于以下A股市场真实量化数据生成专业的早报总结：

【日期】：{date}

【量化指标】：
市场宽度：
- 涨跌家数：{metrics['market_breadth']['up_count']}↑ / {metrics['market_breadth']['down_count']}↓
- 涨跌比：{metrics['market_breadth']['up_ratio']:.1f}%
- 涨停/跌停：{metrics['limit_analysis']['limit_up_count']}家 / {metrics['limit_analysis']['limit_down_count']}家
- 涨停率：{metrics['limit_analysis']['limit_up_ratio']:.2f}%
- 炸板数：{metrics['limit_analysis']['limit_break']}家

资金流向：
- 北向资金净流入：{metrics['capital_flow']['hsgt_net_amount']:.1f}亿元
- 沪股通：{metrics['capital_flow']['hgt']:.1f}亿元
- 深股通：{metrics['capital_flow']['sgt']:.1f}亿元
- 融资余额：{metrics['capital_flow'].get('margin_balance', 0):.1f}亿元
- 融资买入：{metrics['capital_flow'].get('margin_buy', 0):.1f}亿元

板块表现TOP5：
{json.dumps(metrics['sector_performance'], ensure_ascii=False, indent=2)}

市场情绪：
- 情绪评分：{metrics['emotion_indicators']['emotion_score']}/10分
- 情绪等级：{metrics['emotion_indicators']['emotion_level']}

【盘前热点数据】：
{json.dumps(hotspots_data, ensure_ascii=False, indent=2)}

【连板与涨停数据】：
{json.dumps(board_data, ensure_ascii=False, indent=2)}

请生成一份专业的市场总结，严格按照以下5个部分：

一、市场概况与情绪研判
- 基于涨跌比{metrics['market_breadth']['up_ratio']:.1f}%、涨停{metrics['limit_analysis']['limit_up_count']}家等真实数据分析市场情绪
- 必须给出明确的情绪评分（X/10分）和评级
- 说明评分依据的具体数据

二、资金流向与博弈分析
- 分析北向资金流入{metrics['capital_flow']['hsgt_net_amount']:.1f}亿的市场含义
- 解读融资余额变化趋势
- 说明主力资金的操作方向

三、板块轮动与热点挖掘
- 基于TOP5板块数据识别主线热点
- 分析热点持续性和轮动节奏
- 给出具体的板块配置建议

四、投资策略与仓位建议
- 基于情绪评分给出三类策略：
  * 激进策略：具体仓位X-Y%，操作方向
  * 稳健策略：具体仓位X-Y%，操作方向
  * 保守策略：具体仓位X-Y%，操作方向
- 策略必须与市场情绪匹配

五、风险提示与预警
- 基于具体数据识别风险点
- 量化风险程度（如跌停{metrics['limit_analysis']['limit_down_count']}家表明XX风险）
- 给出具体的风控措施

要求：
1. 所有分析必须基于上述真实数据，严禁编造数据
2. 避免"市场整体平稳"等模糊表述，用具体数字说话
3. 仓位建议必须具体到百分比区间
4. 总字数800-1000字
5. 每个判断都要引用具体的量化指标
"""

    return prompt
