#!/usr/bin/env python3
import os
import sys
import time
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.tushare_client import pro
from datetime import datetime

def test_basic_data():
    """测试基础数据获取"""
    print("=" * 50)
    print("测试Tushare数据获取")
    print("=" * 50)

    # 测试token
    print(f"\n1. Tushare Token: {os.getenv('TUSHARE_TOKEN')[:10]}...")

    # 获取交易日期
    trade_date = datetime.now().strftime('%Y%m%d')
    print(f"\n2. 当前日期: {trade_date}")

    # 测试获取日线数据
    print(f"\n3. 测试获取贵州茅台(600519.SH)日线数据...")
    try:
        df_daily = pro.daily(ts_code='600519.SH', start_date='20250920', end_date=trade_date)
        if df_daily is not None and not df_daily.empty:
            print(f"   ✓ 获取到 {len(df_daily)} 条日线数据")
            print(f"   最新数据: {df_daily.iloc[0]['trade_date']} 收盘价: {df_daily.iloc[0]['close']}")
        else:
            print("   ✗ 未获取到数据")
    except Exception as e:
        print(f"   ✗ 错误: {e}")

    # 测试获取实时行情
    print(f"\n4. 测试获取实时行情...")
    try:
        df_basic = pro.daily_basic(ts_code='600519.SH', trade_date=trade_date)
        if df_basic is not None and not df_basic.empty:
            print(f"   ✓ 获取到实时数据")
            print(f"   PE: {df_basic.iloc[0]['pe']}, PB: {df_basic.iloc[0]['pb']}")
        else:
            print("   ✗ 未获取到数据")
    except Exception as e:
        print(f"   ✗ 错误: {e}")

    # 测试获取资金流向
    print(f"\n5. 测试获取资金流向...")
    try:
        df_money = pro.moneyflow(ts_code='600519.SH', start_date='20250920', end_date=trade_date)
        if df_money is not None and not df_money.empty:
            print(f"   ✓ 获取到 {len(df_money)} 条资金流向数据")
        else:
            print("   ✗ 未获取到数据")
    except Exception as e:
        print(f"   ✗ 错误: {e}")

    # 测试获取财务数据
    print(f"\n6. 测试获取财务数据...")
    try:
        df_income = pro.income(ts_code='600519.SH', period='20240930')
        if df_income is not None and not df_income.empty:
            print(f"   ✓ 获取到财务数据")
            print(f"   营收: {df_income.iloc[0]['total_revenue']/1e8:.2f}亿")
        else:
            print("   ✗ 未获取到数据")
    except Exception as e:
        print(f"   ✗ 错误: {e}")

    # 测试获取北向资金
    print(f"\n7. 测试获取北向资金...")
    try:
        df_north = pro.moneyflow_hsgt(trade_date=trade_date)
        if df_north is not None and not df_north.empty:
            print(f"   ✓ 获取到北向资金数据")
            print(f"   净流入: {df_north.iloc[0]['north_money']/100:.2f}亿")
        else:
            print("   ✗ 未获取到北向资金数据（可能需要更高权限）")
    except Exception as e:
        print(f"   ✗ 错误: {e}")

    print("\n" + "=" * 50)

if __name__ == "__main__":
    test_basic_data()