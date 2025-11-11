"""
Tushare数据接口封装 - 完整版
使用真实数据，无模拟数据
"""
import os
import time
import pandas as pd
import tushare as ts
from typing import Optional, Dict, Any, Union, List
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import hashlib
import functools
import socket

# 设置全局socket超时时间为15秒，防止HTTP请求无限挂起
socket.setdefaulttimeout(15)

# 导入缓存配置
try:
    from .cache_config import get_dynamic_ttl
except ImportError:
    # 如果导入失败，使用默认TTL函数
    def get_dynamic_ttl(data_type: str) -> int:
        """默认TTL配置"""
        ttl_config = {
            "stock_realtime": 10 * 60,  # 10分钟
            "stock_daily": 24 * 3600,    # 1天
            "concept": 24 * 3600,        # 1天
            "news": 10 * 60,             # 10分钟
        }
        return ttl_config.get(data_type, 3600)  # 默认1小时

# 配置 Tushare
# 从环境变量读取token
token = os.getenv("TUSHARE_TOKEN")
if not token:
    raise ValueError("TUSHARE_TOKEN environment variable is required. Please set it in .env file")
ts.set_token(token)
pro = ts.pro_api(timeout=15)  # 设置15秒超时，防止API调用挂起

TUSHARE_PRO_API_URL = os.getenv('TUSHARE_PRO_API_URL', 'https://api.waditu.com/dataapi')


def _ensure_https_pro_client(client) -> None:
    """Ensure Tushare uses the verified HTTPS endpoint."""
    try:
        target = TUSHARE_PRO_API_URL.rstrip('/')
        current = getattr(client, '_DataApi__http_url', '')
        if current != target:
            setattr(client, '_DataApi__http_url', target)
    except Exception as exc:
        print(f"[警告] 无法重写Tushare API地址: {exc}")


try:
    from tushare.pro import client as _ts_client_module
    setattr(_ts_client_module.DataApi, '_DataApi__http_url', TUSHARE_PRO_API_URL.rstrip('/'))
except Exception:
    pass

_ensure_https_pro_client(pro)

# 创建缓存目录
CACHE_DIR = Path.home() / ".qsl_cache"
CACHE_DIR.mkdir(exist_ok=True)

# 全局速率限制
_last_api_call = 0
# 5000积分权限：每分钟可调用500次
_api_delay = 0.12  # 5000积分权限，每分钟500次（60/500=0.12秒）

# 严格模式：不使用任何“过期/降级”回退数据
# 设置 STRICT_MODE=1 开启（默认开启）。当为严格模式时：
# - 不返回 _get_any_cached_df 获取的“过期缓存”
# - 当主数据为空或来自过期缓存时，返回空 DataFrame，而不是回退
STRICT_MODE = os.getenv("STRICT_MODE", "1") == "1"


# ========== 异常类 ==========
class APIError(Exception):
    """API调用异常"""
    pass


class RateLimitError(APIError):
    """频率限制异常"""
    pass


class AccessDeniedError(APIError):
    """权限不足异常"""
    pass


class ConfigurationError(APIError):
    """配置错误异常"""
    pass


# ========== 辅助函数 ==========
def _rate_limit():
    """API调用频率限制"""
    global _last_api_call
    current = time.time()
    elapsed = current - _last_api_call
    if elapsed < _api_delay:
        time.sleep(_api_delay - elapsed)
    _last_api_call = time.time()


def _get_cache_key(prefix: str, **kwargs) -> str:
    """生成缓存键"""
    params = json.dumps(kwargs, sort_keys=True)
    hash_val = hashlib.md5(params.encode()).hexdigest()[:8]
    return f"{prefix}_{hash_val}"


def _get_cache_path(key: str) -> Path:
    """获取缓存文件路径"""
    return CACHE_DIR / f"{key}.pkl"


def _save_df_cache(key: str, df: pd.DataFrame):
    """保存DataFrame到缓存"""
    if df is None or df.empty:
        return
    try:
        cache_path = _get_cache_path(key)
        df.to_pickle(cache_path)
    except Exception as e:
        print(f"[缓存] 保存失败: {str(e)}")


def _first_line_from_exception(e: Exception) -> str:
    """提取异常消息第一行，避免在 f-string 中出现反斜杠解析问题"""
    try:
        s = str(e)
        return s.split("\n")[0] if s else ""
    except Exception:
        try:
            return repr(e)
        except Exception:
            return ""


def _get_cached_df(key: str, ttl_seconds: int = 3600) -> Optional[pd.DataFrame]:
    """从缓存读取DataFrame"""
    cache_path = _get_cache_path(key)
    if not cache_path.exists():
        return None
    
    # 检查缓存时效
    mtime = cache_path.stat().st_mtime
    age = time.time() - mtime
    if age > ttl_seconds:
        return None
    
    try:
        return pd.read_pickle(cache_path)
    except Exception:
        return None


def _get_any_cached_df(key: str) -> Optional[pd.DataFrame]:
    """获取任意时效的缓存（用于降级）"""
    cache_path = _get_cache_path(key)
    if not cache_path.exists():
        return None
    try:
        df = pd.read_pickle(cache_path)
        # 标记为过期缓存，供严格模式识别
        try:
            df.attrs["is_stale_cache"] = True
        except Exception:
            pass
        return df
    except Exception:
        return None


def _choose_df(primary: Optional[pd.DataFrame], fallback: Optional[pd.DataFrame]) -> pd.DataFrame:
    """选择数据源
    - 严格模式下：仅返回primary（且必须非过期缓存）；否则返回空
    - 非严格模式：primary优先，否则回退到fallback
    """
    # 严格模式：不允许降级/过期缓存
    if STRICT_MODE:
        if primary is not None and not primary.empty:
            # 若primary带有过期标记，则视作无效
            if getattr(primary, "attrs", None) and primary.attrs.get("is_stale_cache"):
                return pd.DataFrame()
            return primary
        # 不回退
        return pd.DataFrame()
    # 非严格模式：允许回退
    if primary is not None and not primary.empty:
        return primary
    if fallback is not None and not fallback.empty:
        return fallback
    return pd.DataFrame()


def check_cache(key: str, ttl: int = 3600) -> Optional[pd.DataFrame]:
    """检查缓存"""
    return _get_cached_df(key, ttl)


def save_cache(key: str, df: pd.DataFrame):
    """保存缓存"""
    _save_df_cache(key, df)


def _call_api(api_name: str, **kwargs) -> Optional[pd.DataFrame]:
    """
    调用Tushare API的通用方法，带20秒超时

    Args:
        api_name: API接口名称
        **kwargs: API参数

    Returns:
        DataFrame或None
    """
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

    def _do_query():
        _rate_limit()
        return pro.query(api_name, **kwargs)

    try:
        # 使用线程池执行查询，带20秒超时
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_do_query)
            try:
                df = future.result(timeout=20)  # 20秒超时
                return df if df is not None and not df.empty else pd.DataFrame()
            except FutureTimeoutError:
                print(f"[超时] API调用超时: {api_name}, 参数: {kwargs}")
                raise APIError(f"API调用超时(20秒): {api_name}")
    except FutureTimeoutError:
        raise APIError(f"API调用超时(20秒): {api_name}")
    except Exception as e:
        error_msg = str(e)
        if "每天最多访问" in error_msg or "每分钟最多访问" in error_msg:
            raise RateLimitError(f"API频率限制: {error_msg}")
        elif "没有权限" in error_msg or "权限不足" in error_msg:
            raise AccessDeniedError(f"权限不足: {error_msg}")
        elif "请指定正确的接口名" in error_msg:
            raise ConfigurationError(f"接口名称错误: {error_msg}")
        else:
            raise APIError(f"API错误: {api_name}\n原始错误: {error_msg}")


