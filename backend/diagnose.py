#!/usr/bin/env python3
"""
诊断脚本 - 检查系统配置和API连接问题
"""

import os
import sys
from dotenv import load_dotenv
from datetime import datetime

# 加载环境变量
load_dotenv()

print("="*60)
print("股票分析系统诊断工具")
print("="*60)
print(f"运行时间: {datetime.now()}")
print()

# 1. 检查环境配置
print("【1. 环境配置检查】")
print("-"*40)

# 检查 TUSHARE_TOKEN
token = os.getenv("TUSHARE_TOKEN")
if not token:
    print("❌ TUSHARE_TOKEN 未设置")
    print("   解决方案: 在 backend/.env 文件中添加 TUSHARE_TOKEN=你的token")
elif len(token) < 20:
    print(f"❌ TUSHARE_TOKEN 格式不正确 (长度={len(token)})")
    print("   解决方案: 请检查token是否完整")
else:
    print(f"✅ TUSHARE_TOKEN 已设置 ({token[:10]}...{token[-10:]})")

# 检查 Ollama 配置
ollama_url = os.getenv("OLLAMA_URL")
ollama_model = os.getenv("OLLAMA_MODEL")

if not ollama_url:
    print("❌ OLLAMA_URL 未设置")
    print("   解决方案: 在 backend/.env 文件中添加 OLLAMA_URL=http://localhost:11434")
else:
    print(f"✅ OLLAMA_URL 已设置: {ollama_url}")

if not ollama_model:
    print("❌ OLLAMA_MODEL 未设置")
    print("   解决方案: 在 backend/.env 文件中添加 OLLAMA_MODEL=deepseek-r1:8b")
else:
    print(f"✅ OLLAMA_MODEL 已设置: {ollama_model}")

print()

# 2. 检查依赖库
print("【2. 依赖库检查】")
print("-"*40)

required_libs = ['tushare', 'pandas', 'fastapi', 'uvicorn', 'requests']
for lib in required_libs:
    try:
        __import__(lib)
        print(f"✅ {lib} 已安装")
    except ImportError:
        print(f"❌ {lib} 未安装")
        print(f"   解决方案: pip install {lib}")

print()

# 3. 检查 TuShare API 连接
print("【3. TuShare API 连接测试】")
print("-"*40)

if token and len(token) >= 20:
    import tushare as ts
    
    try:
        # 初始化 API
        pro = ts.pro_api(token)
        print("✅ TuShare客户端初始化成功")
        
        # 测试基础接口
        print("\n测试接口调用...")
        test_results = []
        
        # 测试 stock_basic
        try:
            df = pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name', limit=1)
            if df is not None and not df.empty:
                test_results.append(("stock_basic", "✅", f"获取到{len(df)}条数据"))
            else:
                test_results.append(("stock_basic", "⚠️", "返回空数据"))
        except Exception as e:
            error_msg = str(e)
            if "每天最多访问" in error_msg:
                test_results.append(("stock_basic", "🚫", "达到每日访问限制(5次/天)"))
            elif "权限" in error_msg:
                test_results.append(("stock_basic", "🔒", "无权限访问"))
            else:
                test_results.append(("stock_basic", "❌", error_msg[:50]))
        
        # 测试日线数据
        try:
            df = pro.daily(ts_code='600519.SH', start_date='20250101', end_date='20250812')
            if df is not None and not df.empty:
                test_results.append(("daily", "✅", f"获取到{len(df)}条数据"))
            else:
                test_results.append(("daily", "⚠️", "返回空数据"))
        except Exception as e:
            error_msg = str(e)
            if "每天最多访问" in error_msg:
                test_results.append(("daily", "🚫", "达到每日访问限制"))
            elif "权限" in error_msg:
                test_results.append(("daily", "🔒", "无权限访问"))
            else:
                test_results.append(("daily", "❌", error_msg[:50]))
        
        # 打印测试结果
        print("\n接口测试结果:")
        for api_name, status, msg in test_results:
            print(f"  {api_name:15} {status} {msg}")
        
    except Exception as e:
        print(f"❌ TuShare初始化失败: {e}")
else:
    print("⏭️  跳过TuShare测试（token未配置）")

print()

# 4. 检查缓存系统
print("【4. 缓存系统检查】")
print("-"*40)

cache_dir = os.path.join(os.path.dirname(__file__), ".cache")
if os.path.exists(cache_dir):
    cache_files = os.listdir(cache_dir)
    print(f"✅ 缓存目录存在: {cache_dir}")
    print(f"   缓存文件数: {len(cache_files)}")
    
    if cache_files:
        print("   最近的缓存文件:")
        for f in sorted(cache_files)[:5]:
            file_path = os.path.join(cache_dir, f)
            size = os.path.getsize(file_path) / 1024  # KB
            mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
            print(f"     - {f} ({size:.1f}KB, {mtime.strftime('%Y-%m-%d %H:%M')})")
else:
    print("⚠️  缓存目录不存在")
    print("   系统会在首次调用API后自动创建")

print()

# 5. 检查 Ollama 服务
print("【5. Ollama 服务检查】")
print("-"*40)

if ollama_url:
    import requests
    try:
        # 检查服务是否运行
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            print(f"✅ Ollama服务运行正常")
            print(f"   已安装模型数: {len(models)}")
            
            if models:
                print("   可用模型:")
                for model in models[:5]:
                    print(f"     - {model['name']}")
                
                if ollama_model:
                    model_names = [m['name'] for m in models]
                    if ollama_model in model_names:
                        print(f"   ✅ 配置的模型 {ollama_model} 已安装")
                    else:
                        print(f"   ❌ 配置的模型 {ollama_model} 未安装")
                        print(f"      解决方案: ollama pull {ollama_model}")
        else:
            print(f"⚠️  Ollama服务响应异常 (HTTP {response.status_code})")
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到Ollama服务")
        print("   解决方案: ")
        print("   1. 启动Ollama: ollama serve")
        print("   2. 检查端口是否正确")
    except Exception as e:
        print(f"❌ Ollama检查失败: {e}")
else:
    print("⏭️  跳过Ollama测试（URL未配置）")

print()

# 6. 诊断总结
print("【诊断总结】")
print("="*60)

problems = []
solutions = []

# 检查问题
if not token:
    problems.append("TuShare Token未配置")
    solutions.append("在 backend/.env 中设置 TUSHARE_TOKEN")
elif len(token) < 20:
    problems.append("TuShare Token格式错误")
    solutions.append("检查并更正 TUSHARE_TOKEN")

if not ollama_url:
    problems.append("Ollama URL未配置")
    solutions.append("在 backend/.env 中设置 OLLAMA_URL")

if not ollama_model:
    problems.append("Ollama模型未配置")
    solutions.append("在 backend/.env 中设置 OLLAMA_MODEL")

# 输出总结
if problems:
    print("发现以下问题:")
    for i, problem in enumerate(problems, 1):
        print(f"  {i}. {problem}")
    
    print("\n建议解决方案:")
    for i, solution in enumerate(solutions, 1):
        print(f"  {i}. {solution}")
    
    print("\n额外建议:")
    print("  - TuShare免费账户每天只能访问5次主要接口")
    print("  - 建议升级账户或使用缓存数据进行开发")
    print("  - 访问 https://tushare.pro 了解更多")
else:
    print("✅ 所有配置检查通过!")
    print("\n注意事项:")
    print("  - TuShare免费账户有访问限制(5次/天)")
    print("  - 系统已实现缓存机制减少API调用")
    print("  - 如遇到限制，请等待次日重置或升级账户")

print("\n诊断完成!")
print("="*60)