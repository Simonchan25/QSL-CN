"""
北向资金数据获取助手
使用 moneyflow_hsgt 接口获取沪深港通资金流向
"""

import pandas as pd
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from .tushare_client import moneyflow_hsgt
from .trading_date_helper import get_recent_trading_dates


def get_north_money_flow(days: int = 10) -> Dict[str, Any]:
    """
    获取北向资金流向数据

    Args:
        days: 获取最近几天的数据

    Returns:
        包含北向资金流向信息的字典
    """
    result = {
        "has_data": False,
        "latest_date": None,
        "net_amount": 0,           # 当日净流入（亿元）
        "accumulated": 0,           # 累计流入（亿元）
        "hgt_amount": 0,           # 沪股通（亿元）
        "sgt_amount": 0,           # 深股通（亿元）
        "trend_5d": [],            # 5日趋势
        "trend_10d": [],           # 10日趋势
        "data_source": "moneyflow_hsgt",
        "error": None
    }

    try:
        # 获取最近的交易日期
        recent_dates = get_recent_trading_dates(days + 5)  # 多获取几天以确保数据充足

        if not recent_dates:
            result["error"] = "无法获取交易日期"
            return result

        # 北向资金数据更新有延迟，尝试多个时间范围直到找到数据
        from datetime import datetime, timedelta

        df = None
        attempts = []

        # 定义要尝试的日期范围（倒序，从最近到最早）
        # 优先使用最近的数据，如果不可用则使用历史数据
        date_ranges_to_try = [
            # 2025年数据
            ('20251001', '20251031'),
            ('20250901', '20250930'),
            ('20250801', '20250831'),
            # 2024年数据
            ('20241001', '20241031'),
            ('20240901', '20240930'),
            ('20240801', '20240831'),
            ('20240701', '20240731'),
            ('20240601', '20240630'),
        ]

        for start_date, end_date in date_ranges_to_try:
            attempts.append(f"{start_date}-{end_date}")

            # 调用接口获取数据
            df_temp = moneyflow_hsgt(start_date=start_date, end_date=end_date)

            if df_temp is not None and not df_temp.empty:
                df = df_temp
                print(f"[北向资金] 使用日期范围: {start_date} - {end_date} (共{len(df)}条数据)")
                break

        if df is None or df.empty:
            result["error"] = f"接口返回数据为空，已尝试: {', '.join(attempts[:5])}"
            return result

        # 确保数据按日期排序（最新在前）
        df = df.sort_values('trade_date', ascending=False)

        # 处理最新数据
        latest_row = df.iloc[0]
        result["has_data"] = True
        result["latest_date"] = str(latest_row['trade_date'])

        # 数据单位是百万元，转换为亿元
        result["net_amount"] = round(float(latest_row.get('north_money', 0)) / 100, 2)
        result["hgt_amount"] = round(float(latest_row.get('hgt', 0)) / 100, 2)
        result["sgt_amount"] = round(float(latest_row.get('sgt', 0)) / 100, 2)

        # 计算累计流入（最近10天）
        if len(df) > 0:
            result["accumulated"] = round(df.head(10)['north_money'].sum() / 100, 2)

        # 构建5日趋势
        for i in range(min(5, len(df))):
            row = df.iloc[i]
            result["trend_5d"].append({
                "date": str(row['trade_date']),
                "amount": round(float(row.get('north_money', 0)) / 100, 2),
                "hgt": round(float(row.get('hgt', 0)) / 100, 2),
                "sgt": round(float(row.get('sgt', 0)) / 100, 2)
            })

        # 构建10日趋势
        for i in range(min(10, len(df))):
            row = df.iloc[i]
            result["trend_10d"].append({
                "date": str(row['trade_date']),
                "amount": round(float(row.get('north_money', 0)) / 100, 2),
                "hgt": round(float(row.get('hgt', 0)) / 100, 2),
                "sgt": round(float(row.get('sgt', 0)) / 100, 2)
            })

        # 添加统计信息
        if len(df) >= 5:
            recent_5d = df.head(5)['north_money'].values / 100
            result["avg_5d"] = round(recent_5d.mean(), 2)
            result["max_5d"] = round(recent_5d.max(), 2)
            result["min_5d"] = round(recent_5d.min(), 2)

            # 判断资金流向趋势
            if recent_5d[0] > recent_5d.mean() * 1.2:
                result["trend_signal"] = "加速流入"
            elif recent_5d[0] > 0:
                result["trend_signal"] = "持续流入"
            elif recent_5d[0] < recent_5d.mean() * 0.8:
                result["trend_signal"] = "加速流出"
            else:
                result["trend_signal"] = "持续流出"

        print(f"[北向资金] 获取成功: {result['latest_date']} 净流入{result['net_amount']}亿")

    except Exception as e:
        result["error"] = str(e)
        print(f"[北向资金] 获取失败: {e}")

    return result


