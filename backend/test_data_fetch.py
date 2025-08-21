#!/usr/bin/env python3
"""测试数据获取功能"""

import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def test_tushare_connection():
    """测试TuShare连接"""
    print("\n=== 测试 TuShare 连接 ===")
    from core import tushare_client
    
    # 检查token
    token = os.getenv("TUSHARE_TOKEN")
    print(f"Token设置: {'✓' if token else '✗'}")
    
    # 测试获取股票基础信息（使用缓存）
    try:
        df = tushare_client.stock_basic()
        if df is not None and not df.empty:
            print(f"✓ 获取股票列表成功，共 {len(df)} 支股票")
            # 显示茅台信息
            maotai = df[df['symbol'] == '600519']
            if not maotai.empty:
                print(f"  茅台信息: {maotai.iloc[0].to_dict()}")
        else:
            print("✗ 获取股票列表失败（返回空数据）")
    except Exception as e:
        print(f"✗ 获取股票列表失败: {e}")
        if "每天最多访问" in str(e) or "每分钟最多访问" in str(e):
            print("  提示: 已达到API访问限制，尝试使用缓存数据...")

def test_cache_system():
    """测试缓存系统"""
    print("\n=== 测试缓存系统 ===")
    import os
    
    cache_dir = os.path.join(os.path.dirname(__file__), ".cache")
    if os.path.exists(cache_dir):
        files = os.listdir(cache_dir)
        print(f"缓存目录存在，包含 {len(files)} 个文件:")
        for f in files[:5]:  # 只显示前5个
            size = os.path.getsize(os.path.join(cache_dir, f))
            print(f"  - {f} ({size:,} bytes)")
    else:
        print("缓存目录不存在")

def test_analyze_api():
    """测试分析API"""
    print("\n=== 测试分析 API ===")
    from core.analyze import resolve_by_name, run_pipeline
    
    # 测试股票解析（使用本地映射）
    stock_name = "茅台"
    print(f"解析股票: {stock_name}")
    
    try:
        result = resolve_by_name(stock_name)
        if result:
            print(f"✓ 解析成功: {result}")
            
            # 测试完整分析流程
            print(f"\n运行分析流程...")
            analysis = run_pipeline(stock_name, force=False)
            
            if analysis:
                print("✓ 分析完成")
                basic = analysis.get('basic', {}) or {}
                print(f"  股票代码: {basic.get('ts_code')}")
                print(f"  股票名称: {basic.get('name')}")

                # 检查各部分数据（按新结构）
                technical = analysis.get('technical') or {}
                if technical:
                    print(f"  技术信号: {technical.get('tech_signal')}")
                fundamental = analysis.get('fundamental') or {}
                if fundamental:
                    print("  基本面数据: 已获取")
                if analysis.get('macro'):
                    print("  宏观数据: 已获取")
                if analysis.get('news'):
                    print("  新闻数据: 已整合")
                if analysis.get('llm_summary'):
                    text = analysis['llm_summary']
                    preview = text[:100].replace('\n', ' ')
                    print(f"  LLM总结: {preview}...")
            else:
                print("✗ 分析失败（返回空结果）")
        else:
            print(f"✗ 解析失败: 未找到 {stock_name}")
    except Exception as e:
        print(f"✗ 分析失败: {e}")
        if "每天最多访问" in str(e) or "每分钟最多访问" in str(e):
            print("\n⚠️  重要提示:")
            print("  1. TuShare免费账户每天只能访问5次")
            print("  2. 系统已实现缓存机制，会优先使用缓存数据")
            print("  3. 建议升级TuShare账户获取更多访问次数")
            print("  4. 访问 https://tushare.pro 了解更多")

def test_ollama():
    """测试Ollama连接"""
    print("\n=== 测试 Ollama 连接 ===")
    
    ollama_url = os.getenv("OLLAMA_URL")
    ollama_model = os.getenv("OLLAMA_MODEL")
    
    print(f"Ollama URL: {ollama_url}")
    print(f"Ollama Model: {ollama_model}")
    
    # 测试连接
    import requests
    try:
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            print(f"✓ Ollama连接成功，已安装 {len(models)} 个模型")
            
            # 检查指定模型是否存在
            model_names = [m['name'] for m in models]
            if ollama_model in model_names:
                print(f"✓ 模型 {ollama_model} 已安装")
            else:
                print(f"✗ 模型 {ollama_model} 未安装")
                print(f"  可用模型: {', '.join(model_names[:5])}")
        else:
            print(f"✗ Ollama连接失败: HTTP {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("✗ 无法连接到Ollama服务")
        print("  请确保Ollama正在运行: ollama serve")
    except Exception as e:
        print(f"✗ Ollama测试失败: {e}")

if __name__ == "__main__":
    test_cache_system()
    test_tushare_connection()
    test_ollama()
    test_analyze_api()
    
    print("\n" + "="*50)
    print("测试完成！")
    print("\n建议:")
    print("1. 如果遇到API限制，等待明天重置或升级TuShare账户")
    print("2. 确保Ollama服务正在运行")
    print("3. 使用缓存数据进行开发测试")