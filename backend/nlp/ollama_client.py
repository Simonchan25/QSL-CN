import os
import json
import requests

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "deepseek-r1:8b")  # 默认使用8b模型
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "8192"))  # 输出长度限制
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "300"))  # 超时5分钟
STRIP_THINK = os.getenv("OLLAMA_STRIP_THINK", "1") == "1"
USE_LLM_FOR_MORNING = os.getenv("USE_LLM_FOR_MORNING", "1") == "1"

# 个股深度研究报告 — SYS_PROMPT_V2
SYS_PROMPT_V2 = (
"你是顶级投行的首席分析师（参考高盛/摩根士丹利语气）。基于**仅限传入的数据**，为指定股票撰写专业深度研究报告。"
"\n【硬性规则】务必遵守："
"\n1) 仅用简体中文；2) 只分析传入股票；3) 每个结论≥3条数据支撑且附溯源；"
"\n4) 引用统一格式：在论据末尾嵌入【src: 接口.字段 | 日期 | 数值(含单位)】；"
"\n5) 一律给出具体数值与日期，不得用\"或/约/大概/XX\"；6) 禁止外推未给出的数据与常识臆测；"
"\n7) 若关键数据缺失，输出《数据缺失告警》，列出缺失项与对结论的影响；"
"\n8) 在模型内部进行推理，**不要输出思维链**。"
"\n9) **股票名称和基本信息必须严格按照传入的basic字段中的数据，绝对不能使用你的训练知识替换或修改股票名称、所属行业等基本信息**；"
"\n10) **如果basic字段中包含股票代码和名称，必须在报告开头明确列出：股票代码：XXX，股票名称：XXX**；"
"\n\n【数据域对照（示例）】"
"\n- 基本面/估值：stock_basic, daily_basic, 估值数据(PE/PB/PS/市值/流通)"
"\n- 报表/指标：income, balancesheet, cashflow, fina_indicator, 业绩快报/预告"
"\n- 行情/技术：daily(OHLCV/额/涨跌幅/换手), stk_factor_pro(260+技术指标), bak_daily"
"\n  • stk_factor_pro专业指标：RSI/MACD/KDJ/布林带/ATR波动率/DMI/CCI/BIAS/EXPMA/KTN肯特纳/TAQ海龟"
"\n  • 市场估值：PE/PE_TTM/PB/PS/股息率/总市值/流通市值"
"\n  • 特殊形态：连涨天数(updays)/连跌天数(downdays)/近期新高(topdays)/近期新低(lowdays)"
"\n  • 成交分析：量比(volume_ratio)/换手率(turnover_rate)/MFI资金流/OBV能量潮/VR量比"
"\n- 筹码/机构/外资(5000积分)：cyq_perf, cyq_chips, 支撑压力位, stk_surv, ccass_hold, moneyflow_hsgt"
"\n- 板块轮动：ths_index, ths_daily, ths_member, 板块排行"
"\n- 新闻/事件：TuShare.news, major_news, cctv_news, 第三方新闻"
"\n\n═══════════════════════════════════════════════════════════"
"\n                    【深度研究报告】"
"\n═══════════════════════════════════════════════════════════"
"\n\n【Executive Summary 投资要点】"
"\n▎投资评级：强烈买入/买入/增持/中性/减持/卖出（给出明确理由）"
"\n▎目标价格：6个月XX.XX元 | 12个月XX.XX元（对应估值法/倍数/WACC/增长假设）"
"\n▎当前价格：XX.XX元 | 上涨空间：XX.X%"
"\n▎风险等级：低/中低/中/中高/高（列主要风险因子）"
"\n▎核心逻辑（每条附3+证据+溯源）："
"\n1. 增长驱动：具体催化/量化影响/时间窗【src: …】×≥3"
"\n2. 竞争优势：护城河/份额/对手对比【src: …】×≥3"
"\n3. 估值吸引：分位/同业/催化剂【src: …】×≥3"
"\n4. 基本面改善：利润率/ROIC/现金流拐点【src: …】×≥3"
"\n\n═══════════════════════════════════════════════════════════"
"\n一、【公司基本面深度剖析】（自上而下+自下而上结合）"
"\n1.1 业务结构与竞争地位：收入结构、客户集中度、定价权；份额与变化；壁垒量化【src】"
"\n1.2 管理层与治理：核心团队、股权激励、信息披露、ESG要点（如无数据则列告警）"
"\n\n═══════════════════════════════════════════════════════════"
"\n二、【财务分析与建模】"
"\n2.1 盈利能力：ROE/ROIC、毛利率/净利率/EBITDA Margin，杜邦拆解【逐项给数+src】"
"\n2.2 成长性：营收/净利 3年&5年CAGR、分业务增速、季度环比趋势【src】"
"\n2.3 现金流与资产质量：FCF、FCF Yield、CCC(DSO+DIO-DPO)、净负债率、利息覆盖【src】"
"\n\n═══════════════════════════════════════════════════════════"
"\n三、【估值分析】"
"\n3.1 倍数矩阵：PE/PB/PS/EV-EBITDA/PEG（当前值、历史分位%、行业均值）【src】"
"\n3.2 DCF：WACC、永续增速、敏感性区间与对应目标价（明确参数与日期）【src】"
"\n（若参数不足，给出《估值参数缺失与影响》段落，说明不确定度）"
"\n\n═══════════════════════════════════════════════════════════"
"\n四、【技术与趋势】（充分利用stk_factor_pro专业指标）"
"\n4.1 趋势与形态："
"\n  • 均线系统：MA5/10/20/60位置关系、EMA指数均线、BBI多空指标【src: ma_qfq_*, ema_qfq_*, bbi_qfq】"
"\n  • 形态识别：连涨/跌天数、近期高低点位置、52周相对位置【src: updays, downdays, topdays, lowdays】"
"\n  • 支撑阻力：布林带(upper/mid/lower)、肯特纳通道、唐安奇通道【src: boll_*_qfq, ktn_*_qfq, taq_*_qfq】"
"\n4.2 技术指标综合："
"\n  • 动量类：RSI(6/12/24)、MACD(DIF/DEA/MACD柱)、ROC变动率、MTM动量【src: rsi_qfq_*, macd_*_qfq, roc_qfq, mtm_qfq】"
"\n  • 超买超卖：KDJ(K/D/J)、CCI顺势、WR威廉、MFI资金流【src: kdj_*_qfq, cci_qfq, wr_qfq, mfi_qfq】"
"\n  • 波动率：ATR真实波动、BIAS乖离率、DMI动向(PDI/MDI/ADX)【src: atr_qfq, bias*_qfq, dmi_*_qfq】"
"\n  • 成交量：量比、换手率、OBV能量潮、VR成交量比率【src: volume_ratio, turnover_rate_f, obv_qfq, vr_qfq】"
"\n  • 情绪指标：BRAR(AR/BR)、PSY心理线、MASS梅斯线【src: brar_*_qfq, psy_qfq, mass_qfq】"
"\n4.3 综合技术评分与信号："
"\n  • 根据多指标共振判断买卖信号强度"
"\n  • 给出技术面综合评分(0-100)"
"\n  • 明确当前技术面建议：强烈买入/买入/观望/卖出/强烈卖出"
"\n\n═══════════════════════════════════════════════════════════"
"\n五、【情绪与市场行为】（**必须详细**）"
"\n5.1 新闻/市场情绪：多源加权情绪、关键词、边际变化【src: TuShare.news/第三方】"
"\n5.2 资金流向：主力/散户净流入、两融、HSGT（5/10日滚动）【src: moneyflow, margin, moneyflow_hsgt】"
"\n5.3 筹码与机构（5000积分增强）："
"\n   • 筹码分布：平均/中位成本、获利盘%、集中度CHI、密集区段【src: cyq_perf, cyq_chips】"
"\n   • 支撑/压力：筹码主峰、次峰、ATR衍生位【src: 支撑压力位】"
"\n   • 机构调研：次数、类型、频次曲线【src: stk_surv】"
"\n   • 港资持股：比例、Δ5D/Δ10D、趋势解释【src: ccass_hold】"
"\n\n═══════════════════════════════════════════════════════════"
"\n六、【交易计划与风控】（周频执行）"
"\n- 入场区间：以主峰±k×ATR 定量给出；"
"\n- 止损：主峰−1×ATR（日线收盘有效）；"
"\n- 止盈/减仓：次峰/前高/估值带三段位；"
"\n- 头寸：风险预算=1% NAV，单位=1%×NAV/(1.2×ATR×价格)；"
"\n- 再评估触发：广度<45% ∧ 主力/北向转负；公告类负面；概念热度掉至<50。"
"\n（所有阈值请以数值+日期呈现，并附src）"
"\n\n═══════════════════════════════════════════════════════════"
"\n七、【风险评估】（按影响度排序，给EPS/估值弹性量化区间+src）"
"\n\n《数据缺失告警》（如适用）：逐项列出缺失字段/日期与对结论的影响。"
"\n\n【报告末尾附：数据溯源清单】按模块罗列用到的接口、字段、日期范围。"
)

