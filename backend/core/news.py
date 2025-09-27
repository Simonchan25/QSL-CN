from __future__ import annotations

import datetime as dt
from typing import Dict, Any, List, Optional

from .tushare_client import news as ts_news, major_news as ts_major_news, stock_basic, _call_api
from .advanced_data_client import AdvancedDataClient
advanced_client = AdvancedDataClient()


def _fmt_dt_for_api(days_back: int) -> str:
    """TuShare news 接口需要 datetime 格式（YYYY-MM-DD HH:MM:SS）"""
    start = dt.datetime.now() - dt.timedelta(days=days_back)
    return start.strftime("%Y-%m-%d %H:%M:%S")


def _normalize_news_row(row: dict, src: str) -> dict:
    return {
        "src": src,
        "datetime": row.get("datetime") or row.get("time") or row.get("date") or "",
        "title": row.get("title") or row.get("summary") or "",
        "url": row.get("url") or row.get("link") or "",
        "content": row.get("content") or row.get("text") or "",
    }


def _safe_df_to_records(df) -> List[dict]:
    try:
        return df.to_dict(orient="records")
    except Exception:
        return []


def _try_get_stock_name(ts_code: str) -> Optional[str]:
    try:
        base = stock_basic()
        if base is not None and not base.empty:
            hit = base[base["ts_code"] == ts_code]
            if not hit.empty:
                return str(hit.iloc[0].get("name") or "")
    except Exception:
        pass
    return None