def cached(func):
    """缓存装饰器"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # 优先使用force参数
        force = kwargs.get('force', False)
        
        # 生成缓存键
        cache_key = f"{func.__name__}"
        if args:
            cache_key += f"_{'_'.join(str(a) for a in args if a is not None)}"
        if kwargs:
            params = {k: v for k, v in kwargs.items() if k != 'force' and v is not None}
            if params:
                cache_key += f"_{hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()[:8]}"
        
        # 检查缓存
        if not force:
            cached_df = check_cache(cache_key)
            if cached_df is not None:
                return cached_df
        
        # 调用原函数
        result = func(*args, **kwargs)
        
        # 保存缓存
        if result is not None and not result.empty:
            save_cache(cache_key, result)
        
        return result
    
    return wrapper


# ========== 基础数据接口 ==========

@cached
def stock_basic(exchange: str = "", list_status: str = "L", force: bool = False) -> pd.DataFrame:
    """
    获取股票列表
    
    Args:
        exchange: 交易所 SSE上交所 SZSE深交所
        list_status: 上市状态 L上市 D退市 P暂停上市
        force: 强制刷新
    """
    key = f"stock_basic_{exchange}_{list_status}"
    stale = _get_any_cached_df(key)
    
    # 基础数据缓存24小时
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("stock_basic"))
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        df = _call_api("stock_basic", exchange=exchange, list_status=list_status)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


@cached
def stk_limit(ts_code: str = None, trade_date: str = None, force: bool = False) -> pd.DataFrame:
    """获取每日涨跌停价格 - 2000积分接口，每日8:40更新"""
    key = f"stk_limit_{ts_code or 'all'}_{trade_date or 'latest'}"
    stale = _get_any_cached_df(key)

    # 涨跌停价格缓存到当天收盘
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=3600*8)  # 8小时缓存
        if cached_df is not None and not cached_df.empty:
            return cached_df

    try:
        params = {}
        if ts_code:
            params["ts_code"] = ts_code
        if trade_date:
            params["trade_date"] = trade_date
        else:
            # 默认获取今天的涨跌停价格
            import datetime
            params["trade_date"] = datetime.datetime.now().strftime("%Y%m%d")

        df = _call_api("stk_limit", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
            return df
        return stale if stale is not None else pd.DataFrame()
    except Exception as e:
        logger.debug(f"涨跌停接口失败: {str(e)}")
        return stale if stale is not None else pd.DataFrame()

@cached
def bak_daily(ts_code: str, start_date: str = None, end_date: str = None, force: bool = False) -> pd.DataFrame:
    """获取备用行情数据 - 5000积分接口，数据更及时"""
    key = f"bak_daily_{ts_code}_{end_date or 'latest'}"
    stale = _get_any_cached_df(key)

    # 备用行情缓存时间更短，仅30分钟
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=1800)  # 30分钟缓存
        if cached_df is not None and not cached_df.empty:
            return cached_df

    try:
        params = {"ts_code": ts_code}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        df = _call_api("bak_daily", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
            return df
        return stale if stale is not None else pd.DataFrame()
    except Exception as e:
        # 备用接口失败，返回空或缓存
        logger.debug(f"备用行情接口失败: {str(e)}")
        return stale if stale is not None else pd.DataFrame()

@cached
def daily(ts_code: str, start_date: str = None, end_date: str = None, force: bool = False) -> pd.DataFrame:
    """获取日线数据 - 优先尝试备用行情（5000积分），失败则用普通接口"""
    # 首先尝试备用行情接口（更及时）
    try:
        df_bak = bak_daily(ts_code, start_date, end_date, force)
        if df_bak is not None and not df_bak.empty:
            return df_bak
    except:
        pass  # 失败则继续使用普通接口

    # 原有daily接口逻辑
    key = f"daily_{ts_code}_{end_date or 'latest'}"
    stale = _get_any_cached_df(key)
    
    # 行情数据缓存3小时
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("capital_flow"))
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        params = {"ts_code": ts_code}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        df = _call_api("daily", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


@cached
def daily_basic(ts_code: str = None, trade_date: str = None, force: bool = False) -> pd.DataFrame:
    """获取每日指标"""
    key = f"daily_basic_{ts_code or 'all'}_{trade_date or 'latest'}"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("capital_flow"))
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        params = {}
        if ts_code:
            params["ts_code"] = ts_code
        if trade_date:
            params["trade_date"] = trade_date
        
        df = _call_api("daily_basic", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


# ========== 财务数据接口 ==========

@cached
def fina_indicator(ts_code: str, period: str = None, fields: str = None, force: bool = False) -> pd.DataFrame:
    """获取财务指标"""
    key = f"fina_indicator_{ts_code}_{period or 'latest'}"
    stale = _get_any_cached_df(key)
    
    # 财务数据缓存6小时
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("market_breadth"))
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        params = {"ts_code": ts_code}
        if period:
            params["period"] = period
        if fields:
            params["fields"] = fields
        
        df = _call_api("fina_indicator", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


@cached
def income(ts_code: str, period: str = None, force: bool = False) -> pd.DataFrame:
    """获取利润表"""
    key = f"income_{ts_code}_{period or 'latest'}"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("market_breadth"))
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        params = {"ts_code": ts_code}
        if period:
            params["period"] = period
        
        df = _call_api("income", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


@cached
def balancesheet(ts_code: str, period: str = None, force: bool = False) -> pd.DataFrame:
    """获取资产负债表"""
    key = f"balancesheet_{ts_code}_{period or 'latest'}"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("market_breadth"))
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        params = {"ts_code": ts_code}
        if period:
            params["period"] = period
        
        df = _call_api("balancesheet", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


@cached
def cashflow(ts_code: str, period: str = None, force: bool = False) -> pd.DataFrame:
    """获取现金流量表"""
    key = f"cashflow_{ts_code}_{period or 'latest'}"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("market_breadth"))
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        params = {"ts_code": ts_code}
        if period:
            params["period"] = period
        
        df = _call_api("cashflow", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


# ========== 市场数据接口 ==========

@cached
def moneyflow_hsgt(trade_date: str = None, start_date: str = None, end_date: str = None, force: bool = False) -> pd.DataFrame:
    """获取沪深港通资金流向
    
    接口：moneyflow_hsgt
    描述：获取沪股通、深股通、港股通每日资金流向数据
    积分：2000积分起，5000积分每分钟可提取500次
    
    参数:
        trade_date: 交易日期 YYYYMMDD (与start_date二选一)
        start_date: 开始日期 YYYYMMDD (与trade_date二选一)
        end_date: 结束日期 YYYYMMDD
        force: 是否强制刷新缓存
    
    返回字段:
        trade_date: 交易日期
        ggt_ss: 港股通（上海）
        ggt_sz: 港股通（深圳）
        hgt: 沪股通（百万元）
        sgt: 深股通（百万元）
        north_money: 北向资金（百万元）
        south_money: 南向资金（百万元）
    """
    key = f"moneyflow_hsgt_{trade_date or end_date or 'latest'}"
    stale = _get_any_cached_df(key)
    
    # 资金流数据缓存10分钟
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("stock_realtime"))
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        params = {}
        if trade_date:
            params["trade_date"] = trade_date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        df = _call_api("moneyflow_hsgt", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 对于北向资金数据，返回缓存或空数据而不是报错
        print(f"Warning: moneyflow_hsgt API访问失败: {_first_line_from_exception(e)}")
        if stale is not None and not stale.empty:
            return stale
        return pd.DataFrame()
    except (ConfigurationError, APIError) as e:
        # 对于北向资金数据，返回缓存或空数据而不是报错
        print(f"Warning: moneyflow_hsgt API配置错误: {str(e)}")
        if stale is not None and not stale.empty:
            return stale
        return pd.DataFrame()


@cached
def shibor(date: str = None, start_date: str = None, end_date: str = None, force: bool = False) -> pd.DataFrame:
    """获取Shibor利率"""
    from .cache_config import get_dynamic_ttl
    
    key = f"shibor_{date or end_date or 'latest'}"
    stale = _get_any_cached_df(key)
    
    if not force:
        # 使用动态TTL而不是硬编码
        ttl = get_dynamic_ttl("financial_data")
        cached_df = _get_cached_df(key, ttl_seconds=ttl)
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        params = {}
        if date:
            params["date"] = date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        df = _call_api("shibor", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


# ========== 公告和新闻接口 ==========

@cached
def anns(ts_code: str, limit: int = 15, force: bool = False) -> pd.DataFrame:
    """获取公司公告"""
    key = f"anns_{ts_code}_L{limit}"
    stale = _get_any_cached_df(key)
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("stock_realtime"))  # 公告更频繁：10分钟
        if cached_df is not None and not cached_df.empty:
            return cached_df
    try:
        # 使用disclosure_date接口获取公告日期
        df = _call_api("disclosure_date", ts_code=ts_code, limit=limit)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


@cached
def news(src: str = "sina", start_date: str = None, end_date: str = None, limit: int = 100, force: bool = False) -> pd.DataFrame:
    """
    获取新闻资讯
    
    Args:
        src: 新闻来源 sina新浪财经 wallstreetcn华尔街见闻 10jqka同花顺 eastmoney东方财富
        start_date: 开始日期
        end_date: 结束日期 
        limit: 数量限制
        force: 强制刷新
    """
    key = f"news_{src}_{end_date or 'latest'}_{limit}"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("stock_realtime"))  # 新闻缓存10分钟
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
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
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


@cached
def major_news(src: str = "sina", start_date: str = None, end_date: str = None, limit: int = 100, force: bool = False) -> pd.DataFrame:
    """获取重大新闻"""
    key = f"major_news_{src}_{end_date or 'latest'}_{limit}"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("stock_realtime"))
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        params = {"src": src, "limit": limit}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        df = _call_api("major_news", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


# ========== 概念和板块接口 ==========

@cached
def concept(force: bool = False) -> pd.DataFrame:
    """获取概念股分类表"""
    key = "concept_list"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("stock_basic"))  # 概念列表缓存24小时
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        df = _call_api("concept")
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


@cached
def concept_detail(ts_code: str = None, id: str = None, force: bool = False) -> pd.DataFrame:
    """获取概念股明细列表"""
    key = f"concept_detail_{ts_code or id or 'all'}"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("market_breadth"))  # 概念成分股缓存6小时
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        params = {}
        if ts_code:
            params["ts_code"] = ts_code
        if id:
            params["id"] = id
        
        df = _call_api("concept_detail", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


# ========== 股东和高管接口 ==========

@cached
def top10_holders(ts_code: str, force: bool = False) -> pd.DataFrame:
    """获取前十大股东"""
    key = f"top10_holders_{ts_code}"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("stock_basic"))  # 股东数据缓存24小时
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        df = _call_api("top10_holders", ts_code=ts_code)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


@cached
def top10_floatholders(ts_code: str, force: bool = False) -> pd.DataFrame:
    """获取前十大流通股东"""
    key = f"top10_floatholders_{ts_code}"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("stock_basic"))
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        df = _call_api("top10_floatholders", ts_code=ts_code)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


@cached
def stk_holdertrade(ts_code: str = None, start_date: str = None, end_date: str = None, force: bool = False) -> pd.DataFrame:
    """获取股东增减持数据"""
    key = f"stk_holdertrade_{ts_code or 'all'}_{end_date or 'latest'}"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("market_breadth"))
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        params = {}
        if ts_code:
            params["ts_code"] = ts_code
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        df = _call_api("stk_holdertrade", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


# ========== 交易数据接口 ==========

@cached
def block_trade(ts_code: str = None, trade_date: str = None, start_date: str = None, end_date: str = None, force: bool = False) -> pd.DataFrame:
    """获取大宗交易数据"""
    key = f"block_trade_{ts_code or 'all'}_{trade_date or end_date or 'latest'}"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("capital_flow"))
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        params = {}
        if ts_code:
            params["ts_code"] = ts_code
        if trade_date:
            params["trade_date"] = trade_date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        df = _call_api("block_trade", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


@cached
def stk_limit(trade_date: str = None, ts_code: str = None, force: bool = False) -> pd.DataFrame:
    """获取涨跌停统计"""
    key = f"stk_limit_{trade_date or 'latest'}_{ts_code or 'all'}"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("stock_realtime"))  # 涨跌停数据缓存10分钟
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        params = {}
        if trade_date:
            params["trade_date"] = trade_date
        if ts_code:
            params["ts_code"] = ts_code
        
        df = _call_api("stk_limit", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


@cached
def margin_detail(trade_date: str = None, ts_code: str = None, force: bool = False) -> pd.DataFrame:
    """获取融资融券明细"""
    key = f"margin_detail_{trade_date or 'latest'}_{ts_code or 'all'}"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("capital_flow"))
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        params = {}
        if trade_date:
            params["trade_date"] = trade_date
        if ts_code:
            params["ts_code"] = ts_code
        
        df = _call_api("margin_detail", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


# ========== 新股和IPO接口 ==========

@cached
def new_share(start_date: str = None, end_date: str = None, force: bool = False) -> pd.DataFrame:
    """获取IPO新股上市信息"""
    key = f"new_share_{end_date or 'latest'}"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("stock_basic"))
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        df = _call_api("new_share", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


@cached
def share_float(ts_code: str = None, start_date: str = None, end_date: str = None, force: bool = False) -> pd.DataFrame:
    """获取限售股解禁数据"""
    key = f"share_float_{ts_code or 'all'}_{end_date or 'latest'}"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("stock_basic"))
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        params = {}
        if ts_code:
            params["ts_code"] = ts_code
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        df = _call_api("share_float", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


# ========== 龙虎榜接口 ==========

@cached
def top_list(trade_date: str = None, ts_code: str = None, force: bool = False) -> pd.DataFrame:
    """获取龙虎榜每日统计"""
    key = f"top_list_{trade_date or 'latest'}_{ts_code or 'all'}"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("capital_flow"))
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        params = {}
        if trade_date:
            params["trade_date"] = trade_date
        if ts_code:
            params["ts_code"] = ts_code
        
        df = _call_api("top_list", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


@cached
def top_inst(trade_date: str = None, ts_code: str = None, force: bool = False) -> pd.DataFrame:
    """获取龙虎榜机构交易明细"""
    key = f"top_inst_{trade_date or 'latest'}_{ts_code or 'all'}"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("capital_flow"))
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        params = {}
        if trade_date:
            params["trade_date"] = trade_date
        if ts_code:
            params["ts_code"] = ts_code
        
        df = _call_api("top_inst", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


# ========== 宏观经济接口 ==========

@cached
def cn_gdp(start_q: str = None, end_q: str = None, force: bool = False) -> pd.DataFrame:
    """获取中国GDP数据"""
    key = f"cn_gdp_{end_q or 'latest'}"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("historical_prices"))  # GDP数据缓存7天
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        params = {}
        if start_q:
            params["start_q"] = start_q
        if end_q:
            params["end_q"] = end_q
        
        df = _call_api("cn_gdp", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


@cached
def cn_pmi(start_month: str = None, end_month: str = None, force: bool = False) -> pd.DataFrame:
    """获取中国PMI数据"""
    key = f"cn_pmi_{end_month or 'latest'}"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("historical_prices"))  # PMI数据缓存7天
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        params = {}
        if start_month:
            params["start_month"] = start_month
        if end_month:
            params["end_month"] = end_month
        
        df = _call_api("cn_pmi", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


@cached
def fx_reserves(force: bool = False) -> pd.DataFrame:
    """获取外汇储备数据"""
    key = "fx_reserves"
    stale = _get_any_cached_df(key)
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("historical_prices"))
        if cached_df is not None and not cached_df.empty:
            return cached_df
    try:
        # 外汇储备接口可能需要更高权限或不可用
        print(f"[提示] 外汇储备接口需要更高权限或不可用")
        return pd.DataFrame()
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


# ========== 指数接口 ==========

@cached  
def index_daily(ts_code: str, start_date: str = None, end_date: str = None, force: bool = False) -> pd.DataFrame:
    """获取指数日线数据"""
    key = f"index_daily_{ts_code}_{end_date or 'latest'}"
    stale = _get_any_cached_df(key)
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("stock_realtime"))
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
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


# ========== ETF接口 ==========

@cached
def fund_nav(ts_code: str = None, nav_date: str = None, market: str = None, force: bool = False) -> pd.DataFrame:
    """获取公募基金净值"""
    key = f"fund_nav_{ts_code or 'all'}_{nav_date or 'latest'}"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("stock_basic"))
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        params = {}
        if ts_code:
            params["ts_code"] = ts_code
        if nav_date:
            params["nav_date"] = nav_date
        if market:
            params["market"] = market
        
        df = _call_api("fund_nav", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


@cached
def fund_daily(ts_code: str, start_date: str = None, end_date: str = None, force: bool = False) -> pd.DataFrame:
    """获取场内基金日线行情"""
    key = f"fund_daily_{ts_code}_{end_date or 'latest'}"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("capital_flow"))
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        params = {"ts_code": ts_code}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        df = _call_api("fund_daily", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


# ========== 期货接口 ==========

@cached
def fut_daily(ts_code: str = None, trade_date: str = None, exchange: str = None, start_date: str = None, end_date: str = None, force: bool = False) -> pd.DataFrame:
    """获取期货日线行情"""
    key = f"fut_daily_{ts_code or 'all'}_{trade_date or end_date or 'latest'}"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("capital_flow"))
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        params = {}
        if ts_code:
            params["ts_code"] = ts_code
        if trade_date:
            params["trade_date"] = trade_date
        if exchange:
            params["exchange"] = exchange
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        df = _call_api("fut_daily", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


# ========== 期权接口 ==========

@cached
def opt_daily(ts_code: str = None, trade_date: str = None, exchange: str = None, start_date: str = None, end_date: str = None, force: bool = False) -> pd.DataFrame:
    """获取期权日线行情"""
    key = f"opt_daily_{ts_code or 'all'}_{trade_date or end_date or 'latest'}"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("capital_flow"))
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        params = {}
        if ts_code:
            params["ts_code"] = ts_code
        if trade_date:
            params["trade_date"] = trade_date
        if exchange:
            params["exchange"] = exchange
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        df = _call_api("opt_daily", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


# ========== 港股接口 ==========

@cached
def hk_daily(ts_code: str = None, trade_date: str = None, start_date: str = None, end_date: str = None, force: bool = False) -> pd.DataFrame:
    """获取港股日线行情"""
    key = f"hk_daily_{ts_code or 'all'}_{trade_date or end_date or 'latest'}"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("capital_flow"))
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        params = {}
        if ts_code:
            params["ts_code"] = ts_code
        if trade_date:
            params["trade_date"] = trade_date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        df = _call_api("hk_daily", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


# ========== 美股接口 ==========

@cached
def us_daily(ts_code: str = None, trade_date: str = None, start_date: str = None, end_date: str = None, force: bool = False) -> pd.DataFrame:
    """获取美股日线行情"""
    key = f"us_daily_{ts_code or 'all'}_{trade_date or end_date or 'latest'}"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("capital_flow"))
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        params = {}
        if ts_code:
            params["ts_code"] = ts_code
        if trade_date:
            params["trade_date"] = trade_date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        df = _call_api("us_daily", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


# ========== 财经日历接口 ==========

@cached
def eco_cal(date: str = None, start_date: str = None, end_date: str = None, currency: str = None, force: bool = False) -> pd.DataFrame:
    """获取财经日历"""
    key = f"eco_cal_{date or end_date or 'latest'}_{currency or 'all'}"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("stock_basic"))
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        params = {}
        if date:
            params["date"] = date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if currency:
            params["currency"] = currency
        
        df = _call_api("eco_cal", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


# ========== 辅助函数（保持向后兼容） ==========

def clear_cache():
    """清理所有缓存"""
    import shutil
    if CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR)
        CACHE_DIR.mkdir(exist_ok=True)
        print(f"[缓存] 已清理: {CACHE_DIR}")


def get_cache_info() -> Dict[str, Any]:
    """获取缓存信息"""
    cache_files = list(CACHE_DIR.glob("*.pkl"))
    total_size = sum(f.stat().st_size for f in cache_files)
    
    return {
        "cache_dir": str(CACHE_DIR),
        "cache_count": len(cache_files),
        "total_size_mb": round(total_size / 1024 / 1024, 2),
        "oldest_cache": min([f.stat().st_mtime for f in cache_files]) if cache_files else None,
        "newest_cache": max([f.stat().st_mtime for f in cache_files]) if cache_files else None
    }


# ========== 龙虎榜相关函数（向后兼容） ==========

def top_list(trade_date: str = None, ts_code: str = None, force: bool = False) -> pd.DataFrame:
    """获取龙虎榜每日明细
    
    接口：top_list
    描述：龙虎榜每日交易明细
    数据历史：2005年至今
    限量：单次请求返回最大10000行数据
    积分：用户需要至少2000积分
    
    参数:
        trade_date: 交易日期 YYYYMMDD (必选)
        ts_code: 股票代码 (可选)
        force: 是否强制刷新缓存
    
    返回字段:
        trade_date: 交易日期
        ts_code: TS代码
        name: 名称
        close: 收盘价
        pct_change: 涨跌幅
        turnover_rate: 换手率
        amount: 总成交额
        l_sell: 龙虎榜卖出额
        l_buy: 龙虎榜买入额
        l_amount: 龙虎榜成交额
        net_amount: 龙虎榜净买入额
        net_rate: 龙虎榜净买额占比
        amount_rate: 龙虎榜成交额占比
        float_values: 当日流通市值
        reason: 上榜理由
    """
    # trade_date是必选参数
    if not trade_date:
        print("[错误] top_list接口需要提供trade_date参数")
        return pd.DataFrame()
    
    key = f"top_list_{trade_date}_{ts_code or 'all'}"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("capital_flow"))
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        _rate_limit()
        params = {"trade_date": trade_date}  # trade_date是必选参数
        if ts_code:
            params["ts_code"] = ts_code
        
        df = _call_api("top_list", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except Exception as e:
        print(f"[错误] 获取龙虎榜失败: {str(e)}")
        return _choose_df(stale, pd.DataFrame())


def top_inst(trade_date: str = None, ts_code: str = None, force: bool = False) -> pd.DataFrame:
    """获取龙虎榜机构交易明细
    
    接口：top_inst
    描述：龙虎榜机构交易明细
    积分：需要2000积分以上
    
    参数:
        trade_date: 交易日期 YYYYMMDD (必选)
        ts_code: 股票代码 (可选)
        force: 是否强制刷新缓存
    """
    key = f"top_inst_{trade_date or 'latest'}_{ts_code or 'all'}"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("capital_flow"))
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        _rate_limit()
        df = _call_api("top_inst", trade_date=trade_date, ts_code=ts_code)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except Exception as e:
        print(f"[错误] 获取龙虎榜机构明细失败: {str(e)}")
        return _choose_df(stale, pd.DataFrame())

# ========== 业绩预告和快报接口 ==========

@cached
def forecast(ts_code: str = None, ann_date: str = None, start_date: str = None, end_date: str = None, period: str = None, type: str = None, force: bool = False) -> pd.DataFrame:
    """获取业绩预告数据"""
    key = f"forecast_{ts_code or 'all'}_{period or end_date or 'latest'}"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("market_breadth"))
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        params = {}
        if ts_code:
            params["ts_code"] = ts_code
        if ann_date:
            params["ann_date"] = ann_date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if period:
            params["period"] = period
        if type:
            params["type"] = type
        
        df = _call_api("forecast", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


@cached
def express(ts_code: str = None, ann_date: str = None, start_date: str = None, end_date: str = None, period: str = None, force: bool = False) -> pd.DataFrame:
    """获取业绩快报"""
    key = f"express_{ts_code or 'all'}_{period or end_date or 'latest'}"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("market_breadth"))
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        params = {}
        if ts_code:
            params["ts_code"] = ts_code
        if ann_date:
            params["ann_date"] = ann_date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if period:
            params["period"] = period
        
        df = _call_api("express", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


# ========== 宏观经济额外接口 ==========

@cached
def cpi(month: str = None, start_month: str = None, end_month: str = None, force: bool = False) -> pd.DataFrame:
    """获取CPI居民消费价格指数"""
    key = f"cpi_{end_month or 'latest'}"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("historical_prices"))
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        params = {}
        if month:
            params["month"] = month
        if start_month:
            params["start_month"] = start_month
        if end_month:
            params["end_month"] = end_month
        
        df = _call_api("cn_cpi", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


@cached
def ppi(month: str = None, start_month: str = None, end_month: str = None, force: bool = False) -> pd.DataFrame:
    """获取PPI工业生产者价格指数"""
    key = f"ppi_{end_month or 'latest'}"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("historical_prices"))
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        params = {}
        if month:
            params["month"] = month
        if start_month:
            params["start_month"] = start_month
        if end_month:
            params["end_month"] = end_month
        
        df = _call_api("cn_ppi", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


@cached
def money_supply(month: str = None, start_month: str = None, end_month: str = None, force: bool = False) -> pd.DataFrame:
    """获取货币供应量"""
    key = f"money_supply_{end_month or 'latest'}"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("historical_prices"))
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        params = {}
        if month:
            params["month"] = month
        if start_month:
            params["start_month"] = start_month
        if end_month:
            params["end_month"] = end_month
        
        df = _call_api("cn_m", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


# ========== 热点和资金流接口 ==========

@cached
def ths_hot(trade_date: str = None, ts_code: str = None, force: bool = False) -> pd.DataFrame:
    """获取同花顺热门股票"""
    key = f"ths_hot_{trade_date or 'latest'}_{ts_code or 'all'}"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("capital_flow"))
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        params = {}
        if trade_date:
            params["trade_date"] = trade_date
        if ts_code:
            params["ts_code"] = ts_code
        
        df = _call_api("ths_hot", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


@cached  
def stock_hsgt(ts_code: str = None, trade_date: str = None, type: str = None, start_date: str = None, end_date: str = None, force: bool = False) -> pd.DataFrame:
    """获取沪深港通股票列表"""
    key = f"stock_hsgt_{trade_date or 'latest'}_{type or 'all'}"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("stock_basic"))  # 24小时缓存
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        params = {}
        if ts_code:
            params["ts_code"] = ts_code
        if trade_date:
            params["trade_date"] = trade_date
        if type:
            params["type"] = type
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        df = _call_api("stock_hsgt", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


@cached
def moneyflow_ths(ts_code: str = None, trade_date: str = None, start_date: str = None, end_date: str = None, force: bool = False) -> pd.DataFrame:
    """获取同花顺个股资金流向数据"""
    key = f"moneyflow_ths_{ts_code or 'all'}_{trade_date or 'latest'}"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("market_breadth"))  # 6小时缓存
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        params = {}
        if ts_code:
            params["ts_code"] = ts_code
        if trade_date:
            params["trade_date"] = trade_date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        df = _call_api("moneyflow_ths", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


@cached
def moneyflow_dc(ts_code: str = None, trade_date: str = None, start_date: str = None, end_date: str = None, force: bool = False) -> pd.DataFrame:
    """获取东方财富个股资金流向数据"""
    key = f"moneyflow_dc_{ts_code or 'all'}_{trade_date or 'latest'}"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("market_breadth"))  # 6小时缓存
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        params = {}
        if ts_code:
            params["ts_code"] = ts_code
        if trade_date:
            params["trade_date"] = trade_date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        df = _call_api("moneyflow_dc", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


@cached
def suspend_d(ts_code: str = None, trade_date: str = None, start_date: str = None, end_date: str = None, suspend_type: str = None, force: bool = False) -> pd.DataFrame:
    """获取每日停复牌信息"""
    key = f"suspend_d_{trade_date or 'latest'}_{suspend_type or 'all'}"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("financial_data"))  # 12小时缓存
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        params = {}
        if ts_code:
            params["ts_code"] = ts_code
        if trade_date:
            params["trade_date"] = trade_date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if suspend_type:
            params["suspend_type"] = suspend_type
        
        df = _call_api("suspend_d", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


@cached
def dividend(ts_code: str = None, ann_date: str = None, record_date: str = None, ex_date: str = None, imp_ann_date: str = None, force: bool = False) -> pd.DataFrame:
    """获取分红送股数据"""
    key = f"dividend_{ts_code or 'all'}_{ann_date or 'latest'}"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("stock_basic"))  # 24小时缓存
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        params = {}
        if ts_code:
            params["ts_code"] = ts_code
        if ann_date:
            params["ann_date"] = ann_date
        if record_date:
            params["record_date"] = record_date
        if ex_date:
            params["ex_date"] = ex_date
        if imp_ann_date:
            params["imp_ann_date"] = imp_ann_date
        
        df = _call_api("dividend", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


@cached
def moneyflow(ts_code: str = None, trade_date: str = None, start_date: str = None, end_date: str = None, force: bool = False) -> pd.DataFrame:
    """获取个股资金流向"""
    key = f"moneyflow_{ts_code or 'all'}_{trade_date or end_date or 'latest'}"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("stock_realtime"))
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        params = {}
        if ts_code:
            params["ts_code"] = ts_code
        if trade_date:
            params["trade_date"] = trade_date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        df = _call_api("moneyflow", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return _choose_df(df, stale)
    except (RateLimitError, AccessDeniedError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API访问失败: {_first_line_from_exception(e)}")
    except (ConfigurationError, APIError) as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"API配置错误: {str(e)}")


# ========== 涨跌停和市场统计接口 ==========

def limit_list_d(trade_date: str = None, ts_code: str = None, limit_type: str = None, exchange: str = None, force: bool = False) -> pd.DataFrame:
    """获取涨跌停和炸板数据
    
    接口：limit_list_d
    描述：获取A股每日涨跌停、炸板数据情况，数据从2020年开始（不提供ST股票的统计）
    限量：单次最大可以获取2500条数据
    积分：5000积分每分钟可以请求200次
    
    参数:
        trade_date: 交易日期 YYYYMMDD
        ts_code: 股票代码
        limit_type: 涨跌停类型 U涨停 D跌停 Z炸板
        exchange: 交易所 SH上交所 SZ深交所
        force: 是否强制刷新缓存
    
    返回字段:
        trade_date: 交易日期
        ts_code: TS代码
        industry: 行业
        name: 股票名称
        close: 收盘价
        pct_chg: 涨跌幅
        open_times: 打开次数
        up_stat: 连板统计（如3/3表示三连板）
        limit_times: 涨停次数
    """
    key = f"limit_list_d_{trade_date or 'latest'}_{limit_type or 'all'}_{ts_code or 'all'}"
    stale = _get_any_cached_df(key)
    
    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("market_overview"))
        if cached_df is not None and not cached_df.empty:
            return cached_df
    
    try:
        params = {}
        if trade_date:
            params["trade_date"] = trade_date
        if ts_code:
            params["ts_code"] = ts_code
        if limit_type:
            params["limit_type"] = limit_type
        if exchange:
            params["exchange"] = exchange
        
        df = _call_api("limit_list_d", **params)
        if df is not None and not df.empty:
            _save_df_cache(key, df)
        return df if df is not None else pd.DataFrame()
    except Exception as e:
        # 不返回缓存数据，直接报错
        raise Exception(f"获取涨跌停数据失败: {str(e)}")


# ========== 连板统计辅助函数 ==========

def get_continuous_board_stocks(trade_date: str = None, min_boards: int = 2) -> Dict:
    """
    获取连板股票统计
    
    Args:
        trade_date: 交易日期
        min_boards: 最小连板数
    
    Returns:
        包含各连板梯队股票的字典
    """
    try:
        # 获取当日涨停数据
        df = limit_list_d(trade_date=trade_date, limit_type='U')
        
        if df.empty:
            return {}
        
        # 解析连板数据
        board_dict = {}
        for _, row in df.iterrows():
            up_stat = row.get('up_stat', '')
            if up_stat and '/' in up_stat:
                # 解析格式如 "3/3" 表示3连板
                boards = int(up_stat.split('/')[0])
                if boards >= min_boards:
                    if boards not in board_dict:
                        board_dict[boards] = []
                    board_dict[boards].append({
                        'code': row['ts_code'],
                        'name': row['name'],
                        'industry': row.get('industry', ''),
                        'pct_chg': row['pct_chg'],
                        'close': row['close'],
                        'limit_times': row.get('limit_times', 1)
                    })
        
        # 按连板数排序
        sorted_dict = dict(sorted(board_dict.items(), reverse=True))
        return sorted_dict
        
    except Exception as e:
        print(f"[连板统计] 获取失败: {e}")
        return {}


def get_board_statistics(trade_date: str = None) -> Dict:
    """
    获取涨停板统计数据
    
    Returns:
        包含涨停、跌停、炸板等统计的字典
    """
    try:
        stats = {
            'limit_up': 0,      # 涨停数
            'limit_down': 0,    # 跌停数
            'bomb_board': 0,    # 炸板数
            'first_board': 0,   # 首板数
            'continuous_board': 0,  # 连板总数
            'max_continuous': 0,    # 最高连板数
            'board_success_rate': 0,  # 封板成功率
        }
        
        # 获取涨停数据
        up_df = limit_list_d(trade_date=trade_date, limit_type='U')
        if not up_df.empty:
            stats['limit_up'] = len(up_df)
            
            # 统计连板情况
            for _, row in up_df.iterrows():
                up_stat = row.get('up_stat', '')
                if up_stat and '/' in up_stat:
                    boards = int(up_stat.split('/')[0])
                    if boards == 1:
                        stats['first_board'] += 1
                    else:
                        stats['continuous_board'] += 1
                    stats['max_continuous'] = max(stats['max_continuous'], boards)
                else:
                    stats['first_board'] += 1
        
        # 获取跌停数据
        down_df = limit_list_d(trade_date=trade_date, limit_type='D')
        if not down_df.empty:
            stats['limit_down'] = len(down_df)
        
        # 获取炸板数据
        bomb_df = limit_list_d(trade_date=trade_date, limit_type='Z')
        if not bomb_df.empty:
            stats['bomb_board'] = len(bomb_df)
        
        # 计算封板成功率
        total_attempts = stats['limit_up'] + stats['bomb_board']
        if total_attempts > 0:
            stats['board_success_rate'] = round(stats['limit_up'] / total_attempts * 100, 2)
        
        return stats
        
    except Exception as e:
        print(f"[涨停统计] 获取失败: {e}")
        return {
            'limit_up': 0,
            'limit_down': 0,
            'bomb_board': 0,
            'first_board': 0,
            'continuous_board': 0,
            'max_continuous': 0,
            'board_success_rate': 0,
        }


def get_sector_board_analysis(trade_date: str = None) -> List[Dict]:
    """
    获取板块涨停分析
    
    Returns:
        按行业分组的涨停统计
    """
    try:
        # 获取涨停数据
        df = limit_list_d(trade_date=trade_date, limit_type='U')
        
        if df.empty:
            return []
        
        # 按行业分组统计
        industry_stats = {}
        for _, row in df.iterrows():
            industry = row.get('industry', '未知')
            if industry not in industry_stats:
                industry_stats[industry] = {
                    'industry': industry,
                    'count': 0,
                    'stocks': [],
                    'continuous_boards': 0,
                    'max_board': 0
                }
            
            industry_stats[industry]['count'] += 1
            industry_stats[industry]['stocks'].append({
                'code': row['ts_code'],
                'name': row['name'],
                'up_stat': row.get('up_stat', '')
            })
            
            # 统计连板
            up_stat = row.get('up_stat', '')
            if up_stat and '/' in up_stat:
                boards = int(up_stat.split('/')[0])
                if boards > 1:
                    industry_stats[industry]['continuous_boards'] += 1
                industry_stats[industry]['max_board'] = max(
                    industry_stats[industry]['max_board'], boards
                )
        
        # 转换为列表并排序
        result = list(industry_stats.values())
        result.sort(key=lambda x: x['count'], reverse=True)
        
        # 只保留前10个行业
        return result[:10]

    except Exception as e:
        print(f"[板块分析] 获取失败: {e}")
        return []


# ========== 5000积分专属高级接口 ==========

def income_vip(ts_code: str = None, ann_date: str = None, start_date: str = None,
               end_date: str = None, period: str = None, report_type: str = None,
               comp_type: str = None, force: bool = False) -> pd.DataFrame:
    """获取上市公司财务利润表数据（5000积分VIP版本 - 批量获取）

    接口：income_vip
    描述：获取上市公司财务利润表数据，5000积分用户可以批量获取
    数据历史：1990年至今
    限量：单次请求返回最大5000行数据
    积分：需要5000积分

    参数:
        ts_code: 股票代码
        ann_date: 公告日期
        start_date: 报告期开始日期
        end_date: 报告期结束日期
        period: 报告期(YYYYMMDD格式的季报月份)
        report_type: 报告类型：见报告类型说明
        comp_type: 公司类型：1一般工商业 2银行 3保险 4证券
        force: 是否强制刷新缓存

    返回字段:
        ts_code: TS代码
        ann_date: 公告日期
        f_ann_date: 实际公告日期
        end_date: 报告期
        report_type: 报告类型
        comp_type: 公司类型
        basic_eps: 基本每股收益
        diluted_eps: 稀释每股收益
        total_revenue: 营业总收入
        revenue: 营业收入
        int_income: 利息收入
        prem_earned: 已赚保费
        comm_income: 手续费及佣金收入
        n_commis_income: 手续费及佣金净收入
        n_oth_income: 其他经营净收益
        n_oth_b_income: 加:其他业务净收益
        prem_income: 保险业务收入
        out_prem: 减:分出保费
        une_prem_reser: 提取未到期责任准备金
        reins_income: 其中:分保费收入
        n_sec_tb_income: 代理买卖证券业务净收入
        n_sec_uw_income: 证券承销业务净收入
        n_asset_mg_income: 受托客户资产管理业务净收入
        oth_b_income: 其他业务收入
        fv_value_chg_gain: 加:公允价值变动净收益
        invest_income: 加:投资净收益
        ass_invest_income: 其中:对联营企业和合营企业的投资收益
        forex_gain: 加:汇兑净收益
        total_cogs: 营业总成本
        oper_cost: 减:营业成本
        int_exp: 减:利息支出
        comm_exp: 减:手续费及佣金支出
        biz_tax_surchg: 减:营业税金及附加
        sell_exp: 减:销售费用
        admin_exp: 减:管理费用
        fin_exp: 减:财务费用
        assets_impair_loss: 减:资产减值损失
        prem_refund: 退保金
        compens_payout: 赔付总支出
        reser_insur_liab: 提取保险责任准备金
        div_payt: 保单红利支出
        reins_exp: 分保费用
        oper_exp: 营业支出
        compens_payout_refu: 减:摊回赔付支出
        insur_reser_refu: 减:摊回保险责任准备金
        reins_cost_refund: 减:摊回分保费用
        other_bus_cost: 其他业务成本
        operate_profit: 营业利润
        non_oper_income: 加:营业外收入
        non_oper_exp: 减:营业外支出
        nca_disploss: 其中:减:非流动资产处置净损失
        total_profit: 利润总额
        income_tax: 减:所得税费用
        n_income: 净利润(含少数股东损益)
        n_income_attr_p: 净利润(不含少数股东损益)
        minority_gain: 少数股东损益
        oth_compr_income: 其他综合收益
        t_compr_income: 综合收益总额
        compr_inc_attr_p: 归属于母公司(或股东)的综合收益总额
        compr_inc_attr_m_s: 归属于少数股东的综合收益总额
        ebit: 息税前利润
        ebitda: 息税折旧摊销前利润
        insurance_exp: 保险业务支出
        undist_profit: 年初未分配利润
        distable_profit: 可分配利润
        update_flag: 更新标识
    """
    key = _get_cache_key("income_vip", ts_code=ts_code, ann_date=ann_date,
                         start_date=start_date, end_date=end_date,
                         period=period, report_type=report_type, comp_type=comp_type)

    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("financial"))
        if cached_df is not None and not cached_df.empty:
            return cached_df

    try:
        _rate_limit()
        params = {}
        if ts_code: params["ts_code"] = ts_code
        if ann_date: params["ann_date"] = ann_date
        if start_date: params["start_date"] = start_date
        if end_date: params["end_date"] = end_date
        if period: params["period"] = period
        if report_type: params["report_type"] = report_type
        if comp_type: params["comp_type"] = comp_type

        df = pro.income_vip(**params)
        _save_df_cache(key, df)
        return df
    except Exception as e:
        print(f"[income_vip] 获取失败: {e}")
        return _get_any_cached_df(key)


def balancesheet_vip(ts_code: str = None, ann_date: str = None, start_date: str = None,
                    end_date: str = None, period: str = None, report_type: str = None,
                    comp_type: str = None, force: bool = False) -> pd.DataFrame:
    """获取上市公司资产负债表数据（5000积分VIP版本 - 批量获取）

    接口：balancesheet_vip
    描述：获取上市公司资产负债表数据，5000积分用户可以批量获取
    数据历史：1990年至今
    限量：单次请求返回最大5000行数据
    积分：需要5000积分

    参数:
        ts_code: 股票代码
        ann_date: 公告日期
        start_date: 报告期开始日期
        end_date: 报告期结束日期
        period: 报告期(YYYYMMDD格式的季报月份)
        report_type: 报告类型：见报告类型说明
        comp_type: 公司类型：1一般工商业 2银行 3保险 4证券
        force: 是否强制刷新缓存

    返回字段:
        ts_code: TS代码
        ann_date: 公告日期
        f_ann_date: 实际公告日期
        end_date: 报告期
        report_type: 报告类型
        comp_type: 公司类型
        total_share: 期末总股本
        cap_rese: 资本公积金
        undistr_porfit: 未分配利润
        surplus_rese: 盈余公积金
        special_rese: 专项储备
        money_cap: 货币资金
        trad_asset: 交易性金融资产
        notes_receiv: 应收票据
        accounts_receiv: 应收账款
        oth_receiv: 其他应收款
        prepayment: 预付款项
        div_receiv: 应收股利
        int_receiv: 应收利息
        inventories: 存货
        amor_exp: 长期待摊费用
        nca_within_1y: 一年内到期的非流动资产
        sett_rsrv: 结算备付金
        loanto_oth_bank_fi: 拆出资金
        premium_receiv: 应收保费
        reinsur_receiv: 应收分保账款
        reinsur_res_receiv: 应收分保合同准备金
        pur_resale_fa: 买入返售金融资产
        oth_cur_assets: 其他流动资产
        total_cur_assets: 流动资产合计
        fa_avail_for_sale: 可供出售金融资产
        htm_invest: 持有至到期投资
        lt_eqt_invest: 长期股权投资
        invest_real_estate: 投资性房地产
        time_deposits: 定期存款
        oth_assets: 其他资产
        lt_rec: 长期应收款
        fix_assets: 固定资产
        cip: 在建工程
        const_materials: 工程物资
        fixed_assets_disp: 固定资产清理
        produc_bio_assets: 生产性生物资产
        oil_and_gas_assets: 油气资产
        intan_assets: 无形资产
        r_and_d: 研发支出
        goodwill: 商誉
        lt_amor_exp: 长期待摊费用
        defer_tax_assets: 递延所得税资产
        decr_in_disbur: 发放贷款及垫款
        oth_nca: 其他非流动资产
        total_nca: 非流动资产合计
        cash_reser_cb: 现金及存放中央银行款项
        depos_in_oth_bfi: 存放同业和其它金融机构款项
        prec_metals: 贵金属
        deriv_assets: 衍生金融资产
        rr_reins_une_prem: 应收分保未到期责任准备金
        rr_reins_outstd_cla: 应收分保未决赔款准备金
        rr_reins_lins_liab: 应收分保寿险责任准备金
        rr_reins_lthins_liab: 应收分保长期健康险责任准备金
        refund_depos: 存出保证金
        ph_pledge_loans: 保户质押贷款
        refund_cap_depos: 存出资本保证金
        indep_acct_assets: 独立账户资产
        client_depos: 其中：客户资金存款
        client_prov: 其中：客户备付金
        transac_seat_fee: 其中:交易席位费
        invest_as_receiv: 应收款项类投资
        total_assets: 资产总计
        lt_borr: 长期借款
        st_borr: 短期借款
        cb_borr: 向中央银行借款
        depos_ib_deposits: 吸收存款及同业存放
        loan_oth_bank: 拆入资金
        trading_fl: 交易性金融负债
        notes_payable: 应付票据
        acct_payable: 应付账款
        adv_receipts: 预收款项
        sold_for_repur_fa: 卖出回购金融资产款
        comm_payable: 应付手续费及佣金
        payroll_payable: 应付职工薪酬
        taxes_payable: 应交税费
        int_payable: 应付利息
        div_payable: 应付股利
        oth_payable: 其他应付款
        acc_exp: 预提费用
        deferred_inc: 递延收益
        st_bonds_payable: 应付短期债券
        payable_to_reinsurer: 应付分保账款
        rsrv_insur_cont: 保险合同准备金
        acting_trading_sec: 代理买卖证券款
        acting_uw_sec: 代理承销证券款
        non_cur_liab_due_1y: 一年内到期的非流动负债
        oth_cur_liab: 其他流动负债
        total_cur_liab: 流动负债合计
        bond_payable: 应付债券
        lt_payable: 长期应付款
        specific_payables: 专项应付款
        estimated_liab: 预计负债
        defer_tax_liab: 递延所得税负债
        defer_inc_non_cur_liab: 递延收益-非流动负债
        oth_ncl: 其他非流动负债
        total_ncl: 非流动负债合计
        depos_oth_bfi: 同业和其它金融机构存放款项
        deriv_liab: 衍生金融负债
        depos: 吸收存款
        agency_bus_liab: 代理业务负债
        oth_liab: 其他负债
        prem_receiv_adva: 预收保费
        depos_received: 存入保证金
        ph_invest: 保户储金及投资款
        reser_une_prem: 未到期责任准备金
        reser_outstd_claims: 未决赔款准备金
        reser_lins_liab: 寿险责任准备金
        reser_lthins_liab: 长期健康险责任准备金
        indept_acc_liab: 独立账户负债
        pledge_borr: 其中:质押借款
        indem_payable: 应付赔付款
        policy_div_payable: 应付保单红利
        total_liab: 负债合计
        treasury_share: 减:库存股
        ordin_risk_reser: 一般风险准备
        forex_differ: 外币报表折算差额
        invest_loss_unconf: 未确认的投资损失
        minority_int: 少数股东权益
        total_hldr_eqy_exc_min_int: 股东权益合计(不含少数股东权益)
        total_hldr_eqy_inc_min_int: 股东权益合计(含少数股东权益)
        total_liab_hldr_eqy: 负债及股东权益总计
        lt_payroll_payable: 长期应付职工薪酬
        oth_comp_income: 其他综合收益
        oth_eqt_tools: 其他权益工具
        oth_eqt_tools_p_shr: 其他权益工具(优先股)
        lending_funds: 融出资金
        acc_receivable: 应收款项
        st_fin_payable: 应付短期融资款
        payables: 应付款项
        hfs_assets: 持有待售资产
        hfs_sales: 持有待售负债
        cost_fin_assets: 以摊余成本计量的金融资产
        fair_value_fin_assets: 以公允价值计量且其变动计入其他综合收益的金融资产
        update_flag: 更新标识
    """
    key = _get_cache_key("balancesheet_vip", ts_code=ts_code, ann_date=ann_date,
                         start_date=start_date, end_date=end_date,
                         period=period, report_type=report_type, comp_type=comp_type)

    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("financial"))
        if cached_df is not None and not cached_df.empty:
            return cached_df

    try:
        _rate_limit()
        params = {}
        if ts_code: params["ts_code"] = ts_code
        if ann_date: params["ann_date"] = ann_date
        if start_date: params["start_date"] = start_date
        if end_date: params["end_date"] = end_date
        if period: params["period"] = period
        if report_type: params["report_type"] = report_type
        if comp_type: params["comp_type"] = comp_type

        df = pro.balancesheet_vip(**params)
        _save_df_cache(key, df)
        return df
    except Exception as e:
        print(f"[balancesheet_vip] 获取失败: {e}")
        return _get_any_cached_df(key)


def cashflow_vip(ts_code: str = None, ann_date: str = None, start_date: str = None,
                end_date: str = None, period: str = None, report_type: str = None,
                comp_type: str = None, force: bool = False) -> pd.DataFrame:
    """获取上市公司现金流量表数据（5000积分VIP版本 - 批量获取）

    接口：cashflow_vip
    描述：获取上市公司现金流量表数据，5000积分用户可以批量获取
    数据历史：1990年至今
    限量：单次请求返回最大5000行数据
    积分：需要5000积分
    """
    key = _get_cache_key("cashflow_vip", ts_code=ts_code, ann_date=ann_date,
                         start_date=start_date, end_date=end_date,
                         period=period, report_type=report_type, comp_type=comp_type)

    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("financial"))
        if cached_df is not None and not cached_df.empty:
            return cached_df

    try:
        _rate_limit()
        params = {}
        if ts_code: params["ts_code"] = ts_code
        if ann_date: params["ann_date"] = ann_date
        if start_date: params["start_date"] = start_date
        if end_date: params["end_date"] = end_date
        if period: params["period"] = period
        if report_type: params["report_type"] = report_type
        if comp_type: params["comp_type"] = comp_type

        df = pro.cashflow_vip(**params)
        _save_df_cache(key, df)
        return df
    except Exception as e:
        print(f"[cashflow_vip] 获取失败: {e}")
        return _get_any_cached_df(key)


def cyq_perf(ts_code: str, trade_date: str, force: bool = False) -> pd.DataFrame:
    """获取A股筹码分布数据（5000积分专属）

    接口：cyq_perf
    描述：获取A股筹码分布数据，包括集中度、平均成本等指标
    数据历史：2016年至今
    限量：单次请求返回最大5000行数据
    积分：需要5000积分

    参数:
        ts_code: 股票代码（必选）
        trade_date: 交易日期YYYYMMDD（必选）
        force: 是否强制刷新缓存

    返回字段:
        ts_code: TS代码
        trade_date: 交易日期
        his_low: 历史最低价
        his_high: 历史最高价
        cost_5pct: 5%成本价格
        cost_15pct: 15%成本价格
        cost_50pct: 50%成本价格
        cost_85pct: 85%成本价格
        cost_95pct: 95%成本价格
        weight_avg: 平均成本
        winner_rate: 获利盘比例
    """
    key = f"cyq_perf_{ts_code}_{trade_date}"

    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("chip_analysis"))
        if cached_df is not None and not cached_df.empty:
            return cached_df

    try:
        _rate_limit()
        df = pro.cyq_perf(ts_code=ts_code, trade_date=trade_date)
        _save_df_cache(key, df)
        return df
    except Exception as e:
        print(f"[cyq_perf] 获取失败: {e}")
        return _get_any_cached_df(key)


def cyq_chips(ts_code: str, trade_date: str, force: bool = False) -> pd.DataFrame:
    """获取A股筹码分布明细数据（5000积分专属）

    接口：cyq_chips
    描述：获取A股筹码分布明细数据，包括价格区间分布
    数据历史：2016年至今
    限量：单次请求返回最大5000行数据
    积分：需要5000积分

    参数:
        ts_code: 股票代码（必选）
        trade_date: 交易日期YYYYMMDD（必选）
        force: 是否强制刷新缓存

    返回字段:
        ts_code: TS代码
        trade_date: 交易日期
        price: 价格
        percent: 筹码比例
    """
    key = f"cyq_chips_{ts_code}_{trade_date}"

    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("chip_analysis"))
        if cached_df is not None and not cached_df.empty:
            return cached_df

    try:
        _rate_limit()
        df = pro.cyq_chips(ts_code=ts_code, trade_date=trade_date)
        _save_df_cache(key, df)
        return df
    except Exception as e:
        print(f"[cyq_chips] 获取失败: {e}")
        return _get_any_cached_df(key)


def stk_surv(ts_code: str = None, trade_date: str = None, start_date: str = None,
            end_date: str = None, force: bool = False) -> pd.DataFrame:
    """获取机构调研数据（5000积分专属）

    接口：stk_surv
    描述：获取上市公司机构调研数据
    数据历史：2008年至今
    限量：单次请求返回最大1000行数据
    积分：需要5000积分

    参数:
        ts_code: 股票代码
        trade_date: 调研日期
        start_date: 开始日期
        end_date: 结束日期
        force: 是否强制刷新缓存

    返回字段:
        ts_code: TS代码
        trade_date: 调研日期
        visit_org: 调研机构
        org_type: 机构类型
        visit_person: 接待人
        visit_way: 调研方式
        main_topic: 调研主题
        summary: 调研要点
    """
    key = _get_cache_key("stk_surv", ts_code=ts_code, trade_date=trade_date,
                         start_date=start_date, end_date=end_date)

    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("institution"))
        if cached_df is not None and not cached_df.empty:
            return cached_df

    try:
        _rate_limit()
        params = {}
        if ts_code: params["ts_code"] = ts_code
        if trade_date: params["trade_date"] = trade_date
        if start_date: params["start_date"] = start_date
        if end_date: params["end_date"] = end_date

        df = pro.stk_surv(**params)
        _save_df_cache(key, df)
        return df
    except Exception as e:
        print(f"[stk_surv] 获取失败: {e}")
        return _get_any_cached_df(key)


def ccass_hold(ts_code: str, trade_date: str = None, start_date: str = None,
               end_date: str = None, force: bool = False) -> pd.DataFrame:
    """获取港资持股数据（5000积分专属）

    接口：ccass_hold
    描述：获取沪深港通中港资持股数据
    数据历史：2014年至今
    限量：单次请求返回最大10000行数据
    积分：需要5000积分

    参数:
        ts_code: 股票代码（必选）
        trade_date: 交易日期
        start_date: 开始日期
        end_date: 结束日期
        force: 是否强制刷新缓存

    返回字段:
        ts_code: TS代码
        trade_date: 交易日期
        shareholding: 持股数量
        shareholding_ratio: 持股比例
        mock_shareholding: 模拟持股数量
        mock_shareholding_ratio: 模拟持股比例
    """
    key = _get_cache_key("ccass_hold", ts_code=ts_code, trade_date=trade_date,
                         start_date=start_date, end_date=end_date)

    if not force:
        cached_df = _get_cached_df(key, ttl_seconds=get_dynamic_ttl("northbound"))
        if cached_df is not None and not cached_df.empty:
            return cached_df

    try:
        _rate_limit()
        params = {"ts_code": ts_code}
        if trade_date: params["trade_date"] = trade_date
        if start_date: params["start_date"] = start_date
        if end_date: params["end_date"] = end_date

        df = pro.ccass_hold(**params)
        _save_df_cache(key, df)
        return df
    except Exception as e:
        print(f"[ccass_hold] 获取失败: {e}")
        return _get_any_cached_df(key)
