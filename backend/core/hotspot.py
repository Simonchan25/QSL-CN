from __future__ import annotations

import datetime as dt
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

from .tushare_client import stock_basic, daily, news as ts_news, major_news
from .indicators import compute_indicators, build_tech_signal
from .fundamentals import fetch_fundamentals
from .news import analyze_news_sentiment
from nlp.ollama_client import summarize_hotspot


def search_hotspot_news(keyword: str, days_back: int = 3) -> Dict[str, Any]:
    """搜索热点概念相关新闻"""
    start_dt = (dt.datetime.now() - dt.timedelta(days=days_back)).strftime("%Y%m%d %H:%M:%S")
    
    # 搜索多个新闻源
    sources = ["sina", "wallstreetcn", "10jqka", "eastmoney"]
    all_news = []
    
    for src in sources:
        try:
            df = ts_news(src=src, start_date=start_dt, limit=500)
            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    title = str(row.get("title", ""))
                    content = str(row.get("content", ""))
                    if keyword in title or keyword in content:
                        all_news.append({
                            "source": src,
                            "datetime": row.get("datetime"),
                            "title": title,
                            "content": content[:200],  # 截取前200字
                        })
        except Exception:
            continue
    
    # 搜索重大新闻
    try:
        df_major = major_news(limit=100)
        if df_major is not None and not df_major.empty:
            for _, row in df_major.iterrows():
                title = str(row.get("title", ""))
                content = str(row.get("content", ""))
                if keyword in title or keyword in content:
                    all_news.append({
                        "source": "major",
                        "datetime": row.get("datetime"),
                        "title": title,
                        "content": content[:200],
                    })
    except Exception:
        pass
    
    # 按时间排序
    all_news.sort(key=lambda x: x.get("datetime", ""), reverse=True)
    
    return {
        "keyword": keyword,
        "news_count": len(all_news),
        "news_list": all_news[:20],  # 返回最新20条
    }


def find_related_stocks(keyword: str, force: bool = False) -> List[Dict[str, Any]]:
    """根据关键词查找相关股票"""
    base = stock_basic(force=force)
    if base is None or base.empty:
        return []
    
    related = []
    keyword_lower = keyword.lower()
    
    for _, row in base.iterrows():
        if row.get("list_status") != "L":  # 只考虑上市股票
            continue
            
        score = 0
        name = str(row.get("name", "")).lower()
        fullname = str(row.get("fullname", "")).lower()
        industry = str(row.get("industry", "")).lower()
        
        # 名称匹配
        if keyword_lower in name:
            score += 10
        elif keyword_lower in fullname:
            score += 5
        
        # 行业匹配
        if keyword_lower in industry:
            score += 3
        
        # 概念关联（简单关键词映射）
        concept_map = {
            "脑机": ["脑科学", "神经", "接口", "医疗器械", "人工智能"],
            "ai": ["人工智能", "算法", "机器学习", "大数据", "云计算"],
            "新能源": ["锂电", "光伏", "风电", "储能", "充电桩"],
            "半导体": ["芯片", "集成电路", "晶圆", "封测", "设备"],
        }
        
        for concept, keywords in concept_map.items():
            if keyword_lower in concept or concept in keyword_lower:
                for kw in keywords:
                    if kw in name or kw in fullname or kw in industry:
                        score += 2
                        break
        
        if score > 0:
            related.append({
                "ts_code": row.get("ts_code"),
                "name": row.get("name"),
                "industry": row.get("industry"),
                "market": row.get("market"),
                "relevance_score": score,
            })
    
    # 按相关度排序
    related.sort(key=lambda x: x["relevance_score"], reverse=True)
    return related[:30]  # 返回前30个最相关的


