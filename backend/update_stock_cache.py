#!/usr/bin/env python3
"""
股票缓存更新工具
用法: python update_stock_cache.py [--force] [--info]
"""
import sys
import argparse
from pathlib import Path

# 添加当前目录到Python路径
sys.path.append(str(Path(__file__).parent))

from core.stock_cache_manager import get_cache_manager


def main():
    parser = argparse.ArgumentParser(description='股票缓存管理工具')
    parser.add_argument('--force', '-f', action='store_true', 
                       help='强制更新缓存（忽略时间检查）')
    parser.add_argument('--info', '-i', action='store_true', 
                       help='显示缓存信息')
    
    args = parser.parse_args()
    
    cache_manager = get_cache_manager()
    
    if args.info:
        print("=== 股票缓存信息 ===")
        info = cache_manager.get_cache_info()
        if info['status'] == 'ok':
            print(f"更新时间: {info['update_time']}")
            print(f"股票总数: {info['total_count']}")
            print(f"缓存状态: {'新鲜' if info['is_fresh'] else '过期'}")
        else:
            print(f"状态: {info['status']}")
            print(f"信息: {info.get('message', 'N/A')}")
        return
    
    print("开始更新股票缓存...")
    success = cache_manager.update_stock_cache(force=args.force)
    
    if success:
        print("✅ 股票缓存更新成功!")
        # 显示更新后的信息
        info = cache_manager.get_cache_info()
        if info['status'] == 'ok':
            print(f"共缓存 {info['total_count']} 只股票")
    else:
        print("❌ 股票缓存更新失败!")
        sys.exit(1)


if __name__ == '__main__':
    main()