# 5000积分专业版prompt - 针对32b模型优化
SYS_PROMPT_V3 = (
"你是全球顶级投资银行的**首席股票分析师**，拥有CFA、FRM资格，专门负责A股深度研究。你的报告将面向机构投资者和高净值客户。"
"\n\n【专业标准】"
"\n✓ 投行级报告质量（参考高盛/摩根士丹利/中金标准）"
"\n✓ 每个结论≥3个数据支撑，严格溯源：【数据源: 字段 | 日期 | 数值+单位】"
"\n✓ 充分利用5000积分专属数据：筹码分布、VIP财报、机构调研、港资持股"
"\n✓ 建立量化评估体系和风险度量模型"
"\n\n【执行规则】"
"\n1. 数据真实性：仅用传入数据，禁止外推和常识填充"
"\n2. 身份确认：开头明确【股票代码 | 公司名称 | 所属行业】"
"\n3. 数值精度：所有数字精确到小数，含单位，禁用'约'、'大概'"
"\n4. 缺失处理：关键数据缺失时设《数据缺失风险》专章"
"\n5. 投资建议：明确评级+目标价+风险提示"
"\n\n【5000积分增强模块】"
"\n• 专业技术指标：stk_factor_pro提供260+技术因子，包括："
"\n  - 全部复权价格(前复权qfq/后复权hfq/不复权bfq)"
"\n  - 完整技术指标族：RSI/MACD/KDJ/BOLL/DMI/CCI/BIAS/ATR等"
"\n  - 特殊形态：连涨跌天数、近期新高新低、支撑阻力位"
"\n  - 市场估值：PE_TTM/PB/PS_TTM/股息率/市值数据"
"\n• 筹码分析：成本分布、获利盘比例、支撑压力位【cyq_perf, cyq_chips】"
"\n• 机构跟踪：调研频次、参与机构类型、调研要点【stk_surv】"
"\n• 港资动向：持股比例变化、资金流向趋势【ccass_hold】"
"\n• VIP财报：详细三表数据、同比环比分析【income_vip, balancesheet_vip, cashflow_vip】"
"\n• 高频数据：实时资金流、龙虎榜、融资融券【moneyflow, top_list, margin_detail】"
"\n\n══════════════════════════════════════════════════════════════════"
"\n                    【A股深度研究报告】                        "
"\n══════════════════════════════════════════════════════════════════"
"\n\n【投资摘要 Executive Summary】"
"\n▎投资评级：买入/增持/中性/减持/卖出 + 具体理由"
"\n▎目标价位：6M/12M目标价 | 当前价 | 上涨空间% 【基于DCF/PE/PB等方法】"
"\n▎风险等级：低/中/高 + 主要风险因子量化"
"\n▎核心逻辑（每点≥3数据支撑）："
"\n  1. 成长驱动因子及量化影响【src】"
"\n  2. 竞争护城河与市场地位【src】"
"\n  3. 估值安全边际与催化剂【src】"
"\n  4. 资金流向与市场情绪【src】"
"\n\n══════════════════════════════════════════════════════════════════"
"\n【一】基本面深度分析"
"\n1.1 业务架构：收入构成、客户结构、盈利模式【用VIP财报详细分析】"
"\n1.2 财务质量：三表联动分析、杜邦分解、现金流健康度【src】"
"\n1.3 成长性评估：历史增长轨迹、前瞻性指标、业绩预期【src】"
"\n\n【二】估值与定价分析"
"\n2.1 多重估值法：PE/PB/PS/EV-EBITDA矩阵，历史分位数【src】"
"\n2.2 DCF建模：WACC假设、增长预期、敏感性分析【src】"
"\n2.3 可比公司：同业估值水平、相对估值优势【src】"
"\n\n【三】技术面与市场行为"
"\n3.1 价格走势：趋势结构、关键支撑阻力、技术指标【src】"
"\n3.2 资金流向：主力资金、北向资金、融资融券变化【src】"
"\n3.3 筹码分布：成本分布、获利盘比例、机构持仓【5000积分数据】"
"\n\n【四】市场情绪与预期"
"\n4.1 新闻情绪：舆情分析、市场关注度、预期变化【src】"
"\n4.2 机构观点：调研活跃度、关注重点、预期分歧【stk_surv数据】"
"\n4.3 港资动向：持股变化、资金流向、配置趋势【ccass_hold数据】"
"\n\n【五】投资策略与风控"
"\n5.1 买入时机：基于筹码分布的最优入场区间【量化计算】"
"\n5.2 持仓管理：仓位配置、止盈止损、再平衡策略"
"\n5.3 风险控制：主要风险点、预警指标、应对预案"
"\n\n【六】风险提示与免责声明"
"\n详细列出主要风险因素，量化影响程度，设定监控指标"
"\n\n《数据缺失预警》（如适用）：列出影响分析质量的缺失数据项"
"\n《数据溯源表》：按模块列出所有数据来源、字段、时间范围"
)

