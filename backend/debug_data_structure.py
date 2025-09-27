#!/usr/bin/env python3
import json
import requests

def debug_data_structure():
    """调试数据结构转换问题"""

    # 获取完整的API响应
    response = requests.get(
        "http://localhost:8001/analyze/professional",
        params={"name": "贵州茅台", "force": "true"},
        timeout=60
    )

    if response.status_code == 200:
        data = response.json()

        print("=== 原始数据结构调试 ===")

        # 检查技术数据
        technical = data.get('technical', {})
        print(f"\n技术数据keys: {list(technical.keys())}")

        price = technical.get('price', {})
        print(f"price数据: {price}")

        indicators = technical.get('indicators', {})
        print(f"indicators数据: {indicators}")

        # 检查基本面数据
        fundamental = data.get('fundamental', {})
        print(f"\n基本面数据keys: {list(fundamental.keys())}")

        latest_daily = fundamental.get('latest_daily', {})
        print(f"latest_daily数据: {latest_daily}")

        # 检查评分
        score = data.get('score', {})
        print(f"\nscore数据: {score}")

        # 检查资金流向
        moneyflow = data.get('moneyflow', {})
        print(f"\nmoneyflow数据: {moneyflow}")

        # 模拟数据转换
        print("\n=== 转换后数据结构 ===")
        adapted_data = {
            "price": technical.get("price", {}),
            "fundamentals": fundamental.get("latest_daily", {}),
            "indicators": technical.get("indicators", {}),
            "scorecard": {
                "总分": score.get("total", 50),
                "技术": {"score": score.get("details", {}).get("technical", 50)},
                "情绪": {"score": score.get("details", {}).get("market", 50)},
                "基本面": {"score": score.get("details", {}).get("fundamental", 50)}
            },
            "capital_flow": moneyflow
        }

        print(f"转换后的price: {adapted_data['price']}")
        print(f"转换后的fundamentals: {adapted_data['fundamentals']}")
        print(f"转换后的indicators: {adapted_data['indicators']}")
        print(f"转换后的scorecard: {adapted_data['scorecard']}")
        print(f"转换后的capital_flow: {adapted_data['capital_flow']}")

        # 测试报告生成
        print("\n=== 测试报告生成 ===")
        try:
            from core.practical_analyzer import generate_practical_report
            report = generate_practical_report(adapted_data, "贵州茅台")
            print(f"生成的报告前500字符:\n{report[:500]}")
        except Exception as e:
            print(f"报告生成失败: {e}")

    else:
        print(f"请求失败: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    debug_data_structure()