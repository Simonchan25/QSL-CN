"""
交易日期辅助函数
"""
from datetime import datetime, timedelta
from typing import Optional, List
from .tushare_client import pro as ts_pro

pro = ts_pro

_trading_dates_cache = None
_cache_expiry = None

def get_recent_trading_dates(days: int = 30) -> List[str]:
    """获取最近的交易日期列表"""
    global _trading_dates_cache, _cache_expiry
    
    # 检查缓存
    if _trading_dates_cache and _cache_expiry and datetime.now() < _cache_expiry:
        return _trading_dates_cache[:days]
    
    try:
        # 获取交易日历
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=60)).strftime('%Y%m%d')
        
        df = pro.trade_cal(exchange='SSE', start_date=start_date, end_date=end_date)
        if not df.empty:
            # 筛选交易日
            trading_dates = df[df['is_open'] == 1]['cal_date'].tolist()
            trading_dates.sort(reverse=True)  # 最新的在前
            
            # 缓存1小时
            _trading_dates_cache = trading_dates
            _cache_expiry = datetime.now() + timedelta(hours=1)
            
            return trading_dates[:days]
    except Exception as e:
        print(f"[警告] 获取交易日历失败: {e}")
    
    # 降级方案：生成最近的日期列表（跳过周末）
    dates = []
    current = datetime.now()
    
    while len(dates) < days:
        # 跳过周末
        if current.weekday() < 5:  # 0-6，0是周一，6是周日
            dates.append(current.strftime('%Y%m%d'))
        current -= timedelta(days=1)
    
    return dates

def find_latest_trading_date_with_data(api_func, max_attempts: int = 10) -> Optional[str]:
    """
    查找最近有数据的交易日期
    
    Args:
        api_func: API调用函数，接受trade_date参数
        max_attempts: 最大尝试次数
    
    Returns:
        有数据的最新交易日期，如果没有则返回None
    """
    trading_dates = get_recent_trading_dates(max_attempts)
    
    for trade_date in trading_dates:
        try:
            result = api_func(trade_date=trade_date)
            if result is not None and not result.empty:
                return trade_date
        except Exception:
            continue
    
    return None

def get_latest_trading_date() -> str:
    """获取最新的交易日期"""
    trading_dates = get_recent_trading_dates(1)
    return trading_dates[0] if trading_dates else datetime.now().strftime('%Y%m%d')