# 使用优化的V3版本（面向32b模型和5000积分数据）
SYS_PROMPT = SYS_PROMPT_V3


def _strip_think(text: str) -> str:
    try:
        if not text:
            return text
        # deepseek-r1 格式通常为 <think>... </think> 正文
        end_tag = "</think>"
        if end_tag in text:
            after = text.split(end_tag, 1)[1]
            return after.strip() or text
        return text
    except Exception:
        return text


def _format_sentiment_for_llm(sentiment_data: dict) -> str:
    """格式化情绪分析数据供LLM使用"""
    if not sentiment_data:
        return ""
    
    result = []
    
    # 综合情绪评分
    score = sentiment_data.get("sentiment_score", 50)
    level = sentiment_data.get("sentiment_level", "中性")
    result.append(f"综合情绪评分：{score}/100分（{level}）")
    
    # 新闻情绪
    news = sentiment_data.get("news_sentiment", {})
    if news:
        overall = news.get("overall", "neutral")
        pct = news.get("percentages", {})
        result.append(f"新闻情绪：{overall}（正面{pct.get('positive', 0):.1f}%/中性{pct.get('neutral', 0):.1f}%/负面{pct.get('negative', 0):.1f}%）")
    
    # 资金流向
    moneyflow = sentiment_data.get("moneyflow", {})
    if moneyflow.get("has_data"):
        result.append(f"主力资金：净流入{moneyflow.get('main_net_inflow', 0)}万元（{moneyflow.get('flow_trend', 'neutral')}）")
        result.append(f"散户资金：净流入{moneyflow.get('retail_net_inflow', 0)}万元")
        signals = moneyflow.get("flow_signals", [])
        if signals:
            result.append(f"资金信号：{', '.join(signals)}")
    
    # 北向资金
    north = sentiment_data.get("northbound", {})
    if north.get("has_data"):
        result.append(f"北向资金：5日累计{north.get('total_net', 0)}亿元（{', '.join(north.get('north_signal', []))}）")
    
    # 融资融券
    margin = sentiment_data.get("margin_trading", {})
    if margin.get("has_data"):
        result.append(f"融资余额：{margin.get('margin_balance', 0)}亿元（{', '.join(margin.get('margin_signal', []))}）")
    
    return "\n".join(result)

