#!/usr/bin/env python3
"""
TuShare连接诊断工具
"""

import os
import socket
import requests
import time
from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("TuShare 连接诊断")
print("=" * 60)

# 1. 检查Token
token = os.getenv("TUSHARE_TOKEN")
if token:
    print(f"✅ Token已配置 (长度: {len(token)})")
else:
    print("❌ Token未配置")

print("-" * 60)

# 2. 测试DNS解析
print("\n测试DNS解析...")
try:
    ip = socket.gethostbyname("api.waditu.com")
    print(f"✅ DNS解析成功: api.waditu.com -> {ip}")
except Exception as e:
    print(f"❌ DNS解析失败: {e}")

# 3. 测试网络连接
print("\n测试网络连接...")
hosts_to_test = [
    ("api.waditu.com", 80, "TuShare API (HTTP)"),
    ("api.waditu.com", 443, "TuShare API (HTTPS)"),
    ("tushare.pro", 443, "TuShare官网"),
    ("www.baidu.com", 443, "百度（测试国内网络）"),
    ("www.google.com", 443, "Google（测试国际网络）"),
]

for host, port, desc in hosts_to_test:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print(f"  ✅ {desc:30} [{host}:{port}] - 连接成功")
        else:
            print(f"  ❌ {desc:30} [{host}:{port}] - 连接失败")
    except Exception as e:
        print(f"  ❌ {desc:30} [{host}:{port}] - 错误: {e}")

# 4. 测试HTTP请求
print("\n测试HTTP请求...")
urls = [
    ("http://api.waditu.com", "TuShare API (HTTP)"),
    ("https://api.waditu.com", "TuShare API (HTTPS)"),
    ("https://tushare.pro", "TuShare官网"),
]

for url, desc in urls:
    try:
        response = requests.get(url, timeout=5)
        print(f"  ✅ {desc:30} - 状态码: {response.status_code}")
    except requests.exceptions.Timeout:
        print(f"  ⏱️ {desc:30} - 请求超时")
    except requests.exceptions.ConnectionError:
        print(f"  ❌ {desc:30} - 连接错误")
    except Exception as e:
        print(f"  ❌ {desc:30} - 错误: {e}")

# 5. 诊断结果和建议
print("\n" + "=" * 60)
print("诊断结果和建议")
print("=" * 60)

# 测试是否能连接到TuShare
can_connect = False
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    result = sock.connect_ex(("api.waditu.com", 80))
    sock.close()
    can_connect = (result == 0)
except:
    pass

if not can_connect:
    print("\n❌ 无法连接到TuShare服务器")
    print("\n可能的原因和解决方案：")
    print("\n1. 网络限制")
    print("   - 某些地区或网络环境可能无法直接访问TuShare")
    print("   - 解决方案: 使用代理或VPN")
    
    print("\n2. 服务器维护")
    print("   - TuShare服务器可能正在维护")
    print("   - 解决方案: 稍后再试，或查看 https://tushare.pro 官网公告")
    
    print("\n3. 使用代理访问")
    print("   如果需要代理，可以在代码中设置:")
    print("   ```python")
    print("   import os")
    print("   os.environ['HTTP_PROXY'] = 'http://your-proxy:port'")
    print("   os.environ['HTTPS_PROXY'] = 'http://your-proxy:port'")
    print("   ```")
    
    print("\n4. 使用备用方案")
    print("   - 考虑使用其他数据源（如akshare、yfinance等）")
    print("   - 或者使用缓存的历史数据进行测试")
    
else:
    print("\n✅ 可以连接到TuShare服务器")
    print("\n下一步：")
    print("1. 确认Token是否正确")
    print("2. 检查账户权限和积分")
    print("3. 访问 https://tushare.pro 查看账户状态")

print("\n" + "=" * 60)
print("其他信息")
print("=" * 60)
print(f"Python版本: {sys.version}")
print(f"当前时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")

# 导入sys
import sys