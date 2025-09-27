"""验证数据获取修复"""
import requests
import json
import time

def test_api():
    """测试API是否返回价格数据"""
    print("=== 测试API修复效果 ===\n")

    # 测试股票列表
    test_stocks = ['贵州茅台', '比亚迪', '宁德时代']

    for stock_name in test_stocks:
        print(f"\n测试股票: {stock_name}")
        print("-" * 30)

        try:
            # 使用POST接口
            print("  调用/analyze接口...")
            resp = requests.post(
                "http://localhost:8001/analyze",
                json={"name": stock_name, "force": True},
                timeout=60
            )

            if resp.status_code == 200:
                data = resp.json()

                # 检查prices字段
                if 'prices' in data:
                    prices = data['prices']
                    print(f"  ✓ prices字段存在，包含 {len(prices)} 条数据")

                    if prices:
                        latest = prices[0] if isinstance(prices, list) else prices
                        print(f"    最新日期: {latest.get('trade_date', 'N/A')}")
                        print(f"    最新收盘: {latest.get('close', 'N/A')}")
                else:
                    print(f"  ✗ 没有prices字段")
                    print(f"    返回的字段: {list(data.keys())}")

                # 检查technical字段
                if 'technical' in data:
                    tech = data['technical']
                    print(f"  ✓ technical字段存在")
                    if 'prices' in tech:
                        print(f"    technical中有prices: {len(tech['prices'])} 条")
                    else:
                        print(f"    technical中没有prices")

                # 检查评分
                if 'score' in data:
                    score = data['score']
                    print(f"  ✓ 综合评分: {score.get('total', 'N/A')}")

                # 保存完整响应供分析
                filename = f"{stock_name}_response.json"
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2, default=str)
                print(f"  响应已保存到: {filename}")

            else:
                print(f"  ✗ API返回错误: {resp.status_code}")
                print(f"    错误信息: {resp.text[:200]}")

        except requests.Timeout:
            print(f"  ✗ 请求超时")
        except Exception as e:
            print(f"  ✗ 请求失败: {e}")

        time.sleep(2)  # 避免过快请求

def test_stream_api():
    """测试流式API"""
    print("\n\n=== 测试流式API ===\n")

    try:
        import requests

        # 使用SSE客户端测试流式接口
        print("测试 /analyze/stream 接口...")
        url = "http://localhost:8001/analyze/stream?name=贵州茅台&force=true"

        with requests.get(url, stream=True, timeout=30) as resp:
            if resp.status_code == 200:
                print("✓ 流式连接成功")

                # 读取前几个事件
                line_count = 0
                for line in resp.iter_lines():
                    if line_count > 20:  # 只读前20行
                        break
                    if line:
                        decoded = line.decode('utf-8')
                        if decoded.startswith('data:'):
                            try:
                                data = json.loads(decoded[5:])
                                if 'step' in data:
                                    print(f"  进度: {data['step']}")
                            except:
                                pass
                    line_count += 1

            else:
                print(f"✗ 流式API错误: {resp.status_code}")
    except Exception as e:
        print(f"✗ 流式API测试失败: {e}")

def main():
    """主函数"""
    print("开始验证修复效果...")
    print("="*50)

    # 1. 测试普通API
    test_api()

    # 2. 测试流式API
    test_stream_api()

    print("\n" + "="*50)
    print("验证完成！")
    print("\n建议：")
    print("1. 如果prices数据正常返回，说明修复成功")
    print("2. 请在前端界面测试，确认数据显示正常")
    print("3. 如果仍有问题，请查看生成的JSON文件分析数据结构")

if __name__ == "__main__":
    main()