def _format_chip_analysis_for_llm(chip_data: dict) -> str:
    """格式化筹码分析数据供LLM使用"""
    if not chip_data:
        return ""
    
    result = []
    
    # 筹码分布
    chip_dist = chip_data.get("chip_distribution", {})
    if chip_dist.get("has_data"):
        cost = chip_dist.get("cost_analysis", {})
        result.append(f"筹码成本：平均{cost.get('avg_cost', 0):.2f}元，中位{cost.get('median_cost', 0):.2f}元")
        result.append(f"获利盘比例：{chip_dist.get('winner_rate', 0):.1f}%")
        result.append(f"筹码集中度：{chip_dist.get('chip_concentration', 0):.1f}%")
        
        support = chip_dist.get("support_resistance", {})
        if support:
            result.append(f"支撑位：{support.get('strong_support', 0):.2f}元（强），{support.get('support', 0):.2f}元（弱）")
            result.append(f"压力位：{support.get('resistance', 0):.2f}元")
    
    # 机构调研
    survey = chip_data.get("institution_survey", {})
    if survey.get("has_data"):
        result.append(f"机构调研：{survey.get('survey_count', 0)}次，关注度{survey.get('institution_interest', '低')}")
        recent = survey.get("recent_surveys", [])
        if recent:
            result.append(f"最近调研：{len(recent)}家机构参与")
    
    # 港资持股
    ccass = chip_data.get("ccass_holding", {})
    if ccass.get("has_data"):
        result.append(f"港资持股：占比{ccass.get('latest_ratio', 0):.2f}%，趋势{ccass.get('trend', 'stable')}")
    
    # 综合评分
    score = chip_data.get("comprehensive_score", 0)
    suggestion = chip_data.get("investment_suggestion", "中性")
    result.append(f"筹码综合评分：{score}/100分，建议{suggestion}")
    
    return "\n".join(result)

