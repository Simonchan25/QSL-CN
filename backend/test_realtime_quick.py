#!/usr/bin/env python3
import os
import json
import requests
from datetime import datetime

def test_realtime():
    """测试实时数据获取"""
    base_url = "http://localhost:8001"

    print("=" * 50)
    print("测试实时数据接口")
    print("=" * 50)

    # 1. 测试市场概览
    print("\n1. 获取市场概览...")
    try:
        resp = requests.get(f"{base_url}/market", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            print(f"   ✓ 市场概览获取成功")
            if 'market_breadth' in data:
                mb = data['market_breadth']
                print(f"   上涨: {mb.get('up_count')}家, 下跌: {mb.get('down_count')}家")
            if 'indices' in data:
                print(f"   获取到 {len(data['indices'])} 个指数数据")
        else:
            print(f"   ✗ 获取失败: {resp.status_code}")
    except Exception as e:
        print(f"   ✗ 错误: {e}")

    # 2. 测试个股分析（简化版）
    print("\n2. 测试个股分析接口...")
    try:
        resp = requests.post(
            f"{base_url}/analyze",
            json={"name": "贵州茅台"},
            timeout=60  # 60秒超时
        )
        if resp.status_code == 200:
            data = resp.json()
            print(f"   ✓ 分析数据获取成功")

            # 检查各个数据部分
            if 'technical' in data:
                tech = data['technical']
                if tech and 'latest_quote' in tech:
                    quote = tech['latest_quote']
                    print(f"   最新价格: {quote.get('close')}, 涨幅: {quote.get('pct_chg')}%")

            if 'fundamental' in data:
                print(f"   ✓ 基本面数据已获取")

            if 'market' in data:
                print(f"   ✓ 市场数据已获取")

            if 'news' in data:
                news_count = len(data.get('news', []))
                print(f"   ✓ 获取到 {news_count} 条相关新闻")
        else:
            print(f"   ✗ 获取失败: {resp.status_code}")
            print(f"   错误: {resp.text[:200]}")
    except requests.exceptions.Timeout:
        print(f"   ✗ 请求超时（60秒）")
    except Exception as e:
        print(f"   ✗ 错误: {e}")

    # 3. 测试实时行情
    print("\n3. 测试实时行情接口...")
    try:
        resp = requests.get(
            f"{base_url}/realtime/quote/600519.SH",
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            if data:
                print(f"   ✓ 实时行情获取成功")
                print(f"   股票: {data.get('name')}")
                print(f"   最新价: {data.get('price')}")
                print(f"   涨跌幅: {data.get('pct_chg')}%")
                print(f"   成交量: {data.get('volume')}手")
        else:
            print(f"   ✗ 获取失败: {resp.status_code}")
    except Exception as e:
        print(f"   ✗ 错误: {e}")

    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)

if __name__ == "__main__":
    test_realtime()