"""快速测试Tushare API连接"""
import os
import sys
import tushare as ts

# 设置token
token = os.getenv("TUSHARE_TOKEN", "e470904e8ad4c47e1d2f9dcdbe69bc98c5e7ecaa2adf66fdd64c3082")
print(f"使用Token: {token[:20]}...")

# 设置token并创建pro对象
ts.set_token(token)
pro = ts.pro_api()

# 测试1：获取交易日历
print("\n1. 测试获取交易日历...")
try:
    df = pro.trade_cal(exchange='SSE', start_date='20250101', end_date='20250131')
    if df is not None and not df.empty:
        print(f"✓ 成功获取 {len(df)} 条记录")
    else:
        print("✗ 获取数据为空")
except Exception as e:
    print(f"✗ 错误: {e}")

# 测试2：获取股票基本信息
print("\n2. 测试获取贵州茅台基本信息...")
try:
    df = pro.daily(ts_code='600519.SH', start_date='20250101', end_date='20250125')
    if df is not None and not df.empty:
        print(f"✓ 成功获取 {len(df)} 条日线数据")
        print(f"   最新日期: {df['trade_date'].max()}")
        print(f"   最新收盘价: {df[df['trade_date'] == df['trade_date'].max()]['close'].values[0]}")
    else:
        print("✗ 获取数据为空")
except Exception as e:
    print(f"✗ 错误: {e}")

# 测试3：测试用户权限
print("\n3. 测试用户权限信息...")
try:
    user_info = pro.user(token=token)
    if user_info is not None:
        print(f"✓ 用户信息获取成功")
        print(f"   积分: {user_info.get('point', 'N/A')}")
    else:
        print("✗ 无法获取用户信息")
except Exception as e:
    print(f"✗ 错误: {e}")
    # 尝试另一种方式
    try:
        print("尝试备用方式...")
        import requests
        resp = requests.post('http://api.waditu.com',
                           json={'api_name': 'user',
                                 'token': token,
                                 'params': {},
                                 'fields': ''})
        if resp.status_code == 200:
            data = resp.json()
            print(f"API响应: {data}")
    except Exception as e2:
        print(f"备用方式也失败: {e2}")

print("\n测试完成")