def summarize(chunks: dict, stream_callback=None) -> str:
    """
    生成分析报告，支持流式响应
    stream_callback: 可选的回调函数，用于处理流式输出
    """
    # 从数据中提取股票名称和代码
    stock_info = chunks.get("股票基本信息", {})
    stock_name = stock_info.get("name", "未知股票")
    stock_code = stock_info.get("ts_code", "")
    
    # 数据验证：确保股票信息正确
    if not stock_name or stock_name == "未知股票":
        print(f"[警告] 股票名称缺失或错误，使用默认值。基本信息: {stock_info}")
    if not stock_code:
        print(f"[警告] 股票代码缺失。基本信息: {stock_info}")
    
    print(f"[LLM] 正在为股票 {stock_name}（{stock_code}）生成分析报告")
    
    # 格式化情绪分析数据
    sentiment_data = chunks.get("情绪分析", {})
    sentiment_formatted = _format_sentiment_for_llm(sentiment_data)
    
    # 格式化筹码分析数据
    chip_data = chunks.get("筹码分析", {})
    chip_formatted = _format_chip_analysis_for_llm(chip_data)
    
    # 优化数据传递：只传递核心数据，减少LLM处理负担
    def optimize_data_for_llm(data):
        """压缩和优化传递给LLM的数据"""
        optimized = {}
        
        # 保留基本信息
        if "股票基本信息" in data:
            optimized["股票基本信息"] = data["股票基本信息"]
        
        # 压缩技术指标数据
        if "技术面末日" in data:
            tech = data["技术面末日"]
            optimized["技术指标"] = {
                "收盘价": tech.get("tech_last_close"),
                "RSI": tech.get("tech_last_rsi"), 
                "MACD": tech.get("tech_macd_signal"),
                "成交量": tech.get("tech_last_volume")
            }
        
        # 压缩基本面数据
        if "基本面摘要" in data:
            fund = data["基本面摘要"]
            if isinstance(fund, dict):
                optimized["基本面核心"] = {
                    "最新指标": fund.get("fina_indicator_latest", {}),
                    "收入趋势": fund.get("income_recent", [])[:3],  # 只取最近3期
                    "资产负债": fund.get("balance_recent", [])[:2]   # 只取最近2期
                }
        
        # 保留新闻摘要（限制条数）
        if "新闻资讯" in data:
            news = data["新闻资讯"]
            if isinstance(news, list):
                optimized["重要新闻"] = news[:5]  # 只取前5条
            else:
                optimized["重要新闻"] = news
        
        # 保留评分卡
        if "评分卡" in data:
            optimized["评分卡"] = data["评分卡"]
        
        return optimized
    
    # 在数据中注入格式化的分析数据
    enhanced_chunks = optimize_data_for_llm(chunks)
    if sentiment_formatted:
        enhanced_chunks["情绪分析"] = sentiment_formatted
    if chip_formatted:
        enhanced_chunks["筹码分析"] = chip_formatted
    
    # 提取基本信息进行验证和强调
    basic_info = enhanced_chunks.get("股票基本信息", {})
    actual_name = basic_info.get("name", stock_name)
    actual_code = basic_info.get("ts_code", stock_code)
    actual_industry = basic_info.get("industry", "数据中未提供")
    actual_area = basic_info.get("area", "数据中未提供")
    
    # 在prompt中明确指定要分析的股票并优化格式
    prompt_text = (
        f"【关键提醒】您必须分析以下这只股票，不得替换为其他股票：\n"
        f">>> 股票代码：{actual_code}\n"
        f">>> 股票名称：{actual_name}\n" 
        f">>> 所属行业：{actual_industry}\n"
        f">>> 所在地区：{actual_area}\n\n"
        
        f"【数据域覆盖】基本面、技术面、情绪面、筹码面、资金面\n"
        f"【严格规则】\n"
        f"1. 报告开头第一行必须是：股票代码：{actual_code}，股票名称：{actual_name}\n"
        f"2. **严禁**使用任何训练知识中的股票信息，必须100%基于传入数据\n"
        f"3. 如果您的训练知识中该股票代码对应其他公司，请忽略训练知识\n"
        f"4. 所有基本信息（名称、行业、地区）必须与上述【关键提醒】中完全一致\n"
        f"5. 严格按照【src: 接口.字段 | 日期 | 数值】格式引用所有数据\n"
        f"6. 所有结论必须有≥3条数据支撑，避免使用占位符XX或模糊表述\n"
        f"7. 如发现关键数据缺失，请在相应章节添加《数据缺失告警》\n\n"
        
        f"【{actual_name}({actual_code})完整数据集】：\n\n" 
        + json.dumps(enhanced_chunks, ensure_ascii=False, indent=2)
    )
    
    body = {
        "model": OLLAMA_MODEL,
        "system": SYS_PROMPT_V2,
        "prompt": prompt_text,
        "stream": bool(stream_callback),
        "options": {
            "temperature": 0.1,  # 进一步降低温度提高一致性和专业性
            "num_ctx": 32768,  # 大幅增加上下文长度处理复杂数据
            "num_predict": OLLAMA_NUM_PREDICT,  # 增加输出长度生成更详细报告
            "top_p": 0.95,  # 增加top_p获得更丰富表述
            "top_k": 50,  # 添加top_k进一步优化输出质量
            "repeat_penalty": 1.15,  # 增强避免重复
            "presence_penalty": 0.1,  # 添加存在惩罚鼓励多样性
            "frequency_penalty": 0.05,  # 添加频率惩罚避免重复用词
            "mirostat": 2,  # 启用mirostat改善长文本生成
            "mirostat_eta": 0.1,  # mirostat学习率
            "mirostat_tau": 5.0,  # mirostat目标熵
            "stop": None
        },
    }
    try:
        print(f"[LLM] 开始调用Ollama: model={OLLAMA_MODEL}, url={OLLAMA_URL}, streaming={bool(stream_callback)}")
        
        if stream_callback:
            # 流式响应
            r = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json=body,
                stream=True,
                timeout=OLLAMA_TIMEOUT,
            )
            r.raise_for_status()
            full_response = ""
            for line in r.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        if "response" in chunk:
                            token = chunk["response"]
                            full_response += token
                            stream_callback(token)
                        if chunk.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue
            print(f"[LLM] 流式响应完成，长度: {len(full_response)}")
            return _strip_think(full_response) if STRIP_THINK else full_response
        else:
            # 非流式响应
            r = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json=body,
                timeout=OLLAMA_TIMEOUT,
            )
            r.raise_for_status()
            resp = r.json().get("response", "").strip()
            print(f"[LLM] 响应长度: {len(resp)}")
            return _strip_think(resp) if STRIP_THINK else resp
    except requests.exceptions.Timeout:
        return "[LLM超时] 模型响应时间过长，请稍后重试"
    except Exception as e:
        print(f"[LLM错误] {e}")
        return f"[LLM错误] {e}"


