import os
import time
import functools
import datetime as dt
from typing import Optional, List, Dict, Any

import pandas as pd
import tushare as ts
from cachetools import TTLCache

# 导入模拟数据模块
from .mock_data import (
    is_mock_mode, get_mock_stock_basic, get_mock_daily, get_mock_daily_basic,
    get_mock_fina_indicator, get_mock_income, get_mock_balancesheet,
    get_mock_cashflow, get_mock_forecast, get_mock_express, get_mock_news,
    get_mock_anns, get_mock_moneyflow, get_mock_margin_detail,
    get_mock_moneyflow_hsgt, get_mock_stk_limit, get_mock_macro_data
)

_TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN")
_pro = ts.pro_api(_TUSHARE_TOKEN) if _TUSHARE_TOKEN else None
_cache = TTLCache(maxsize=256, ttl=60 * 10)

# 磁盘缓存目录（持久化缓存，降低 TuShare 限频影响）
_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".cache")
os.makedirs(_CACHE_DIR, exist_ok=True)

_last_call_ts = 0.0
_MIN_INTERVAL = 0.6


def _rate_limit():
    global _last_call_ts
    now = time.time()
    wait = _MIN_INTERVAL - (now - _last_call_ts)
    if wait > 0:
        time.sleep(wait)
    _last_call_ts = time.time()


def cached(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        key = (func.__name__, tuple(args), tuple(sorted(kwargs.items())))
        if key in _cache:
            return _cache[key]
        out = func(*args, **kwargs)
        _cache[key] = out
        return out

    return wrapper


def _ensure_client():
    global _pro
    if _pro is not None:
        return _pro
    token = os.getenv("TUSHARE_TOKEN")
    if not token:
        raise ConfigurationError(
            "配置错误: 缺少环境变量 TUSHARE_TOKEN\n"
            "解决方案: 请在 backend/.env 文件中设置 TUSHARE_TOKEN=你的token"
        )
    if len(token) < 20:
        raise ConfigurationError(
            f"配置错误: TUSHARE_TOKEN 格式不正确 (长度={len(token)})\n"
            "解决方案: 请检查 backend/.env 中的 TUSHARE_TOKEN 是否完整"
        )
    try:
        _pro = ts.pro_api(token)
    except Exception as e:
        raise ConfigurationError(
            f"配置错误: 无法初始化TuShare客户端\n"
            f"原因: {str(e)}\n"
            "解决方案: 检查token是否有效，网络是否正常"
        )
    return _pro


class RateLimitError(Exception):
    """TuShare API访问频率限制错误"""
    pass


def _is_rate_limited_message(msg: str) -> bool:
    if not msg:
        return False
    keys = ["每分钟最多访问", "每小时最多访问", "超过访问频次", "访问太频繁", "每天最多访问"]
    return any(k in msg for k in keys)


class AccessDeniedError(Exception):
    """TuShare API权限不足错误"""
    pass


def _is_access_denied_message(msg: str) -> bool:
    if not msg:
        return False
    keys = ["没有接口访问权限", "无权限", "权限不足", "权限"]
    return any(k in msg for k in keys)


class ConfigurationError(Exception):
    """配置错误"""
    pass


class APIError(Exception):
    """TuShare API调用错误"""
    pass


def _cache_path(key: str) -> str:
    safe = key.replace("/", "_")
    return os.path.join(_CACHE_DIR, f"{safe}.csv")


# 记录抓取降级/缓存使用的备注，供上层展示
_NOTES: List[Dict[str, Any]] = []


def _add_note(note: Dict[str, Any]) -> None:
    try:
        ts_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        note = {"ts": ts_str, **note}
        _NOTES.append(note)
    except Exception:
        pass


def pop_notes() -> List[Dict[str, Any]]:
    notes = list(_NOTES)
    _NOTES.clear()
    return notes


def _cache_meta(key: str, df: Optional[pd.DataFrame]) -> Dict[str, Any]:
    meta: Dict[str, Any] = {"cache_key": key}
    try:
        path = _cache_path(key)
        meta["cache_file"] = os.path.basename(path)
        if os.path.exists(path):
            meta["cache_mtime"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(path)))
        if df is not None and isinstance(df, pd.DataFrame):
            meta["cache_rows"] = int(len(df))
    except Exception:
        pass
    return meta


def _get_cached_df(key: str, ttl_seconds: int):
    path = _cache_path(key)
    if not os.path.exists(path):
        return None
    age = time.time() - os.path.getmtime(path)
    if age > ttl_seconds:
        return None
    try:
        return pd.read_csv(path)
    except Exception:
        return None