def analyze_stock_brief(ts_code: str, force: bool = False) -> Dict[str, Any]:
    """快速分析单个股票的核心指标"""
    try:
        # 获取最近价格数据
        end = dt.date.today().strftime("%Y%m%d")
        start = (dt.date.today() - dt.timedelta(days=60)).strftime("%Y%m%d")
        px = daily(ts_code, start, end, force)
        
        tech_score = 0
        price_change = None
        
        if px is not None and not px.empty:
            px = px.sort_values("trade_date").reset_index(drop=True)
            px = compute_indicators(px)
            
            if len(px) >= 2:
                last = px.iloc[-1]
                prev = px.iloc[-2]
                price_change = round((float(last["close"]) - float(prev["close"])) / float(prev["close"]) * 100, 2)
                
                # 简化的技术评分
                rsi = last.get("rsi14")
                if pd.notna(rsi):
                    if 40 <= rsi <= 60:
                        tech_score += 50
                    elif rsi < 30:
                        tech_score += 30
                    elif rsi > 70:
                        tech_score += 20
                    else:
                        tech_score += 35
                
                dif = last.get("dif")
                dea = last.get("dea")
                if pd.notna(dif) and pd.notna(dea):
                    tech_score += 30 if dif > dea else 10
        
        # 获取基本面关键指标
        fundamental = fetch_fundamentals(ts_code)
        fund_score = 0
        
        if fundamental:
            latest = fundamental.get("fina_indicator_latest", {})
            roe = latest.get("roe")
            if roe and float(roe) > 15:
                fund_score += 40
            elif roe and float(roe) > 10:
                fund_score += 25
            elif roe and float(roe) > 5:
                fund_score += 15
            
            inc = fundamental.get("income_recent", [])
            if inc and len(inc) >= 2:
                rev1 = inc[0].get("revenue")
                rev2 = inc[1].get("revenue")
                if rev1 and rev2 and float(rev1) > float(rev2):
                    fund_score += 30
        
        return {
            "ts_code": ts_code,
            "price_change_pct": price_change,
            "tech_score": min(100, tech_score),
            "fund_score": min(100, fund_score),
            "total_score": min(100, (tech_score * 0.6 + fund_score * 0.4)),
        }
    except Exception:
        return {
            "ts_code": ts_code,
            "price_change_pct": None,
            "tech_score": 0,
            "fund_score": 0,
            "total_score": 0,
        }


def analyze_hotspot(keyword: str, force: bool = False) -> Dict[str, Any]:
    """分析热点概念"""
    
    # 1. 搜索相关新闻
    news_data = search_hotspot_news(keyword)
    
    # 2. 查找相关股票
    related_stocks = find_related_stocks(keyword, force)
    
    if not related_stocks:
        return {
            "keyword": keyword,
            "news": news_data,
            "stocks": [],
            "industry_distribution": {},
            "summary": f"未找到与'{keyword}'相关的A股标的",
        }
    
    # 3. 并发分析每个股票
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_stock = {
            executor.submit(analyze_stock_brief, stock["ts_code"], force): stock
            for stock in related_stocks[:20]  # 只分析前20个最相关的
        }
        
        analyzed_stocks = []
        for future in as_completed(future_to_stock):
            stock = future_to_stock[future]
            try:
                analysis = future.result()
                analyzed_stocks.append({
                    **stock,
                    **analysis,
                })
            except Exception:
                analyzed_stocks.append({
                    **stock,
                    "price_change_pct": None,
                    "tech_score": 0,
                    "fund_score": 0,
                    "total_score": 0,
                })
    
    # 4. 综合评分排序
    for stock in analyzed_stocks:
        # 综合得分 = 相关度20% + 技术面40% + 基本面40%
        stock["final_score"] = round(
            stock["relevance_score"] * 2 +  # 相关度满分20
            stock["tech_score"] * 0.4 +
            stock["fund_score"] * 0.4,
            1
        )
    
    analyzed_stocks.sort(key=lambda x: x["final_score"], reverse=True)
    
    # 5. 行业分布统计
    industry_dist = {}
    for stock in analyzed_stocks:
        industry = stock.get("industry", "未知")
        industry_dist[industry] = industry_dist.get(industry, 0) + 1
    
    # 按数量排序
    industry_dist = dict(sorted(industry_dist.items(), key=lambda x: x[1], reverse=True))
    
    # 6. 新闻情绪分析
    news_texts = [n["title"] + " " + n.get("content", "") for n in news_data["news_list"]]
    sentiment = analyze_news_sentiment({"flash_news": [{"title": t, "content": ""} for t in news_texts]})
    
    return {
        "keyword": keyword,
        "news": news_data,
        "news_sentiment": sentiment,
        "stocks": analyzed_stocks[:10],  # 返回前10个
        "industry_distribution": industry_dist,
        "stock_count": len(related_stocks),
        "analyzed_count": len(analyzed_stocks),
    }