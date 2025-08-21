import datetime as dt
from typing import Optional, Dict, Any, List, cast, Callable
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

from .tushare_client import stock_basic, daily, anns, pop_notes
from .indicators import compute_indicators, build_tech_signal
from .fundamentals import fetch_fundamentals
from .macro import fetch_macro_snapshot
from .news import fetch_news_summary, format_news_for_llm, analyze_news_sentiment
from nlp.ollama_client import summarize

PRICE_YEARS = 2
MAX_NEWS = 15


def _date_str(days_ago: int) -> str:
    d = dt.date.today() - dt.timedelta(days=days_ago)
    return d.strftime("%Y%m%d")


def resolve_by_name(name_keyword: str, force: bool = False) -> Optional[dict]:
    # 1) 先查本地静态映射，避免频控
    import json, os
    mapping_path = os.path.join(os.path.dirname(__file__), 'symbol_map.json')
    try:
        with open(mapping_path, 'r', encoding='utf-8') as f:
            items = json.load(f)
        kw = str(name_keyword).strip()
        for it in items:
            if kw == it.get('name') or kw in (it.get('aliases') or []):
                return {
                    'ts_code': it['ts_code'],
                    'symbol': it['ts_code'].split('.')[0],
                    'name': it['name'],
                    'market': 'SH' if it['ts_code'].endswith('.SH') else 'SZ' if it['ts_code'].endswith('.SZ') else 'BJ',
                    'list_status': 'L'
                }
    except Exception:
        pass

    # 2) 回退 TuShare 的基础表
    base: pd.DataFrame = stock_basic(force=force)
    if base is None or base.empty:
        return None
    if "name" not in base.columns or "fullname" not in base.columns:
        return None

    kw = str(name_keyword).strip()
    name_col: pd.Series = pd.Series(base["name"], dtype="string")
    name_mask: pd.Series = name_col.str.contains(kw, case=False, regex=False, na=False)  # type: ignore[reportAttributeAccessIssue]
    hit = base[name_mask]
    if hit.empty:
        fullname_col: pd.Series = pd.Series(base["fullname"], dtype="string")
        fullname_mask: pd.Series = fullname_col.str.contains(kw, case=False, regex=False, na=False)  # type: ignore[reportAttributeAccessIssue]
        hit = base[fullname_mask]
        if hit.empty:
            return None

    hit = hit.copy()
    hit["rank"] = 0
    hit.loc[hit["list_status"] != "L", "rank"] += 100
    market_col: pd.Series = pd.Series(hit["market"], dtype="string")
    bj_mask: pd.Series = market_col.str.contains("北交", na=False)  # type: ignore[reportAttributeAccessIssue]
    hit.loc[bj_mask, "rank"] += 10
    name_len: pd.Series = pd.Series(hit["name"], dtype="string").str.len().fillna(999)  # type: ignore[reportAttributeAccessIssue]
    length_diff: pd.Series = (name_len - len(kw)).abs()
    hit["rank"] = cast(pd.Series, hit["rank"]) + length_diff
    by_cols: tuple[str, ...] = ("rank", "market", "ts_code")
    hit = hit.sort_values(by=by_cols).reset_index(drop=True)  # type: ignore[reportCallIssue]
    return hit.iloc[0].to_dict()


