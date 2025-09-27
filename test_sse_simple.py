#!/usr/bin/env python3
"""
简单测试后端SSE流式接口
"""

import requests
import time

def test_sse_endpoint():
    """测试SSE端点"""
    print("测试SSE流式分析接口...")

    url = "http://localhost:8001/analyze/stream"
    params = {
        "name": "平安银行",
        "force": "true"
    }

    try:
        # 使用stream=True来处理流式响应
        response = requests.get(url, params=params, stream=True, timeout=10)
        print(f"HTTP状态码: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")

        if response.status_code == 200:
            print("开始读取SSE数据流...")
            line_count = 0
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    print(f"[{line_count}] {line}")
                    line_count += 1
                    if line_count > 20:  # 限制输出行数
                        print("...输出太多，停止读取")
                        break
        else:
            print("SSE请求失败")
            print("响应内容:", response.text[:500])

    except requests.exceptions.Timeout:
        print("SSE请求超时")
    except Exception as e:
        print(f"SSE请求异常: {e}")

def test_http_endpoint():
    """测试HTTP端点"""
    print("\n测试HTTP专业分析接口...")

    url = "http://localhost:8001/analyze/professional"
    params = {
        "name": "平安银行",
        "force": "true"
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"HTTP状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("HTTP接口成功")
            print(f"返回数据字段: {list(data.keys())}")
            if 'text' in data:
                print(f"报告文本长度: {len(data['text'])}")
            if 'score' in data:
                print(f"评分信息: {data['score']}")
        else:
            print("HTTP请求失败")
            print("响应内容:", response.text[:500])

    except Exception as e:
        print(f"HTTP请求异常: {e}")

if __name__ == "__main__":
    print("=== 后端接口测试 ===")

    # 先测试健康检查
    try:
        health_resp = requests.get("http://localhost:8001/health", timeout=5)
        if health_resp.status_code == 200:
            print("✓ 后端健康检查通过")
        else:
            print("✗ 后端健康检查失败")
            exit(1)
    except Exception as e:
        print(f"✗ 无法连接后端: {e}")
        exit(1)

    # 测试两个接口
    test_sse_endpoint()
    test_http_endpoint()

    print("\n测试完成")