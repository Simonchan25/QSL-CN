#!/usr/bin/env python3
import requests
import json
import pprint

def check_data_structure():
    """检查API返回的数据结构"""
    url = "http://localhost:8001/analyze/professional"
    params = {
        "name": "贵州茅台",
        "force": "true"
    }

    print("正在请求数据...")
    response = requests.get(url, params=params, timeout=60)

    if response.status_code == 200:
        data = response.json()

        print("\n=== 数据结构检查 ===")
        print(f"顶层字段: {list(data.keys())}")

        # 检查技术数据
        technical = data.get('technical', {})
        print(f"\n技术数据字段: {list(technical.keys())}")

        # 检查价格数据
        latest_price = technical.get('latest_price')
        price = technical.get('price')
        prices = technical.get('prices', [])

        print(f"\nlatest_price: {latest_price}")
        print(f"price: {price}")
        print(f"prices类型: {type(prices)}, 长度: {len(prices) if isinstance(prices, list) else 'N/A'}")

        if isinstance(prices, list) and len(prices) > 0:
            print(f"第一条价格数据: {prices[0]}")

        # 检查基本面数据
        fundamental = data.get('fundamental', {})
        print(f"\n基本面数据字段: {list(fundamental.keys())[:10]}")

        # 检查市场数据
        market = data.get('market', {})
        print(f"\n市场数据字段: {list(market.keys())[:10]}")

        # 检查新闻数据
        news = data.get('news', [])
        print(f"\n新闻数据: 类型={type(news)}, 数量={len(news) if isinstance(news, list) else 'N/A'}")

        # 检查专业报告
        professional_report = data.get('professional_report')
        print(f"\n专业报告: {'存在' if professional_report else '不存在'}")

        # 检查professional_data
        professional_data = data.get('professional_data', {})
        print(f"\n专业数据字段: {list(professional_data.keys()) if professional_data else '空'}")

        # 保存完整数据用于分析
        with open('analyze_response.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n完整响应已保存到 analyze_response.json")

    else:
        print(f"请求失败: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    check_data_structure()