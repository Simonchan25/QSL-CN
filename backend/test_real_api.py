"""测试真实的API返回数据"""
import requests
import json
import sys

def test_analyze_api():
    """测试分析API的实际返回"""
    print("=== 测试分析API ===\n")

    # 1. 测试 POST /analyze 接口
    print("1. 测试 POST /analyze 接口...")
    try:
        response = requests.post(
            "http://localhost:8001/analyze",
            json={"name": "贵州茅台", "force": True},
            timeout=60
        )

        if response.status_code == 200:
            data = response.json()

            print("✓ API调用成功")
            print(f"\n返回的顶层字段: {list(data.keys())}\n")

            # 检查关键字段
            critical_fields = ['prices', 'tech', 'technical', 'fundamental', 'score']

            for field in critical_fields:
                if field in data:
                    if field == 'prices':
                        prices = data[field]
                        if isinstance(prices, list) and len(prices) > 0:
                            print(f"✓ {field}: 包含 {len(prices)} 条数据")
                            print(f"  最新数据: {prices[0] if prices else 'N/A'}")
                        else:
                            print(f"✗ {field}: 存在但是空的或格式错误")
                            print(f"  类型: {type(prices)}, 内容: {prices[:100] if str(prices) else 'empty'}")
                    else:
                        print(f"✓ {field}: 存在 (类型: {type(data[field]).__name__})")
                else:
                    print(f"✗ {field}: 不存在")

            # 保存完整响应
            with open('analyze_response.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            print("\n完整响应已保存到 analyze_response.json")

        else:
            print(f"✗ API返回错误: {response.status_code}")
            print(f"错误信息: {response.text[:500]}")

    except Exception as e:
        print(f"✗ 请求失败: {e}")

    # 2. 测试 GET /analyze/professional 接口
    print("\n\n2. 测试 GET /analyze/professional 接口...")
    try:
        response = requests.get(
            "http://localhost:8001/analyze/professional",
            params={"name": "贵州茅台", "force": True},
            timeout=60
        )

        if response.status_code == 200:
            data = response.json()

            print("✓ API调用成功")
            print(f"\n返回的顶层字段: {list(data.keys())}\n")

            # 检查prices字段
            if 'prices' in data:
                prices = data['prices']
                print(f"✓ prices字段存在")
                print(f"  类型: {type(prices)}")
                if isinstance(prices, list):
                    print(f"  数量: {len(prices)}")
                    if prices:
                        print(f"  第一条: {prices[0]}")
                elif prices is None:
                    print(f"  值为None")
                else:
                    print(f"  异常类型: {prices}")
            else:
                print("✗ prices字段不存在")

                # 检查是否在其他地方
                for key in data.keys():
                    if 'price' in key.lower():
                        print(f"  发现相关字段: {key}")

            # 保存响应
            with open('professional_response.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            print("\n完整响应已保存到 professional_response.json")

        else:
            print(f"✗ API返回错误: {response.status_code}")

    except Exception as e:
        print(f"✗ 请求失败: {e}")

def test_stream_api():
    """测试流式API"""
    print("\n\n3. 测试 GET /analyze/stream 接口...")

    try:
        # 使用流式请求
        with requests.get(
            "http://localhost:8001/analyze/stream",
            params={"name": "贵州茅台", "force": True},
            stream=True,
            timeout=60
        ) as response:

            if response.status_code == 200:
                print("✓ 流式连接成功\n")

                result_data = None
                event_count = 0

                for line in response.iter_lines():
                    if line:
                        decoded = line.decode('utf-8')

                        # 解析SSE事件
                        if decoded.startswith('event:'):
                            event_name = decoded[6:].strip()

                        elif decoded.startswith('data:'):
                            try:
                                data = json.loads(decoded[5:])
                                event_count += 1

                                # 如果是result事件，保存数据
                                if event_name == 'result':
                                    result_data = data
                                    print(f"收到result事件")

                                # 打印进度
                                if event_name == 'progress':
                                    step = data.get('step', '')
                                    if step:
                                        print(f"  进度: {step}")

                            except json.JSONDecodeError:
                                pass

                print(f"\n共收到 {event_count} 个事件")

                # 检查结果数据
                if result_data:
                    print("\n分析result数据:")
                    print(f"  顶层字段: {list(result_data.keys())}")

                    if 'prices' in result_data:
                        prices = result_data['prices']
                        if isinstance(prices, list):
                            print(f"  ✓ prices存在: {len(prices)} 条")
                        else:
                            print(f"  ✗ prices类型异常: {type(prices)}")
                    else:
                        print("  ✗ prices字段不存在")

                    # 保存结果
                    with open('stream_result.json', 'w', encoding='utf-8') as f:
                        json.dump(result_data, f, ensure_ascii=False, indent=2, default=str)
                    print("\n结果已保存到 stream_result.json")

            else:
                print(f"✗ 流式API错误: {response.status_code}")

    except Exception as e:
        print(f"✗ 流式请求失败: {e}")

def main():
    print("开始测试真实API返回...")
    print("="*50)

    # 测试各个接口
    test_analyze_api()
    test_stream_api()

    print("\n" + "="*50)
    print("测试完成！")
    print("\n请检查生成的JSON文件，确认:")
    print("1. prices字段是否存在")
    print("2. prices是否包含数据")
    print("3. 数据格式是否正确")

if __name__ == "__main__":
    main()