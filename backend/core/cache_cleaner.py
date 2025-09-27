"""
缓存清理工具 - 清理过期的实时数据缓存
确保股票分析使用最新的市场数据
"""
import os
import time
import glob
from datetime import datetime, timedelta
from pathlib import Path

# 缓存目录
CACHE_DIR = Path.home() / ".qsl_cache"

def clean_stale_cache(max_age_hours: int = 6) -> int:
    """
    清理过期的缓存文件
    
    Args:
        max_age_hours: 缓存文件最大年龄（小时），超过此时间的文件将被删除
        
    Returns:
        清理的文件数量
    """
    if not CACHE_DIR.exists():
        return 0
    
    current_time = time.time()
    cutoff_time = current_time - (max_age_hours * 3600)
    cleaned_count = 0
    
    # 需要清理的缓存类型（实时数据）
    real_time_patterns = [
        "daily_*.pkl",           # 日线数据
        "daily_basic_*.pkl",     # 每日指标
        "moneyflow_*.pkl",       # 资金流向
        "margin_detail_*.pkl",   # 融资融券
        "top_list_*.pkl",        # 龙虎榜
        "stk_limit_*.pkl",       # 涨跌停
        "news_*.pkl",            # 新闻数据
        "major_news_*.pkl",      # 重大新闻
    ]
    
    for pattern in real_time_patterns:
        cache_files = glob.glob(str(CACHE_DIR / pattern))
        for file_path in cache_files:
            try:
                file_mtime = os.path.getmtime(file_path)
                if file_mtime < cutoff_time:
                    os.remove(file_path)
                    cleaned_count += 1
                    print(f"[缓存清理] 删除过期文件: {os.path.basename(file_path)}")
            except Exception as e:
                print(f"[缓存清理] 清理文件失败 {file_path}: {e}")
    
    return cleaned_count


def clean_specific_stock_cache(ts_code: str) -> int:
    """
    清理特定股票的所有缓存
    
    Args:
        ts_code: 股票代码
        
    Returns:
        清理的文件数量
    """
    if not CACHE_DIR.exists():
        return 0
    
    cleaned_count = 0
    
    # 查找包含特定股票代码的缓存文件
    pattern = f"*{ts_code}*.pkl"
    cache_files = glob.glob(str(CACHE_DIR / pattern))
    
    for file_path in cache_files:
        try:
            os.remove(file_path)
            cleaned_count += 1
            print(f"[缓存清理] 删除股票缓存: {os.path.basename(file_path)}")
        except Exception as e:
            print(f"[缓存清理] 清理股票缓存失败 {file_path}: {e}")
    
    return cleaned_count


def get_cache_stats() -> dict:
    """
    获取缓存统计信息
    
    Returns:
        缓存统计数据
    """
    if not CACHE_DIR.exists():
        return {"total_files": 0, "total_size": 0, "oldest_file": None, "newest_file": None}
    
    cache_files = list(CACHE_DIR.glob("*.pkl"))
    
    if not cache_files:
        return {"total_files": 0, "total_size": 0, "oldest_file": None, "newest_file": None}
    
    total_size = sum(f.stat().st_size for f in cache_files)
    
    # 获取最老和最新的文件
    file_times = [(f, f.stat().st_mtime) for f in cache_files]
    oldest_file = min(file_times, key=lambda x: x[1])
    newest_file = max(file_times, key=lambda x: x[1])
    
    return {
        "total_files": len(cache_files),
        "total_size": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "oldest_file": {
            "name": oldest_file[0].name,
            "date": datetime.fromtimestamp(oldest_file[1]).strftime("%Y-%m-%d %H:%M:%S")
        },
        "newest_file": {
            "name": newest_file[0].name,
            "date": datetime.fromtimestamp(newest_file[1]).strftime("%Y-%m-%d %H:%M:%S")
        }
    }


def ensure_fresh_data(ts_code: str = None, force: bool = False) -> dict:
    """
    确保使用新鲜数据的预处理函数
    
    Args:
        ts_code: 股票代码，如果提供则清理该股票的缓存
        force: 是否强制清理所有实时数据缓存
        
    Returns:
        操作结果
    """
    result = {"cleaned_files": 0, "action": "none"}
    
    if force:
        # 强制清理所有实时数据缓存
        result["cleaned_files"] = clean_stale_cache(max_age_hours=0)
        result["action"] = "force_clean_all"
    elif ts_code:
        # 清理特定股票的缓存
        result["cleaned_files"] = clean_specific_stock_cache(ts_code)
        result["action"] = f"clean_stock_{ts_code}"
    else:
        # 智能清理：在交易时间更严格，非交易时间放宽
        from datetime import datetime, time
        
        now = datetime.now()
        current_time = now.time()
        
        # 判断是否在交易时间内（9:30-15:00）
        trading_start = time(9, 30)
        trading_end = time(15, 0)
        is_trading_hours = trading_start <= current_time <= trading_end
        
        # 判断是否是工作日
        is_weekday = now.weekday() < 5
        
        if is_trading_hours and is_weekday:
            # 交易时间内：更严格的缓存策略（2小时）
            max_age = 2
        elif is_weekday:
            # 工作日非交易时间：中等缓存策略（4小时）
            max_age = 4
        else:
            # 周末：宽松缓存策略（8小时）
            max_age = 8
            
        result["cleaned_files"] = clean_stale_cache(max_age_hours=max_age)
        result["action"] = f"smart_clean_{max_age}h"
    
    return result


if __name__ == "__main__":
    # 命令行工具测试
    print("=== 缓存统计 ===")
    stats = get_cache_stats()
    print(f"总文件数: {stats['total_files']}")
    print(f"总大小: {stats['total_size_mb']} MB")
    if stats['oldest_file']:
        print(f"最老文件: {stats['oldest_file']['name']} ({stats['oldest_file']['date']})")
    if stats['newest_file']:
        print(f"最新文件: {stats['newest_file']['name']} ({stats['newest_file']['date']})")
    
    print("\n=== 清理过期缓存 ===")
    cleaned = clean_stale_cache(max_age_hours=6)
    print(f"清理了 {cleaned} 个过期文件")