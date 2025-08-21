"""
分层缓存策略 - 区分快慢变数据
"""
import os
import json
import time
import pickle
import hashlib
from typing import Any, Optional, Dict, Callable
from functools import wraps
from datetime import datetime, timedelta
import pandas as pd

class CacheLevel:
    """缓存级别定义"""
    # 快变数据 (1-5分钟)
    REALTIME = 60           # 1分钟 - 实时行情
    QUICK = 300            # 5分钟 - 资金流向、新闻
    
    # 中速变化 (15分钟-1小时)
    MEDIUM = 900           # 15分钟 - 日内指标
    HOURLY = 3600          # 1小时 - 公告、研报
    
    # 慢变数据 (1天-1周)
    DAILY = 86400          # 1天 - 财务数据、基本面
    WEEKLY = 604800        # 1周 - 宏观数据
    MONTHLY = 2592000      # 30天 - 历史数据

class SmartCache:
    """智能分层缓存"""
    
    def __init__(self, cache_dir: str = None):
        self.cache_dir = cache_dir or os.path.join(
            os.path.dirname(__file__), '../.cache'
        )
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # 内存缓存（一级缓存）
        self._memory_cache: Dict[str, Dict] = {}
        
        # 重试策略配置
        self.retry_config = {
            'max_retries': 3,
            'initial_delay': 1,  # 秒
            'backoff_factor': 2,  # 指数退避因子
            'max_delay': 30      # 最大延迟
        }
    
    def _make_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """生成缓存键"""
        key_data = f"{prefix}:{args}:{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_file_path(self, key: str, level: str) -> str:
        """获取缓存文件路径"""
        level_dir = os.path.join(self.cache_dir, level)
        os.makedirs(level_dir, exist_ok=True)
        return os.path.join(level_dir, f"{key}.pkl")
    
    def get(self, key: str, level: int = CacheLevel.QUICK) -> Optional[Any]:
        """
        获取缓存数据
        优先级: 内存缓存 > 磁盘缓存
        """
        # 1. 检查内存缓存
        if key in self._memory_cache:
            cache_data = self._memory_cache[key]
            if time.time() - cache_data['timestamp'] < level:
                return cache_data['data']
            else:
                # 过期，清理内存缓存
                del self._memory_cache[key]
        
        # 2. 检查磁盘缓存
        level_name = self._get_level_name(level)
        file_path = self._get_file_path(key, level_name)
        
        if os.path.exists(file_path):
            try:
                with open(file_path, 'rb') as f:
                    cache_data = pickle.load(f)
                    if time.time() - cache_data['timestamp'] < level:
                        # 加载到内存缓存
                        self._memory_cache[key] = cache_data
                        return cache_data['data']
                    else:
                        # 过期，删除文件
                        os.remove(file_path)
            except Exception as e:
                print(f"[缓存] 读取失败: {e}")
        
        return None
    
    def set(self, key: str, data: Any, level: int = CacheLevel.QUICK):
        """设置缓存数据"""
        cache_data = {
            'data': data,
            'timestamp': time.time(),
            'level': level
        }
        
        # 1. 写入内存缓存
        self._memory_cache[key] = cache_data
        
        # 2. 写入磁盘缓存（慢变数据才写磁盘）
        if level >= CacheLevel.HOURLY:
            level_name = self._get_level_name(level)
            file_path = self._get_file_path(key, level_name)
            try:
                with open(file_path, 'wb') as f:
                    pickle.dump(cache_data, f)
            except Exception as e:
                print(f"[缓存] 写入失败: {e}")
    
    def _get_level_name(self, level: int) -> str:
        """获取缓存级别名称"""
        if level <= CacheLevel.REALTIME:
            return "realtime"
        elif level <= CacheLevel.QUICK:
            return "quick"
        elif level <= CacheLevel.MEDIUM:
            return "medium"
        elif level <= CacheLevel.HOURLY:
            return "hourly"
        elif level <= CacheLevel.DAILY:
            return "daily"
        elif level <= CacheLevel.WEEKLY:
            return "weekly"
        else:
            return "monthly"
    
    def clear_expired(self):
        """清理过期缓存"""
        # 清理内存缓存
        expired_keys = []
        for key, cache_data in self._memory_cache.items():
            if time.time() - cache_data['timestamp'] > cache_data['level']:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._memory_cache[key]
        
        # 清理磁盘缓存
        for level_name in os.listdir(self.cache_dir):
            level_dir = os.path.join(self.cache_dir, level_name)
            if not os.path.isdir(level_dir):
                continue
            
            for file_name in os.listdir(level_dir):
                file_path = os.path.join(level_dir, file_name)
                try:
                    with open(file_path, 'rb') as f:
                        cache_data = pickle.load(f)
                        if time.time() - cache_data['timestamp'] > cache_data['level']:
                            os.remove(file_path)
                except:
                    # 损坏的缓存文件，直接删除
                    os.remove(file_path)
    
    def invalidate(self, pattern: str = None):
        """使缓存失效"""
        if pattern:
            # 按模式清理
            keys_to_delete = [k for k in self._memory_cache.keys() if pattern in k]
            for key in keys_to_delete:
                del self._memory_cache[key]
        else:
            # 清理所有
            self._memory_cache.clear()