def _get_any_cached_df(key: str):
    path = _cache_path(key)
    if not os.path.exists(path):
        return None
    try:
        return pd.read_csv(path)
    except Exception:
        return None


def _save_df_cache(key: str, df: pd.DataFrame) -> None:
    try:
        path = _cache_path(key)
        df.to_csv(path, index=False)
    except Exception:
        pass


def _call_api(method_name: str, **kwargs):
    # 检查是否启用模拟模式
    if is_mock_mode():
        # 根据不同的API返回对应的模拟数据
        if method_name == "stock_basic":
            return get_mock_stock_basic()
        elif method_name == "daily":
            ts_code = kwargs.get("ts_code", "000001.SZ")
            start_date = kwargs.get("start_date", "20250101")
            end_date = kwargs.get("end_date", "20250116")
            return get_mock_daily(ts_code, start_date, end_date)
        elif method_name == "daily_basic":
            ts_code = kwargs.get("ts_code", "000001.SZ")
            trade_date = kwargs.get("trade_date")
            end_date = kwargs.get("end_date")
            return get_mock_daily_basic(ts_code, trade_date, end_date)
        elif method_name == "fina_indicator":
            ts_code = kwargs.get("ts_code", "000001.SZ")
            return get_mock_fina_indicator(ts_code)
        elif method_name == "income":
            ts_code = kwargs.get("ts_code", "000001.SZ")
            limit = kwargs.get("limit", 8)
            return get_mock_income(ts_code, limit)
        elif method_name == "balancesheet":
            ts_code = kwargs.get("ts_code", "000001.SZ")
            limit = kwargs.get("limit", 4)
            return get_mock_balancesheet(ts_code, limit)
        elif method_name == "cashflow":
            ts_code = kwargs.get("ts_code", "000001.SZ")
            limit = kwargs.get("limit", 4)
            return get_mock_cashflow(ts_code, limit)
        elif method_name == "forecast":
            ts_code = kwargs.get("ts_code", "000001.SZ")
            return get_mock_forecast(ts_code)
        elif method_name == "express":
            ts_code = kwargs.get("ts_code", "000001.SZ")
            return get_mock_express(ts_code)
        elif method_name == "news":
            src = kwargs.get("src", "sina")
            limit = kwargs.get("limit", 100)
            return get_mock_news(src, limit)
        elif method_name == "anns":
            ts_code = kwargs.get("ts_code", "000001.SZ")
            limit = kwargs.get("limit", 15)
            return get_mock_anns(ts_code, limit)
        elif method_name == "moneyflow":
            ts_code = kwargs.get("ts_code", "000001.SZ")
            start_date = kwargs.get("start_date")
            end_date = kwargs.get("end_date")
            return get_mock_moneyflow(ts_code, start_date, end_date)
        elif method_name == "margin_detail":
            ts_code = kwargs.get("ts_code")
            trade_date = kwargs.get("trade_date")
            return get_mock_margin_detail(ts_code, trade_date)
        elif method_name == "moneyflow_hsgt":
            trade_date = kwargs.get("trade_date")
            return get_mock_moneyflow_hsgt(trade_date)
        elif method_name == "stk_limit":
            ts_code = kwargs.get("ts_code")
            trade_date = kwargs.get("trade_date")
            return get_mock_stk_limit(ts_code, trade_date)
        elif method_name in ["cn_cpi", "cn_ppi", "cn_m", "shibor", "cn_gdp", "cn_pmi"]:
            macro_data = get_mock_macro_data()
            if method_name == "cn_cpi":
                return macro_data["cpi"]
            elif method_name == "cn_ppi":
                return macro_data["ppi"]
            elif method_name == "cn_m":
                return macro_data["money_supply"]
            elif method_name == "shibor":
                return macro_data["shibor"]
            elif method_name == "cn_gdp":
                return macro_data["gdp"]
            elif method_name == "cn_pmi":
                return macro_data["pmi"]
        else:
            # 返回空数据框作为默认值
            print(f"[模拟] 接口 {method_name} 暂无模拟数据，返回空数据框")
            return pd.DataFrame()
    
    # 原有的API调用逻辑
    _rate_limit()
    try:
        pro = _ensure_client()
    except ConfigurationError:
        raise
    
    if not hasattr(pro, method_name):
        raise APIError(
            f"API错误: TuShare不支持接口 '{method_name}'\n"
            f"可能原因: 1) 接口名称错误 2) 需要升级tushare库\n"
            "解决方案: 检查接口名称或运行 pip install --upgrade tushare"
        )
    
    func = getattr(pro, method_name)
    try:
        result = func(**kwargs)
        if result is None:
            raise APIError(f"API错误: 接口 {method_name} 返回空结果")
        return result
    except Exception as e:
        msg = str(e)
        if _is_rate_limited_message(msg):
            if "每天最多访问" in msg:
                raise RateLimitError(
                    f"API限制: {msg}\n"
                    "解决方案: 1) 等待明天重置 2) 升级TuShare账户获取更多配额\n"
                    "访问 https://tushare.pro 了解更多"
                )
            raise RateLimitError(f"API限制: {msg}")
        if _is_access_denied_message(msg):
            raise AccessDeniedError(
                f"权限错误: {msg}\n"
                "解决方案: 升级TuShare账户获取该接口权限\n"
                "访问 https://tushare.pro/document/1?doc_id=108 了解权限详情"
            )
        if "请指定正确的接口名" in msg:
            raise APIError(
                f"API错误: 接口名称 '{method_name}' 不正确\n"
                f"原始错误: {msg}"
            )
        raise APIError(f"API错误: {msg}")


