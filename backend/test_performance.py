#!/usr/bin/env python3
import time
import requests

def test_performance():
    """测试优化后的性能"""
    base_url = "http://localhost:8001"

    print("=== 性能测试开始 ===")

    # 测试快速接口
    print("\n1. 测试快速接口...")
    start_time = time.time()
    response = requests.get(f"{base_url}/analyze/quick",
                          params={"name": "贵州茅台"},
                          timeout=10)
    quick_time = time.time() - start_time

    if response.status_code == 200:
        print(f"   ✓ 快速接口成功: {quick_time:.2f}秒")
        data = response.json()
        if "text" in data and len(data["text"]) > 100:
            print(f"   ✓ 报告内容正常: {len(data['text'])}字符")
        else:
            print(f"   ⚠ 报告内容可能异常: {len(data.get('text', ''))}字符")
    else:
        print(f"   ✗ 快速接口失败: {response.status_code}")

    # 测试专业接口
    print("\n2. 测试专业接口...")
    start_time = time.time()
    response = requests.get(f"{base_url}/analyze/professional",
                          params={"name": "贵州茅台", "force": "true"},
                          timeout=60)
    pro_time = time.time() - start_time

    if response.status_code == 200:
        print(f"   ✓ 专业接口成功: {pro_time:.2f}秒")
        data = response.json()
        if "text" in data and len(data["text"]) > 300:
            print(f"   ✓ 专业报告内容正常: {len(data['text'])}字符")
        else:
            print(f"   ⚠ 专业报告内容可能异常: {len(data.get('text', ''))}字符")
    else:
        print(f"   ✗ 专业接口失败: {response.status_code}")

    print(f"\n=== 测试完成 ===")
    print(f"快速接口: {quick_time:.2f}秒")
    print(f"专业接口: {pro_time:.2f}秒")
    print(f"性能提升: {(pro_time/quick_time):.1f}x")

if __name__ == "__main__":
    test_performance()