# 装饰器工厂
def cached(level: int = CacheLevel.QUICK):
    """
    缓存装饰器
    
    使用示例:
    @cached(level=CacheLevel.DAILY)
    def get_financial_data(ts_code):
        return fetch_from_api(ts_code)
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{func.__module__}.{func.__name__}"
            cache_key = hashlib.md5(
                f"{cache_key}:{args}:{sorted(kwargs.items())}".encode()
            ).hexdigest()
            
            # 尝试从缓存获取
            result = _cache.get(cache_key, level)
            if result is not None:
                return result
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 保存到缓存
            if result is not None:
                _cache.set(cache_key, result, level)
            
            return result
        return wrapper
    return decorator

def with_retry(func: Callable):
    """
    失败重试装饰器（指数退避）
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        max_retries = 3
        delay = 1
        
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"[重试] {func.__name__} 失败{max_retries}次: {e}")
                    raise
                
                wait_time = delay * (2 ** attempt)  # 指数退避
                print(f"[重试] {func.__name__} 第{attempt+1}次失败，{wait_time}秒后重试")
                time.sleep(wait_time)
        
        return None
    return wrapper

# 缓存分类映射
CACHE_CATEGORY = {
    # 快变数据
    'daily': CacheLevel.REALTIME,       # 日线行情
    'moneyflow': CacheLevel.REALTIME,   # 资金流向
    'news': CacheLevel.QUICK,           # 新闻
    'anns': CacheLevel.QUICK,           # 公告
    
    # 中速数据
    'daily_basic': CacheLevel.MEDIUM,   # 每日指标
    'margin': CacheLevel.MEDIUM,        # 融资融券
    
    # 慢变数据
    'stock_basic': CacheLevel.DAILY,    # 股票列表
    'income': CacheLevel.DAILY,         # 利润表
    'balancesheet': CacheLevel.DAILY,   # 资产负债表
    'cashflow': CacheLevel.DAILY,       # 现金流量表
    'fina_indicator': CacheLevel.DAILY, # 财务指标
    
    # 极慢数据
    'concept': CacheLevel.WEEKLY,       # 概念板块
    'cn_gdp': CacheLevel.WEEKLY,        # GDP
    'cn_cpi': CacheLevel.WEEKLY,        # CPI
    'cn_pmi': CacheLevel.WEEKLY,        # PMI
}

def get_cache_level(api_name: str) -> int:
    """根据API名称获取缓存级别"""
    return CACHE_CATEGORY.get(api_name, CacheLevel.QUICK)

# 全局缓存实例
_cache = SmartCache()

def get_smart_cache() -> SmartCache:
    """获取智能缓存实例"""
    return _cache