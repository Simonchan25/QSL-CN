"""
模拟数据模块 - 用于TuShare服务器维护期间的测试
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

def get_mock_stock_basic():
    """模拟股票列表数据"""
    stocks = [
        {"ts_code": "000001.SZ", "symbol": "000001", "name": "平安银行", "area": "深圳", "industry": "银行", "market": "主板", "list_status": "L"},
        {"ts_code": "000002.SZ", "symbol": "000002", "name": "万科A", "area": "深圳", "industry": "房地产", "market": "主板", "list_status": "L"},
        {"ts_code": "600519.SH", "symbol": "600519", "name": "贵州茅台", "area": "贵州", "industry": "白酒", "market": "主板", "list_status": "L"},
        {"ts_code": "000858.SZ", "symbol": "000858", "name": "五粮液", "area": "四川", "industry": "白酒", "market": "主板", "list_status": "L"},
        {"ts_code": "002371.SZ", "symbol": "002371", "name": "北方华创", "area": "北京", "industry": "半导体", "market": "中小板", "list_status": "L"},
        {"ts_code": "300750.SZ", "symbol": "300750", "name": "宁德时代", "area": "福建", "industry": "电池", "market": "创业板", "list_status": "L"},
        {"ts_code": "002230.SZ", "symbol": "002230", "name": "科大讯飞", "area": "安徽", "industry": "人工智能", "market": "中小板", "list_status": "L"},
        {"ts_code": "688111.SH", "symbol": "688111", "name": "金山办公", "area": "北京", "industry": "软件", "market": "科创板", "list_status": "L"},
        {"ts_code": "300124.SZ", "symbol": "300124", "name": "汇川技术", "area": "深圳", "industry": "工控", "market": "创业板", "list_status": "L"},
        {"ts_code": "002555.SZ", "symbol": "002555", "name": "三七互娱", "area": "广东", "industry": "游戏", "market": "中小板", "list_status": "L"},
        # 脑机概念股
        {"ts_code": "300775.SZ", "symbol": "300775", "name": "三角防务", "area": "陕西", "industry": "脑机接口", "market": "创业板", "list_status": "L"},
        {"ts_code": "688066.SH", "symbol": "688066", "name": "航天宏图", "area": "北京", "industry": "脑科学", "market": "科创板", "list_status": "L"},
        {"ts_code": "002382.SZ", "symbol": "002382", "name": "蓝帆医疗", "area": "山东", "industry": "医疗器械", "market": "中小板", "list_status": "L"},
        # AI概念股
        {"ts_code": "002410.SZ", "symbol": "002410", "name": "广联达", "area": "北京", "industry": "人工智能", "market": "中小板", "list_status": "L"},
        {"ts_code": "000977.SZ", "symbol": "000977", "name": "浪潮信息", "area": "山东", "industry": "AI服务器", "market": "主板", "list_status": "L"},
        {"ts_code": "300454.SZ", "symbol": "300454", "name": "深信服", "area": "深圳", "industry": "网络安全", "market": "创业板", "list_status": "L"},
    ]
    return pd.DataFrame(stocks)


def get_mock_daily(ts_code, start_date, end_date):
    """模拟日线数据"""
    start = pd.to_datetime(start_date, format='%Y%m%d')
    end = pd.to_datetime(end_date, format='%Y%m%d')
    dates = pd.date_range(start=start, end=end, freq='B')  # 工作日
    
    # 生成模拟价格数据
    base_price = random.uniform(10, 500)
    data = []
    
    for i, date in enumerate(dates):
        # 模拟价格波动
        change = np.random.normal(0, 0.02)  # 2%标准差
        close = base_price * (1 + change)
        open_price = close * (1 + np.random.normal(0, 0.01))
        high = max(open_price, close) * (1 + abs(np.random.normal(0, 0.005)))
        low = min(open_price, close) * (1 - abs(np.random.normal(0, 0.005)))
        
        data.append({
            "ts_code": ts_code,
            "trade_date": date.strftime('%Y%m%d'),
            "open": round(open_price, 2),
            "high": round(high, 2),
            "low": round(low, 2),
            "close": round(close, 2),
            "pre_close": round(base_price, 2),
            "change": round(close - base_price, 2),
            "pct_chg": round(change * 100, 2),
            "vol": random.randint(100000, 1000000),
            "amount": random.randint(1000000, 10000000)
        })
        base_price = close
    
    return pd.DataFrame(data)


def get_mock_daily_basic(ts_code, trade_date=None, end_date=None):
    """模拟每日指标数据"""
    data = [{
        "ts_code": ts_code,
        "trade_date": trade_date or end_date or datetime.now().strftime('%Y%m%d'),
        "pe": round(random.uniform(10, 50), 2),
        "pe_ttm": round(random.uniform(10, 50), 2),
        "pb": round(random.uniform(1, 5), 2),
        "ps": round(random.uniform(1, 10), 2),
        "ps_ttm": round(random.uniform(1, 10), 2),
        "dv_ratio": round(random.uniform(0, 3), 2),
        "dv_ttm": round(random.uniform(0, 3), 2),
        "total_mv": round(random.uniform(1000000, 10000000), 2),
        "circ_mv": round(random.uniform(500000, 5000000), 2),
        "turnover_rate": round(random.uniform(0.5, 5), 2),
        "turnover_rate_f": round(random.uniform(0.5, 5), 2),
        "volume_ratio": round(random.uniform(0.5, 2), 2),
    }]
    return pd.DataFrame(data)


def get_mock_fina_indicator(ts_code):
    """模拟财务指标数据"""
    dates = pd.date_range(end=datetime.now(), periods=4, freq='Q')
    data = []
    
    for date in dates:
        data.append({
            "ts_code": ts_code,
            "end_date": date.strftime('%Y%m%d'),
            "roe": round(random.uniform(5, 25), 2),
            "roa": round(random.uniform(3, 15), 2),
            "grossprofit_margin": round(random.uniform(20, 60), 2),
            "netprofit_margin": round(random.uniform(5, 30), 2),
            "asset_turn": round(random.uniform(0.5, 1.5), 2),
            "op_yoy": round(random.uniform(-20, 50), 2),
            "or_yoy": round(random.uniform(-20, 50), 2),
            "profit_dedt": round(random.uniform(-30, 100), 2),
            "q_dtprofit": round(random.uniform(-30, 100), 2),
            "q_profit_yoy": round(random.uniform(-30, 100), 2),
            "q_gr_yoy": round(random.uniform(-20, 50), 2),
            "current_ratio": round(random.uniform(1, 3), 2),
            "quick_ratio": round(random.uniform(0.8, 2.5), 2),
            "debt_to_eqt": round(random.uniform(0.3, 1.5), 2),
        })
    
    return pd.DataFrame(data)


def get_mock_income(ts_code, limit=8):
    """模拟利润表数据"""
    dates = pd.date_range(end=datetime.now(), periods=limit, freq='Q')
    data = []
    
    for date in dates:
        revenue = random.uniform(1000000, 10000000)
        data.append({
            "ts_code": ts_code,
            "end_date": date.strftime('%Y%m%d'),
            "revenue": round(revenue, 2),
            "n_income": round(revenue * random.uniform(0.05, 0.2), 2),
            "n_income_attr_p": round(revenue * random.uniform(0.04, 0.18), 2),
            "total_profit": round(revenue * random.uniform(0.06, 0.25), 2),
            "operate_profit": round(revenue * random.uniform(0.07, 0.22), 2),
        })
    
    return pd.DataFrame(data)


def get_mock_balancesheet(ts_code, limit=4):
    """模拟资产负债表数据"""
    dates = pd.date_range(end=datetime.now(), periods=limit, freq='Q')
    data = []
    
    for date in dates:
        total_assets = random.uniform(10000000, 100000000)
        data.append({
            "ts_code": ts_code,
            "end_date": date.strftime('%Y%m%d'),
            "total_assets": round(total_assets, 2),
            "total_liab": round(total_assets * random.uniform(0.3, 0.7), 2),
        })
    
    return pd.DataFrame(data)


def get_mock_cashflow(ts_code, limit=4):
    """模拟现金流量表数据"""
    dates = pd.date_range(end=datetime.now(), periods=limit, freq='Q')
    data = []
    
    for date in dates:
        data.append({
            "ts_code": ts_code,
            "end_date": date.strftime('%Y%m%d'),
            "n_cashflow_act": round(random.uniform(100000, 1000000), 2),
            "procure_fixed_assets": round(random.uniform(10000, 100000), 2),
        })
    
    return pd.DataFrame(data)


def get_mock_forecast(ts_code):
    """模拟业绩预告"""
    return pd.DataFrame([{
        "ts_code": ts_code,
        "ann_date": datetime.now().strftime('%Y%m%d'),
        "end_date": (datetime.now() + timedelta(days=90)).strftime('%Y%m%d'),
        "type": "预增",
        "p_change_min": 30,
        "p_change_max": 50,
        "net_profit_min": 1000000,
        "net_profit_max": 1500000,
        "summary": "公司预计本期净利润较上年同期增长30%-50%",
    }])


def get_mock_express(ts_code):
    """模拟业绩快报"""
    return pd.DataFrame([{
        "ts_code": ts_code,
        "ann_date": datetime.now().strftime('%Y%m%d'),
        "end_date": datetime.now().strftime('%Y%m%d'),
        "revenue": 5000000,
        "operate_profit": 800000,
        "total_profit": 750000,
        "n_income": 600000,
        "eps": 0.85,
    }])


def get_mock_news(src="sina", limit=100):
    """模拟新闻数据"""
    news_templates = [
        "央行释放流动性，市场信心提振",
        "科技板块集体走强，AI概念股领涨",
        "新能源车销量创新高，产业链受益",
        "半导体行业迎来新机遇",
        "消费升级趋势明显，白酒板块表现强势",
        "医药生物板块调整，关注创新药机会",
        "5G应用加速落地，通信板块值得关注",
        "碳中和政策推进，新能源板块持续受益",
    ]
    
    data = []
    for i in range(min(limit, len(news_templates))):
        data.append({
            "datetime": (datetime.now() - timedelta(hours=i)).strftime('%Y-%m-%d %H:%M:%S'),
            "title": news_templates[i % len(news_templates)],
            "content": f"详细内容：{news_templates[i % len(news_templates)]}...",
            "src": src
        })
    
    return pd.DataFrame(data)


def get_mock_index_daily(ts_code, start_date=None, end_date=None):
    """模拟指数日线数据"""
    # 定义各指数的基础价格
    index_base_prices = {
        "000001.SH": {"name": "上证指数", "base": 2950.0, "change": 0.8},
        "399001.SZ": {"name": "深证成指", "base": 9200.0, "change": 1.2},
        "399006.SZ": {"name": "创业板指", "base": 1680.0, "change": -0.5},
        "000300.SH": {"name": "沪深300", "base": 3580.0, "change": 0.6},
        "000016.SH": {"name": "上证50", "base": 2420.0, "change": 0.3},
        "000905.SH": {"name": "中证500", "base": 4850.0, "change": 1.5},
    }
    
    if ts_code not in index_base_prices:
        # 如果指数不在预定义中，使用默认值
        index_info = {"name": "未知指数", "base": 3000.0, "change": 0.0}
    else:
        index_info = index_base_prices[ts_code]
    
    # 生成最近一天的数据
    today = datetime.now()
    trade_date = today.strftime('%Y%m%d')
    
    base_price = index_info["base"]
    pct_change = index_info["change"]
    
    # 模拟当日价格
    close_price = base_price * (1 + pct_change / 100)
    open_price = close_price * (1 + np.random.normal(0, 0.002))
    high_price = max(open_price, close_price) * (1 + abs(np.random.normal(0, 0.001)))
    low_price = min(open_price, close_price) * (1 - abs(np.random.normal(0, 0.001)))
    
    data = [{
        "ts_code": ts_code,
        "trade_date": trade_date,
        "close": round(close_price, 2),
        "open": round(open_price, 2),
        "high": round(high_price, 2),
        "low": round(low_price, 2),
        "pct_chg": round(pct_change, 2),
        "change": round(base_price * pct_change / 100, 2),
        "vol": random.randint(50000000, 200000000),  # 成交量
        "amount": random.randint(60000000, 300000000)  # 成交额
    }]
    
    return pd.DataFrame(data)


def get_mock_anns(ts_code, limit=15):
    """模拟公司公告"""
    ann_types = [
        "2024年第三季度报告",
        "关于股东减持计划的公告",
        "关于签订重大合同的公告",
        "股东大会决议公告",
        "关于对外投资的公告",
    ]
    
    data = []
    for i in range(min(limit, len(ann_types))):
        data.append({
            "ts_code": ts_code,
            "ann_date": (datetime.now() - timedelta(days=i*5)).strftime('%Y%m%d'),
            "title": ann_types[i % len(ann_types)],
            "ann_id": f"ANN{i:06d}",
        })
    
    return pd.DataFrame(data)


def get_mock_moneyflow(ts_code, start_date=None, end_date=None):
    """模拟资金流向数据"""
    if not end_date:
        end_date = datetime.now().strftime('%Y%m%d')
    if not start_date:
        start_date = (datetime.now() - timedelta(days=20)).strftime('%Y%m%d')
    
    dates = pd.date_range(start=start_date, end=end_date, freq='B')
    data = []
    
    for date in dates:
        base = random.uniform(1000000, 10000000)
        data.append({
            "ts_code": ts_code,
            "trade_date": date.strftime('%Y%m%d'),
            "buy_elg_amount": base * random.uniform(0.1, 0.3),
            "buy_lg_amount": base * random.uniform(0.1, 0.2),
            "buy_md_amount": base * random.uniform(0.2, 0.3),
            "buy_sm_amount": base * random.uniform(0.3, 0.4),
            "sell_elg_amount": base * random.uniform(0.1, 0.25),
            "sell_lg_amount": base * random.uniform(0.1, 0.2),
            "sell_md_amount": base * random.uniform(0.2, 0.3),
            "sell_sm_amount": base * random.uniform(0.3, 0.45),
        })
    
    return pd.DataFrame(data)


def get_mock_margin_detail(ts_code=None, trade_date=None):
    """模拟融资融券数据"""
    if not trade_date:
        trade_date = datetime.now().strftime('%Y%m%d')
    
    return pd.DataFrame([{
        "ts_code": ts_code or "000001.SZ",
        "trade_date": trade_date,
        "rzye": random.uniform(100000000, 1000000000),  # 融资余额
        "rqye": random.uniform(10000000, 100000000),    # 融券余额
    }])


def get_mock_moneyflow_hsgt(trade_date=None):
    """模拟北向资金数据"""
    if not trade_date:
        trade_date = datetime.now().strftime('%Y%m%d')
    
    dates = pd.date_range(end=trade_date, periods=5, freq='B')
    data = []
    
    for date in dates:
        data.append({
            "trade_date": date.strftime('%Y%m%d'),
            "hgt_net": random.uniform(-5000, 10000),  # 沪股通净流入（百万）
            "sgt_net": random.uniform(-3000, 8000),   # 深股通净流入（百万）
        })
    
    return pd.DataFrame(data)


def get_mock_stk_limit(ts_code=None, trade_date=None):
    """模拟涨跌停数据"""
    if not trade_date:
        trade_date = datetime.now().strftime('%Y%m%d')
    
    # 生成多只股票的涨跌停数据
    stocks = get_mock_stock_basic().sample(n=min(50, len(get_mock_stock_basic())))
    data = []
    
    for _, stock in stocks.iterrows():
        if random.random() > 0.7:  # 30%概率涨停或跌停
            price = random.uniform(10, 100)
            is_up = random.random() > 0.4  # 60%涨停，40%跌停
            data.append({
                "ts_code": stock['ts_code'],
                "trade_date": trade_date,
                "up_limit": price * 1.1 if is_up else 0,
                "down_limit": 0 if is_up else price * 0.9,
            })
    
    return pd.DataFrame(data)


def get_mock_macro_data():
    """模拟宏观经济数据"""
    return {
        "cpi": pd.DataFrame([{
            "month": datetime.now().strftime('%Y%m'),
            "cpi": 102.3,
            "cpi_yoy": 2.3,
            "cpi_mom": 0.3,
        }]),
        "ppi": pd.DataFrame([{
            "month": datetime.now().strftime('%Y%m'),
            "ppi_yoy": -0.5,
            "ppi_mom": 0.1,
        }]),
        "money_supply": pd.DataFrame([{
            "month": datetime.now().strftime('%Y%m'),
            "m0_yoy": 5.2,
            "m1_yoy": 6.8,
            "m2_yoy": 8.5,
        }]),
        "shibor": pd.DataFrame([{
            "date": datetime.now().strftime('%Y%m%d'),
            "on": 1.85,
            "1w": 2.10,
            "1m": 2.35,
            "3m": 2.50,
        }]),
        "gdp": pd.DataFrame([{
            "quarter": datetime.now().strftime('%Y%m'),
            "gdp": 296298.0,
            "gdp_yoy": 5.2,
        }]),
        "pmi": pd.DataFrame([{
            "month": datetime.now().strftime('%Y%m'),
            "pmi": 50.8,
            "pmi_mfg": 50.5,
            "pmi_non_mfg": 51.2,
        }]),
    }


# 模拟数据开关
MOCK_MODE = True  # 设置为True启用模拟数据

def is_mock_mode():
    """检查是否处于模拟模式"""
    return MOCK_MODE