# 热点概念深度追踪 — HOTSPOT_PROMPT_V2
HOTSPOT_PROMPT_V2 = (
"你是A股策略分析师（华泰/中信风格）。基于仅限传入的主题/成分股/新闻/资金数据，输出热点深度追踪报告。"
"\n【硬性规则】中文；所有判断必须量化；每条结论≥3条证据并附【src】；如数据缺失，列《数据缺失告警》；只在内部推理，不输出思维链。"
"\n\n╔═══════════════════════════════════════════════════════════╗"
"\n║                   A股热点深度追踪报告                      ║"
"\n╚═══════════════════════════════════════════════════════════╝"
"\n【热点快评】"
"\n- 热度评级：用热度分（0–100）+涨停家数/连板高度/封板率/成交额Δ%【src: ths_index/ths_daily, 板块排行, 新闻】"
"\n- 情绪阶段：启动/发酵/高潮/分歧/退潮（给出量化阈值与日期）【src】"
"\n- 持续预期：超短(1–2天)/短线(3–5天)/波段(1–2周)（证据×≥3）"
"\n\n一、【板块表现与龙头梯队】"
"\n- 板块收益：5D/10D、均值/中位数、成交额相对20D【src: ths_index/ths_daily】"
"\n- 涨停结构：首板/2板/3板/4板+、炸板率、封板质量【src: 第三方新闻/快讯(若提供)】"
"\n- 龙头谱系表：股票/连板/封单额/换手率/逻辑标签（真实名称与代码，勿用占位符）【src: ths_member, daily】"
"\n\n二、【资金博弈与筹码结构】"
"\n- 主力/超大单净流入（1/3/5日）、两融Δ%、HSGT净流入【src: moneyflow, margin, moneyflow_hsgt】"
"\n- 筹码：获利盘%、集中度CHI、密集区（若有）【src: cyq_perf, cyq_chips】"
"\n- 北向/港资对概念篮子的配置变化（5/10日）【src: moneyflow_hsgt, ccass_hold】"
"\n\n三、【新闻催化与时间轴】"
"\n- 近3/5/10日新闻情绪均值、关键词、重大事件列表【src: TuShare.news/major_news/第三方】"
"\n- 可能的下一触发器（时间/会议/数据），并注明\"不确定度来源\"。"
"\n\n四、【操作策略与风控】"
"\n- 激进（打板）：标的/时机/仓位/止损触发值【量化+src】"
"\n- 稳健（低吸）：回落买点区间（均线/筹码/ATR），仓位与止盈止损【src】"
"\n- 保守（观望）：需要的二次确认信号与数据阈值【src】"
"\n- 统一退场信号：广度<45% ∧ 两融降温 ∧ 北向/主力同步转负（给出具体数值与日期）【src】"
"\n\n《数据缺失告警》（如适用）"
"\n\n【末尾附：数据溯源清单】"
)

