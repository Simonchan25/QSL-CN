# 缓存配置优化
import datetime as dt
from typing import Dict, Any, Optional

# 不同数据类型的TTL配置（秒）- 完整覆盖所有数据类型
CACHE_TTL_CONFIG: Dict[str, int] = {
    # 实时数据 - 极短TTL (1-3分钟)
    "stock_realtime": 1 * 60,       # 1分钟 - 个股实时数据
    "market_overview": 2 * 60,      # 2分钟 - 市场概况
    "index_realtime": 2 * 60,       # 2分钟 - 指数实时

    # 准实时数据 - 短TTL (3-30分钟)
    "index_daily": 3 * 60,          # 3分钟 - 指数日线(交易时段频繁更新)
    "moneyflow": 10 * 60,           # 10分钟 - 资金流向
    "stk_limit": 10 * 60,           # 10分钟 - 涨跌停数据
    "anns": 10 * 60,                # 10分钟 - 最新公告
    "hot_stocks": 15 * 60,          # 15分钟 - 热点股票
    "capital_flow": 30 * 60,        # 30分钟 - 大额资金流向
    "market_breadth": 30 * 60,      # 30分钟 - 市场宽度
    "news": 30 * 60,                # 30分钟 - 新闻资讯
    
    # 交易数据 - 中TTL (1-3小时)
    "dragon_tiger": 1 * 3600,       # 1小时 - 龙虎榜
    "top_list": 3 * 3600,           # 3小时 - 龙虎榜统计
    "block_trade": 3 * 3600,        # 3小时 - 大宗交易
    "daily": 3 * 3600,              # 3小时 - 日线数据
    "daily_basic": 3 * 3600,        # 3小时 - 每日指标
    "adj_factor": 3 * 3600,         # 3小时 - 复权因子
    "margin": 3 * 3600,             # 3小时 - 融资融券
    "margin_detail": 3 * 3600,      # 3小时 - 融资融券明细
    "hsgt_top10": 3 * 3600,         # 3小时 - 沪深港通十大成交股
    
    # 财务数据 - 长TTL (6-12小时)
    "holders": 6 * 3600,            # 6小时 - 股东信息
    "stk_holdertrade": 6 * 3600,    # 6小时 - 股东增减持
    "income": 6 * 3600,             # 6小时 - 利润表
    "cashflow": 6 * 3600,           # 6小时 - 现金流量表
    "balancesheet": 6 * 3600,       # 6小时 - 资产负债表
    "forecast": 6 * 3600,           # 6小时 - 业绩预告
    "express": 6 * 3600,            # 6小时 - 业绩快报
    "fina_indicator": 6 * 3600,     # 6小时 - 财务指标
    "financial_data": 12 * 3600,    # 12小时 - 综合财务数据
    "suspend_d": 12 * 3600,         # 12小时 - 停复牌信息
    
    # 基础数据 - 适度TTL
    "stock_basic": 12 * 3600,       # 12小时 - 股票基本信息
    "concept": 6 * 3600,            # 6小时 - 概念分类（更频繁更新）
    "concept_detail": 3 * 3600,     # 3小时 - 概念明细（更频繁更新）
    "dividend": 24 * 3600,          # 24小时 - 分红送股
    "top10_holders": 24 * 3600,     # 24小时 - 前十大股东
    "top10_floatholders": 24 * 3600, # 24小时 - 前十大流通股东
    "fund_nav": 24 * 3600,          # 24小时 - 基金净值
    "fund_portfolio": 24 * 3600,    # 24小时 - 基金持仓
    "pledge_stat": 24 * 3600,       # 24小时 - 股权质押统计
    "pledge_detail": 24 * 3600,     # 24小时 - 股权质押明细
    "repurchase": 24 * 3600,        # 24小时 - 股票回购
    "share_float": 24 * 3600,       # 24小时 - 限售股解禁
    
    # 历史数据 - 最长TTL (7天)
    "historical_prices": 7 * 24 * 3600,  # 7天 - 历史价格数据
    "dividend_history": 7 * 24 * 3600,   # 7天 - 分红历史
    "namechange": 7 * 24 * 3600,    # 7天 - 股票曾用名
    
    # 宏观数据 - 最长TTL (7天)
    "cn_gdp": 7 * 24 * 3600,        # 7天 - GDP数据
    "cn_cpi": 7 * 24 * 3600,        # 7天 - CPI数据
    "cn_pmi": 7 * 24 * 3600,        # 7天 - PMI数据
    "cn_money": 7 * 24 * 3600,      # 7天 - 货币供应量
    "fx_reserves": 7 * 24 * 3600,   # 7天 - 外汇储备
    "money_supply": 7 * 24 * 3600,  # 7天 - 货币供应
    "cpi": 7 * 24 * 3600,           # 7天 - 居民消费价格指数
    
    # 其他数据 - 中等TTL
    "announcements": 2 * 3600,      # 2小时 - 公司公告
    "index_classify": 6 * 3600,     # 6小时 - 指数分类
    "index_member": 6 * 3600,       # 6小时 - 指数成分
}

