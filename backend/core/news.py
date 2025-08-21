from __future__ import annotations

import datetime as dt
from typing import Dict, Any, List, Optional

from .tushare_client import news as ts_news, major_news as ts_major_news, cctv_news as ts_cctv_news, stock_basic


def _fmt_dt_for_api(days_back: int) -> str:
    start = dt.datetime.now() - dt.timedelta(days=days_back)
    return start.strftime("%Y%m%d %H:%M:%S")


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

    # 1) 快讯（多源聚合）
    flash_sources = ["sina", "wallstreetcn", "10jqka", "eastmoney"]
    flash: List[dict] = []
    for src in flash_sources:
        try:
            df = ts_news(src=src, start_date=start_dt, limit=200)
            for row in _safe_df_to_records(df):
                flash.append(_normalize_news_row(row, src))
        except Exception:
            # 单个源失败不影响整体
            continue

    # 2) 重大新闻
    majors: List[dict] = []
    try:
        df_major = ts_major_news(limit=50)
        for row in _safe_df_to_records(df_major):
            majors.append(_normalize_news_row(row, "major"))
    except Exception:
        pass

    # 3) 新闻联播近 N 天（取3天）
    cctv: List[dict] = []
    try:
        for i in range(min(days_back, 3)):
            day = (dt.date.today() - dt.timedelta(days=i)).strftime("%Y%m%d")
            df_cctv = ts_cctv_news(date=day)
            for row in _safe_df_to_records(df_cctv):
                cctv.append(_normalize_news_row(row, "cctv"))
    except Exception:
        pass

    # 4) 个股相关新闻（基于标题/内容做简单匹配）
    symbol = ts_code.split(".")[0]
    stock_name = _try_get_stock_name(ts_code) or ""
    stock_related: List[dict] = []
    if flash:
        for item in flash:
            text = f"{item.get('title','')} {item.get('content','')}"
            if symbol and symbol in text:
                stock_related.append(item)
            elif stock_name and stock_name in text:
                stock_related.append(item)

    summary = {
        "flash_news_count": len(flash),
        "major_news_count": len(majors),
        "cctv_news_count": len(cctv),
        "stock_news_count": len(stock_related),
        "data_sources": flash_sources + ["major", "cctv"],
    }

    return {
        "summary": summary,
        "flash_news": flash,
        "major_news": majors,
        "stock_news": stock_related,
        "cctv_news": cctv,
    }


def analyze_news_sentiment(news_bundle: Dict[str, Any]) -> Dict[str, Any]:
    """非常简单的基于关键词的情绪分析。"""
    positive_keys = [
        "上涨", "增持", "利好", "突破", "盈利", "扭亏", "改善", "增长", "涨停", "上调",
        "创新高", "回购", "提价", "超预期", "扩产", "订单增加", "中标", "签约",
    ]
    negative_keys = [
        "下跌", "暴跌", "亏损", "预亏", "裁员", "利空", "减持", "处罚", "下调", "破发",
        "违约", "下滑", "爆雷", "降级", "降价", "停产", "亏损扩大", "被调查",
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
    for key in ("flash_news", "major_news", "stock_news"):
        items.extend(news_bundle.get(key) or [])

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


