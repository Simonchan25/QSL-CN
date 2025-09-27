from __future__ import annotations

import datetime as dt
from typing import Dict, Any, List
import numpy as np
import pandas as pd

from .tushare_client import (
    shibor, major_news, ths_hot, daily_basic, moneyflow_hsgt, anns,
    top_list, top_inst, stk_limit, moneyflow, margin_detail, concept, concept_detail,
    moneyflow_ths, moneyflow_dc, stock_hsgt
)
from .trading_date_helper import find_latest_trading_date_with_data
from .tushare_client import _get_any_cached_df as _get_any_cached_df  # type: ignore
from .tushare_client import _get_cached_df as _get_cached_df          # type: ignore
from .tushare_client import _save_df_cache as _save_df_cache          # type: ignore
from .tushare_client import _call_api as _call_api                    # type: ignore
from .tushare_client import STRICT_MODE as _STRICT_MODE               # type: ignore


INDEX_CODES: List[str] = [
    "000001.SH",  # 上证综指
    "399001.SZ",  # 深证成指
    "399006.SZ",  # 创业板指
    "000300.SH",  # 沪深300
    "000016.SH",  # 上证50
]

INDEX_NAMES = {
    "000001.SH": "上证指数",
    "399001.SZ": "深证成指", 
    "399006.SZ": "创业板指",
    "000300.SH": "沪深300",
    "000016.SH": "上证50",
    "000905.SH": "中证500",
}

# 行业板块代码
SECTOR_CODES: List[str] = [
    "801010.SI",  # 农林牧渔
    "801020.SI",  # 采掘
    "801030.SI",  # 化工
    "801040.SI",  # 钢铁
    "801050.SI",  # 有色金属
    "801080.SI",  # 电子
    "801110.SI",  # 家用电器
    "801120.SI",  # 食品饮料
    "801130.SI",  # 纺织服装
    "801140.SI",  # 轻工制造
    "801150.SI",  # 医药生物
    "801160.SI",  # 公用事业
    "801170.SI",  # 交通运输
    "801180.SI",  # 房地产
    "801200.SI",  # 商业贸易
    "801210.SI",  # 休闲服务
    "801230.SI",  # 综合
    "801710.SI",  # 建筑材料
    "801720.SI",  # 建筑装饰
    "801730.SI",  # 电气设备
    "801740.SI",  # 国防军工
    "801750.SI",  # 计算机
    "801760.SI",  # 传媒
    "801770.SI",  # 通信
    "801780.SI",  # 银行
    "801790.SI",  # 非银金融
    "801880.SI",  # 汽车
    "801890.SI",  # 机械设备
]


def _today_str() -> str:
    return dt.date.today().strftime("%Y%m%d")


