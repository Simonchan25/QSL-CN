"""诊断前端显示0数据的问题"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.analyze_optimized import run_pipeline_optimized
from core.analyze import resolve_by_name
from core.tushare_client import daily
import json


def test_direct_data_fetch():
    """直接测试数据获取"""
    print("=== 直接测试数据获取 ===\n")

    test_stocks = [
        ('贵州茅台', '600519.SH'),
        ('比亚迪', '002594.SZ'),
    ]

    for name, ts_code in test_stocks:
        print(f"\n测试 {name} ({ts_code}):")

        # 1. 测试股票解析
        print(f"  1. 解析股票...")
        stock_info = resolve_by_name(name, force=True)
        if stock_info:
            print(f"     ✓ 解析成功: {stock_info['ts_code']}")
        else:
            print(f"     ✗ 解析失败")
            continue

        # 2. 测试直接获取日线数据
        print(f"  2. 直接获取日线数据...")
        try:
            from datetime import datetime, timedelta
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')

            df = daily(ts_code=ts_code, start_date=start_date, end_date=end_date, force=True)
            if df is not None and not df.empty:
                print(f"     ✓ 获取 {len(df)} 条数据")
                print(f"       最新日期: {df['trade_date'].max()}")
                print(f"       最新收盘: {df.iloc[0]['close']}")
            else:
                print(f"     ✗ 返回空数据")
        except Exception as e:
            print(f"     ✗ 错误: {e}")


def test_optimized_pipeline():
    """测试优化版流程（前端使用的）"""
    print("\n\n=== 测试优化版流程 ===\n")

    stock_name = '贵州茅台'
    print(f"分析股票: {stock_name}")

    # 追踪进度
    steps_log = []

    def progress_callback(step, data):
        steps_log.append((step, data))
        print(f"  [{step}]")

    try:
        # 使用优化版本（前端调用的）
        result = run_pipeline_optimized(
            stock_name,
            force=True,
            progress=progress_callback,
            timeout_seconds=10  # 设置较短超时以快速发现问题
        )

        if result:
            print("\n分析结果:")

            # 基础信息
            basic = result.get('basic', {})
            print(f"  基础信息: {basic.get('name', 'N/A')} ({basic.get('ts_code', 'N/A')})")

            # 技术数据
            tech = result.get('technical', {})
            if tech:
                print(f"  技术数据: {len(tech)} 项")
                if 'prices' in tech:
                    print(f"    价格数据: {len(tech['prices'])} 条")
                if 'latest_price' in tech:
                    print(f"    最新价格: {tech['latest_price']}")
            else:
                print(f"  技术数据: 无 ⚠️")

            # 基本面数据
            fundamental = result.get('fundamental', {})
            print(f"  基本面数据: {len(fundamental)} 项")

            # 新闻数据
            news = result.get('news', {})
            print(f"  新闻数据: {news.get('count', 0)} 条")

            # 评分
            score = result.get('score', {})
            print(f"  综合评分: {score.get('total', 'N/A')}")

            # 检查是否有错误
            for key in ['technical', 'fundamental', 'news', 'market']:
                if result.get(key, {}).get('error'):
                    print(f"  ⚠️ {key} 有错误: {result[key]['error']}")

            # 保存结果供分析
            with open('analyze_result.json', 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2, default=str)
            print("\n结果已保存到 analyze_result.json")

            return result
        else:
            print("✗ 分析返回空结果")
            return None

    except Exception as e:
        print(f"✗ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_api_response_format():
    """测试API响应格式"""
    print("\n\n=== 测试API响应格式 ===\n")

    # 模拟前端调用后端API
    import requests

    try:
        # 测试健康检查
        print("1. 测试健康检查...")
        resp = requests.get("http://localhost:8001/health", timeout=5)
        if resp.status_code == 200:
            print(f"   ✓ 健康检查正常: {resp.json()}")
        else:
            print(f"   ✗ 健康检查失败: {resp.status_code}")
    except Exception as e:
        print(f"   ✗ 无法连接后端: {e}")
        print("   请确保后端服务正在运行")
        return

    # 测试分析接口
    print("\n2. 测试分析接口...")
    try:
        # 使用analyze接口（POST）
        resp = requests.post(
            "http://localhost:8001/analyze",
            json={"name": "贵州茅台", "force": True},
            timeout=30
        )
        if resp.status_code == 200:
            data = resp.json()
            print(f"   ✓ 分析成功")
            print(f"     返回数据字段: {list(data.keys())}")

            # 检查关键字段
            if 'prices' in data:
                print(f"     价格数据: {len(data['prices'])} 条")
            else:
                print(f"     ⚠️ 没有prices字段")

            if 'json' in data:
                json_data = data['json']
                if 'prices' in json_data:
                    print(f"     JSON中价格数据: {len(json_data['prices'])} 条")
                else:
                    print(f"     ⚠️ JSON中没有prices字段")

            # 保存响应
            with open('api_response.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            print("\n   API响应已保存到 api_response.json")

        else:
            print(f"   ✗ 分析失败: {resp.status_code}")
            print(f"     错误: {resp.text}")

    except requests.Timeout:
        print(f"   ✗ 请求超时")
    except Exception as e:
        print(f"   ✗ 请求失败: {e}")


def main():
    """主函数"""
    print("开始诊断前端显示0数据的问题...")
    print("="*50)

    # 1. 测试直接数据获取
    test_direct_data_fetch()

    # 2. 测试优化版流程
    result = test_optimized_pipeline()

    # 3. 测试API响应格式
    test_api_response_format()

    # 诊断结论
    print("\n" + "="*50)
    print("诊断结论：")

    if result and not result.get('technical', {}).get('prices'):
        print("⚠️ 问题确认：分析流程完成但没有价格数据")
        print("\n可能原因：")
        print("1. analyze_optimized.py中的_fetch_technical_data函数没有正确返回prices字段")
        print("2. 日期范围设置有问题")
        print("3. 数据缓存导致的问题")
        print("\n建议修复：")
        print("1. 检查_fetch_technical_data函数的返回值格式")
        print("2. 确保返回的字典包含'prices'字段")
        print("3. 清理缓存后重试")


if __name__ == "__main__":
    main()