def _choose_df(primary: Optional[pd.DataFrame], fallback: Optional[pd.DataFrame]) -> pd.DataFrame:
    if primary is not None and isinstance(primary, pd.DataFrame) and not primary.empty:
        return primary
    if fallback is not None and isinstance(fallback, pd.DataFrame) and not fallback.empty:
        return fallback
    if primary is not None and isinstance(primary, pd.DataFrame):
        return primary
    if fallback is not None and isinstance(fallback, pd.DataFrame):
        return fallback
    return pd.DataFrame()


def _ttl_for_daily(end_date: str) -> int:
    try:
        end = dt.datetime.strptime(end_date, "%Y%m%d").date()
        today = dt.date.today()
        delta_days = (today - end).days
        if delta_days <= 1:
            return 15 * 60  # 15分钟内更新，适合短线需求
        if delta_days <= 3:
            return 60 * 60  # 1小时
        return 7 * 24 * 3600  # 历史数据1周
    except Exception:
        return 60 * 60


@cached
def stock_basic(force: bool = False) -> pd.DataFrame:
    # 检查是否启用模拟模式
    if is_mock_mode():
        print("[模拟] 使用模拟股票列表数据")
        return get_mock_stock_basic()
    
    # 先读本地缓存（24h）
    stale = _get_any_cached_df("stock_basic")
    if not force:
        cached_df = _get_cached_df("stock_basic", ttl_seconds=24 * 3600)
        if cached_df is not None and not cached_df.empty:
            return cached_df
    try:
        df = _call_api(
            "stock_basic",
            fields="ts_code,symbol,name,area,industry,market,list_status,fullname",
        )
        if df is not None and not df.empty:
            _save_df_cache("stock_basic", df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        msg = str(e).split('\\n')[0]
        print(f"[缓存] 使用缓存数据，API错误: {msg}")
        _add_note({"api": "stock_basic", "reason": "rate_or_perm", "message": msg, **_cache_meta("stock_basic", stale)})
        return _choose_df(stale, None)
    except (ConfigurationError, APIError) as e:
        msg = str(e)
        print(f"[错误] {msg}")
        _add_note({"api": "stock_basic", "reason": "api_error", "message": msg, **_cache_meta("stock_basic", stale)})
        return _choose_df(stale, pd.DataFrame())
    except Exception as e:
        # 网络连接失败时返回模拟数据
        print(f"[模拟] TuShare服务器不可用，使用模拟数据: {str(e)[:50]}")
        return get_mock_stock_basic()


@cached
def daily(ts_code: str, start_date: str, end_date: str, force: bool = False) -> pd.DataFrame:
    if is_mock_mode():
        print(f"[模拟] 使用模拟日线数据: {ts_code}")
        return get_mock_daily(ts_code, start_date, end_date)
    
    key = f"daily_{ts_code}_{start_date}_{end_date}"
    stale = _get_any_cached_df(key)
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=_ttl_for_daily(end_date))
        if cached_df is not None and not cached_df.empty:
            return cached_df
    try:
        df = _call_api("daily", ts_code=ts_code, start_date=start_date, end_date=end_date)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        msg = str(e).split('\\n')[0]
        print(f"[缓存] 使用缓存数据，API错误: {msg}")
        _add_note({"api": "daily", "ts_code": ts_code, "reason": "rate_or_perm", "message": msg, **_cache_meta(key, stale)})
        return _choose_df(stale, None)
    except (ConfigurationError, APIError) as e:
        msg = str(e)
        print(f"[错误] {msg}")
        _add_note({"api": "daily", "ts_code": ts_code, "reason": "api_error", "message": msg, **_cache_meta(key, stale)})
        return _choose_df(stale, pd.DataFrame())
    except Exception as e:
        print(f"[模拟] TuShare服务器不可用，使用模拟数据")
        return get_mock_daily(ts_code, start_date, end_date)