def get_cache_ttl(data_type: str) -> int:
    """获取数据类型对应的TTL"""
    return CACHE_TTL_CONFIG.get(data_type, 3600)  # 默认1小时

def is_trading_hours() -> bool:
    """判断是否在交易时间"""
    now = dt.datetime.now()
    weekday = now.weekday()
    hour = now.hour
    minute = now.minute
    
    # 非交易日（周六日）
    if weekday >= 5:
        return False
    
    # 交易时间：9:30-11:30, 13:00-15:00
    morning_start = dt.time(9, 30)
    morning_end = dt.time(11, 30)
    afternoon_start = dt.time(13, 0)
    afternoon_end = dt.time(15, 0)
    
    current_time = dt.time(hour, minute)
    
    return (morning_start <= current_time <= morning_end or 
            afternoon_start <= current_time <= afternoon_end)

def get_dynamic_ttl(data_type: str, context: Optional[Dict[str, Any]] = None) -> int:
    """
    动态缓存策略 - 根据多种因素智能调整TTL

    Args:
        data_type: 数据类型
        context: 上下文信息 {
            'ts_code': 股票代码,
            'is_hot': 是否热门股,
            'has_event': 是否有重大事件,
            'market_volatile': 市场是否剧烈波动
        }
    """
    base_ttl = get_cache_ttl(data_type)

    # 初始化调整系数
    multiplier = 1.0

    # 1. 自动判断热门股票（如果提供了ts_code但没有is_hot）
    if context and 'ts_code' in context and 'is_hot' not in context:
        context['is_hot'] = is_hot_stock(context['ts_code'])

    # 2. 交易时间调整（基础调整）
    if is_trading_hours():
        # 交易时间缩短TTL
        if data_type in ["stock_realtime", "moneyflow", "news", "anns"]:
            base_multiplier = 0.3  # 实时数据大幅缩短
        elif data_type in ["market_overview", "index_realtime", "capital_flow"]:
            base_multiplier = 0.5  # 市场数据适度缩短
        else:
            base_multiplier = 0.7  # 其他数据略微缩短
    else:
        # 非交易时间延长TTL
        if is_pre_market_hours():
            # 盘前时段（8:00-9:30）适度缓存
            base_multiplier = 1.5
        elif is_after_hours():
            # 盘后时段（15:00-18:00）正常缓存
            base_multiplier = 1.0
        else:
            # 夜间和周末，但不要延长太多
            base_multiplier = 2.0  # 从3.0改为2.0

    multiplier *= base_multiplier

    # 3. 热门股票调整（独立计算，不受时间段影响）
    if context and context.get('is_hot'):
        # 热门股票始终需要更频繁更新
        hot_multiplier = 0.3 if data_type in ["news", "anns", "stock_realtime"] else 0.5
        # 使用较小值（更频繁更新）
        multiplier = min(multiplier, multiplier * hot_multiplier)

    # 4. 重大事件调整
    if context and context.get('has_event'):
        # 有重大事件时大幅缩短TTL
        if data_type in ["news", "anns", "stock_realtime"]:
            multiplier *= 0.2  # 新闻和公告需要高频更新
        else:
            multiplier *= 0.5

    # 5. 市场波动调整
    if context and context.get('market_volatile'):
        # 市场剧烈波动时缩短TTL
        multiplier *= 0.6

    # 6. 数据类型特殊处理
    if data_type == "news":
        # 新闻数据在任何情况下不超过30分钟
        max_ttl = 30 * 60
    elif data_type == "anns":
        # 公告数据在任何情况下不超过15分钟
        max_ttl = 15 * 60
    elif data_type == "stock_realtime":
        # 实时数据在交易时间不超过1分钟
        max_ttl = 60 if is_trading_hours() else 10 * 60
    else:
        max_ttl = base_ttl * 3  # 其他数据最多3倍基础TTL

    # 计算最终TTL
    final_ttl = int(base_ttl * multiplier)

    # 确保在合理范围内
    min_ttl = 30  # 最少30秒
    final_ttl = max(min_ttl, min(final_ttl, max_ttl))

    return final_ttl

def is_pre_market_hours() -> bool:
    """判断是否在盘前时段"""
    now = dt.datetime.now()
    weekday = now.weekday()

    # 周末不算盘前
    if weekday >= 5:
        return False

    hour = now.hour
    minute = now.minute
    current_time = dt.time(hour, minute)

    pre_market_start = dt.time(8, 0)
    pre_market_end = dt.time(9, 30)

    return pre_market_start <= current_time < pre_market_end

def is_after_hours() -> bool:
    """判断是否在盘后时段"""
    now = dt.datetime.now()
    weekday = now.weekday()

    # 周末不算盘后
    if weekday >= 5:
        return False

    hour = now.hour
    minute = now.minute
    current_time = dt.time(hour, minute)

    after_hours_start = dt.time(15, 0)
    after_hours_end = dt.time(18, 0)

    return after_hours_start <= current_time < after_hours_end

