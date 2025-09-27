"""最终测试 - 验证所有接口正常工作"""
import requests
import json
import time

BASE_URL = "http://localhost:8001"

def test_health():
    """测试健康检查"""
    resp = requests.get(f"{BASE_URL}/health")
    assert resp.status_code == 200
    print("✓ 健康检查正常")

def test_market():
    """测试市场数据"""
    resp = requests.get(f"{BASE_URL}/market")
    assert resp.status_code == 200
    data = resp.json()
    assert 'indices' in data
    print(f"✓ 市场数据正常，获取 {len(data.get('indices', []))} 个指数")

def test_fear_greed():
    """测试恐贪指数"""
    resp = requests.get(f"{BASE_URL}/market/fear-greed-index")
    assert resp.status_code == 200
    data = resp.json()
    assert 'fear_greed_index' in data
    score = data['fear_greed_index']['score']
    level = data['fear_greed_index']['level']
    print(f"✓ 恐贪指数正常: {score} ({level})")

def test_analyze():
    """测试股票分析"""
    resp = requests.post(
        f"{BASE_URL}/analyze",
        json={"name": "贵州茅台", "force": False},
        timeout=30
    )
    assert resp.status_code == 200
    data = resp.json()

    # 检查关键字段
    assert 'prices' in data, "缺少prices字段"
    assert 'score' in data, "缺少score字段"
    assert 'text' in data, "缺少text字段"

    prices_count = len(data.get('prices', []))
    score_total = data.get('score', {}).get('total', 'N/A')

    print(f"✓ 股票分析正常:")
    print(f"  - prices数据: {prices_count} 条")
    print(f"  - 综合评分: {score_total}/100")

def test_analyze_professional():
    """测试专业分析接口"""
    resp = requests.get(
        f"{BASE_URL}/analyze/professional",
        params={"name": "比亚迪", "force": False},
        timeout=30
    )
    assert resp.status_code == 200
    data = resp.json()

    # 检查关键字段
    assert 'prices' in data, "缺少prices字段"
    assert 'professional_analysis' in data, "缺少professional_analysis字段"

    prices_count = len(data.get('prices', []))

    print(f"✓ 专业分析正常:")
    print(f"  - prices数据: {prices_count} 条")
    print(f"  - 数据源: {len(data.get('professional_analysis', {}).get('data_sources', {}))} 个")

def main():
    print("=" * 50)
    print("开始全面测试后端API...")
    print("=" * 50)

    tests = [
        ("健康检查", test_health),
        ("市场数据", test_market),
        ("恐贪指数", test_fear_greed),
        ("股票分析", test_analyze),
        ("专业分析", test_analyze_professional)
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        print(f"\n测试 {name}...")
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ {name} 失败: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {name} 错误: {e}")
            failed += 1

        time.sleep(1)  # 避免请求过快

    print("\n" + "=" * 50)
    print(f"测试结果: {passed} 通过, {failed} 失败")

    if failed == 0:
        print("\n🎉 所有测试通过！系统运行正常！")
        print("\n现在可以访问 http://localhost:2345 使用系统了")
        print("如果还有503错误，请：")
        print("1. 清除浏览器缓存")
        print("2. 刷新页面")
        print("3. 打开浏览器控制台查看具体错误")
    else:
        print("\n⚠️ 有测试失败，请检查错误信息")

if __name__ == "__main__":
    main()