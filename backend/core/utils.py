"""
公共工具函数模块
提供项目中常用的工具函数，避免代码重复
"""
import math
import json
import logging
from typing import Any, Dict, List
import numpy as np
import pandas as pd
from logging.handlers import RotatingFileHandler
import os


def clean_nan_values(obj: Any) -> Any:
    """
    递归清理对象中的 NaN、Inf 等无效浮点数，替换为 None

    Args:
        obj: 需要清理的对象（dict, list, float等）

    Returns:
        清理后的对象
    """
    if isinstance(obj, dict):
        return {k: clean_nan_values(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nan_values(item) for item in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, (np.integer, np.floating)):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return obj.item()
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif pd.isna(obj):
        return None
    return obj


class CustomJSONEncoder(json.JSONEncoder):
    """自定义JSON编码器，处理NaN、inf、numpy类型等特殊值"""

    def default(self, obj):
        if isinstance(obj, (np.integer, np.floating)):
            if np.isnan(obj) or np.isinf(obj):
                return None
            return obj.item()
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif pd.isna(obj) or (isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj))):
            return None
        return super().default(obj)


def setup_logger(
    name: str,
    log_file: str = None,
    level: str = "INFO",
    max_bytes: int = 10485760,  # 10MB
    backup_count: int = 5,
    format_string: str = None
) -> logging.Logger:
    """
    配置日志记录器，支持文件轮转

    Args:
        name: 日志记录器名称
        log_file: 日志文件路径
        level: 日志级别
        max_bytes: 单个日志文件最大字节数
        backup_count: 保留的备份文件数量
        format_string: 日志格式字符串

    Returns:
        配置好的Logger对象
    """
    logger = logging.getLogger(name)

    # 如果已经配置过，直接返回
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if format_string is None:
        format_string = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"

    formatter = logging.Formatter(format_string)

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件处理器（带轮转）
    if log_file:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def safe_float(value: Any, default: float = 0.0) -> float:
    """
    安全地将值转换为float，处理NaN和None

    Args:
        value: 要转换的值
        default: 默认值

    Returns:
        转换后的float值
    """
    if value is None or pd.isna(value):
        return default
    try:
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            return default
        return result
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """
    安全地将值转换为int

    Args:
        value: 要转换的值
        default: 默认值

    Returns:
        转换后的int值
    """
    if value is None or pd.isna(value):
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_get(data: Dict, *keys, default=None) -> Any:
    """
    安全获取嵌套字典值

    Args:
        data: 字典数据
        *keys: 键路径
        default: 默认值

    Returns:
        获取到的值或默认值
    """
    if not isinstance(data, dict):
        return default

    for key in keys:
        if isinstance(data, dict):
            data = data.get(key)
            if data is None:
                return default
        else:
            return default

    return data if data is not None else default


def format_number(num: float, precision: int = 2, unit: str = "") -> str:
    """
    格式化数字，添加千分位分隔符和单位

    Args:
        num: 数字
        precision: 小数位数
        unit: 单位

    Returns:
        格式化后的字符串
    """
    if num is None or pd.isna(num):
        return "N/A"

    try:
        formatted = f"{num:,.{precision}f}"
        if unit:
            formatted += unit
        return formatted
    except (ValueError, TypeError):
        return "N/A"


def format_percentage(num: float, precision: int = 2) -> str:
    """
    格式化百分比

    Args:
        num: 数字（如0.1234表示12.34%）
        precision: 小数位数

    Returns:
        格式化后的百分比字符串
    """
    if num is None or pd.isna(num):
        return "N/A"

    try:
        return f"{num * 100:.{precision}f}%"
    except (ValueError, TypeError):
        return "N/A"


def ensure_dir(path: str) -> None:
    """
    确保目录存在，不存在则创建

    Args:
        path: 目录路径
    """
    os.makedirs(path, exist_ok=True)


def clean_cache_files(cache_dir: str, max_age_days: int = 7) -> int:
    """
    清理超过指定天数的缓存文件

    Args:
        cache_dir: 缓存目录
        max_age_days: 最大保留天数

    Returns:
        清理的文件数量
    """
    import time
    from pathlib import Path

    if not os.path.exists(cache_dir):
        return 0

    current_time = time.time()
    max_age_seconds = max_age_days * 86400
    cleaned_count = 0

    for file_path in Path(cache_dir).rglob('*'):
        if file_path.is_file():
            file_age = current_time - file_path.stat().st_mtime
            if file_age > max_age_seconds:
                try:
                    file_path.unlink()
                    cleaned_count += 1
                except Exception:
                    pass

    return cleaned_count


def retry_on_exception(
    func,
    max_retries: int = 3,
    delay: float = 1.0,
    exceptions: tuple = (Exception,)
):
    """
    重试装饰器，在异常时重试

    Args:
        func: 要执行的函数
        max_retries: 最大重试次数
        delay: 重试间隔（秒）
        exceptions: 要捕获的异常类型

    Returns:
        装饰后的函数
    """
    import time
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        last_exception = None
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                last_exception = e
                if attempt < max_retries - 1:
                    time.sleep(delay)
        raise last_exception

    return wrapper