def is_hot_stock(ts_code: str) -> bool:
    """
    判断是否为热门股票
    基于多个维度：成交量、涨跌幅、换手率等
    """
    try:
        from .tushare_client import daily

        # 获取最近交易数据（注意：daily返回的数据已经包含了基本指标）
        daily_df = daily(ts_code)
        if daily_df is None or daily_df.empty:
            return False

        # 只取最近5天数据
        recent = daily_df.head(5)

        # 从daily数据中直接获取指标（5000积分数据更丰富）
        # 计算平均成交额（亿元）
        avg_amount = recent['amount'].mean() / 10000 if 'amount' in recent.columns else 0

        # 平均换手率（turn_over字段）
        avg_turnover = recent['turn_over'].mean() if 'turn_over' in recent.columns else 0

        # 平均涨跌幅
        avg_change = recent['pct_change'].abs().mean() if 'pct_change' in recent.columns else 0

        # 最新量比
        latest_vol_ratio = daily_df.iloc[0].get('vol_ratio', 0) if not daily_df.empty else 0

        # 总市值（亿）
        total_mv = daily_df.iloc[0].get('total_mv', 0) if not daily_df.empty else 0

        # 热门股判断标准（适配5000积分数据特点）
        is_hot = False

        # 1. 高成交额（根据实际数据调整）
        # 超大盘股（市值>5000亿）：成交额>30亿
        # 大盘股（市值1000-5000亿）：成交额>20亿
        # 中小盘股：成交额>10亿
        if total_mv > 5000 and avg_amount > 30:
            is_hot = True
        elif total_mv > 1000 and avg_amount > 20:
            is_hot = True
        elif avg_amount > 10:
            is_hot = True

        # 2. 高换手率（超过2%为活跃）
        if avg_turnover > 2:
            is_hot = True

        # 3. 高量比（超过1.5为放量）
        if latest_vol_ratio > 1.5:
            is_hot = True

        # 4. 剧烈波动（平均涨跌幅超过2%）
        if avg_change > 2:
            is_hot = True

        # 5. 连续大涨大跌（3天涨跌幅绝对值都超过2%）
        if len(recent) >= 3:
            recent_changes = recent.head(3)['pct_change'].abs() if 'pct_change' in recent.columns else None
            if recent_changes is not None and (recent_changes > 2).all():
                is_hot = True

        return is_hot

    except Exception as e:
        # 如果获取数据失败，返回False
        import logging
        logging.error(f"判断热门股失败 {ts_code}: {e}")
        return False

def has_major_event(ts_code: str) -> bool:
    """
    判断股票是否有重大事件
    基于：重大公告、异常波动、停复牌等
    """
    try:
        # 尝试使用智能事件检测器
        from .event_detector import has_major_event_smart
        from .tushare_client import anns, daily
        from .news import fetch_recent_news

        # 获取实时数据传入事件检测器
        announcements = None
        news = None
        price_data = None

        try:
            # 获取最近公告（限制数量避免太慢）
            ann_df = anns(ts_code, limit=10)
            if ann_df is not None and not ann_df.empty:
                announcements = []
                for _, row in ann_df.iterrows():
                    announcements.append({
                        'title': row.get('title', ''),
                        'ann_date': row.get('ann_date', '')
                    })
        except:
            pass

        try:
            # 获取最近新闻
            news_data = fetch_recent_news(days_back=1)
            if news_data:
                # 只保留包含股票代码的新闻
                stock_code_short = ts_code.split('.')[0]
                news = [n for n in news_data if stock_code_short in str(n.get('content', ''))][:10]
        except:
            pass

        try:
            # 获取最新价格数据
            daily_df = daily(ts_code)
            if daily_df is not None and not daily_df.empty:
                row = daily_df.iloc[0]
                price_data = {
                    'pct_chg': row.get('pct_chg', 0),
                    'volume_ratio': row.get('vol', 0) / row.get('vol', 1),  # 简化的量比
                    'turnover_rate': row.get('turnover_rate', 0),
                    'amplitude': row.get('high', 0) - row.get('low', 0),
                }
        except:
            pass

        # 调用事件检测器
        return has_major_event_smart(ts_code, announcements, news, price_data)

    except Exception as e:
        # 如果事件检测器不可用，使用简单规则
        # 可以维护一个已知的重大事件列表
        major_event_stocks = {
            # 示例：最近有重大事件的股票
            # '002594.SZ': '新车型发布',
            # '600519.SH': '业绩预告',
        }
        return ts_code in major_event_stocks

def get_market_volatility() -> float:
    """
    获取市场波动率
    可以基于：指数涨跌幅、成交量、VIX指数等
    """
    # 这里简化处理，实际可以计算：
    # 1. 主要指数的日内波动
    # 2. 成交量相对历史均值的比例
    # 3. 涨跌停数量

    return 0.5  # 返回0-1的波动率，0.5表示正常

def is_market_volatile() -> bool:
    """判断市场是否剧烈波动"""
    return get_market_volatility() > 0.7

# 导出新增的函数
__all__ = [
    'CACHE_TTL_CONFIG',
    'get_cache_ttl',
    'get_dynamic_ttl',
    'is_trading_hours',
    'is_pre_market_hours',
    'is_after_hours',
    'is_hot_stock',
    'has_major_event',
    'is_market_volatile'
]