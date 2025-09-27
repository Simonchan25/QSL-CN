#!/usr/bin/env python3
"""
测试深度分析功能
"""
import os
import sys
import json
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置环境变量
os.environ["TUSHARE_TOKEN"] = "e470904e8ad4c47e1d2f9dcdbe69bc98c5e7ecaa2adf66fdd64c3082"

def test_deep_analysis():
    """测试深度分析"""
    from core.analyze import run_pipeline

    print("=" * 60)
    print("测试RGTI风格深度分析")
    print("=" * 60)

    # 分析贵州茅台
    result = run_pipeline('贵州茅台', force=True)

    if result:
        # 检查关键字段
        print("\n1. 数据结构:")
        print(f"   包含字段: {list(result.keys())}")

        # 检查摘要内容
        if 'summary' in result:
            summary = result['summary']
            print(f"\n2. 深度分析摘要 (前800字):")
            print("-" * 40)
            print(summary[:800])
            print("-" * 40)

            # 检查关键特征
            features = [
                "深度分析概览",
                "近期行情与涨势亮点",
                "最新财报实况",
                "分析师观点与目标价",
                "市场情绪与新闻面",
                "风险评估与投资价值",
                "行业地位与业务前景",
                "投资策略建议",
                "简明总结与前瞻见解"
            ]

            print("\n3. RGTI风格特征检查:")
            for feature in features:
                if feature in summary:
                    print(f"   ✅ {feature}")
                else:
                    print(f"   ❌ {feature}")

        # 检查评分系统
        if 'score' in result:
            score = result['score']
            print(f"\n4. 六维度评分系统:")
            print(f"   总分: {score.get('total', 0)}/100")
            print(f"   评级: {score.get('rating', 'N/A')}")
            if 'details' in score:
                print("   详细评分:")
                for key, value in score['details'].items():
                    print(f"     - {key}: {value}")

        # 检查PE/PB数据
        if 'fundamental' in result and 'fina_indicator_latest' in result['fundamental']:
            metrics = result['fundamental']['fina_indicator_latest']
            print(f"\n5. 估值数据:")
            print(f"   PE: {metrics.get('pe', '无数据')}")
            print(f"   PB: {metrics.get('pb', '无数据')}")
            print(f"   ROE: {metrics.get('roe', '无数据')}")

        print("\n" + "=" * 60)
        print("✅ 测试完成!")
        print("=" * 60)

        # 保存完整结果供检查
        with open('test_result.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        print("\n完整结果已保存到 test_result.json")

    else:
        print("❌ 分析失败，返回空结果")

if __name__ == "__main__":
    test_deep_analysis()