@cached
def fina_indicator(ts_code: str, force: bool = False) -> pd.DataFrame:
    if is_mock_mode():
        return get_mock_fina_indicator(ts_code)
    
    key = f"fina_indicator_{ts_code}"
    stale = _get_any_cached_df(key)
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=7 * 24 * 3600)
        if cached_df is not None and not cached_df.empty:
            return cached_df
    try:
        df = _call_api("fina_indicator", ts_code=ts_code)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        print(f"[缓存] 使用缓存数据，API错误: {str(e).split('\\n')[0]}")
        return _choose_df(stale, None)
    except (ConfigurationError, APIError) as e:
        print(f"[错误] {str(e)}")
        return _choose_df(stale, pd.DataFrame())
    except Exception:
        return get_mock_fina_indicator(ts_code)


@cached
def income(ts_code: str, limit: int = 8, force: bool = False) -> pd.DataFrame:
    if is_mock_mode():
        return get_mock_income(ts_code, limit)
    
    key = f"income_{ts_code}_L{limit}"
    stale = _get_any_cached_df(key)
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=7 * 24 * 3600)
        if cached_df is not None and not cached_df.empty:
            return cached_df
    try:
        df = _call_api("income", ts_code=ts_code, limit=limit)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        print(f"[缓存] 使用缓存数据，API错误: {str(e).split('\\n')[0]}")
        return _choose_df(stale, None)
    except (ConfigurationError, APIError) as e:
        print(f"[错误] {str(e)}")
        return _choose_df(stale, pd.DataFrame())
    except Exception:
        return get_mock_income(ts_code, limit)


@cached
def balancesheet(ts_code: str, limit: int = 4, force: bool = False) -> pd.DataFrame:
    if is_mock_mode():
        return get_mock_balancesheet(ts_code, limit)
    
    key = f"balancesheet_{ts_code}_L{limit}"
    stale = _get_any_cached_df(key)
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=7 * 24 * 3600)
        if cached_df is not None and not cached_df.empty:
            return cached_df
    try:
        df = _call_api("balancesheet", ts_code=ts_code, limit=limit)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        print(f"[缓存] 使用缓存数据，API错误: {str(e).split('\\n')[0]}")
        return _choose_df(stale, None)
    except (ConfigurationError, APIError) as e:
        print(f"[错误] {str(e)}")
        return _choose_df(stale, pd.DataFrame())
    except Exception:
        return get_mock_balancesheet(ts_code, limit)


@cached
def cashflow(ts_code: str, limit: int = 4, force: bool = False) -> pd.DataFrame:
    if is_mock_mode():
        return get_mock_cashflow(ts_code, limit)
    
    key = f"cashflow_{ts_code}_L{limit}"
    stale = _get_any_cached_df(key)
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=7 * 24 * 3600)
        if cached_df is not None and not cached_df.empty:
            return cached_df
    try:
        df = _call_api("cashflow", ts_code=ts_code, limit=limit)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        print(f"[缓存] 使用缓存数据，API错误: {str(e).split('\\n')[0]}")
        return _choose_df(stale, None)
    except (ConfigurationError, APIError) as e:
        print(f"[错误] {str(e)}")
        return _choose_df(stale, pd.DataFrame())
    except Exception:
        return get_mock_cashflow(ts_code, limit)


@cached
def anns(ts_code: str, limit: int = 15, force: bool = False) -> pd.DataFrame:
    """获取公司公告"""
    key = f"anns_{ts_code}_L{limit}"
    stale = _get_any_cached_df(key)
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=10 * 60)  # 公告更频繁：10分钟
        if cached_df is not None and not cached_df.empty:
            return cached_df
    try:
        # TuShare Pro 的公告接口是 'anns'，但需要权限
        df = _call_api("anns", ts_code=ts_code, limit=limit)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        print(f"[缓存] 使用缓存数据，API错误: {str(e).split('\\n')[0]}")
        return _choose_df(stale, None)
    except (ConfigurationError, APIError) as e:
        print(f"[错误] {str(e)}")
        return _choose_df(stale, pd.DataFrame())


