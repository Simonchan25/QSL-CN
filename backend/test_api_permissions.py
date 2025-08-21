#!/usr/bin/env python3
"""
TuShare API权限测试脚本
测试各个API接口的可用性和权限
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

print("=" * 60)
print("TuShare API 权限测试")
print("=" * 60)

# 检查Token配置
token = os.getenv("TUSHARE_TOKEN")
if not token:
    print("❌ 错误: 未找到TUSHARE_TOKEN环境变量")
    print("   请在 backend/.env 文件中设置 TUSHARE_TOKEN=你的token")
    sys.exit(1)

print(f"✅ Token已配置 (长度: {len(token)})")
print("-" * 60)

import tushare as ts

# 初始化pro接口
try:
    pro = ts.pro_api(token)
    print("✅ TuShare Pro接口初始化成功")
except Exception as e:
    print(f"❌ TuShare Pro接口初始化失败: {e}")
    sys.exit(1)

print("-" * 60)
print("开始测试各个API接口权限...")
print("-" * 60)

# 测试数据
test_ts_code = "000001.SZ"  # 平安银行
test_date = datetime.now().strftime("%Y%m%d")
test_start = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
test_end = datetime.now().strftime("%Y%m%d")

# API测试列表
api_tests = [
    # 基础接口（通常免费或低积分）
    {
        "name": "股票列表",
        "api": "stock_basic",
        "params": {},
        "required": True,
        "category": "基础数据"
    },
    {
        "name": "日线行情",
        "api": "daily",
        "params": {"ts_code": test_ts_code, "start_date": test_start, "end_date": test_end},
        "required": True,
        "category": "行情数据"
    },
    
    # 基本面接口
    {
        "name": "每日指标",
        "api": "daily_basic",
        "params": {"ts_code": test_ts_code, "trade_date": test_date},
        "required": False,
        "category": "基本面"
    },
    {
        "name": "财务指标",
        "api": "fina_indicator",
        "params": {"ts_code": test_ts_code},
        "required": True,
        "category": "基本面"
    },
    {
        "name": "利润表",
        "api": "income",
        "params": {"ts_code": test_ts_code},
        "required": True,
        "category": "基本面"
    },
    {
        "name": "资产负债表",
        "api": "balancesheet",
        "params": {"ts_code": test_ts_code},
        "required": True,
        "category": "基本面"
    },
    {
        "name": "现金流量表",
        "api": "cashflow",
        "params": {"ts_code": test_ts_code},
        "required": True,
        "category": "基本面"
    },
    {
        "name": "业绩预告",
        "api": "forecast",
        "params": {"ts_code": test_ts_code},
        "required": False,
        "category": "基本面"
    },
    {
        "name": "业绩快报",
        "api": "express",
        "params": {"ts_code": test_ts_code},
        "required": False,
        "category": "基本面"
    },
    
    # 技术面接口
    {
        "name": "涨跌停价格",
        "api": "stk_limit",
        "params": {"trade_date": test_date},
        "required": False,
        "category": "技术面"
    },
    {
        "name": "指数日线",
        "api": "index_daily",
        "params": {"ts_code": "000001.SH"},
        "required": False,
        "category": "技术面"
    },
    
    # 情绪面接口
    {
        "name": "个股资金流向",
        "api": "moneyflow",
        "params": {"ts_code": test_ts_code},
        "required": False,
        "category": "情绪面"
    },
    {
        "name": "融资融券明细",
        "api": "margin_detail",
        "params": {"trade_date": test_date},
        "required": False,
        "category": "情绪面"
    },
    {
        "name": "沪深港通资金流向",
        "api": "moneyflow_hsgt",
        "params": {"trade_date": test_date},
        "required": False,
        "category": "情绪面"
    },
    {
        "name": "公司公告",
        "api": "anns",
        "params": {"ts_code": test_ts_code},
        "required": False,
        "category": "情绪面"
    },
    {
        "name": "新闻快讯",
        "api": "news",
        "params": {"src": "sina", "limit": 10},
        "required": False,
        "category": "情绪面"
    },
    {
        "name": "重大新闻",
        "api": "major_news",
        "params": {"limit": 10},
        "required": False,
        "category": "情绪面"
    },
    
    # 宏观经济接口
    {
        "name": "CPI数据",
        "api": "cn_cpi",
        "params": {},
        "required": False,
        "category": "宏观经济"
    },
    {
        "name": "PPI数据",
        "api": "cn_ppi",
        "params": {},
        "required": False,
        "category": "宏观经济"
    },
    {
        "name": "货币供应量",
        "api": "cn_m",
        "params": {},
        "required": False,
        "category": "宏观经济"
    },
    {
        "name": "SHIBOR利率",
        "api": "shibor",
        "params": {},
        "required": False,
        "category": "宏观经济"
    },
    {
        "name": "GDP数据",
        "api": "cn_gdp",
        "params": {},
        "required": False,
        "category": "宏观经济"
    },
    {
        "name": "PMI数据",
        "api": "cn_pmi",
        "params": {},
        "required": False,
        "category": "宏观经济"
    },
]

# 统计结果
results = {
    "success": [],
    "failed": [],
    "no_permission": [],
    "rate_limited": []
}

current_category = None

for test in api_tests:
    # 打印分类标题
    if test["category"] != current_category:
        current_category = test["category"]
        print(f"\n【{current_category}】")
    
    try:
        # 调用API
        if hasattr(pro, test["api"]):
            result = getattr(pro, test["api"])(**test["params"])
            
            if result is not None and not result.empty:
                row_count = len(result)
                print(f"  ✅ {test['name']:20} - 成功 (返回{row_count}行数据)")
                results["success"].append(test["name"])
            else:
                print(f"  ⚠️  {test['name']:20} - 返回空数据")
                results["failed"].append(test["name"])
        else:
            print(f"  ❌ {test['name']:20} - 接口不存在")
            results["failed"].append(test["name"])
            
    except Exception as e:
        error_msg = str(e)
        
        if "没有权限" in error_msg or "无权限" in error_msg or "权限不足" in error_msg:
            print(f"  🔒 {test['name']:20} - 无权限")
            results["no_permission"].append(test["name"])
        elif "每分钟最多访问" in error_msg or "每小时最多访问" in error_msg or "超过访问频次" in error_msg:
            print(f"  ⏱️  {test['name']:20} - 频率限制")
            results["rate_limited"].append(test["name"])
        else:
            print(f"  ❌ {test['name']:20} - 错误: {error_msg[:50]}")
            results["failed"].append(test["name"])
    
    # 避免频率限制
    import time
    time.sleep(0.5)

# 打印总结
print("\n" + "=" * 60)
print("测试结果总结")
print("=" * 60)

print(f"\n✅ 成功: {len(results['success'])}个接口")
if results['success']:
    print("   " + ", ".join(results['success'][:5]))
    if len(results['success']) > 5:
        print(f"   ... 等共{len(results['success'])}个")

print(f"\n🔒 无权限: {len(results['no_permission'])}个接口")
if results['no_permission']:
    print("   " + ", ".join(results['no_permission'][:5]))
    if len(results['no_permission']) > 5:
        print(f"   ... 等共{len(results['no_permission'])}个")

print(f"\n⏱️  频率限制: {len(results['rate_limited'])}个接口")
if results['rate_limited']:
    print("   " + ", ".join(results['rate_limited']))

print(f"\n❌ 失败: {len(results['failed'])}个接口")
if results['failed']:
    print("   " + ", ".join(results['failed']))

# 建议
print("\n" + "=" * 60)
print("建议")
print("=" * 60)

if len(results['success']) < 5:
    print("⚠️  基础接口可用性较低，请检查:")
    print("   1. Token是否正确")
    print("   2. 账户是否有足够积分")
    print("   3. 访问 https://tushare.pro 查看账户状态")

if results['no_permission']:
    print("\n📌 部分接口需要升级权限:")
    print("   1. 新闻类接口需要单独购买(1000元/年)")
    print("   2. 其他接口需要提升积分等级")
    print("   3. 访问 https://tushare.pro/document/1?doc_id=108 了解权限详情")

if results['rate_limited']:
    print("\n⏰ 遇到频率限制，建议:")
    print("   1. 稍后再试")
    print("   2. 升级账户提高频率限制")
    print("   3. 使用缓存减少API调用")

print("\n测试完成！")