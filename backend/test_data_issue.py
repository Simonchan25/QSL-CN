"""测试数据获取问题"""
import os
import sys
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.tushare_client import pro, daily, stock_basic
from core.analyze import resolve_by_name, run_pipeline
import pandas as pd

def test_tushare_connection():
    """测试Tushare API连接"""
    print("=== 测试Tushare API连接 ===")
    try:
        # 获取用户信息
        token = os.getenv("TUSHARE_TOKEN", "e470904e8ad4c47e1d2f9dcdbe69bc98c5e7ecaa2adf66fdd64c3082")
        print(f"使用Token: {token[:10]}...")

        # 测试基础连接
        print("\n1. 测试股票列表获取...")
        df = pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name,area,industry,list_date')
        if df is not None and not df.empty:
            print(f"✓ 获取到 {len(df)} 只股票")
        else:
            print("✗ 获取股票列表失败")
            return False

        # 测试日线数据获取
        print("\n2. 测试日线数据获取 (贵州茅台)...")
        df_daily = daily('600519.SH', start_date='20240101', end_date='20241231', force=True)
        if df_daily is not None and not df_daily.empty:
            print(f"✓ 获取到 {len(df_daily)} 条日线数据")
            print(f"  最新数据: {df_daily['trade_date'].max() if 'trade_date' in df_daily else 'N/A'}")
        else:
            print("✗ 获取日线数据失败")

        return True

    except Exception as e:
        print(f"✗ API连接失败: {e}")
        return False


def test_resolve_stock(name):
    """测试股票解析"""
    print(f"\n=== 测试股票解析: {name} ===")
    try:
        result = resolve_by_name(name, force=True)
        if result:
            print(f"✓ 解析成功:")
            print(f"  名称: {result.get('name')}")
            print(f"  代码: {result.get('ts_code')}")
            print(f"  行业: {result.get('industry')}")
            print(f"  地区: {result.get('area')}")
            return result
        else:
            print(f"✗ 无法解析股票: {name}")
            return None
    except Exception as e:
        print(f"✗ 解析失败: {e}")
        return None


def test_pipeline(name):
    """测试完整分析流程"""
    print(f"\n=== 测试完整分析流程: {name} ===")

    # 进度跟踪
    progress_log = []

    def track_progress(step, payload):
        progress_log.append({'step': step, 'payload': payload})
        print(f"  [{step}] {payload.get('progress_desc', '')}")

    try:
        result = run_pipeline(name, force=True, progress=track_progress)

        if result:
            print(f"\n✓ 分析完成，数据摘要:")

            # 基础信息
            basic = result.get('basic', {})
            if basic:
                print(f"  股票: {basic.get('name')} ({basic.get('ts_code')})")

            # 价格数据
            prices = result.get('prices', [])
            if prices:
                print(f"  价格数据: {len(prices)} 条")
            else:
                print(f"  价格数据: 0 条 ⚠️")

            # 技术指标
            tech = result.get('tech', {})
            if tech:
                print(f"  技术指标: {len(tech)} 项")

            # 财务数据
            fundamental = result.get('fundamental', {})
            if fundamental:
                print(f"  财务数据: {len(fundamental)} 类")

            # 新闻数据
            news = result.get('news', {})
            if news:
                print(f"  新闻数量: {news.get('total_count', 0)}")

            # 评分
            scoring = result.get('scorecard', {})
            if scoring:
                print(f"  综合评分: {scoring.get('score_total', 'N/A')}")

            return result
        else:
            print("✗ 分析失败：返回空结果")
            return None

    except Exception as e:
        print(f"✗ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """主测试函数"""
    print("开始诊断数据获取问题...")
    print("-" * 50)

    # 1. 测试API连接
    if not test_tushare_connection():
        print("\n❌ Tushare API连接失败，请检查:")
        print("1. 网络连接是否正常")
        print("2. Tushare token是否有效")
        print("3. API权限是否足够（需要5000积分）")
        return

    # 2. 测试股票解析
    test_stocks = ['贵州茅台', '600519', '比亚迪', '002594']
    for stock in test_stocks:
        test_resolve_stock(stock)

    # 3. 测试完整流程
    print("\n" + "=" * 50)
    result = test_pipeline('贵州茅台')

    if result and not result.get('prices'):
        print("\n⚠️ 警告：虽然分析完成，但价格数据为空")
        print("可能原因：")
        print("1. 股票代码解析错误")
        print("2. 日期范围不正确")
        print("3. API权限不足")
        print("4. 缓存数据问题")

    print("\n" + "=" * 50)
    print("诊断完成")


if __name__ == "__main__":
    main()