def _scorecard(tech: Dict[str, Any], fundamental: Dict[str, Any], macro: Dict[str, Any], sentiment: Dict[str, Any] = None) -> Dict[str, Any]:
    # 新权重分配：技术面40%，情绪面35%，基本面20%，宏观5%
    score_fund = 0.0  # 基本面满分20
    score_tech = 0.0  # 技术面满分40
    score_sentiment = 0.0  # 情绪面满分35
    score_macro = 0.0  # 宏观满分5

    # 基本面评分（满分20）
    latest = (fundamental or {}).get("fina_indicator_latest", {})
    roe = latest.get("roe")
    net_margin = latest.get("netprofit_margin")
    debt_ratio = None
    bal = (fundamental or {}).get("balance_recent") or []
    if bal:
        debt_ratio = bal[0].get("debt_ratio")

    inc = (fundamental or {}).get("income_recent") or []
    rev_trend = 0
    profit_trend = 0
    if inc:
        take = inc[:4]
        revenues = [float(x.get("revenue")) for x in take if x.get("revenue") is not None]
        profits = [float(x.get("n_income")) for x in take if x.get("n_income") is not None]
        if len(revenues) >= 2:
            rev_trend = 1 if revenues[0] >= revenues[-1] else -1
        if len(profits) >= 2:
            profit_trend = 1 if profits[0] >= profits[-1] else -1

    if roe is not None:
        score_fund += max(0.0, min(8.0, float(roe) / 20.0 * 8.0))
    if net_margin is not None:
        score_fund += max(0.0, min(4.0, float(net_margin) / 20.0 * 4.0))
    if debt_ratio is not None:
        dr = float(debt_ratio)
        if dr < 0.3:
            score_fund += 3.0
        elif dr < 0.6:
            score_fund += 2.0
        elif dr < 0.8:
            score_fund += 1.0
    score_fund += (2.0 if rev_trend > 0 else 0.0) + (3.0 if profit_trend > 0 else 0.0)
    score_fund = min(20.0, max(0.0, score_fund))

    # 技术面评分（满分40）
    rsi = tech.get("tech_last_rsi")
    dif = tech.get("tech_last_dif")
    dea = tech.get("tech_last_dea")
    close = tech.get("tech_last_close")
    signal = tech.get("tech_signal") or ""
    
    if rsi is not None:
        if 40 <= rsi <= 60:
            score_tech += 15  # 中性区间，健康
        elif rsi < 30:
            score_tech += 10  # 超卖，可能反弹
        elif rsi > 70:
            score_tech += 5   # 超买，风险
        else:
            score_tech += 8
    
    if dif is not None and dea is not None:
        score_tech += 15 if dif > dea else 5  # 金叉/死叉
    
    if isinstance(signal, str):
        if "收盘<=下轨" in signal:
            score_tech += 8  # 下轨支撑
        elif "收盘>=上轨" in signal:
            score_tech += 3  # 上轨压力
        else:
            score_tech += 5
    
    score_tech = min(40.0, max(0.0, score_tech))

    # 情绪面评分（满分35）
    if sentiment:
        overall = sentiment.get("overall", "neutral")
        percentages = sentiment.get("percentages", {})
        pos_pct = percentages.get("positive", 0)
        neg_pct = percentages.get("negative", 0)
        
        # 基础情绪得分
        if overall == "positive":
            score_sentiment += 20
        elif overall == "neutral":
            score_sentiment += 10
        else:  # negative
            score_sentiment += 5
        
        # 细化评分
        if pos_pct > 60:
            score_sentiment += 10
        elif pos_pct > 40:
            score_sentiment += 7
        elif pos_pct > 20:
            score_sentiment += 4
        
        # 负面新闻惩罚
        if neg_pct > 40:
            score_sentiment -= 5
        elif neg_pct > 20:
            score_sentiment -= 2
        
        score_sentiment = min(35.0, max(0.0, score_sentiment))

    # 宏观评分（满分5）
    m2 = (macro or {}).get("m2_latest", {}).get("m2_yoy")
    on_shibor = (macro or {}).get("shibor_latest", {}).get("on")
    try:
        m2 = float(m2) if m2 is not None else None
    except Exception:
        m2 = None
    try:
        on_shibor = float(on_shibor) if on_shibor is not None else None
    except Exception:
        on_shibor = None
    
    if m2 is not None:
        if m2 >= 8:
            score_macro += 2
        elif m2 >= 5:
            score_macro += 1
    
    if on_shibor is not None:
        if on_shibor <= 1.5:
            score_macro += 2
        elif on_shibor <= 2.0:
            score_macro += 1
    
    score_macro = min(5.0, max(0.0, score_macro))

    total = round(score_fund + score_tech + score_sentiment + score_macro, 1)
    return {
        "score_total": total,
        "score_fundamental": round(score_fund, 1),
        "score_technical": round(score_tech, 1),
        "score_sentiment": round(score_sentiment, 1),
        "score_macro": round(score_macro, 1),
    }