@cached
def cpi(force: bool = False):
    key = "cpi"
    stale = _get_any_cached_df(key)
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=24 * 3600)
        if cached_df is not None and not cached_df.empty:
            return cached_df
    try:
        df = _call_api("cn_cpi")  # 正确的接口名是 cn_cpi
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        print(f"[缓存] 使用缓存数据，API错误: {str(e).split('\\n')[0]}")
        return _choose_df(stale, None)
    except (ConfigurationError, APIError) as e:
        print(f"[错误] {str(e)}")
        return _choose_df(stale, pd.DataFrame())
    except Exception as e:
        # 如果接口不可用，返回空DataFrame
        print(f"[警告] API接口调用失败: {str(e)}")
        return _choose_df(stale, pd.DataFrame())


@cached
def ppi(force: bool = False):
    key = "ppi"
    stale = _get_any_cached_df(key)
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=24 * 3600)
        if cached_df is not None and not cached_df.empty:
            return cached_df
    try:
        df = _call_api("cn_ppi")  # 正确的接口名是 cn_ppi
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        print(f"[缓存] 使用缓存数据，API错误: {str(e).split('\\n')[0]}")
        return _choose_df(stale, None)
    except (ConfigurationError, APIError) as e:
        print(f"[错误] {str(e)}")
        return _choose_df(stale, pd.DataFrame())
    except Exception as e:
        # 如果接口不可用，返回空DataFrame
        print(f"[警告] API接口调用失败: {str(e)}")
        return _choose_df(stale, pd.DataFrame())


@cached
def money_supply(force: bool = False):
    key = "money_supply"
    stale = _get_any_cached_df(key)
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=24 * 3600)
        if cached_df is not None and not cached_df.empty:
            return cached_df
    try:
        df = _call_api("cn_m")  # 正确的接口名是 cn_m
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        print(f"[缓存] 使用缓存数据，API错误: {str(e).split('\\n')[0]}")
        return _choose_df(stale, None)
    except (ConfigurationError, APIError) as e:
        print(f"[错误] {str(e)}")
        return _choose_df(stale, pd.DataFrame())
    except Exception as e:
        # 如果接口不可用，返回空DataFrame
        print(f"[警告] API接口调用失败: {str(e)}")
        return _choose_df(stale, pd.DataFrame())


@cached
def news(src: str = "sina", start_date: Optional[str] = None, end_date: Optional[str] = None, limit: int = 100, force: bool = False) -> pd.DataFrame:
    """获取新闻快讯数据
    
    Args:
        src: 新闻来源 (sina-新浪, wallstreetcn-华尔街见闻, 10jqka-同花顺, eastmoney-东方财富)
        start_date: 开始日期 (格式：YYYYMMDD HH:MM:SS)
        end_date: 结束日期
        limit: 数据条数
    """
    key = f"news_{src}_L{limit}"
    stale = _get_any_cached_df(key)
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=10 * 60)  # 新闻10分钟缓存
        if cached_df is not None and not cached_df.empty:
            return cached_df
    try:
        # TuShare Pro 新闻接口
        params = {"src": src, "limit": limit}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
            
        df = _call_api("news", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        print(f"[缓存] 使用缓存数据，API错误: {str(e).split('\\n')[0]}")
        return _choose_df(stale, None)
    except (ConfigurationError, APIError) as e:
        print(f"[错误] {str(e)}")
        # 尝试使用免费版本的接口
        try:
            print("[尝试] 使用免费版新闻接口...")
            # 免费版本使用 ts.get_latest_news()
            import tushare as ts
            news_df = ts.get_latest_news(top=limit, show_content=True)
            if news_df is not None and not news_df.empty:
                # 转换格式以匹配Pro版本
                news_df = news_df.rename(columns={
                    'title': 'title',
                    'time': 'datetime',
                    'url': 'url',
                    'content': 'content'
                })
                _save_df_cache(key, news_df)
                return news_df
        except Exception as e2:
            print(f"[错误] 免费版接口也失败: {str(e2)}")
        return _choose_df(stale, pd.DataFrame())


@cached
def major_news(limit: int = 30, force: bool = False) -> pd.DataFrame:
    """获取重大财经新闻"""
    key = f"major_news_L{limit}"
    stale = _get_any_cached_df(key)
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=30 * 60)  # 重大新闻30分钟缓存
        if cached_df is not None and not cached_df.empty:
            return cached_df
    try:
        # TuShare Pro 重大新闻接口
        df = _call_api("major_news", limit=limit)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        print(f"[缓存] 使用缓存数据，API错误: {str(e).split('\\n')[0]}")
        return _choose_df(stale, None)
    except (ConfigurationError, APIError) as e:
        print(f"[错误] {str(e)}")
        return _choose_df(stale, pd.DataFrame())