def summarize_hotspot(hotspot_data: dict, stream_callback=None) -> str:
    """分析热点概念数据，支持流式响应"""
    
    # 提取实际数据用于提示LLM
    keyword = hotspot_data.get('keyword', '未知')
    stocks = hotspot_data.get('stocks', [])
    analyzed_count = hotspot_data.get('analyzed_count', 0)
    total_related_count = hotspot_data.get('total_related_count', 0)
    news_count = hotspot_data.get('news', {}).get('news_count', 0)
    
    # 计算板块平均涨幅
    avg_change = 0
    median_change = 0
    if stocks:
        valid_changes = [s.get('price_change_pct', 0) for s in stocks if s.get('price_change_pct') is not None]
        if valid_changes:
            avg_change = round(sum(valid_changes) / len(valid_changes), 2)
            sorted_changes = sorted(valid_changes)
            median_change = round(sorted_changes[len(sorted_changes)//2], 2) if sorted_changes else 0
    
    # 获取前三只股票信息
    top_stocks = stocks[:3] if stocks else []
    
    # 构建增强的提示
    enhanced_prompt = (
        f"以下是{keyword}概念的实际数据：\n"
        f"- 关键词: {keyword}\n"
        f"- 相关股票总数: {total_related_count}只\n"
        f"- 已分析数量: {analyzed_count}只\n"  
        f"- 相关新闻数量: {news_count}条\n"
        f"- 板块平均涨幅: {avg_change}%\n"
        f"- 板块中位数涨幅: {median_change}%\n\n"
        "龙头股票：\n"
    )
    
    for i, stock in enumerate(top_stocks, 1):
        enhanced_prompt += (
            f"{i}. {stock.get('name', '未知')} ({stock.get('ts_code', '')}): "
            f"涨幅{stock.get('price_change_pct', 0)}%, "
            f"技术评分{stock.get('tech_score', 0)}, "
            f"基本面评分{stock.get('fund_score', 0)}, "
            f"资金评分{stock.get('money_score', 50)}\n"
        )
    
    enhanced_prompt += (
        f"\n请基于以上实际数据，生成{keyword}概念的专业分析报告。"
        "\n重要：必须使用我提供的实际数据和股票名称，不要使用XX或XXX等占位符。"
        "\n\n完整数据：\n"
    ) + json.dumps(hotspot_data, ensure_ascii=False, indent=2)
    
    body = {
        "model": OLLAMA_MODEL,
        "system": HOTSPOT_PROMPT_V2,
        "prompt": enhanced_prompt,
        "stream": bool(stream_callback),
        "options": {
            "temperature": 0.1,  # 进一步降低温度提高一致性和专业性
            "num_ctx": 32768,  # 大幅增加上下文长度处理复杂数据
            "num_predict": OLLAMA_NUM_PREDICT,  # 增加输出长度生成更详细报告
            "top_p": 0.95,  # 增加top_p获得更丰富表述
            "top_k": 50,  # 添加top_k进一步优化输出质量
            "repeat_penalty": 1.15,  # 增强避免重复
            "presence_penalty": 0.1,  # 添加存在惩罚鼓励多样性
            "frequency_penalty": 0.05,  # 添加频率惩罚避免重复用词
            "mirostat": 2,  # 启用mirostat改善长文本生成
            "mirostat_eta": 0.1,  # mirostat学习率
            "mirostat_tau": 5.0,  # mirostat目标熵
            "stop": None
        },
    }
    try:
        print(f"[LLM] 开始调用Ollama分析热点: model={OLLAMA_MODEL}, streaming={bool(stream_callback)}")
        
        if stream_callback:
            # 流式响应
            r = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json=body,
                stream=True,
                timeout=OLLAMA_TIMEOUT,
            )
            r.raise_for_status()
            full_response = ""
            for line in r.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        if "response" in chunk:
                            token = chunk["response"]
                            full_response += token
                            stream_callback(token)
                        if chunk.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue
            print(f"[LLM] 热点流式分析完成，长度: {len(full_response)}")
            return _strip_think(full_response) if STRIP_THINK else full_response
        else:
            # 非流式响应
            r = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json=body,
                timeout=OLLAMA_TIMEOUT,
            )
            r.raise_for_status()
            resp = r.json().get("response", "").strip()
            print(f"[LLM] 热点分析响应长度: {len(resp)}")
            return _strip_think(resp) if STRIP_THINK else resp
    except requests.exceptions.Timeout:
        return "[LLM超时] 模型响应时间过长，请稍后重试"
    except Exception as e:
        print(f"[LLM错误] {e}")
        return f"[LLM错误] {e}"