def run_pipeline(
    name_keyword: str,
    force: bool = False,
    progress: Optional[Callable[[str, Optional[Dict[str, Any]]], None]] = None,
) -> Dict[str, Any]:
    def _emit(step: str, payload: Optional[Dict[str, Any]] = None) -> None:
        if progress is not None:
            try:
                progress(step, payload or {})
            except Exception:
                pass
    # 允许直接输入代码以绕开对 stock_basic 的频控：
    def _guess_ts_code(s: str) -> Optional[str]:
        t = s.strip().upper()
        import re
        if re.fullmatch(r"\d{6}\.(SH|SZ|BJ)", t):
            return t
        if re.fullmatch(r"\d{6}", t):
            sym = t
            if sym.startswith(("600", "601", "603", "605", "688")):
                return f"{sym}.SH"
            if sym.startswith(("000", "001", "002", "003", "300", "301")):
                return f"{sym}.SZ"
            if sym.startswith(("430", "83", "87", "88")):
                return f"{sym}.BJ"
        return None

    _emit("resolve:start", {"input": name_keyword})
    ts_code_guess = _guess_ts_code(name_keyword)
    base: Dict[str, Any] = {}
    if ts_code_guess:
        ts_code = ts_code_guess
        base = {"ts_code": ts_code, "symbol": ts_code.split(".")[0], "name": name_keyword}
    else:
        base_resolved = resolve_by_name(name_keyword, force=force)
        if not base_resolved:
            raise ValueError(f"未找到包含“{name_keyword}”的A股")
        base = base_resolved
        ts_code = base["ts_code"]
    _emit("resolve:done", {"base": base})

    end = _date_str(0)
    start = (dt.date.today() - dt.timedelta(days=365 * PRICE_YEARS + 30)).strftime("%Y%m%d")
    _emit("fetch:parallel:start", {"ts_code": ts_code})

    # 并发抓取（受全局限速影响，但可与非TS计算重叠）
    with ThreadPoolExecutor(max_workers=4) as ex:
        fut_px = ex.submit(daily, ts_code, start, end, force)
        fut_fund = ex.submit(fetch_fundamentals, ts_code)
        fut_macro = ex.submit(fetch_macro_snapshot)
        fut_news = ex.submit(fetch_news_summary, ts_code, 7)
        fut_anns = ex.submit(anns, ts_code, MAX_NEWS, force)

        px = fut_px.result()
        fundamental = fut_fund.result()
        news_summary = fut_news.result()
        macro = fut_macro.result()
        news_df = fut_anns.result()

    _emit("fetch:parallel:done", {
        "px_rows": int(0 if px is None else len(px)),
        "fundamental_keys": list(fundamental.keys() if isinstance(fundamental, dict) else []),
        "macro_keys": list(macro.keys() if isinstance(macro, dict) else []),
    })
    tech: Dict[str, Any] = {}
    if not px.empty:
        px = px.sort_values("trade_date").reset_index(drop=True)
        px = compute_indicators(px)
        last = px.iloc[-1]
        tech = {
            "tech_last_close": float(last.get("close")) if pd.notna(last.get("close")) else None,
            "tech_last_rsi": round(float(last.get("rsi14")), 2) if pd.notna(last.get("rsi14")) else None,
            "tech_last_macd": round(float(last.get("macd")), 4) if pd.notna(last.get("macd")) else None,
            "tech_last_dif": round(float(last.get("dif")), 4) if pd.notna(last.get("dif")) else None,
            "tech_last_dea": round(float(last.get("dea")), 4) if pd.notna(last.get("dea")) else None,
            "tech_signal": build_tech_signal(last),
        }
    _emit("compute:technical", tech)

    # fundamental 已在并发阶段获取

    # 获取公司公告
    news_list: List[Dict[str, Any]] = []
    if not news_df.empty:
        news_df = news_df.sort_values("ann_date", ascending=False).head(MAX_NEWS)
        for _, r in news_df.iterrows():
            news_list.append(
                {
                    "ann_date": r.get("ann_date"),
                    "title": r.get("title"),
                    "seq": r.get("ann_id") or r.get("seq"),
                }
            )
    
    _emit("fetch:announcements", {"count": len(news_list)})
    # 获取全面的新闻资讯（已并发获取）
    news_sentiment = analyze_news_sentiment(news_summary)
    _emit("compute:news_sentiment", news_sentiment)
    
    macro = fetch_macro_snapshot()

    score = _scorecard(tech, fundamental, macro, news_sentiment)
    _emit("compute:scorecard", score)

    # 准备LLM分析的数据
    llm_data = {
        "股票基本信息": base,
        "基本面摘要": fundamental,
        "技术面末日": tech,
        "公告列表": news_list,
        "新闻资讯": format_news_for_llm(news_summary, max_items=10),
        "新闻情绪": news_sentiment,
        "宏观快照": macro,
        "评分卡": score,
    }
    
    _emit("llm:summary:start", None)
    llm_summary = summarize(llm_data)
    _emit("llm:summary:done", {"length": len(llm_summary or "")})

    # 拉取抓取备注（限额/权限/缓存）
    notes = pop_notes()

    return {
        "basic": base,
        "technical": tech,
        "fundamental": fundamental,
        "announcements": news_list,  # 公司公告
        "news": {  # 新闻资讯
            "summary": news_summary.get("summary"),
            "sentiment": news_sentiment,
            "flash_news": news_summary.get("flash_news", [])[:10],  # 最新10条快讯
            "major_news": news_summary.get("major_news", [])[:5],   # 最新5条重大新闻
            "stock_news": news_summary.get("stock_news", [])[:10],  # 个股相关新闻
            "cctv_news": news_summary.get("cctv_news", [])[:3],     # 新闻联播要点
        },
        "macro": macro,
        "scorecard": score,
        "llm_summary": llm_summary,
        "notes": notes,
    }