@cached
def cctv_news(date: Optional[str] = None, force: bool = False) -> pd.DataFrame:
    """获取新闻联播文字稿
    
    Args:
        date: 日期 (格式：YYYYMMDD)
    """
    if date is None:
        date = dt.date.today().strftime("%Y%m%d")
    
    key = f"cctv_news_{date}"
    stale = _get_any_cached_df(key)
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=24 * 3600)  # 新闻联播24小时缓存
        if cached_df is not None and not cached_df.empty:
            return cached_df
    try:
        # TuShare Pro CCTV新闻接口
        df = _call_api("cctv_news", date=date)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        print(f"[缓存] 使用缓存数据，API错误: {str(e).split('\\n')[0]}")
        return _choose_df(stale, None)
    except (ConfigurationError, APIError) as e:
        print(f"[错误] {str(e)}")
        return _choose_df(stale, pd.DataFrame())


@cached
def shibor(force: bool = False):
    key = "shibor"
    stale = _get_any_cached_df(key)
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=6 * 3600)  # SHIBOR 日内更敏感
        if cached_df is not None and not cached_df.empty:
            return cached_df
    try:
        df = _call_api("shibor")
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        print(f"[缓存] 使用缓存数据，API错误: {str(e).split('\\n')[0]}")
        return _choose_df(stale, None)
    except (ConfigurationError, APIError) as e:
        print(f"[错误] {str(e)}")
        return _choose_df(stale, pd.DataFrame())


# ============ 新增接口：增强基本面分析 ============

