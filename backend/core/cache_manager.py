"""
统一缓存管理器 - 提高系统性能
"""
import json
import os
import time
import pickle
import hashlib
from typing import Any, Optional, Callable, Dict
from functools import wraps
from datetime import datetime, timedelta
import threading


class CacheManager:
    """统一缓存管理器"""

    def __init__(self, base_dir: str = ".cache"):
        self.base_dir = base_dir
        self.ensure_cache_dir()
        self._lock = threading.Lock()
        self._memory_cache = {}  # 内存缓存
        self._cache_stats = {
            'hits': 0,
            'misses': 0,
            'saves': 0
        }

    def ensure_cache_dir(self):
        """确保缓存目录存在"""
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir, exist_ok=True)

        # 创建子目录
        for subdir in ['news', 'stock', 'market', 'hotspot', 'technical']:
            path = os.path.join(self.base_dir, subdir)
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)

    def _get_cache_key(self, key: str, namespace: str = 'default') -> str:
        """生成缓存键"""
        # 使用MD5确保文件名安全
        safe_key = hashlib.md5(key.encode()).hexdigest()
        return f"{namespace}_{safe_key}"

    def _get_cache_path(self, cache_key: str, namespace: str = 'default') -> str:
        """获取缓存文件路径"""
        return os.path.join(self.base_dir, namespace, f"{cache_key}.cache")

    def get(self, key: str, namespace: str = 'default',
            max_age: int = 3600) -> Optional[Any]:
        """
        获取缓存数据

        Args:
            key: 缓存键
            namespace: 命名空间
            max_age: 最大缓存时间（秒）

        Returns:
            缓存的数据，如果不存在或过期返回None
        """
        cache_key = self._get_cache_key(key, namespace)

        # 先检查内存缓存
        memory_key = f"{namespace}:{cache_key}"
        if memory_key in self._memory_cache:
            data, timestamp = self._memory_cache[memory_key]
            if time.time() - timestamp < max_age:
                self._cache_stats['hits'] += 1
                return data

        # 检查文件缓存
        cache_path = self._get_cache_path(cache_key, namespace)

        if os.path.exists(cache_path):
            try:
                mtime = os.path.getmtime(cache_path)
                if time.time() - mtime < max_age:
                    with open(cache_path, 'rb') as f:
                        data = pickle.load(f)

                    # 存入内存缓存
                    self._memory_cache[memory_key] = (data, mtime)
                    self._cache_stats['hits'] += 1
                    return data
            except Exception as e:
                print(f"[缓存] 读取失败 {key}: {e}")

        self._cache_stats['misses'] += 1
        return None

    def set(self, key: str, data: Any, namespace: str = 'default') -> bool:
        """
        设置缓存数据

        Args:
            key: 缓存键
            data: 要缓存的数据
            namespace: 命名空间

        Returns:
            是否成功
        """
        try:
            cache_key = self._get_cache_key(key, namespace)
            cache_path = self._get_cache_path(cache_key, namespace)

            # 确保目录存在
            cache_dir = os.path.dirname(cache_path)
            if not os.path.exists(cache_dir):
                os.makedirs(cache_dir, exist_ok=True)

            # 存入文件缓存
            with self._lock:
                with open(cache_path, 'wb') as f:
                    pickle.dump(data, f)

                # 同时存入内存缓存
                memory_key = f"{namespace}:{cache_key}"
                self._memory_cache[memory_key] = (data, time.time())

                # 限制内存缓存大小
                if len(self._memory_cache) > 100:
                    # 删除最旧的项
                    oldest = min(self._memory_cache.items(),
                                 key=lambda x: x[1][1])
                    del self._memory_cache[oldest[0]]

            self._cache_stats['saves'] += 1
            return True
        except Exception as e:
            print(f"[缓存] 保存失败 {key}: {e}")
            return False

    def delete(self, key: str, namespace: str = 'default') -> bool:
        """删除缓存"""
        cache_key = self._get_cache_key(key, namespace)
        cache_path = self._get_cache_path(cache_key, namespace)

        # 删除内存缓存
        memory_key = f"{namespace}:{cache_key}"
        if memory_key in self._memory_cache:
            del self._memory_cache[memory_key]

        # 删除文件缓存
        if os.path.exists(cache_path):
            try:
                os.remove(cache_path)
                return True
            except Exception:
                pass

        return False

    def clear_namespace(self, namespace: str) -> int:
        """清空指定命名空间的缓存"""
        count = 0
        namespace_dir = os.path.join(self.base_dir, namespace)

        if os.path.exists(namespace_dir):
            for file in os.listdir(namespace_dir):
                if file.endswith('.cache'):
                    try:
                        os.remove(os.path.join(namespace_dir, file))
                        count += 1
                    except Exception:
                        pass

        # 清理内存缓存
        keys_to_delete = [k for k in self._memory_cache.keys()
                          if k.startswith(f"{namespace}:")]
        for key in keys_to_delete:
            del self._memory_cache[key]

        return count

    def clean_expired(self, max_age: int = 86400) -> int:
        """清理过期缓存"""
        count = 0
        current_time = time.time()

        for root, dirs, files in os.walk(self.base_dir):
            for file in files:
                if file.endswith('.cache'):
                    file_path = os.path.join(root, file)
                    try:
                        mtime = os.path.getmtime(file_path)
                        if current_time - mtime > max_age:
                            os.remove(file_path)
                            count += 1
                    except Exception:
                        pass

        return count

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total_size = 0
        file_count = 0

        for root, dirs, files in os.walk(self.base_dir):
            for file in files:
                if file.endswith('.cache'):
                    file_count += 1
                    file_path = os.path.join(root, file)
                    try:
                        total_size += os.path.getsize(file_path)
                    except Exception:
                        pass

        return {
            'hits': self._cache_stats['hits'],
            'misses': self._cache_stats['misses'],
            'saves': self._cache_stats['saves'],
            'hit_rate': self._cache_stats['hits'] / max(1, self._cache_stats['hits'] + self._cache_stats['misses']),
            'memory_items': len(self._memory_cache),
            'file_count': file_count,
            'total_size_mb': round(total_size / 1024 / 1024, 2)
        }


