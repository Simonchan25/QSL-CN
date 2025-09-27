#!/usr/bin/env python3
"""
快速验证测试
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=== 快速数据验证 ===\n")

# 1. 测试概念映射
print("1. 测试概念映射:")
try:
    from core.concept_manager import get_concept_manager
    cm = get_concept_manager()

    # 测试脑机概念
    stocks = cm.find_stocks_by_concept("脑机")
    print(f"   '脑机' 找到 {len(stocks)} 只股票")
    if stocks:
        print(f"   示例: {stocks[:3]}")
    else:
        print("   ❌ 未找到脑机相关股票")

    # 测试新能源
    stocks = cm.find_stocks_by_concept("新能源")
    print(f"   '新能源' 找到 {len(stocks)} 只股票")

except Exception as e:
    print(f"   ❌ 错误: {e}")

# 2. 测试数据实时性
print("\n2. 测试数据实时性:")
try:
    from core.tushare_client import daily_basic
    from datetime import datetime

    # 获取今日数据（使用force=True强制刷新）
    today = datetime.now().strftime('%Y%m%d')
    df = daily_basic(trade_date=today, force=True)

    if df is not None and not df.empty:
        print(f"   ✓ 获取到 {len(df)} 条数据")
        # 检查是否有今日数据
        if 'trade_date' in df.columns:
            dates = df['trade_date'].unique()
            print(f"   数据日期: {dates[0] if len(dates) > 0 else '无'}")
    else:
        print("   ⚠️ 无法获取今日数据（可能非交易日）")

except Exception as e:
    print(f"   ❌ 错误: {e}")

# 3. 检查缓存设置
print("\n3. 缓存时间设置:")
try:
    from core.cache_config import CACHE_TTL_CONFIG

    key_data_types = {
        "stock_realtime": "实时股票",
        "hot_stocks": "热点股票",
        "concept": "概念板块",
        "daily_basic": "日线数据"
    }

    for key, name in key_data_types.items():
        ttl = CACHE_TTL_CONFIG.get(key, 0)
        hours = ttl / 3600
        print(f"   {name}: {hours:.1f} 小时")

except Exception as e:
    print(f"   ❌ 错误: {e}")

# 4. 检查文件重复
print("\n4. 重复文件检查:")
import glob
duplicates = {
    "热点分析": ["core/hotspot.py", "core/enhanced_hotspot_analyzer.py"],
    "分析器": ["core/analyze.py", "core/practical_analyzer.py", "core/market_ai_analyzer.py"]
}

for func, files in duplicates.items():
    existing = [f for f in files if os.path.exists(f)]
    if len(existing) > 1:
        print(f"   ⚠️ {func} 有 {len(existing)} 个文件:")
        for f in existing:
            size = os.path.getsize(f) / 1024
            print(f"      - {os.path.basename(f)} ({size:.1f}KB)")

print("\n=== 验证完成 ===")

# 5. 总结问题
print("\n发现的问题:")
print("1. 概念映射可能不准确（需要检查实际匹配结果）")
print("2. 概念数据缓存24小时太长，影响实时性")
print("3. 存在功能重复的文件")
print("4. 需要确认数据是否来自API还是缓存")