def fetch_news_summary(ts_code: str, days_back: int = 7) -> Dict[str, Any]:
    start_dt = _fmt_dt_for_api(days_back)
    end_dt = dt.datetime.now().strftime("%Y%m%d")

    # 1) 快讯（多源聚合）- 扩展新闻源，增加调试信息
    flash_sources = ["sina", "wallstreetcn", "10jqka", "eastmoney", "yuncaijing", "cls"]
    flash: List[dict] = []
    successful_sources = []

    for src in flash_sources:
        try:
            df = ts_news(src=src, start_date=start_dt, end_date=end_dt, limit=200)
            if df is not None and not df.empty:
                successful_sources.append(f"{src}({len(df)}条)")
                for row in _safe_df_to_records(df):
                    flash.append(_normalize_news_row(row, src))
        except Exception as e:
            # 单个源失败不影响整体，但记录错误
            print(f"[新闻源] {src} 获取失败: {e}")
            continue

    if successful_sources:
        print(f"[新闻源] 成功获取: {', '.join(successful_sources)}")
    else:
        print(f"[新闻源] 警告：所有快讯源都获取失败，时间范围 {start_dt}-{end_dt}")

    # 2) 重大新闻
    majors: List[dict] = []
    try:
        # major_news 需要日期参数
        df_major = ts_major_news(start_date=start_dt, end_date=end_dt, limit=50)
        for row in _safe_df_to_records(df_major):
            majors.append(_normalize_news_row(row, "major"))
    except Exception as e:
        print(f"[新闻源] 获取重大新闻失败: {e}")

    # 3) 新闻联播近 N 天（5000积分权限）
    cctv: List[dict] = []
    try:
        # 直接使用advanced_client的cctv_news函数
        # 获取最近几天的新闻联播
        for days_ago in range(min(days_back, 3)):  # 最多获取3天
            date = (dt.datetime.now() - dt.timedelta(days=days_ago)).strftime("%Y%m%d")
            df_cctv = advanced_client.cctv_news(date=date)
            if df_cctv is not None and not df_cctv.empty:
                for row in _safe_df_to_records(df_cctv):
                    cctv.append({
                        "src": "cctv",
                        "datetime": row.get("date", date),
                        "title": row.get("title", ""),
                        "content": row.get("content", ""),
                        "url": ""
                    })
                print(f"[新闻源] CCTV新闻联播 {date}: {len(df_cctv)}条")
    except Exception as e:
        # CCTV新闻需要更高权限，失败不影响其他功能
        print(f"[新闻源] CCTV新闻联播获取失败（需要5000积分权限）: {e}")

    # 4) 公司新闻 - 5000积分权限可使用ts_code参数
    company_news: List[dict] = []
    try:
        # news接口在积分足够时支持ts_code参数
        df_company = _call_api('news', ts_code=ts_code, start_date=start_dt, end_date=end_dt, limit=120)
        if df_company is not None and not df_company.empty:
            for row in _safe_df_to_records(df_company):
                # 注意：title可能为None，内容在content中
                item = _normalize_news_row(row, "company")
                # 如果title为空，从 content 提取
                if not item.get('title') and item.get('content'):
                    item['title'] = item['content'][:100] + '...' if len(item['content']) > 100 else item['content']
                company_news.append(item)
            print(f"[新闻源] 公司新闻: {len(company_news)}条")
    except Exception as e:
        # 如果权限不足或API错误，不影响其他功能
        print(f"[新闻源] 公司新闻获取失败: {e}")

    # 5) 个股相关新闻（使用智能分层匹配）
    symbol = ts_code.split(".")[0]
    stock_name = _try_get_stock_name(ts_code) or ""

    print(f"[新闻匹配] 目标股票: {stock_name} ({symbol})")

    # 先使用智能分层匹配作为主方案（稳定快速）
    from .smart_news_matcher import smart_matcher

    # 扩展候选新闻源
    candidate_sources = company_news + flash + majors + cctv

    if candidate_sources:
        print(f"[新闻匹配] 候选新闻总数: {len(candidate_sources)}")

        # 提前获取公告数据用于增强匹配
        announcements = None
        try:
            from .tushare_client import anns as ts_anns
            ann_df = ts_anns(ts_code=ts_code, limit=10)
            if ann_df is not None and not ann_df.empty:
                announcements = []
                for _, row in ann_df.iterrows():
                    announcements.append({
                        'title': row.get('title', ''),
                        'ann_date': row.get('ann_date', '')
                    })
                print(f"[新闻匹配] 获取到{len(announcements)}条公告用于增强匹配")
        except:
            pass

        # 使用智能分层匹配（包含增强功能）
        import os
        # 默认启用LLM（因为你说Ollama一直运行）
        use_llm = os.getenv("USE_LLM_FOR_NEWS", "1") == "1"  # 默认启用

        matches = smart_matcher.match_news(
            ts_code=ts_code,
            news_items=candidate_sources,
            include_competitor=True,
            include_industry=True,
            include_sector=False,
            announcements=announcements,
            use_llm=use_llm
        )

        # 格式化结果（仍需要smart_matcher来格式化）
        from .smart_news_matcher import smart_matcher
        result = smart_matcher.format_results(matches)
        stock_related = result['news']
        stats = result['stats']

        print(f"[新闻匹配] 总计: {stats['total']}条 (直接: {stats['direct']}, 竞品: {stats.get('competitor', 0)}, 行业: {stats['industry']})")
        print(f"[新闻匹配] 质量分布: 高{stats['high_confidence']}, 中{stats['medium_confidence']}, 低{stats['low_confidence']}")

        matched_count = len(stock_related)
    else:
        stock_related = []
        matched_count = 0

    print(f"[新闻匹配] 最终匹配到相关新闻: {matched_count} 条")

    # 6) 补充公司公告（公告默认为直接相关）
    announcements = []
    try:
        from .tushare_client import anns as ts_anns
        df_anns = ts_anns(ts_code=ts_code, limit=20)
        if df_anns is not None and len(df_anns) > 0:
            print(f"[新闻匹配] 获取到公告: {len(df_anns)} 条")
            for row in _safe_df_to_records(df_anns):
                ann_item = {
                    "src": "ann",
                    "datetime": row.get("ann_date", ""),
                    "title": row.get("title", ""),
                    "url": "",
                    "content": "",
                    # 公告默认标记为直接相关
                    'relevance_type': 'direct',
                    'match_score': 100,
                    'matched_terms': ['公司公告'],
                    'confidence': 'high'
                }
                stock_related.append(ann_item)
                matched_count += 1

    except Exception as e:
        print(f"[新闻匹配] 获取公告失败: {e}")

    print(f"[新闻匹配] 最终匹配结果: {len(stock_related)} 条（含公告）")

    # 去重（按标题+日期）和排序优化
    seen = set()
    unique_stock_news = []
    for item in stock_related:
        key = (item.get("title"), item.get("datetime"))
        if key in seen:
            continue
        seen.add(key)
        unique_stock_news.append(item)

    # 优化排序：先按匹配分数降序，再按时间降序
    unique_stock_news.sort(key=lambda x: (
        x.get("match_score", 0),  # 首先按匹配分数
        x.get("datetime") or ""   # 然后按时间
    ), reverse=True)

    summary = {
        "flash_news_count": len(flash),
        "company_news_count": len(company_news),
        "major_news_count": len(majors),
        "cctv_news_count": len(cctv),
        "stock_news_count": len(unique_stock_news),
        "data_sources": flash_sources + ["company", "major", "ann", "cctv"],
    }

    return {
        "summary": summary,
        "flash_news": flash,
        "major_news": majors,
        "company_news": company_news,
        "stock_news": unique_stock_news,
        "cctv_news": cctv,
    }