def format_north_money_text(data: Dict[str, Any]) -> str:
    """
    格式化北向资金数据为文本描述

    Args:
        data: 北向资金数据字典

    Returns:
        格式化的文本描述
    """
    if not data.get("has_data"):
        return "北向资金数据暂不可用"

    text_parts = []

    # 当日情况
    amount = data.get("net_amount", 0)
    date = data.get("latest_date", "")

    if amount > 0:
        text_parts.append(f"北向资金净流入{abs(amount):.1f}亿元")
    else:
        text_parts.append(f"北向资金净流出{abs(amount):.1f}亿元")

    # 沪深股通细分
    hgt = data.get("hgt_amount", 0)
    sgt = data.get("sgt_amount", 0)
    if hgt != 0 or sgt != 0:
        details = []
        if hgt > 0:
            details.append(f"沪股通流入{hgt:.1f}亿")
        elif hgt < 0:
            details.append(f"沪股通流出{abs(hgt):.1f}亿")

        if sgt > 0:
            details.append(f"深股通流入{sgt:.1f}亿")
        elif sgt < 0:
            details.append(f"深股通流出{abs(sgt):.1f}亿")

        if details:
            text_parts.append(f"（{'/'.join(details)}）")

    # 趋势信号
    signal = data.get("trend_signal", "")
    if signal:
        text_parts.append(f"，呈{signal}趋势")

    # 累计情况
    accumulated = data.get("accumulated", 0)
    if accumulated != 0:
        if accumulated > 0:
            text_parts.append(f"，近10日累计流入{accumulated:.1f}亿")
        else:
            text_parts.append(f"，近10日累计流出{abs(accumulated):.1f}亿")

    return "".join(text_parts)


def get_north_money_analysis() -> Dict[str, Any]:
    """
    获取北向资金深度分析

    Returns:
        包含详细分析的字典
    """
    # 获取基础数据
    flow_data = get_north_money_flow(days=20)

    if not flow_data.get("has_data"):
        return {
            "status": "no_data",
            "message": flow_data.get("error", "数据不可用")
        }

    analysis = {
        "status": "success",
        "basic": flow_data,
        "analysis": {},
        "signals": []
    }

    # 分析资金流向特征
    net_amount = flow_data.get("net_amount", 0)
    avg_5d = flow_data.get("avg_5d", 0)

    # 1. 流入强度分析
    if abs(net_amount) > 100:
        intensity = "巨额"
    elif abs(net_amount) > 50:
        intensity = "大额"
    elif abs(net_amount) > 20:
        intensity = "中等"
    else:
        intensity = "小额"

    analysis["analysis"]["intensity"] = intensity

    # 2. 趋势持续性分析
    trend_5d = flow_data.get("trend_5d", [])
    if len(trend_5d) >= 3:
        # 检查连续性
        continuous_in = all(d["amount"] > 0 for d in trend_5d[:3])
        continuous_out = all(d["amount"] < 0 for d in trend_5d[:3])

        if continuous_in:
            analysis["signals"].append("连续3日流入")
            analysis["analysis"]["continuity"] = "持续流入"
        elif continuous_out:
            analysis["signals"].append("连续3日流出")
            analysis["analysis"]["continuity"] = "持续流出"
        else:
            analysis["analysis"]["continuity"] = "震荡"

    # 3. 沪深偏好分析
    hgt = flow_data.get("hgt_amount", 0)
    sgt = flow_data.get("sgt_amount", 0)

    if hgt > 0 and sgt > 0:
        if abs(hgt) > abs(sgt) * 1.5:
            analysis["analysis"]["preference"] = "偏好沪市大盘股"
            analysis["signals"].append("资金偏好沪市")
        elif abs(sgt) > abs(hgt) * 1.5:
            analysis["analysis"]["preference"] = "偏好深市成长股"
            analysis["signals"].append("资金偏好深市")
        else:
            analysis["analysis"]["preference"] = "沪深均衡配置"
    elif hgt > 0 and sgt < 0:
        analysis["analysis"]["preference"] = "买沪卖深"
        analysis["signals"].append("沪强深弱")
    elif hgt < 0 and sgt > 0:
        analysis["analysis"]["preference"] = "买深卖沪"
        analysis["signals"].append("深强沪弱")

    # 4. 投资建议
    if net_amount > 50:
        analysis["suggestion"] = "北向资金大幅流入，市场情绪积极，可适度加仓"
    elif net_amount > 20:
        analysis["suggestion"] = "北向资金温和流入，市场趋势向好"
    elif net_amount < -50:
        analysis["suggestion"] = "北向资金大幅流出，谨慎操作，控制仓位"
    elif net_amount < -20:
        analysis["suggestion"] = "北向资金流出，短期观望为宜"
    else:
        analysis["suggestion"] = "北向资金流向平稳，维持现有策略"

    return analysis