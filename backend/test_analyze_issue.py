"""测试分析流程数据获取问题"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.analyze import resolve_by_name, run_pipeline
from core.tushare_client import daily
import json

def test_analyze_step_by_step(stock_name):
    """分步测试分析流程"""
    print(f"=== 测试分析流程：{stock_name} ===\n")

    # Step 1: 解析股票
    print("Step 1: 解析股票名称...")
    stock_info = resolve_by_name(stock_name, force=True)
    if not stock_info:
        print(f"✗ 无法解析股票：{stock_name}")
        return None

    print(f"✓ 解析成功: {stock_info['name']} ({stock_info['ts_code']})")

    # Step 2: 获取日线数据
    print(f"\nStep 2: 获取日线数据...")
    ts_code = stock_info['ts_code']

    # 测试不同时间范围
    test_ranges = [
        ('20250101', '20250125', '2025年1月'),
        ('20241201', '20241231', '2024年12月'),
        ('20240101', '20241231', '2024全年'),
    ]

    for start_date, end_date, desc in test_ranges:
        print(f"  测试 {desc} ({start_date} - {end_date})...")
        try:
            df = daily(ts_code, start_date=start_date, end_date=end_date, force=True)
            if df is not None and not df.empty:
                print(f"    ✓ 获取 {len(df)} 条数据")
                print(f"      最早: {df['trade_date'].min()}, 最新: {df['trade_date'].max()}")
                break
            else:
                print(f"    ✗ 返回空数据")
        except Exception as e:
            print(f"    ✗ 错误: {e}")

    # Step 3: 完整分析流程
    print(f"\nStep 3: 运行完整分析流程...")

    progress_log = []

    def progress_callback(step, payload):
        progress_log.append({'step': step, 'payload': payload})
        # 只打印重要步骤
        if step in ['resolve:done', 'fetch:parallel:done', 'compute:scorecard', 'complete']:
            print(f"  [{step}]")
            if step == 'fetch:parallel:done' and payload:
                print(f"    价格数据: {payload.get('px_rows', 0)} 行")
                print(f"    基本面: {len(payload.get('fundamental_keys', []))} 项")
                print(f"    宏观: {len(payload.get('macro_keys', []))} 项")

    try:
        result = run_pipeline(stock_name, force=True, progress=progress_callback)

        if result:
            print("\n✓ 分析完成")

            # 检查关键数据
            print("\n数据完整性检查:")

            # 价格数据
            prices = result.get('prices', [])
            print(f"  价格数据: {len(prices)} 条 {'✓' if prices else '✗'}")

            # 技术指标
            tech = result.get('tech', {})
            print(f"  技术指标: {len(tech)} 项 {'✓' if tech else '✗'}")

            # 基本面数据
            fundamental = result.get('fundamental', {})
            print(f"  基本面数据: {len(fundamental)} 类 {'✓' if fundamental else '✗'}")

            # 新闻数据
            news = result.get('news', {})
            news_count = news.get('total_count', 0) if news else 0
            print(f"  新闻数据: {news_count} 条 {'✓' if news_count > 0 else '✗'}")

            # 如果价格数据为空，诊断原因
            if not prices:
                print("\n⚠️ 价格数据为空，可能原因：")
                print("1. 检查进度日志中的fetch:parallel步骤")
                for log in progress_log:
                    if 'fetch:parallel' in log['step']:
                        print(f"   {log['step']}: {log.get('payload', {})}")

                print("\n2. 尝试直接获取日线数据...")
                try:
                    from datetime import datetime, timedelta
                    end = datetime.now()
                    start = end - timedelta(days=30)

                    df_test = daily(
                        ts_code,
                        start_date=start.strftime('%Y%m%d'),
                        end_date=end.strftime('%Y%m%d'),
                        force=True
                    )
                    if df_test is not None and not df_test.empty:
                        print(f"   直接调用成功，获取 {len(df_test)} 条")
                        print(f"   这说明run_pipeline中的日期范围可能有问题")
                    else:
                        print(f"   直接调用也返回空数据")
                except Exception as e:
                    print(f"   直接调用失败: {e}")

            return result
        else:
            print("✗ 分析返回空结果")
            return None

    except Exception as e:
        print(f"✗ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """主测试函数"""
    test_stocks = ['贵州茅台', '比亚迪', '宁德时代']

    for stock in test_stocks:
        result = test_analyze_step_by_step(stock)
        print("\n" + "="*50 + "\n")

        if result and not result.get('prices'):
            print(f"⚠️ {stock} 分析成功但价格数据为空！")

    print("测试完成")


if __name__ == "__main__":
    main()