#!/usr/bin/env python3
"""
TuShare 基础API快速测试
"""

import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

print("=" * 60)
print("TuShare 基础API快速测试")
print("=" * 60)

# 检查Token
token = os.getenv("TUSHARE_TOKEN")
if not token:
    print("❌ 未找到TUSHARE_TOKEN")
    sys.exit(1)

print(f"✅ Token已配置 (长度: {len(token)})")

import tushare as ts

# 测试1: 初始化
try:
    pro = ts.pro_api(token)
    print("✅ API初始化成功")
except Exception as e:
    print(f"❌ API初始化失败: {e}")
    sys.exit(1)

print("-" * 60)

# 测试2: 股票列表（最基础的接口）
print("\n测试 stock_basic (股票列表)...")
try:
    df = pro.stock_basic(fields="ts_code,name,area,industry,list_status")
    if df is not None and not df.empty:
        print(f"✅ 成功! 获取到 {len(df)} 只股票")
        print(f"   示例: {df.iloc[0]['name']} ({df.iloc[0]['ts_code']})")
    else:
        print("⚠️ 返回空数据")
except Exception as e:
    print(f"❌ 失败: {e}")

# 测试3: 日线数据
print("\n测试 daily (日线行情)...")
try:
    df = pro.daily(ts_code='000001.SZ', start_date='20250101', end_date='20250116')
    if df is not None and not df.empty:
        print(f"✅ 成功! 获取到 {len(df)} 条数据")
    else:
        print("⚠️ 返回空数据")
except Exception as e:
    error_msg = str(e)
    if "没有权限" in error_msg or "无权限" in error_msg:
        print(f"🔒 无权限访问")
    elif "每分钟最多访问" in error_msg:
        print(f"⏱️ 频率限制")
    else:
        print(f"❌ 失败: {e}")

# 测试4: 财务数据
print("\n测试 income (利润表)...")
try:
    df = pro.income(ts_code='000001.SZ', limit=1)
    if df is not None and not df.empty:
        print(f"✅ 成功! 获取到财务数据")
    else:
        print("⚠️ 返回空数据")
except Exception as e:
    error_msg = str(e)
    if "没有权限" in error_msg or "无权限" in error_msg:
        print(f"🔒 无权限访问")
    elif "每分钟最多访问" in error_msg:
        print(f"⏱️ 频率限制")
    else:
        print(f"❌ 失败: {e}")

# 测试5: 新闻接口
print("\n测试 news (新闻接口)...")
try:
    df = pro.news(src='sina', limit=1)
    if df is not None and not df.empty:
        print(f"✅ 成功! 新闻接口可用")
    else:
        print("⚠️ 返回空数据")
except Exception as e:
    error_msg = str(e)
    if "没有权限" in error_msg or "无权限" in error_msg:
        print(f"🔒 无权限访问 (需要单独购买)")
    else:
        print(f"❌ 失败: {e}")

# 测试6: 公告接口
print("\n测试 anns (公告接口)...")
try:
    df = pro.anns(ts_code='000001.SZ', limit=1)
    if df is not None and not df.empty:
        print(f"✅ 成功! 公告接口可用")
    else:
        print("⚠️ 返回空数据")
except Exception as e:
    error_msg = str(e)
    if "没有权限" in error_msg or "无权限" in error_msg:
        print(f"🔒 无权限访问 (需要权限)")
    else:
        print(f"❌ 失败: {e}")

print("\n" + "=" * 60)
print("测试完成!")
print("=" * 60)
print("\n提示:")
print("1. 如果基础接口（stock_basic, daily）都失败，请检查Token是否正确")
print("2. 新闻类接口通常需要单独购买权限")
print("3. 访问 https://tushare.pro 查看你的账户权限")