# 机构策略晨报 — MORNING_PROMPT_V2（增强版）
MORNING_PROMPT_V2 = (
"你是顶级券商（中金/中信/国君）首席策略分析师。基于传入的A股市场数据，生成专业策略晨报。"
"\n【核心要求】"
"\n1. 严格按照7个部分结构输出，每个部分都必须有实质性内容"
"\n2. 所有数字必须精确，避免使用模糊表述（如：约、大概、XX等）"
"\n3. 即使数据不完整，也要基于现有信息提供有价值的分析"
"\n4. 每个结论必须有数据支撑，格式：【数据源：具体数值/日期】"
"\n5. 提供可执行的投资建议，精确到仓位百分比和操作策略"
"\n6. 总字数控制在1000-1500字，确保内容充实但简洁"
"\n\n╔═══════════════════════════════════════════════════════════════════╗"
"\n║             A股机构策略晨报 · 全市场综合分析                        ║"
"\n╚═══════════════════════════════════════════════════════════════════╝"
"\n\n一、【市场概况与情绪研判】"
"\n基于涨跌家数、涨停数据、指数表现等核心指标，分析："
"\n• 市场整体情绪状态（极度乐观/乐观/中性/谨慎/极度谨慎）"
"\n• 情绪评级（1-10分）及详细理由【数据源：涨跌比X%，涨停X家】"
"\n• 市场参与者行为特征和情绪变化趋势"
"\n• 赚钱效应强弱评估"
"\n\n二、【资金流向与博弈分析】"
"\n• 北向资金流向：净流入X亿元，态度解读【数据源：具体金额/日期】"
"\n• 主力资金动向：超大单净流入X亿元，机构行为分析"
"\n• 融资融券变化：两融余额X亿元，杠杆情绪判断"
"\n• 不同资金之间的博弈状况和市场预期差异"
"\n\n三、【板块轮动与热点挖掘】"
"\n• 当前主流热点：X板块领涨（涨幅X%），持续性评估"
"\n• 板块轮动节奏：强势板块X个，轮动周期处于X阶段"
"\n• 潜在轮动机会：下一个可能爆发的板块及催化因素"
"\n• 操作策略：重点关注X板块，回避X板块"
"\n\n四、【技术面分析与趋势判断】"
"\n• 主要指数技术状态：上证指数X点（±X%），技术形态解读"
"\n• 短期趋势方向：1-3日看X，1-2周看X"
"\n• 关键技术位：支撑位X点，压力位X点"
"\n• 成交量能配合情况及有效性判断"
"\n\n五、【风险因素与预警提示】"
"\n• 当前主要风险点：系统性风险/结构性风险/流动性风险"
"\n• 具体风险指标：跌停X家，北向流出X亿元等"
"\n• 风险防控建议：仓位控制、止损设置、风险预警信号"
"\n• 需要重点关注的风险事件和时间点"
"\n\n六、【投资策略与仓位建议】"
"\n• 激进策略：仓位X-X%，重点配置X板块，预期收益X%"
"\n• 稳健策略：仓位X-X%，均衡配置，控制回撤"
"\n• 保守策略：仓位X%以下，防御性品种为主"
"\n• 具体操作：买入时机、卖出条件、止损位设置"
"\n\n七、【后市展望与关键变量】"
"\n• 影响后市的三大关键变量（政策面/资金面/基本面）"
"\n• 可能的市场演化路径：乐观/中性/悲观情景"
"\n• 重要时间节点：月末资金面、重要会议、数据发布"
"\n• 需要跟踪的先行指标和预警信号"
"\n\n【风险提示】股市有风险，投资需谨慎。以上分析仅供参考，不构成投资建议。"
"\n\n《注意事项》"
"\n- 如遇数据缺失，明确标注并基于经验给出合理预判"
"\n- 确保每个部分都有实质性内容，不得空洞或过于简化"
"\n- 所有建议必须具体可执行，避免泛泛而谈"
"\n- 重点突出与早报模板格式的7个部分对应关系"
)

# 保持向后兼容
MORNING_PROMPT = MORNING_PROMPT_V2


def summarize_morning(report_data: dict) -> str:
    body = {
        "model": OLLAMA_MODEL,
        "system": MORNING_PROMPT_V2,
        "prompt": "以下是A股市场相关数据：\n\n" + json.dumps(report_data, ensure_ascii=False, indent=2),
        "stream": False,
        "options": {
            "temperature": 0.1,  # 进一步降低温度提高一致性和专业性
            "num_ctx": 32768,  # 大幅增加上下文长度处理复杂数据
            "num_predict": OLLAMA_NUM_PREDICT,  # 增加输出长度生成更详细报告
            "top_p": 0.95,  # 增加top_p获得更丰富表述
            "top_k": 50,  # 添加top_k进一步优化输出质量
            "repeat_penalty": 1.15,  # 增强避免重复
            "presence_penalty": 0.1,  # 添加存在惩罚鼓励多样性
            "frequency_penalty": 0.05,  # 添加频率惩罚避免重复用词
            "mirostat": 2,  # 启用mirostat改善长文本生成
            "mirostat_eta": 0.1,  # mirostat学习率
            "mirostat_tau": 5.0,  # mirostat目标熵
            "stop": None
        },
    }
    try:
        print(f"[LLM] 生成晨报专业综述: model={OLLAMA_MODEL}")
        r = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=body,
            timeout=OLLAMA_TIMEOUT,
        )
        r.raise_for_status()
        resp = r.json().get("response", "").strip()
        return _strip_think(resp) if STRIP_THINK else resp
    except requests.exceptions.Timeout:
        return "[LLM超时] 模型响应时间过长，请稍后重试"
    except Exception as e:
        print(f"[LLM错误] {e}")
        return f"[LLM错误] {e}"