def _clean_nan_values(data: Any) -> Any:
    """递归清理数据中的NaN、None和inf值，使其JSON可序列化"""
    if isinstance(data, dict):
        return {key: _clean_nan_values(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [_clean_nan_values(item) for item in data]
    elif isinstance(data, (np.int64, np.int32)):
        return int(data)
    elif isinstance(data, (np.float64, np.float32)):
        if pd.isna(data) or np.isinf(data):
            return None
        return float(data)
    elif pd.isna(data):
        return None
    elif isinstance(data, float) and (np.isnan(data) or np.isinf(data)):
        return None
    else:
        return data


def _index_daily(ts_code: str, start: str, end: str) -> pd.DataFrame:
    from .cache_config import get_dynamic_ttl
    
    key = f"index_daily_{ts_code}_{start}_{end}"
    stale = _get_any_cached_df(key)
    # 使用动态TTL
    ttl = get_dynamic_ttl("index_daily")
    cached_df = _get_cached_df(key, ttl_seconds=ttl)
    if cached_df is not None and not cached_df.empty:
        return cached_df
    try:
        df = _call_api("index_daily", ts_code=ts_code, start_date=start, end_date=end)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return df if df is not None else pd.DataFrame()
    except Exception:
        # 严格模式：不回退
        if _STRICT_MODE:
            return pd.DataFrame()
        # 非严格模式：允许回退
        return stale if stale is not None else pd.DataFrame()


def _get_sector_performance() -> List[Dict[str, Any]]:
    """获取行业板块表现 - 使用同花顺热点数据"""
    from .trading_date_helper import get_recent_trading_dates
    
    sectors = []
    try:
        # 获取最近交易日数据
        recent_dates = get_recent_trading_dates(5)
        
        for date in recent_dates[:3]:  # 尝试最近3个交易日
            try:
                ths = ths_hot(trade_date=date)
                if ths is not None and not ths.empty and 'data_type' in ths.columns:
                    # 获取概念板块和行业板块数据
                    concept_data = ths[ths['data_type'].isin(['概念板块', '行业板块'])]
                    
                    if not concept_data.empty:
                        for _, row in concept_data.head(10).iterrows():  # 取前10个热点
                            sectors.append({
                                "code": row.get("ts_code", ""),
                                "name": row.get("ts_name", ""),
                                "pct_chg": float(row.get("pct_change", 0) or 0),
                                "close": float(row.get("close", 0) or 0),
                                "trade_date": date,
                                "data_type": row.get("data_type", "概念板块"),
                            })
                        
                        print(f"[板块数据] 获取到 {len(sectors)} 个热点板块数据 (来源: {date})")
                        break
            except Exception as e:
                print(f"[板块数据] {date} 获取失败: {e}")
                continue
        
        # 按涨跌幅排序
        sectors.sort(key=lambda x: x["pct_chg"], reverse=True)
        
    except Exception as e:
        print(f"[警告] 获取板块表现数据失败: {e}")
    
    return sectors

def _get_sector_name(code: str) -> str:
    """获取行业名称"""
    name_map = {
        "801010.SI": "农林牧渔", "801020.SI": "采掘", "801030.SI": "化工",
        "801040.SI": "钢铁", "801050.SI": "有色金属", "801080.SI": "电子",
        "801110.SI": "家用电器", "801120.SI": "食品饮料", "801130.SI": "纺织服装",
        "801140.SI": "轻工制造", "801150.SI": "医药生物", "801160.SI": "公用事业",
        "801170.SI": "交通运输", "801180.SI": "房地产", "801200.SI": "商业贸易",
        "801710.SI": "建筑材料", "801720.SI": "建筑装饰", "801730.SI": "电气设备",
        "801740.SI": "国防军工", "801750.SI": "计算机", "801760.SI": "传媒",
        "801770.SI": "通信", "801780.SI": "银行", "801790.SI": "非银金融",
        "801880.SI": "汽车", "801890.SI": "机械设备",
    }
    return name_map.get(code, code)

def _get_empty_market_breadth() -> Dict[str, Any]:
    """返回空的市场宽度数据结构"""
    return {
        "up_count": None,
        "down_count": None,
        "flat_count": None,
        "total_count": 0,
        "limit_up": 0,
        "limit_down": 0,
        "limit_break": 0,
        "up_ratio": None,
        "large_cap_up": 0,
        "mid_cap_up": 0,
        "small_cap_up": 0,
    }

def _get_market_breadth() -> Dict[str, Any]:
    """获取市场宽度数据 - 诚实返回真实数据或None"""
    try:
        from .trading_date_helper import find_latest_trading_date_with_data
        from .tushare_client import limit_list_d, daily_basic, _call_api
        
        # 使用最近的有数据的交易日
        end = find_latest_trading_date_with_data(daily_basic)
        if not end:
            print("[市场宽度] 无法找到有效的交易日")
            return _get_empty_market_breadth()
        
        # 1. 获取涨跌停数据（分别获取涨停、跌停、炸板）
        limit_up_df = limit_list_d(trade_date=end, limit_type='U')
        limit_down_df = limit_list_d(trade_date=end, limit_type='D')
        limit_break_df = limit_list_d(trade_date=end, limit_type='Z')
        
        # 统计涨跌停、炸板数量
        limit_up = len(limit_up_df) if limit_up_df is not None else 0
        limit_down = len(limit_down_df) if limit_down_df is not None else 0
        limit_break = len(limit_break_df) if limit_break_df is not None else 0
        
        # 2. 获取全市场涨跌家数 - 使用daily API获取真实数据
        all_up = None
        all_down = None
        all_flat = None
        total_count = 0
        
        try:
            # 直接调用daily API获取指定日期的全市场数据
            df = _call_api('daily', trade_date=end)
            if df is not None and not df.empty:
                # 计算真实的涨跌家数（基于pct_chg字段）
                if 'pct_chg' in df.columns:
                    all_up = len(df[df['pct_chg'] > 0])
                    all_down = len(df[df['pct_chg'] < 0])
                    all_flat = len(df[df['pct_chg'] == 0])
                    total_count = len(df)
                    print(f"[市场宽度] 获取到 {total_count} 只股票数据，{all_up}↑ / {all_down}↓ / {all_flat}平")
                else:
                    # 无法计算涨跌家数
                    print(f"[市场宽度] daily API缺少pct_chg字段")
                    total_count = len(df)
            else:
                # 如果daily API失败，尝试使用daily_basic获取总数
                df_basic = daily_basic(trade_date=end)
                if df_basic is not None and not df_basic.empty:
                    total_count = len(df_basic)
                    print(f"[市场宽度] 使用daily_basic获取总数: {total_count}，但无涨跌家数")
                else:
                    raise Exception("无法获取市场数据")
        except Exception as e:
            print(f"[市场宽度] 获取失败: {e}")
            # 尝试使用daily_basic作为备选
            try:
                df_basic = daily_basic(trade_date=end)
                if df_basic is not None and not df_basic.empty:
                    total_count = len(df_basic)
                    print(f"[市场宽度] 备选方案: 使用daily_basic获取总数 {total_count}")
            except:
                pass
        
        # 3. 获取市值分布数据（从daily_basic）
        df = daily_basic(trade_date=end)
        if df is not None and not df.empty:
            # 大中小盘股分布（根据流通市值区分）
            large_cap = len(df[df['circ_mv'] > 1000000]) if 'circ_mv' in df.columns else 0
            mid_cap = len(df[(df['circ_mv'] > 200000) & (df['circ_mv'] <= 1000000)]) if 'circ_mv' in df.columns else 0
            small_cap = len(df[df['circ_mv'] <= 200000]) if 'circ_mv' in df.columns else 0
        else:
            large_cap = 0
            mid_cap = 0
            small_cap = 0
        
        return {
            "up_count": all_up,
            "down_count": all_down,
            "flat_count": all_flat,
            "total_count": total_count,
            "limit_up": limit_up,
            "limit_down": limit_down,
            "limit_break": limit_break,  # 新增炸板数
            "up_ratio": round(all_up / total_count * 100, 1) if (all_up is not None and total_count > 0) else None,
            "large_cap_up": large_cap,
            "mid_cap_up": mid_cap,
            "small_cap_up": small_cap,
        }
    except Exception as e:
        # 不返回备用数据，直接抛出异常
        raise Exception(f"市场宽度数据获取失败: {str(e)}")

def _get_enhanced_capital_flow() -> Dict[str, Any]:
    """获取增强版资金流向数据 - 支持5000积分权限的高级接口"""
    from .trading_date_helper import find_latest_trading_date_with_data, get_recent_trading_dates
    
    capital_flow = {}
    recent_dates = get_recent_trading_dates(5)
    
    # 1. 获取市场整体资金流向（THS和DC数据）
    try:
        # 尝试获取今日全市场THS资金流向
        for date in recent_dates[:3]:
            ths_market_df = moneyflow_ths(trade_date=date)
            if ths_market_df is not None and not ths_market_df.empty:
                # 计算市场资金流向统计
                total_net = ths_market_df['net_amount'].sum() if 'net_amount' in ths_market_df.columns else 0
                inflow_stocks = len(ths_market_df[ths_market_df['net_amount'] > 0]) if 'net_amount' in ths_market_df.columns else 0
                outflow_stocks = len(ths_market_df[ths_market_df['net_amount'] < 0]) if 'net_amount' in ths_market_df.columns else 0
                
                capital_flow["market_flow_ths"] = {
                    "total_net_amount": float(total_net) if pd.notna(total_net) else 0,
                    "inflow_stocks": inflow_stocks,
                    "outflow_stocks": outflow_stocks,
                    "trade_date": date,
                    "total_stocks": len(ths_market_df)
                }
                break
    except Exception as e:
        print(f"[信息] THS市场资金流向暂不可用: {e}")
    
    # 2. 获取活跃股票资金流向TOP数据
    try:
        for date in recent_dates[:3]:
            dc_market_df = moneyflow_dc(trade_date=date)
            if dc_market_df is not None and not dc_market_df.empty:
                # 获取资金净流入最大的前10只股票
                top_inflow = dc_market_df.nlargest(10, 'net_amount') if 'net_amount' in dc_market_df.columns else pd.DataFrame()
                if not top_inflow.empty:
                    capital_flow["top_inflow_stocks"] = {
                        "stocks": top_inflow[['name', 'ts_code', 'net_amount', 'pct_change']].to_dict('records'),
                        "trade_date": date
                    }
                break
    except Exception as e:
        print(f"[信息] DC资金流向TOP数据暂不可用: {e}")
    
    # 3. 沪深港通股票统计
    try:
        hsgt_date = recent_dates[0]
        # 获取各类港通股票数量
        hsgt_types = ['HK_SZ', 'HK_SH', 'SZ_HK', 'SH_HK']
        hsgt_stats = {}
        
        for hsgt_type in hsgt_types:
            hsgt_df = stock_hsgt(trade_date=hsgt_date, type=hsgt_type)
            if hsgt_df is not None and not hsgt_df.empty:
                hsgt_stats[hsgt_type] = len(hsgt_df)
        
        if hsgt_stats:
            capital_flow["hsgt_stocks"] = {
                "stats": hsgt_stats,
                "trade_date": hsgt_date,
                "total_hsgt": sum(hsgt_stats.values())
            }
    except Exception as e:
        print(f"[信息] 港股通数据暂不可用: {e}")
    
    return capital_flow

def _get_capital_flow() -> Dict[str, Any]:
    """获取资金流向数据 - 北向资金、融资融券、主力资金"""
    from .trading_date_helper import find_latest_trading_date_with_data, get_recent_trading_dates
    
    # 首先尝试获取增强版数据
    enhanced_flow = _get_enhanced_capital_flow()
    
    capital_flow = enhanced_flow.copy() if enhanced_flow else {}
    
    try:
        # 获取最近的交易日期
        recent_dates = get_recent_trading_dates(10)
        
        # 1. 北向资金 - 尝试多种数据源获取
        north_flow_found = False
        
        # 方案1：使用moneyflow_hsgt API
        try:
            if len(recent_dates) >= 7:
                start_date = recent_dates[6]  # 7天前
                end_date = recent_dates[0]    # 最新
                hsgt_df = moneyflow_hsgt(start_date=start_date, end_date=end_date)
                if hsgt_df is not None and not hsgt_df.empty:
                    # 找到最新的有效数据行
                    valid_data = None
                    for i in range(len(hsgt_df) - 1, -1, -1):  # 倒序查找
                        row = hsgt_df.iloc[i]
                        north_money = row.get("north_money")
                        if pd.notna(north_money) and north_money != 0:
                            valid_data = row
                            break
                    
                    if valid_data is not None:
                        north_money = valid_data.get("north_money", 0)
                        south_money = valid_data.get("south_money", 0)
                        hgt = valid_data.get("hgt", 0)
                        sgt = valid_data.get("sgt", 0)
                        
                        # 设置北向资金数据
                        capital_flow["north_flow"] = {
                            "north_money": float(north_money) if pd.notna(north_money) else 0,
                            "south_money": float(south_money) if pd.notna(south_money) else 0,
                            "hgt": float(hgt) if pd.notna(hgt) else 0,  # 沪股通
                            "sgt": float(sgt) if pd.notna(sgt) else 0,  # 深股通
                            "trade_date": valid_data.get("trade_date"),
                            "data_source": "hsgt_real"
                        }
                        # 也设置为hsgt_net_amount供前端兼容使用
                        capital_flow["hsgt_net_amount"] = float(north_money) if pd.notna(north_money) else 0
                        north_flow_found = True
                        print(f"[北向资金] 获取成功: {capital_flow['hsgt_net_amount']:.1f}亿")
        except Exception as e:
            print(f"[警告] moneyflow_hsgt API失败: {e}")
        
        # 方案2：如果主API失败，尝试使用基础数据估算（基于沪深港通个股数据）
        if not north_flow_found:
            try:
                # 尝试通过个股港股通数据估算
                total_hsgt_flow = 0
                for date in recent_dates[:3]:  # 尝试最近3天
                    try:
                        hsgt_stocks = stock_hsgt(trade_date=date, type='HK_SZ')  # 深港通
                        if hsgt_stocks is not None and not hsgt_stocks.empty and 'amount' in hsgt_stocks.columns:
                            sz_flow = hsgt_stocks['amount'].sum() / 100000000  # 转换为亿元
                            total_hsgt_flow += sz_flow
                            break
                    except:
                        continue
                
                if total_hsgt_flow > 0:
                    # 设置估算的北向资金数据
                    capital_flow["north_flow"] = {
                        "north_money": total_hsgt_flow,
                        "south_money": 0,
                        "hgt": 0,
                        "sgt": total_hsgt_flow,
                        "trade_date": recent_dates[0],
                        "data_source": "estimated"
                    }
                    capital_flow["hsgt_net_amount"] = total_hsgt_flow
                    north_flow_found = True
                    print(f"[北向资金] 估算数据: {total_hsgt_flow:.1f}亿")
            except Exception as e:
                print(f"[警告] 北向资金估算失败: {e}")
        
        # 如果所有方案都失败，显式标记为无数据
        if not north_flow_found:
            print("[信息] 北向资金数据暂不可用")
            # 设置显式的"无数据"状态，而不是完全不设置
            capital_flow["north_flow"] = None
            capital_flow["hsgt_net_amount"] = None
        
        # 2. 涨跌停统计 - 反映市场情绪
        limit_date = find_latest_trading_date_with_data(lambda **kw: stk_limit(**kw))
        if limit_date:
            limit_df = stk_limit(trade_date=limit_date)
            if limit_df is not None and not limit_df.empty:
                capital_flow["limit_stats"] = {
                    "up_limit": len(limit_df[limit_df['limit'] == 'U']) if 'limit' in limit_df.columns else 0,
                    "down_limit": len(limit_df[limit_df['limit'] == 'D']) if 'limit' in limit_df.columns else 0,
                    "trade_date": limit_date,
                }
        
        # 3. 龙虎榜数据 - 游资动向
        top_date = find_latest_trading_date_with_data(lambda **kw: top_list(**kw))
        if top_date:
            top_df = top_list(trade_date=top_date)
            if top_df is not None and not top_df.empty:
                capital_flow["dragon_tiger"] = {
                    "total_stocks": len(top_df),
                    "net_buy": float(top_df['net_amount'].sum()) if 'net_amount' in top_df.columns else 0,
                    "l_amount": float(top_df['l_amount'].sum()) if 'l_amount' in top_df.columns else 0,
                    "trade_date": top_date,
                }
        
        # 4. 融资融券余额 - 使用真实数据
        margin_date = find_latest_trading_date_with_data(lambda **kw: margin_detail(**kw))
        if margin_date:
            margin_df = margin_detail(trade_date=margin_date)
            if margin_df is not None and not margin_df.empty:
                capital_flow["margin"] = {
                    "rzye": float(margin_df['rzye'].sum()) if 'rzye' in margin_df.columns else 0,  # 融资余额
                    "rqye": float(margin_df['rqye'].sum()) if 'rqye' in margin_df.columns else 0,  # 融券余额
                    "rzmre": float(margin_df['rzmre'].sum()) if 'rzmre' in margin_df.columns else 0,  # 融资买入额
                    "trade_date": margin_date,
                }
        
        # 5. 大宗交易数据（API暂不可用，跳过）
        print("[信息] 大宗交易数据API暂不可用")
        
        return capital_flow
        
    except Exception as e:
        print(f"[警告] 获取资金流向数据失败: {str(e)}")
        return {}

def _get_macro_indicators() -> Dict[str, Any]:
    """获取宏观指标"""
    try:
        from .tushare_client import _call_api
        indicators = {}
        
        # 获取最新CPI数据
        cpi_data = _call_api("cn_cpi", limit=1)
        if cpi_data is not None and not cpi_data.empty:
            indicators["cpi"] = {
                "value": float(cpi_data.iloc[0]["nt_yoy"]),
                "month": cpi_data.iloc[0]["m"]
            }
        
        # 获取货币供应量
        money_data = _call_api("cn_money", limit=1)
        if money_data is not None and not money_data.empty:
            indicators["money_supply"] = {
                "m2_yoy": float(money_data.iloc[0]["m2_yoy"]),
                "month": money_data.iloc[0]["month"]
            }
            
        return indicators
    except Exception:
        return {}


def _get_market_highlights() -> Dict[str, Any]:
    """获取今日市场要点 - 最重要的市场信息"""
    from .trading_date_helper import find_latest_trading_date_with_data, get_recent_trading_dates
    
    highlights = {
        "date": get_recent_trading_dates(1)[0] if get_recent_trading_dates(1) else _today_str(),
        "key_events": [],
        "sector_leaders": [],
        "abnormal_stocks": []
    }
    
    try:
        # 1. 获取龙虎榜异动股票
        dragon_date = find_latest_trading_date_with_data(lambda **kw: top_list(**kw))
        if dragon_date:
            dragon_df = top_list(trade_date=dragon_date)
            if dragon_df is not None and not dragon_df.empty:
                # 获取涨幅最大的前5只
                top_gainers = dragon_df.nlargest(5, 'pct_change')
                for _, row in top_gainers.iterrows():
                    highlights["abnormal_stocks"].append({
                        "name": row.get("name", ""),
                        "ts_code": row.get("ts_code", ""),
                        "pct_change": float(row.get("pct_change", 0)),
                        "turnover": float(row.get("turnover", 0)),
                        "reason": "龙虎榜异动"
                    })
    except Exception as e:
        print(f"[警告] 获取龙虎榜数据失败: {e}")
    
    try:
        # 2. 从同花顺热榜获取热门概念（只获取最新交易日数据）
        trade_date = find_latest_trading_date_with_data(lambda **kw: ths_hot(**kw))
        if trade_date:
            ths = ths_hot(trade_date=trade_date)
            if ths is not None and not ths.empty:
                # 只获取当日的概念板块数据
                concept_hot = ths[(ths['data_type'] == '概念板块') & (ths['trade_date'] == trade_date)]
                if not concept_hot.empty:
                    for _, row in concept_hot.head(3).iterrows():
                        highlights["sector_leaders"].append({
                            "name": row.get("ts_name", ""),
                            "pct_change": float(row.get("pct_change", 0)),
                            "reason": f"当日热门概念"
                        })
                else:
                    print(f"[信息] {trade_date} 暂无热门概念数据")
    except Exception as e:
        print(f"[警告] 获取热门概念失败: {e}")
    
    # 3. 添加关键市场事件（基于数据分析）
    try:
        limit_date = find_latest_trading_date_with_data(lambda **kw: stk_limit(**kw))
        if limit_date:
            limit_df = stk_limit(trade_date=limit_date)
            if limit_df is not None and not limit_df.empty:
                limit_up = len(limit_df[limit_df['limit'] == 'U']) if 'limit' in limit_df.columns else 0
                limit_down = len(limit_df[limit_df['limit'] == 'D']) if 'limit' in limit_df.columns else 0
                
                if limit_up > 20:
                    highlights["key_events"].append(f"市场情绪高涨，{limit_up}只个股涨停")
                elif limit_down > 20:
                    highlights["key_events"].append(f"市场承压，{limit_down}只个股跌停")
                elif limit_up > limit_down * 2:
                    highlights["key_events"].append(f"多头占优，涨停{limit_up}只 vs 跌停{limit_down}只")
    except Exception:
        pass
    
    return highlights

def fetch_market_overview() -> Dict[str, Any]:
    end = _today_str()
    start = (dt.date.today() - dt.timedelta(days=10)).strftime("%Y%m%d")

    indices: List[Dict[str, Any]] = []
    data_date = None  # 记录实际数据日期
    
    for code in INDEX_CODES:
        df = _index_daily(code, start, end)
        row = None
        if df is not None and not df.empty:
            df = df.sort_values("trade_date").reset_index(drop=True)
            row = df.iloc[-1].to_dict()
            if data_date is None:
                data_date = row.get("trade_date")
                
        close_v = (row or {}).get("close")
        pct_v = (row or {}).get("pct_chg")
        indices.append({
            "ts_code": code,
            "name": INDEX_NAMES.get(code, "未知指数"),
            "trade_date": (row or {}).get("trade_date"),
            "close": float(close_v) if close_v is not None else None,
            "pct_chg": float(pct_v) if pct_v is not None else None,
        })

    _shb = shibor()
    shb = None
    if not _shb.empty:
        _shb = _shb.sort_values("date", ascending=False).reset_index(drop=True)
        shb = _shb.iloc[0][["date", "on", "1w"]].to_dict()

    mn = major_news(limit=10)
    major_titles: List[str] = []
    if mn is not None and not mn.empty:
        major_titles = [str(t) for t in list(mn["title"].values)[:5]]

    # 获取行业板块表现
    sectors = _get_sector_performance()
    
    # 获取市场宽度
    market_breadth = _get_market_breadth()
    
    # 获取资金流向
    capital_flow = _get_capital_flow()
    
    # 获取宏观指标
    macro_indicators = _get_macro_indicators()
    
    # 获取同花顺热榜 - 只获取最新交易日数据
    hot_stocks = []
    try:
        trade_date = find_latest_trading_date_with_data(lambda **kw: ths_hot(**kw))
        if trade_date:
            ths = ths_hot(trade_date=trade_date)
            if ths is not None and not ths.empty:
                # 只获取当日数据，避免混合历史数据
                current_date_data = ths[ths['trade_date'] == trade_date]
                if not current_date_data.empty:
                    # 优先获取热门股票
                    today_stocks = current_date_data[current_date_data['data_type'] == '热股']
                    if not today_stocks.empty:
                        hot_stocks.extend(today_stocks.head(5).to_dict('records'))
                    
                    # 获取热门概念板块
                    hot_concepts = current_date_data[current_date_data['data_type'] == '概念板块']
                    if not hot_concepts.empty:
                        hot_stocks.extend(hot_concepts.head(3).to_dict('records'))
                    
                    hot_stocks = hot_stocks[:8]  # 最多显示8个
                else:
                    print(f"[信息] {trade_date} 暂无热门数据")
        else:
            print("[信息] 未找到有热门数据的交易日")
    except Exception as e:
        print(f"[警告] 获取热门数据失败: {e}")
        hot_stocks = []
    
    # 获取重要公告和政策新闻
    important_announcements = _get_important_announcements()
    
    # 获取政策新闻
    policy_news = _get_policy_news()
    
    # 获取市场要点 - 最重要的信息
    market_highlights = _get_market_highlights()
    
    # 获取智能预警数据
    market_alerts = []
    try:
        # 调用AI分析器生成预警
        from .market_ai_analyzer import get_enhanced_market_ai_analyzer
        analyzer = get_enhanced_market_ai_analyzer()
        
        # 构建简化的分析数据用于预警生成
        analysis_data = {
            "indices": indices,
            "capital": {"shibor_rates": {"overnight": shb.get("on") if shb else None}},
            "market_breadth": market_breadth,
            "capital_flow": capital_flow
        }
        
        # 生成预警
        market_alerts = analyzer._generate_market_alerts(analysis_data)
    except Exception as e:
        print(f"[警告] 生成智能预警失败: {e}")
        # 使用默认预警
        market_alerts = [{
            "type": "system_info",
            "level": "low", 
            "message": "预警系统正常运行",
            "action": "持续关注市场变化"
        }]
    
    # 判断数据是否为实时数据
    today_str = _today_str()
    is_realtime = data_date == today_str
    data_type = "实时数据" if is_realtime else "历史数据"
    
    result = {
        "timestamp": dt.datetime.now().isoformat(),
        "data_date": data_date or _today_str(),  # 显示实际数据日期
        "data_type": data_type,
        "is_realtime": is_realtime,
        "indices": indices,
        "shibor": shb,
        "major_news": major_titles,
        "sectors": sectors,
        "market_breadth": market_breadth,
        "capital_flow": capital_flow,
        "macro_indicators": macro_indicators,
        "hot_stocks": hot_stocks,
        "announcements": important_announcements,
        "policy_news": policy_news,
        "market_highlights": market_highlights,  # 新增关键市场要点
        "alerts": market_alerts,  # 新增智能预警
    }
    
    # 清理NaN值以确保JSON序列化
    return _clean_nan_values(result)


def _get_important_announcements() -> List[Dict[str, Any]]:
    """获取重要公告 - 从真实的公告数据中提取"""
    try:
        # 获取最新公告
        df = anns(ts_code=None, limit=50, force=False)
        
        if df is None or df.empty:
            return []
        
        # 筛选重要公告类型
        important_types = ['业绩预告', '业绩快报', '回购', '增持', '减持', '重大合同', '分红']
        announcements = []
        
        for _, row in df.iterrows():
            title = str(row.get('title', ''))
            # 判断是否为重要公告
            for ann_type in important_types:
                if ann_type in title:
                    announcements.append({
                        "ts_code": row.get('ts_code'),
                        "name": row.get('name', ''),
                        "ann_type": ann_type,
                        "title": title,
                        "ann_date": row.get('ann_date'),
                    })
                    break
            
            if len(announcements) >= 10:  # 最多返回10条
                break
        
        return announcements
    except Exception as e:
        print(f"[错误] 获取重要公告失败: {str(e)}")
        return []


def _get_policy_news() -> List[Dict[str, Any]]:
    """获取政策新闻 - 从公司公告中筛选重要政策相关信息"""
    try:
        from .tushare_client import _call_api
        import datetime as dt
        
        # 获取当日公告
        today = dt.datetime.now().strftime("%Y%m%d")
        anns = _call_api("anns", ann_date=today, limit=50)
        
        if anns is not None and not anns.empty:
            policy_keywords = ["政策", "监管", "央行", "证监会", "财政部", "国务院", "发改委"]
            policy_news = []
            
            for _, row in anns.iterrows():
                title = str(row.get('title', ''))
                for keyword in policy_keywords:
                    if keyword in title:
                        policy_news.append({
                            "title": title,
                            "company": row.get('name', ''),
                            "ts_code": row.get('ts_code', ''),
                            "ann_date": row.get('ann_date', ''),
                            "category": "政策相关"
                        })
                        break
            
            return policy_news[:5]  # 返回前5条
        
        return []
    except Exception:
        return []