@cached
def daily_basic(ts_code: str, trade_date: str = None, start_date: str = None, end_date: str = None, force: bool = False) -> pd.DataFrame:
    """获取每日指标数据（PE、PB、市值等）"""
    key = f"daily_basic_{ts_code}_{trade_date or end_date or 'latest'}"
    stale = _get_any_cached_df(key)
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=6 * 3600)
        if cached_df is not None and not cached_df.empty:
            return cached_df
    try:
        params = {"ts_code": ts_code}
        if trade_date:
            params["trade_date"] = trade_date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        df = _call_api("daily_basic", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        print(f"[缓存] 使用缓存数据，API错误: {str(e).split('\\n')[0]}")
        return _choose_df(stale, None)
    except (ConfigurationError, APIError) as e:
        print(f"[错误] {str(e)}")
        return _choose_df(stale, pd.DataFrame())


@cached
def forecast(ts_code: str, period: str = None, force: bool = False) -> pd.DataFrame:
    """获取业绩预告数据"""
    key = f"forecast_{ts_code}_{period or 'latest'}"
    stale = _get_any_cached_df(key)
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=24 * 3600)
        if cached_df is not None and not cached_df.empty:
            return cached_df
    try:
        params = {"ts_code": ts_code}
        if period:
            params["period"] = period
        
        df = _call_api("forecast", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        print(f"[缓存] 使用缓存数据，API错误: {str(e).split('\\n')[0]}")
        return _choose_df(stale, None)
    except (ConfigurationError, APIError) as e:
        print(f"[错误] {str(e)}")
        return _choose_df(stale, pd.DataFrame())


@cached
def express(ts_code: str, period: str = None, force: bool = False) -> pd.DataFrame:
    """获取业绩快报数据"""
    key = f"express_{ts_code}_{period or 'latest'}"
    stale = _get_any_cached_df(key)
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=24 * 3600)
        if cached_df is not None and not cached_df.empty:
            return cached_df
    try:
        params = {"ts_code": ts_code}
        if period:
            params["period"] = period
        
        df = _call_api("express", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        print(f"[缓存] 使用缓存数据，API错误: {str(e).split('\\n')[0]}")
        return _choose_df(stale, None)
    except (ConfigurationError, APIError) as e:
        print(f"[错误] {str(e)}")
        return _choose_df(stale, pd.DataFrame())


# ============ 新增接口：增强技术面分析 ============

@cached
def stk_limit(ts_code: str = None, trade_date: str = None, force: bool = False) -> pd.DataFrame:
    """获取涨跌停数据"""
    key = f"stk_limit_{ts_code or 'all'}_{trade_date or 'latest'}"
    stale = _get_any_cached_df(key)
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=10 * 60)
        if cached_df is not None and not cached_df.empty:
            return cached_df
    try:
        params = {}
        if ts_code:
            params["ts_code"] = ts_code
        if trade_date:
            params["trade_date"] = trade_date
        
        df = _call_api("stk_limit", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        print(f"[缓存] 使用缓存数据，API错误: {str(e).split('\\n')[0]}")
        return _choose_df(stale, None)
    except (ConfigurationError, APIError) as e:
        print(f"[错误] {str(e)}")
        return _choose_df(stale, pd.DataFrame())


# ============ 新增接口：增强情绪面分析 ============

@cached
def moneyflow(ts_code: str, start_date: str = None, end_date: str = None, force: bool = False) -> pd.DataFrame:
    """获取个股资金流向数据"""
    key = f"moneyflow_{ts_code}_{end_date or 'latest'}"
    stale = _get_any_cached_df(key)
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=10 * 60)
        if cached_df is not None and not cached_df.empty:
            return cached_df
    try:
        params = {"ts_code": ts_code}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        df = _call_api("moneyflow", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        print(f"[缓存] 使用缓存数据，API错误: {str(e).split('\\n')[0]}")
        return _choose_df(stale, None)
    except (ConfigurationError, APIError) as e:
        print(f"[错误] {str(e)}")
        return _choose_df(stale, pd.DataFrame())


# ============ 新增接口：市场流动性指标 ============

@cached
def margin_detail(ts_code: str = None, trade_date: str = None, force: bool = False) -> pd.DataFrame:
    """获取融资融券明细"""
    key = f"margin_detail_{ts_code or 'all'}_{trade_date or 'latest'}"
    stale = _get_any_cached_df(key)
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=24 * 3600)
        if cached_df is not None and not cached_df.empty:
            return cached_df
    try:
        params = {}
        if ts_code:
            params["ts_code"] = ts_code
        if trade_date:
            params["trade_date"] = trade_date
        
        df = _call_api("margin_detail", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        print(f"[缓存] 使用缓存数据，API错误: {str(e).split('\\n')[0]}")
        return _choose_df(stale, None)
    except (ConfigurationError, APIError) as e:
        print(f"[错误] {str(e)}")
        return _choose_df(stale, pd.DataFrame())


@cached
def moneyflow_hsgt(trade_date: str = None, force: bool = False) -> pd.DataFrame:
    """获取沪深港通资金流向"""
    key = f"moneyflow_hsgt_{trade_date or 'latest'}"
    stale = _get_any_cached_df(key)
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=10 * 60)
        if cached_df is not None and not cached_df.empty:
            return cached_df
    try:
        params = {}
        if trade_date:
            params["trade_date"] = trade_date
        
        df = _call_api("moneyflow_hsgt", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        print(f"[缓存] 使用缓存数据，API错误: {str(e).split('\\n')[0]}")
        return _choose_df(stale, None)
    except (ConfigurationError, APIError) as e:
        print(f"[错误] {str(e)}")
        return _choose_df(stale, pd.DataFrame())


# ============ 新增接口：宏观经济指标 ============

@cached
def cn_gdp(force: bool = False) -> pd.DataFrame:
    """获取GDP数据"""
    key = "cn_gdp"
    stale = _get_any_cached_df(key)
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=7 * 24 * 3600)
        if cached_df is not None and not cached_df.empty:
            return cached_df
    try:
        df = _call_api("cn_gdp")
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        print(f"[缓存] 使用缓存数据，API错误: {str(e).split('\\n')[0]}")
        return _choose_df(stale, None)
    except (ConfigurationError, APIError) as e:
        print(f"[错误] {str(e)}")
        return _choose_df(stale, pd.DataFrame())


@cached
def cn_pmi(force: bool = False) -> pd.DataFrame:
    """获取PMI数据"""
    key = "cn_pmi"
    stale = _get_any_cached_df(key)
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=24 * 3600)
        if cached_df is not None and not cached_df.empty:
            return cached_df
    try:
        df = _call_api("cn_pmi")
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        print(f"[缓存] 使用缓存数据，API错误: {str(e).split('\\n')[0]}")
        return _choose_df(stale, None)
    except (ConfigurationError, APIError) as e:
        print(f"[错误] {str(e)}")
        return _choose_df(stale, pd.DataFrame())