def analyze_news_sentiment(news_bundle: Dict[str, Any]) -> Dict[str, Any]:
    """非常简单的基于关键词的情绪分析。"""
    positive_keys = [
        "上涨", "增持", "利好", "突破", "盈利", "扭亏", "改善", "增长", "涨停", "上调",
        "创新高", "回购", "提价", "超预期", "扩产", "订单增加", "中标", "签约",
        # 银行业相关正面
        "净息差改善", "资本充足率提升", "不良下降", "不良率下降", "拨备覆盖率提升", "贷款增长", "存款增长",
    ]
    negative_keys = [
        "下跌", "暴跌", "亏损", "预亏", "裁员", "利空", "减持", "处罚", "下调", "破发",
        "违约", "下滑", "爆雷", "降级", "降价", "停产", "亏损扩大", "被调查",
        # 银行业相关负面
        "净息差收窄", "资本充足率下降", "不良上升", "不良率上升", "拨备不足", "信用风险暴露",
    ]

    def judge(text: str) -> str:
        for k in positive_keys:
            if k in text:
                return "positive"
        for k in negative_keys:
            if k in text:
                return "negative"
        return "neutral"

    items: List[dict] = []
    
    # 处理输入数据类型兼容性：支持字典和列表两种格式
    if isinstance(news_bundle, list):
        # 如果输入是列表，直接使用
        items = news_bundle
    elif isinstance(news_bundle, dict):
        # 如果输入是字典，从指定键中提取新闻列表
        for key in ("flash_news", "major_news", "company_news", "stock_news"):
            items.extend(news_bundle.get(key) or [])
    else:
        # 如果输入格式不正确，返回中性结果
        print(f"[警告] analyze_news_sentiment 收到不支持的数据类型: {type(news_bundle)}")
        return {
            "overall": "neutral",
            "counts": {"positive": 0, "negative": 0, "neutral": 1},
            "percentages": {"positive": 0.0, "negative": 0.0, "neutral": 100.0}
        }

    counts = {"positive": 0, "negative": 0, "neutral": 0}
    for it in items:
        text = f"{it.get('title','')} {it.get('content','')}"
        label = judge(text)
        counts[label] += 1

    total = max(1, sum(counts.values()))
    percentages = {k: round(v * 100.0 / total, 1) for k, v in counts.items()}
    overall = (
        "positive" if counts["positive"] > counts["negative"] else
        "negative" if counts["negative"] > counts["positive"] else
        "neutral"
    )

    return {"counts": counts, "percentages": percentages, "overall": overall}


def format_news_for_llm(news_bundle: Dict[str, Any], max_items: int = 10) -> List[str]:
    """将新闻汇总为适合提示词的小条目列表。"""
    lines: List[str] = []

    def take(items: List[dict], n: int) -> List[dict]:
        return (items or [])[:n]

    for it in take(news_bundle.get("major_news") or [], 5):
        lines.append(f"[重大] {it.get('datetime','')}: {it.get('title','')}")
    for it in take(news_bundle.get("flash_news") or [], max_items):
        lines.append(f"[快讯] {it.get('datetime','')}: {it.get('title','')}")
    for it in take(news_bundle.get("stock_news") or [], max_items):
        lines.append(f"[个股] {it.get('datetime','')}: {it.get('title','')}")
    for it in take(news_bundle.get("cctv_news") or [], 3):
        lines.append(f"[联播] {it.get('datetime','')}: {it.get('title','')}")

    return lines
