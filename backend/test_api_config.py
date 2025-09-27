#!/usr/bin/env python3
"""
测试API配置问题
"""
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置环境变量
os.environ["TUSHARE_TOKEN"] = "e470904e8ad4c47e1d2f9dcdbe69bc98c5e7ecaa2adf66fdd64c3082"

def test_basic_apis():
    """测试基础API"""
    from core.tushare_client import _call_api, stock_basic

    print("="*60)
    print("测试基础API配置")
    print("="*60)

    # 1. 测试token设置
    print("\n1. 检查token设置:")
    import tushare as ts
    try:
        # 检查当前token
        print(f"   环境变量token: {os.environ.get('TUSHARE_TOKEN')[:20]}...")

        # 测试最简单的API
        df = _call_api('stock_basic', exchange='', list_status='L', limit=5)
        if df is not None and not df.empty:
            print(f"   ✅ 基础接口正常: 获取到 {len(df)} 条股票数据")
        else:
            print("   ❌ 基础接口失败: 返回空数据")
    except Exception as e:
        print(f"   ❌ 基础接口错误: {str(e)}")

def test_advanced_apis():
    """测试高级API"""
    from core.tushare_client import _call_api

    print("\n2. 测试高级API:")
    ts_code = "000001.SZ"

    # 测试各种高级接口
    apis_to_test = [
        ("top10_holders", {"ts_code": ts_code}),
        ("top10_floatholders", {"ts_code": ts_code}),
        ("stk_holdertrade", {"ts_code": ts_code}),
        ("block_trade", {"ts_code": ts_code}),
        ("margin_detail", {"ts_code": ts_code}),
        ("moneyflow", {"ts_code": ts_code}),
        ("dividend", {"ts_code": ts_code}),
    ]

    for api_name, params in apis_to_test:
        try:
            df = _call_api(api_name, **params)
            if df is not None and not df.empty:
                print(f"   ✅ {api_name}: 获取到 {len(df)} 条数据")
            else:
                print(f"   ⚠️  {api_name}: 返回空数据")
        except Exception as e:
            error_msg = str(e)
            if "没有权限" in error_msg or "权限不足" in error_msg:
                print(f"   🔒 {api_name}: 权限不足")
            elif "每分钟最多访问" in error_msg:
                print(f"   ⏰ {api_name}: 频率限制")
            else:
                print(f"   ❌ {api_name}: {error_msg[:50]}...")

def test_date_params():
    """测试日期参数问题"""
    from core.tushare_client import _call_api
    from datetime import datetime, timedelta

    print("\n3. 测试日期参数:")

    # 准备日期
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=5)).strftime('%Y%m%d')

    ts_code = "000001.SZ"

    # 测试需要日期参数的接口
    date_apis = [
        ("daily", {"ts_code": ts_code, "start_date": start_date, "end_date": end_date}),
        ("daily_basic", {"ts_code": ts_code, "start_date": start_date, "end_date": end_date}),
        ("moneyflow", {"ts_code": ts_code, "start_date": start_date, "end_date": end_date}),
    ]

    for api_name, params in date_apis:
        try:
            df = _call_api(api_name, **params)
            if df is not None and not df.empty:
                print(f"   ✅ {api_name}: 获取到 {len(df)} 条数据")
                if len(df) > 0:
                    # 显示一些数据样本
                    print(f"      最新日期: {df.iloc[0].get('trade_date', 'N/A')}")
            else:
                print(f"   ⚠️  {api_name}: 返回空数据")
        except Exception as e:
            print(f"   ❌ {api_name}: {str(e)[:50]}...")

def test_specific_failing_apis():
    """测试具体失败的API"""
    from core.tushare_client import top10_holders, top10_floatholders, moneyflow

    print("\n4. 测试具体失败的API:")

    ts_code = "000001.SZ"

    print(f"\n   测试股票: {ts_code}")

    # 测试股东数据
    try:
        print("   测试 top10_holders...")
        holders = top10_holders(ts_code, force=True)
        if holders is not None and not holders.empty:
            print(f"   ✅ top10_holders: {len(holders)} 条记录")
        else:
            print("   ⚠️  top10_holders: 空数据")
    except Exception as e:
        print(f"   ❌ top10_holders: {str(e)}")

    # 测试流通股东
    try:
        print("   测试 top10_floatholders...")
        float_holders = top10_floatholders(ts_code, force=True)
        if float_holders is not None and not float_holders.empty:
            print(f"   ✅ top10_floatholders: {len(float_holders)} 条记录")
        else:
            print("   ⚠️  top10_floatholders: 空数据")
    except Exception as e:
        print(f"   ❌ top10_floatholders: {str(e)}")

    # 测试资金流向
    try:
        print("   测试 moneyflow...")
        from datetime import datetime, timedelta
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=5)).strftime('%Y%m%d')

        flow = moneyflow(ts_code=ts_code, start_date=start_date, end_date=end_date, force=True)
        if flow is not None and not flow.empty:
            print(f"   ✅ moneyflow: {len(flow)} 条记录")
        else:
            print("   ⚠️  moneyflow: 空数据")
    except Exception as e:
        print(f"   ❌ moneyflow: {str(e)}")

def main():
    """运行所有测试"""
    print("Tushare API配置问题排查")
    print("Token权限: 5000积分")

    test_basic_apis()
    test_advanced_apis()
    test_date_params()
    test_specific_failing_apis()

    print("\n" + "="*60)
    print("测试完成")
    print("="*60)

if __name__ == "__main__":
    main()