@cached
def fx_reserves(force: bool = False) -> pd.DataFrame:
    """获取外汇储备数据"""
    key = "fx_reserves"
    stale = _get_any_cached_df(key)
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=7 * 24 * 3600)
        if cached_df is not None and not cached_df.empty:
            return cached_df
    try:
        df = _call_api("fx_reserves")
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        print(f"[缓存] 使用缓存数据，API错误: {str(e).split('\\n')[0]}")
        return _choose_df(stale, None)
    except (ConfigurationError, APIError) as e:
        print(f"[错误] {str(e)}")
        return _choose_df(stale, pd.DataFrame())


@cached  
def index_daily(ts_code: str, start_date: str = None, end_date: str = None, force: bool = False) -> pd.DataFrame:
    """获取指数日线数据"""
    key = f"index_daily_{ts_code}_{end_date or 'latest'}"
    stale = _get_any_cached_df(key)
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=10 * 60)
        if cached_df is not None and not cached_df.empty:
            return cached_df
    try:
        params = {"ts_code": ts_code}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        df = _call_api("index_daily", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        print(f"[缓存] 使用缓存数据，API错误: {str(e).split('\\n')[0]}")
        return _choose_df(stale, None)
    except (ConfigurationError, APIError) as e:
        print(f"[错误] {str(e)}")
        return _choose_df(stale, pd.DataFrame())


@cached
def ths_hot(force: bool = False) -> pd.DataFrame:
    """获取同花顺热榜数据"""
    key = "ths_hot"
    stale = _get_any_cached_df(key)
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=15 * 60)  # 15分钟缓存
        if cached_df is not None and not cached_df.empty:
            return cached_df
    try:
        # 使用TuShare的ths_hot接口
        df = _call_api("ths_hot")
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        print(f"[缓存] 使用缓存数据，API错误: {str(e).split('\\n')[0]}")
        return _choose_df(stale, None)
    except (ConfigurationError, APIError) as e:
        print(f"[错误] {str(e)}")
        return _choose_df(stale, pd.DataFrame())
    except Exception:
        # 如果API不可用，返回模拟数据
        return _get_mock_ths_hot()


def _get_mock_ths_hot() -> pd.DataFrame:
    """获取同花顺热榜模拟数据"""
    import random
    
    mock_stocks = [
        {"ts_code": "000858.SZ", "name": "五粮液", "hot_rank": 1, "hot_value": 98.5},
        {"ts_code": "600519.SH", "name": "贵州茅台", "hot_rank": 2, "hot_value": 96.2},
        {"ts_code": "002594.SZ", "name": "比亚迪", "hot_rank": 3, "hot_value": 94.8},
        {"ts_code": "300750.SZ", "name": "宁德时代", "hot_rank": 4, "hot_value": 93.1},
        {"ts_code": "000001.SZ", "name": "平安银行", "hot_rank": 5, "hot_value": 91.7},
        {"ts_code": "601318.SH", "name": "中国平安", "hot_rank": 6, "hot_value": 90.3},
        {"ts_code": "600036.SH", "name": "招商银行", "hot_rank": 7, "hot_value": 88.9},
        {"ts_code": "000002.SZ", "name": "万科A", "hot_rank": 8, "hot_value": 87.5},
        {"ts_code": "002415.SZ", "name": "海康威视", "hot_rank": 9, "hot_value": 86.1},
        {"ts_code": "000858.SZ", "name": "五粮液", "hot_rank": 10, "hot_value": 84.7},
        {"ts_code": "600900.SH", "name": "长江电力", "hot_rank": 11, "hot_value": 83.3},
        {"ts_code": "601012.SH", "name": "隆基绿能", "hot_rank": 12, "hot_value": 81.9},
        {"ts_code": "600887.SH", "name": "伊利股份", "hot_rank": 13, "hot_value": 80.5},
        {"ts_code": "000063.SZ", "name": "中兴通讯", "hot_rank": 14, "hot_value": 79.1},
        {"ts_code": "002714.SZ", "name": "牧原股份", "hot_rank": 15, "hot_value": 77.7},
    ]
    
    # 添加一些随机波动
    for stock in mock_stocks:
        stock["hot_value"] += random.uniform(-2, 2)
    
    return pd.DataFrame(mock_stocks)

