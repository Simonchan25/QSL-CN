#!/usr/bin/env python3
"""
测试新闻功能
"""

import os
import sys
from dotenv import load_dotenv
from pprint import pprint

# 加载环境变量
load_dotenv()

print("="*60)
print("新闻功能测试")
print("="*60)

# 1. 测试免费版新闻接口
print("\n【1. 测试免费版新闻接口】")
print("-"*40)

try:
    import tushare as ts
    
    # 获取最新新闻
    print("获取最新财经新闻（免费版）...")
    try:
        news_df = ts.get_latest_news(top=5, show_content=True)
    except Exception as e:
        print(f"❌ 免费版接口 get_latest_news 抛错: {e}")
        news_df = None
    
    if news_df is not None and not news_df.empty:
        print(f"✅ 获取到 {len(news_df)} 条新闻")
        for idx, row in news_df.head(3).iterrows():
            print(f"\n新闻 {idx+1}:")
            print(f"  标题: {row.get('title', 'N/A')}")
            print(f"  时间: {row.get('time', 'N/A')}")
            print(f"  链接: {row.get('url', 'N/A')[:50]}...")
            content = row.get('content', '')
            if content:
                print(f"  内容: {content[:100]}...")
        else:
            print("❌ 获取新闻失败或返回空数据（免费版接口可能不稳定）")
        
except Exception as e:
    print(f"❌ 免费版接口测试失败: {e}")

print()

# 2. 测试Pro版新闻接口
print("\n【2. 测试Pro版新闻接口】")
print("-"*40)

from core.tushare_client import news, major_news, cctv_news

# 测试快讯接口
print("\n测试新闻快讯接口...")
sources = ["sina", "wallstreetcn", "10jqka", "eastmoney"]

for src in sources:
    try:
        df = news(src=src, limit=2)
        if df is not None and not df.empty:
            print(f"✅ {src}: 获取到 {len(df)} 条快讯")
        else:
            print(f"⚠️  {src}: 无数据")
    except Exception as e:
        error_msg = str(e)
        if "权限" in error_msg:
            print(f"🔒 {src}: 需要权限")
        else:
            print(f"❌ {src}: {error_msg[:50]}")

# 测试重大新闻
print("\n测试重大新闻接口...")
try:
    df = major_news(limit=5)
    if df is not None and not df.empty:
        print(f"✅ 获取到 {len(df)} 条重大新闻")
    else:
        print("⚠️  无重大新闻数据")
except Exception as e:
    error_msg = str(e)
    if "权限" in error_msg:
        print(f"🔒 需要权限访问重大新闻")
    else:
        print(f"❌ 错误: {error_msg[:50]}")

# 测试新闻联播
print("\n测试新闻联播接口...")
try:
    from datetime import datetime
    today = datetime.now().strftime("%Y%m%d")
    df = cctv_news(date=today)
    if df is not None and not df.empty:
        print(f"✅ 获取到今日新闻联播 {len(df)} 条")
    else:
        print("⚠️  无新闻联播数据")
except Exception as e:
    error_msg = str(e)
    if "权限" in error_msg:
        print(f"🔒 需要权限访问新闻联播")
    else:
        print(f"❌ 错误: {error_msg[:50]}")

print()

# 3. 测试新闻汇总功能
print("\n【3. 测试新闻汇总功能】")
print("-"*40)

from core.news import fetch_news_summary, analyze_news_sentiment

try:
    print("获取7天内的新闻汇总...")
    news_data = fetch_news_summary(ts_code="600519.SH", days_back=7)
    
    if news_data:
        summary = news_data.get("summary", {})
        print(f"✅ 新闻汇总成功:")
        print(f"  - 快讯数量: {summary.get('flash_news_count', 0)}")
        print(f"  - 重大新闻: {summary.get('major_news_count', 0)}")
        print(f"  - 新闻联播: {summary.get('cctv_news_count', 0)}")
        print(f"  - 个股相关: {summary.get('stock_news_count', 0)}")
        print(f"  - 数据来源: {', '.join(summary.get('data_sources', []))}")
        
        # 分析情绪
        sentiment = analyze_news_sentiment(news_data)
        print(f"\n新闻情绪分析:")
        print(f"  - 积极: {sentiment['percentages']['positive']}%")
        print(f"  - 消极: {sentiment['percentages']['negative']}%")
        print(f"  - 中性: {sentiment['percentages']['neutral']}%")
        print(f"  - 整体情绪: {sentiment['overall']}")
        
        # 显示部分快讯
        if news_data.get("flash_news"):
            print(f"\n最新快讯 (前3条):")
            for i, item in enumerate(news_data["flash_news"][:3], 1):
                print(f"  {i}. [{item.get('datetime')}] {item.get('title')}")
                
except Exception as e:
    print(f"❌ 新闻汇总失败: {e}")

print()

# 4. 测试完整分析流程（包含新闻）
print("\n【4. 测试完整分析流程】")
print("-"*40)

from core.analyze import run_pipeline

try:
    print("运行完整分析（包含新闻）...")
    result = run_pipeline("茅台", force=False)
    
    if result:
        # 检查新闻数据
        news_info = result.get("news", {})
        
        if news_info:
            print("✅ 新闻数据已整合到分析结果中")
            
            # 显示新闻统计
            if news_info.get("summary"):
                print(f"  新闻统计: {news_info['summary']}")
            
            # 显示情绪分析
            if news_info.get("sentiment"):
                sentiment = news_info["sentiment"]
                print(f"  市场情绪: {sentiment.get('overall', 'N/A')}")
            
            # 显示部分新闻
            if news_info.get("flash_news"):
                print(f"  最新快讯数: {len(news_info['flash_news'])}")
            if news_info.get("major_news"):
                print(f"  重大新闻数: {len(news_info['major_news'])}")
            if news_info.get("stock_news"):
                print(f"  个股新闻数: {len(news_info['stock_news'])}")
        else:
            print("⚠️  分析结果中无新闻数据")
            
except Exception as e:
    print(f"❌ 完整分析失败: {e}")
    import traceback
    traceback.print_exc()

print()
print("="*60)
print("测试完成!")
print("\n说明:")
print("1. 免费版TuShare可以获取基础新闻")
print("2. Pro版新闻接口需要相应权限")
print("3. 系统已实现新闻缓存机制")
print("4. 新闻数据已整合到股票分析流程中")