# 全局缓存管理器实例
cache_manager = CacheManager()


def cached(namespace: str = 'default', ttl: int = 3600,
           key_func: Optional[Callable] = None):
    """
    缓存装饰器

    Args:
        namespace: 缓存命名空间
        ttl: 缓存时间（秒）
        key_func: 自定义键生成函数

    Example:
        @cached(namespace='stock', ttl=1800)
        def get_stock_info(ts_code: str):
            return fetch_from_api(ts_code)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # 默认使用函数名和参数生成键
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = "_".join(key_parts)

            # 尝试从缓存获取
            cached_data = cache_manager.get(cache_key, namespace, ttl)
            if cached_data is not None:
                print(f"[缓存命中] {func.__name__}")
                return cached_data

            # 执行函数
            result = func(*args, **kwargs)

            # 保存到缓存
            if result is not None:
                cache_manager.set(cache_key, result, namespace)

            return result
        return wrapper
    return decorator


def cache_key_with_date(prefix: str = ''):
    """生成带日期的缓存键"""
    today = datetime.now().strftime('%Y%m%d')
    return f"{prefix}_{today}" if prefix else today


# 专用缓存装饰器
def cache_stock_data(ttl: int = 1800):
    """股票数据缓存（30分钟）"""
    return cached(namespace='stock', ttl=ttl)


def cache_news_data(ttl: int = 900):
    """新闻数据缓存（15分钟）"""
    return cached(namespace='news', ttl=ttl)


def cache_market_data(ttl: int = 300):
    """市场数据缓存（5分钟）"""
    return cached(namespace='market', ttl=ttl)


def cache_hotspot_data(ttl: int = 3600):
    """热点数据缓存（1小时）"""
    return cached(namespace='hotspot', ttl=ttl)