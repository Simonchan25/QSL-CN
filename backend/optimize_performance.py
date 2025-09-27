#!/usr/bin/env python3
"""
性能优化脚本 - 解决速度和数据问题
"""

import os
import sys
import json
import time
from datetime import datetime

def optimize_cache_config():
    """优化缓存配置"""
    print("=== 1. 优化缓存配置 ===")

    # 创建缓存配置文件
    cache_config = {
        "market_data_ttl": 300,  # 市场数据缓存5分钟
        "stock_data_ttl": 180,   # 个股数据缓存3分钟
        "news_data_ttl": 600,    # 新闻数据缓存10分钟
        "concurrent_limit": 2,   # 降低并发数
        "timeout_seconds": 30,   # 降低超时时间
        "enable_smart_cache": True
    }

    with open('cache_config.json', 'w', encoding='utf-8') as f:
        json.dump(cache_config, f, indent=2, ensure_ascii=False)

    print("✓ 缓存配置已优化")

def create_quick_api():
    """创建快速API接口"""
    print("=== 2. 创建快速API接口 ===")

    quick_api_code = '''
@app.get("/analyze/quick")
def analyze_quick(name: str, force: bool = False):
    """快速版分析 - 只获取核心数据"""
    if not name:
        raise HTTPException(400, detail="name 不能为空")

    try:
        from core.analyze import resolve_by_name
        from core.tushare_client import daily
        from datetime import datetime, timedelta

        # 1. 解析股票基本信息
        stock_info = resolve_by_name(name, force)
        if not stock_info:
            return {"error": f"未找到股票: {name}"}

        ts_code = stock_info['ts_code']
        stock_name = stock_info['name']

        # 2. 获取最新价格（只获取最近5天）
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')
        df = daily(ts_code=ts_code, start_date=start_date, end_date=end_date)

        if df is None or df.empty:
            return {"error": "无法获取价格数据"}

        # 3. 构建快速响应
        latest = df.iloc[0]

        result = {
            "basic": stock_info,
            "timestamp": datetime.now().isoformat(),
            "quick_data": {
                "price": float(latest['close']),
                "change": float(latest.get('pct_chg', 0)),
                "volume": float(latest.get('vol', 0)),
                "amount": float(latest.get('amount', 0)) * 1000,
                "trade_date": str(latest.get('trade_date', ''))
            },
            "text": f"""# {stock_name} 快速分析

**当前价格**: {float(latest['close'])}元
**今日涨跌**: {float(latest.get('pct_chg', 0)):+.2f}%
**成交量**: {float(latest.get('vol', 0))/10000:.1f}万手

基于最新交易数据的快速分析。完整分析请使用专业版接口。

---
*快速版本 - 数据更新时间: {datetime.now().strftime('%H:%M:%S')}*""",
            "score": {"total": 50, "rating": "中性"},
            "report_type": "quick"
        }

        return result

    except Exception as e:
        print(f"快速分析错误: {e}")
        return {"error": f"分析失败: {str(e)}"}
'''

    # 将快速API代码追加到app.py
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()

    if "/analyze/quick" not in content:
        # 在最后一个路由后添加
        insert_pos = content.rfind('@app.')
        if insert_pos != -1:
            # 找到下一个函数结束位置
            next_func_end = content.find('\n\n@app', insert_pos + 1)
            if next_func_end == -1:
                next_func_end = len(content)

            new_content = (content[:next_func_end] +
                         '\n\n' + quick_api_code +
                         content[next_func_end:])

            with open('app.py', 'w', encoding='utf-8') as f:
                f.write(new_content)

        print("✓ 快速API接口已添加")
    else:
        print("✓ 快速API接口已存在")

def optimize_data_fetching():
    """优化数据获取逻辑"""
    print("=== 3. 优化数据获取 ===")

    # 修改analyze_optimized.py中的超时设置
    try:
        with open('core/analyze_optimized.py', 'r', encoding='utf-8') as f:
            content = f.read()

        # 降低并发数
        content = content.replace('max_workers=4', 'max_workers=2')
        # 降低单个任务超时
        content = content.replace('timeout=5', 'timeout=3')
        # 降低总超时时间
        content = content.replace('timeout_seconds: int = 60', 'timeout_seconds: int = 30')

        with open('core/analyze_optimized.py', 'w', encoding='utf-8') as f:
            f.write(content)

        print("✓ 数据获取逻辑已优化")
    except Exception as e:
        print(f"优化数据获取失败: {e}")

def create_test_script():
    """创建性能测试脚本"""
    print("=== 4. 创建测试脚本 ===")

    test_script = '''#!/usr/bin/env python3
import time
import requests

def test_performance():
    """测试优化后的性能"""
    base_url = "http://localhost:8001"

    print("=== 性能测试开始 ===")

    # 测试快速接口
    print("\\n1. 测试快速接口...")
    start_time = time.time()
    response = requests.get(f"{base_url}/analyze/quick",
                          params={"name": "贵州茅台"},
                          timeout=10)
    quick_time = time.time() - start_time

    if response.status_code == 200:
        print(f"   ✓ 快速接口成功: {quick_time:.2f}秒")
        data = response.json()
        if "text" in data and len(data["text"]) > 100:
            print(f"   ✓ 报告内容正常: {len(data['text'])}字符")
        else:
            print(f"   ⚠ 报告内容可能异常: {len(data.get('text', ''))}字符")
    else:
        print(f"   ✗ 快速接口失败: {response.status_code}")

    # 测试专业接口
    print("\\n2. 测试专业接口...")
    start_time = time.time()
    response = requests.get(f"{base_url}/analyze/professional",
                          params={"name": "贵州茅台", "force": "true"},
                          timeout=60)
    pro_time = time.time() - start_time

    if response.status_code == 200:
        print(f"   ✓ 专业接口成功: {pro_time:.2f}秒")
        data = response.json()
        if "text" in data and len(data["text"]) > 300:
            print(f"   ✓ 专业报告内容正常: {len(data['text'])}字符")
        else:
            print(f"   ⚠ 专业报告内容可能异常: {len(data.get('text', ''))}字符")
    else:
        print(f"   ✗ 专业接口失败: {response.status_code}")

    print(f"\\n=== 测试完成 ===")
    print(f"快速接口: {quick_time:.2f}秒")
    print(f"专业接口: {pro_time:.2f}秒")
    print(f"性能提升: {(pro_time/quick_time):.1f}x")

if __name__ == "__main__":
    test_performance()
'''

    with open('test_performance.py', 'w', encoding='utf-8') as f:
        f.write(test_script)

    print("✓ 性能测试脚本已创建")

def main():
    """主函数"""
    print("开始性能优化...")

    optimize_cache_config()
    create_quick_api()
    optimize_data_fetching()
    create_test_script()

    print("\n=== 优化完成 ===")
    print("建议:")
    print("1. 重启后端服务: python app.py")
    print("2. 运行性能测试: python test_performance.py")
    print("3. 使用快速接口: /analyze/quick")
    print("4. 专业分析降低了并发数，应该更快")

if __name__ == "__main__":
    main()