"""
图表生成器
生成可嵌入Markdown的K线图和预测对比图
集成Kronos深度学习模型进行专业K线预测
"""
import base64
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timedelta
import io
import json
import requests
import os
import logging

logger = logging.getLogger(__name__)


def _get_trade_date(price_dict: Dict) -> str:
    """兼容不同的日期字段名，提取交易日期"""
    return str(price_dict.get('trade_date') or price_dict.get('date') or price_dict.get('datetime', ''))


def generate_kline_svg(prices: List[Dict], indicators: Dict, stock_name: str = "",
                       predictions: List[Dict] = None) -> str:
    """
    生成K线图SVG (包含预测曲线)
    返回Base64编码的SVG，可直接嵌入Markdown
    """
    if not prices or len(prices) == 0:
        return ""

    # 只显示最近60天
    display_prices = prices[:60][::-1]  # 反转为正序

    # 图表尺寸
    width = 1200
    height = 500
    padding = {'top': 40, 'right': 100, 'bottom': 60, 'left': 60}
    chart_width = width - padding['left'] - padding['right']
    chart_height = height - padding['top'] - padding['bottom']

    # 计算价格范围
    all_prices = [p['high'] for p in display_prices] + [p['low'] for p in display_prices]
    if predictions:
        all_prices.extend([p['predicted_price'] for p in predictions])

    max_price = max(all_prices)
    min_price = min(all_prices)
    price_range = max_price - min_price
    padding_price = price_range * 0.1

    max_y = max_price + padding_price
    min_y = min_price - padding_price
    total_range = max_y - min_y

    # K线宽度
    candle_width = max(4, min(14, chart_width / len(display_prices) - 3))

    # 坐标转换
    def price_to_y(price):
        return padding['top'] + ((max_y - price) / total_range) * chart_height

    def index_to_x(index):
        return padding['left'] + (index * (chart_width / len(display_prices))) + candle_width

    # 开始构建SVG
    svg_parts = []
    svg_parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">')

    # 背景
    svg_parts.append(f'<rect width="{width}" height="{height}" fill="#1a1d29"/>')

    # 标题
    svg_parts.append(f'<text x="{width/2}" y="25" fill="#ffffff" font-size="18" font-weight="bold" text-anchor="middle">')
    svg_parts.append(f'{stock_name} - 日K线图 {"+ AI预测对比" if predictions else ""}')
    svg_parts.append('</text>')

    # 网格线和价格标签
    for i in range(5):
        ratio = i / 4
        y = padding['top'] + chart_height * ratio
        price = max_y - total_range * ratio

        svg_parts.append(f'<line x1="{padding["left"]}" y1="{y}" x2="{width - padding["right"]}" y2="{y}" stroke="#2a2e3f" stroke-width="1" stroke-dasharray="4,4"/>')
        svg_parts.append(f'<text x="{width - padding["right"] + 10}" y="{y + 5}" fill="#8b93a7" font-size="12">{price:.2f}</text>')

    # 绘制K线
    for idx, price in enumerate(display_prices):
        x = index_to_x(idx)
        open_y = price_to_y(price['open'])
        close_y = price_to_y(price['close'])
        high_y = price_to_y(price['high'])
        low_y = price_to_y(price['low'])

        is_rise = price['close'] >= price['open']
        color = '#ef5350' if is_rise else '#26a69a'

        body_top = min(open_y, close_y)
        body_height = abs(close_y - open_y) or 1

        # 影线
        svg_parts.append(f'<line x1="{x + candle_width/2}" y1="{high_y}" x2="{x + candle_width/2}" y2="{low_y}" stroke="{color}" stroke-width="1.5"/>')

        # K线实体
        svg_parts.append(f'<rect x="{x}" y="{body_top}" width="{candle_width}" height="{body_height}" fill="{color if is_rise else "#1a1d29"}" stroke="{color}" stroke-width="1.5"/>')

        # 日期标签（每10天）
        if idx % 10 == 0:
            date_str = str(_get_trade_date(price))
            date_label = f"{date_str[4:6]}/{date_str[6:8]}"
            svg_parts.append(f'<text x="{x + candle_width/2}" y="{height - padding["bottom"] + 20}" fill="#8b93a7" font-size="11" text-anchor="middle">{date_label}</text>')

    # 绘制MA5均线
    ma5_points = []
    for idx in range(4, len(display_prices)):
        ma5 = sum(display_prices[i]['close'] for i in range(idx-4, idx+1)) / 5
        x = index_to_x(idx) + candle_width/2
        y = price_to_y(ma5)
        ma5_points.append(f"{x},{y}")

    if ma5_points:
        svg_parts.append(f'<polyline points="{" ".join(ma5_points)}" fill="none" stroke="#ffb74d" stroke-width="2" opacity="0.8"/>')

    # 绘制预测曲线
    if predictions and len(predictions) > 0:
        # 预测起点从最后一个实际数据点开始
        pred_start_idx = len(display_prices) - 1
        pred_points = []

        # 添加起点（最后一个实际价格）
        x_start = index_to_x(pred_start_idx) + candle_width/2
        y_start = price_to_y(display_prices[-1]['close'])
        pred_points.append(f"{x_start},{y_start}")

        # 添加预测点
        for i, pred in enumerate(predictions):
            # 预测点的x坐标：从最后一根K线之后开始
            x = padding['left'] + ((pred_start_idx + i + 1) * (chart_width / len(display_prices))) + candle_width
            y = price_to_y(pred['predicted_price'])
            pred_points.append(f"{x},{y}")

            # 绘制预测点标记
            svg_parts.append(f'<circle cx="{x}" cy="{y}" r="4" fill="#9333ea" stroke="#ffffff" stroke-width="1"/>')

            # 如果有实际价格，绘制对比
            if 'actual_price' in pred and pred['actual_price']:
                actual_y = price_to_y(pred['actual_price'])
                # 实际价格点
                svg_parts.append(f'<circle cx="{x}" cy="{actual_y}" r="4" fill="#10b981" stroke="#ffffff" stroke-width="1"/>')
                # 连接预测和实际的误差线
                svg_parts.append(f'<line x1="{x}" y1="{y}" x2="{x}" y2="{actual_y}" stroke="#f59e0b" stroke-width="1" stroke-dasharray="2,2"/>')

        # 绘制预测曲线
        if len(pred_points) > 1:
            svg_parts.append(f'<polyline points="{" ".join(pred_points)}" fill="none" stroke="#9333ea" stroke-width="2.5" stroke-dasharray="5,5" opacity="0.9"/>')

    # 图例
    legend_y = padding['top'] + 20
    svg_parts.append(f'<line x1="{padding["left"]}" y1="{legend_y}" x2="{padding["left"] + 30}" y2="{legend_y}" stroke="#ef5350" stroke-width="3"/>')
    svg_parts.append(f'<text x="{padding["left"] + 35}" y="{legend_y + 4}" fill="#ef5350" font-size="12">涨</text>')

    svg_parts.append(f'<line x1="{padding["left"] + 70}" y1="{legend_y}" x2="{padding["left"] + 100}" y2="{legend_y}" stroke="#26a69a" stroke-width="3"/>')
    svg_parts.append(f'<text x="{padding["left"] + 105}" y="{legend_y + 4}" fill="#26a69a" font-size="12">跌</text>')

    svg_parts.append(f'<line x1="{padding["left"] + 140}" y1="{legend_y}" x2="{padding["left"] + 170}" y2="{legend_y}" stroke="#ffb74d" stroke-width="2"/>')
    svg_parts.append(f'<text x="{padding["left"] + 175}" y="{legend_y + 4}" fill="#ffb74d" font-size="12">MA5</text>')

    if predictions:
        svg_parts.append(f'<line x1="{padding["left"] + 220}" y1="{legend_y}" x2="{padding["left"] + 250}" y2="{legend_y}" stroke="#9333ea" stroke-width="2" stroke-dasharray="5,5"/>')
        svg_parts.append(f'<text x="{padding["left"] + 255}" y="{legend_y + 4}" fill="#9333ea" font-size="12">AI预测</text>')

        svg_parts.append(f'<circle cx="{padding["left"] + 320}" cy="{legend_y}" r="4" fill="#10b981" stroke="#ffffff" stroke-width="1"/>')
        svg_parts.append(f'<text x="{padding["left"] + 330}" y="{legend_y + 4}" fill="#10b981" font-size="12">实际</text>')

    # 最新价格标注
    if display_prices:
        latest = display_prices[-1]
        latest_y = price_to_y(latest['close'])
        is_rise = len(display_prices) > 1 and latest['close'] >= display_prices[-2]['close']

        svg_parts.append(f'<rect x="{width - padding["right"]}" y="{latest_y - 15}" width="90" height="30" fill="{"#ef5350" if is_rise else "#26a69a"}" rx="4"/>')
        svg_parts.append(f'<text x="{width - padding["right"] + 45}" y="{latest_y + 5}" fill="#ffffff" font-size="14" font-weight="bold" text-anchor="middle">{latest["close"]:.2f}</text>')

    svg_parts.append('</svg>')

    # 合并SVG
    svg_content = ''.join(svg_parts)

    # Base64编码
    svg_base64 = base64.b64encode(svg_content.encode('utf-8')).decode('utf-8')

    return f"data:image/svg+xml;base64,{svg_base64}"


def calculate_prediction_accuracy(predictions: List[Dict]) -> Dict[str, Any]:
    """
    计算预测准确度指标
    """
    if not predictions:
        return {}

    # 只计算有实际价格的预测
    valid_preds = [p for p in predictions if 'actual_price' in p and p['actual_price']]

    if not valid_preds:
        return {
            'total_predictions': len(predictions),
            'validated': 0,
            'accuracy': None,
            'avg_error': None,
            'error_rate': None
        }

    # 计算误差
    errors = []
    error_rates = []

    for pred in valid_preds:
        predicted = pred['predicted_price']
        actual = pred['actual_price']

        error = abs(predicted - actual)
        errors.append(error)

        if actual != 0:
            error_rate = (error / actual) * 100
            error_rates.append(error_rate)

    avg_error = sum(errors) / len(errors) if errors else 0
    avg_error_rate = sum(error_rates) / len(error_rates) if error_rates else 0

    # 使用中位数误差率，更能反映整体预测质量（避免极端值影响）
    sorted_error_rates = sorted(error_rates)
    median_error_rate = sorted_error_rates[len(sorted_error_rates) // 2] if sorted_error_rates else 0

    # 计算预测质量（考虑多个指标）
    # 如果最大误差率>20%，或者平均误差率>10%，预测质量不佳
    max_error_rate = max(error_rates) if error_rates else 0

    # 准确度计算：基于中位数误差率，但要惩罚极端值
    if max_error_rate > 20:
        # 有严重偏离的预测，准确度大打折扣
        accuracy = max(0, 100 - avg_error_rate - (max_error_rate - 20) / 2)
    else:
        # 使用中位数误差率计算准确度
        accuracy = max(0, 100 - median_error_rate)

    return {
        'total_predictions': len(predictions),
        'validated': len(valid_preds),
        'accuracy': round(accuracy, 2),
        'avg_error': round(avg_error, 2),
        'avg_error_rate': round(avg_error_rate, 2),
        'median_error_rate': round(median_error_rate, 2),
        'max_error': round(max(errors), 2) if errors else 0,
        'max_error_rate': round(max_error_rate, 2) if errors else 0,
        'min_error': round(min(errors), 2) if errors else 0,
    }


def generate_prediction_table(predictions: List[Dict], accuracy_metrics: Dict) -> str:
    """
    生成预测对比表格（Markdown格式）
    """
    if not predictions:
        return ""

    lines = []
    lines.append("\n### 📊 AI预测 vs 实际价格对比\n")

    if accuracy_metrics.get('accuracy') is not None:
        acc = accuracy_metrics['accuracy']
        max_err_rate = accuracy_metrics.get('max_error_rate', 0)
        avg_err_rate = accuracy_metrics.get('avg_error_rate', 0)

        # 更严格的评级标准
        if max_err_rate > 20 or avg_err_rate > 10:
            grade = "❌ 差"
        elif max_err_rate > 15 or avg_err_rate > 7:
            grade = "⚠️ 需改进"
        elif max_err_rate > 10 or avg_err_rate > 5:
            grade = "📊 一般"
        elif max_err_rate > 5 or avg_err_rate > 3:
            grade = "✅ 良好"
        else:
            grade = "🌟 优秀"

        lines.append(f"**预测质量**: {grade} (准确度: {acc}%)\n")
        lines.append(f"**平均误差**: ±{accuracy_metrics.get('avg_error', 0):.2f}元 ({avg_err_rate:.2f}%)\n")
        lines.append(f"**最大误差**: ±{accuracy_metrics.get('max_error', 0):.2f}元 ({max_err_rate:.2f}%)\n")
        lines.append(f"**验证数量**: {accuracy_metrics.get('validated', 0)}/{accuracy_metrics.get('total_predictions', 0)}天\n")

    lines.append("\n| 日期 | AI预测价格 | 实际价格 | 误差 | 误差率 | 状态 |\n")
    lines.append("|------|-----------|---------|------|--------|------|\n")

    for pred in predictions[:10]:  # 只显示前10个
        date = pred.get('date', '-')
        predicted = pred.get('predicted_price', 0)
        actual = pred.get('actual_price')

        if actual:
            error = abs(predicted - actual)
            error_rate = (error / actual * 100) if actual != 0 else 0
            status = "✅" if error_rate < 5 else "⚠️" if error_rate < 10 else "❌"

            lines.append(f"| {date} | {predicted:.2f} | {actual:.2f} | {error:.2f} | {error_rate:.2f}% | {status} |\n")
        else:
            lines.append(f"| {date} | {predicted:.2f} | 待验证 | - | - | ⏳ |\n")

    return ''.join(lines)


def embed_chart_in_markdown(svg_data_url: str, caption: str = "") -> str:
    """
    将SVG图表嵌入Markdown
    使用HTML div包裹以确保渲染
    """
    if not svg_data_url:
        return ""

    lines = []
    lines.append("\n### 📈 K线图表\n\n")
    if caption:
        lines.append(f"_{caption}_\n\n")

    # 使用div包裹img标签，确保正确渲染
    lines.append('<div class="chart-container">\n')
    lines.append(f'  <img src="{svg_data_url}" alt="K线图" style="max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);" />\n')
    lines.append('</div>\n\n')

    return ''.join(lines)


def generate_price_predictions(prices: List[Dict], stock_name: str, technical: Dict,
                               fundamental: Dict, days: int = 7, ts_code: str = None,
                               use_kronos: bool = True) -> Dict[str, List[Dict]]:
    """
    生成价格预测（优先使用Kronos深度学习模型）
    返回字典: {
        'historical': [过去7天的预测，用于验证准确率],
        'future': [未来5天的预测]
    }

    Args:
        use_kronos: 是否使用Kronos模型（默认True），False则使用传统LLM方法
    """
    if not prices or len(prices) < 15:
        return {'historical': [], 'future': []}

    # 优先使用Kronos模型进行预测
    if use_kronos and ts_code:
        try:
            logger.info(f"使用Kronos模型预测 {stock_name} ({ts_code})")
            print(f"[Kronos] 开始Kronos预测: {stock_name} ({ts_code})")
            result = _generate_kronos_predictions(prices, stock_name, ts_code, days)
            print(f"[Kronos] Kronos预测结果: 历史{len(result.get('historical', []))}条, 未来{len(result.get('future', []))}条")
            return result
        except Exception as e:
            logger.warning(f"Kronos预测失败，回退到传统方法: {e}")
            print(f"[Kronos] Kronos预测失败: {e}")
            import traceback
            traceback.print_exc()
            # 如果Kronos失败，回退到传统LLM方法

    # 传统LLM预测方法（作为备选）
    logger.info(f"使用传统方法预测 {stock_name}")
    historical_predictions = _generate_historical_predictions(prices, stock_name, technical, fundamental, 7)
    future_predictions = _generate_future_predictions(prices, stock_name, technical, fundamental, 5)

    return {
        'historical': historical_predictions,
        'future': future_predictions
    }


def _generate_kronos_predictions(prices: List[Dict], stock_name: str, ts_code: str,
                                 days: int = 7) -> Dict[str, List[Dict]]:
    """
    使用Kronos深度学习模型生成K线预测

    Args:
        prices: 历史价格数据（按日期倒序）
        stock_name: 股票名称
        ts_code: 股票代码
        days: 历史验证天数

    Returns:
        包含historical和future预测的字典
    """
    try:
        from .kronos_predictor import get_kronos_service
        import torch

        # 获取Kronos服务
        if torch.cuda.is_available():
            device = "cuda:0"
        elif torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"

        kronos = get_kronos_service(device=device)

        # Kronos需要的是正序数据（最早到最新）
        # 而prices是倒序的，需要反转
        prices_asc = list(reversed(prices))

        # 1. 生成历史预测（用于验证准确率）
        # 使用前N-7天的数据预测最后7天
        if len(prices_asc) < 50:
            logger.warning(f"数据不足50天，无法进行Kronos预测")
            return {'historical': [], 'future': []}

        historical_predictions = []

        # 计算需要预测的历史天数（扩展到14天以验证模型准确性）
        hist_days = min(days, 14)  # 最多预测14天历史
        available_days = len(prices_asc)

        if available_days > hist_days + 50:
            # 使用前面的数据预测最后hist_days天
            hist_cutoff = available_days - hist_days
            hist_input_prices = prices_asc[:hist_cutoff]

            # 构造输入日期
            # 兼容不同的日期字段名
            last_price = hist_input_prices[-1]
            date_field = last_price.get('trade_date') or last_price.get('date') or last_price.get('datetime', '')
            last_hist_date = datetime.strptime(str(date_field), '%Y%m%d')

            # 生成目标日期（实际已经发生的日期）
            target_dates = []
            current_date = last_hist_date
            for i in range(hist_days):
                current_date += timedelta(days=1)
                while current_date.weekday() >= 5:  # 跳过周末
                    current_date += timedelta(days=1)
                target_dates.append(current_date)

            # 构造Kronos预测请求（使用确定性预测保证结果一致性）
            try:
                # 低温度预测：T=0.1接近确定性，避免数值问题
                hist_result = kronos.predict_kline(
                    ts_code=ts_code,
                    pred_len=hist_days,
                    lookback=min(200, len(hist_input_prices)),  # 使用较少的历史数据
                    T=0.1,  # 低温度 = 接近确定性（避免T=0导致的inf/nan问题）
                    top_p=1.0,  # 不限制采样范围
                    sample_count=1,  # 单次预测即可
                    end_date=_get_trade_date(hist_input_prices[-1])
                )

                if hist_result and 'predicted_data' in hist_result:
                    pred_data = hist_result['predicted_data']

                    # 获取实际数据（最后hist_days天）
                    actual_data = prices_asc[-hist_days:]

                    # 匹配预测和实际数据
                    for i in range(min(len(pred_data['dates']), len(actual_data))):
                        predicted = pred_data['close'][i]
                        actual = actual_data[i]['close']
                        # 计算误差率
                        error_pct = abs(predicted - actual) / actual * 100 if actual > 0 else 0

                        historical_predictions.append({
                            'date': pred_data['dates'][i],
                            'predicted_price': predicted,
                            'actual_price': actual,
                            'error_pct': round(error_pct, 2),  # 添加误差率字段
                            'predicted_high': pred_data['high'][i],
                            'predicted_low': pred_data['low'][i],
                            'actual_high': actual_data[i]['high'],
                            'actual_low': actual_data[i]['low'],
                        })

                logger.info(f"Kronos历史预测完成: {len(historical_predictions)}天")

            except Exception as e:
                logger.error(f"Kronos历史预测失败: {e}")

        # 2. 生成未来预测（扩展到10天提供更长期视野）
        future_predictions = []
        future_days = 10  # 预测未来10天

        try:
            # 使用所有历史数据预测未来（接近确定性预测）
            future_result = kronos.predict_kline(
                ts_code=ts_code,
                pred_len=future_days,
                lookback=min(400, len(prices_asc)),  # 使用更多历史数据
                T=0.1,  # 低温度 = 接近确定性（避免T=0导致的inf/nan问题）
                top_p=1.0,  # 不限制采样范围
                sample_count=1  # 低温度预测单次即可
            )

            if future_result and 'predicted_data' in future_result:
                pred_data = future_result['predicted_data']

                for i in range(len(pred_data['dates'])):
                    future_predictions.append({
                        'date': pred_data['dates'][i],
                        'predicted_price': pred_data['close'][i],
                        'actual_price': None,  # 未来数据，无实际价格
                        'predicted_high': pred_data['high'][i],
                        'predicted_low': pred_data['low'][i],
                        'predicted_open': pred_data['open'][i],
                    })

                logger.info(f"Kronos未来预测完成: {len(future_predictions)}天")

        except Exception as e:
            logger.error(f"Kronos未来预测失败: {e}")

        return {
            'historical': historical_predictions,
            'future': future_predictions
        }

    except ImportError as e:
        logger.error(f"Kronos模型未安装: {e}")
        return {'historical': [], 'future': []}
    except Exception as e:
        logger.error(f"Kronos预测异常: {e}", exc_info=True)
        return {'historical': [], 'future': []}


def _generate_historical_predictions(prices: List[Dict], stock_name: str, technical: Dict,
                                     fundamental: Dict, days: int = 7) -> List[Dict]:
    """
    生成历史预测（预测过去7天以验证准确率）
    注意：prices按日期倒序排列，prices[0]是最新的日期
    """
    if not prices or len(prices) < 15:
        return []

    try:
        # prices按日期倒序：[今天, 昨天, 前天, ...]
        # 使用第8-14天（prices[7:14]）的数据预测第1-7天（prices[0:7]）
        train_start = 7  # 从第8天开始（7天前到14天前的数据）
        train_end = 14    # 到第15天

        train_prices = prices[train_start:train_end]  # 第8-14天，用于训练
        predict_prices = prices[:days]  # 最近7天，我们要预测的目标（已有实际价格）

        if len(train_prices) < 5:
            return _generate_fallback_predictions_with_actual(prices, days)

        # 计算训练数据的趋势
        latest_train_price = train_prices[0]['close']
        ma5 = sum(p['close'] for p in train_prices[:5]) / 5
        ma10 = sum(p['close'] for p in train_prices) / len(train_prices)

        # 计算价格变化趋势
        price_changes = []
        for i in range(1, min(len(train_prices), 5)):
            change = (train_prices[i-1]['close'] - train_prices[i]['close']) / train_prices[i]['close'] * 100
            price_changes.append(change)

        avg_change = sum(price_changes) / len(price_changes) if price_changes else 0
        volatility = sum(abs(c) for c in price_changes) / len(price_changes) if price_changes else 1.0

        # 构建预测提示 - 要求预测未来7天（实际是过去7天，我们有答案）
        price_history = ", ".join([f"{_get_trade_date(p)}: ¥{p['close']:.2f}" for p in train_prices[:5]])

        prompt = f"""你是一个精准的股票价格预测模型。基于历史数据，预测{stock_name}接下来{days}天的收盘价。

历史数据分析（{len(train_prices)}天）：
- 基准价格: ¥{latest_train_price:.2f}
- 5日均价(MA5): ¥{ma5:.2f}
- 10日均价(MA10): ¥{ma10:.2f}
- 近期价格序列: {price_history}
- 平均日波动: {avg_change:+.2f}%
- 波动率: {volatility:.2f}%
- 技术面强度: {technical.get('score', 0)}/40分
- 基本面强度: {fundamental.get('score', 0)}/20分

趋势判断：
{'价格上升趋势' if avg_change > 0.5 else '价格下降趋势' if avg_change < -0.5 else '价格横盘震荡'}

预测要求：
1. 基于MA5和MA10的位置关系，MA5 {'>' if ma5 > ma10 else '<'} MA10，趋势{'向上' if ma5 > ma10 else '向下'}
2. 每日价格波动应控制在±{volatility:.1f}%以内（历史波动率）
3. 整体趋势与历史趋势保持一致（{'上涨' if avg_change > 0 else '下跌' if avg_change < 0 else '震荡'}）
4. 价格围绕MA5({ma5:.2f})波动

返回格式（仅JSON数组，无其他文字）：
[{{"day": 1, "price": 数字}}, {{"day": 2, "price": 数字}}, ..., {{"day": {days}, "price": 数字}}]"""

        # 调用Ollama API
        ollama_model = os.getenv('OLLAMA_MODEL', 'qwen2.5:32b')
        response = requests.post('http://localhost:11434/api/generate',
            json={
                'model': ollama_model,
                'prompt': prompt,
                'stream': False,
                'options': {
                    'temperature': 0.3,  # 降低温度以获得更稳定的预测
                    'num_predict': 500
                }
            },
            timeout=30
        )

        if response.status_code != 200:
            print(f"LLM预测失败: {response.status_code}")
            return _generate_fallback_predictions(latest_price, ma5, ma10, days)

        result = response.json()
        llm_response = result.get('response', '').strip()

        # 提取JSON数组
        import re
        json_match = re.search(r'\[[\s\S]*\]', llm_response)
        if not json_match:
            print("LLM未返回有效JSON，使用回退预测")
            return _generate_fallback_predictions_with_actual(prices, days)

        predictions_data = json.loads(json_match.group())

        # 转换为标准格式 - 预测的是过去7天，所以都有实际价格
        predictions = []

        for i, pred in enumerate(predictions_data[:days]):
            pred_price = float(pred.get('price', latest_train_price))

            # 获取实际价格（这是过去的数据，我们都有）
            actual_data = predict_prices[i] if i < len(predict_prices) else None
            actual_price = actual_data['close'] if actual_data else None

            # 计算误差
            error = abs(pred_price - actual_price) if actual_price else 0
            error_pct = (error / actual_price * 100) if actual_price else 0

            predictions.append({
                'date': datetime.strptime(str(_get_trade_date(actual_data)), '%Y%m%d').strftime('%Y-%m-%d') if actual_data else '',
                'predicted_price': round(pred_price, 2),
                'actual_price': round(actual_price, 2) if actual_price else None,
                'error': round(error, 2),
                'error_pct': round(error_pct, 2)
            })

        return predictions

    except Exception as e:
        print(f"生成预测时出错: {str(e)}")
        return _generate_fallback_predictions(latest_price, ma5, ma10, days)


def _generate_fallback_predictions_with_actual(prices: List[Dict], days: int = 7) -> List[Dict]:
    """
    改进的回退预测算法（使用EMA和历史波动率）
    """
    predictions = []

    # 使用过去7-14天计算趋势，预测过去7天
    if len(prices) < 15:
        return []

    train_prices = prices[7:15]
    predict_prices = prices[:days]

    # 计算EMA（指数移动平均）权重更大给近期数据
    ema_period = len(train_prices)
    multiplier = 2 / (ema_period + 1)
    ema = train_prices[-1]['close']  # 从最早的数据开始
    for p in reversed(train_prices[:-1]):
        ema = (p['close'] - ema) * multiplier + ema

    # 计算历史波动率
    price_changes = []
    for i in range(1, len(train_prices)):
        change_pct = (train_prices[i-1]['close'] - train_prices[i]['close']) / train_prices[i]['close']
        price_changes.append(change_pct)

    volatility = sum(abs(c) for c in price_changes) / len(price_changes) if price_changes else 0.01

    # 计算趋势（最近3天 vs 之前5天）
    recent_avg = sum(p['close'] for p in train_prices[:3]) / 3
    earlier_avg = sum(p['close'] for p in train_prices[3:8]) / 5 if len(train_prices) > 7 else recent_avg
    trend_direction = 1 if recent_avg > earlier_avg else -1
    trend_strength = abs(recent_avg - earlier_avg) / earlier_avg if earlier_avg != 0 else 0

    # 预测（使用EMA作为基准，加上趋势修正）
    current_price = train_prices[0]['close']

    for i in range(days):
        # 基于EMA预测，但考虑趋势和波动
        # 趋势影响随时间递减
        trend_factor = trend_direction * trend_strength * (1 - i / days)
        predicted = ema * (1 + trend_factor)

        # 考虑均值回归（价格不会无限偏离EMA）
        if abs(predicted - ema) / ema > volatility * 2:
            predicted = ema + (predicted - ema) * 0.5

        # 获取实际价格
        actual_data = predict_prices[i] if i < len(predict_prices) else None
        actual_price = actual_data['close'] if actual_data else None

        # 计算误差
        error = abs(predicted - actual_price) if actual_price else 0
        error_pct = (error / actual_price * 100) if actual_price else 0

        predictions.append({
            'date': datetime.strptime(str(_get_trade_date(actual_data)), '%Y%m%d').strftime('%Y-%m-%d') if actual_data else '',
            'predicted_price': round(predicted, 2),
            'actual_price': round(actual_price, 2) if actual_price else None,
            'error': round(error, 2),
            'error_pct': round(error_pct, 2)
        })

    return predictions


def _generate_fallback_predictions(latest_price: float, ma5: float, ma10: float, days: int) -> List[Dict]:
    """
    当LLM不可用时的回退预测（基于简单趋势）- 旧版本保留兼容性
    """
    predictions = []

    # 计算趋势
    trend = (ma5 - ma10) / ma10 if ma10 != 0 else 0
    daily_change = trend / 5  # 分散到每日

    base_date = datetime.now()
    current_price = latest_price

    for i in range(days):
        # 简单线性预测 + 小幅随机波动
        import random
        random.seed(42 + i)  # 固定种子保证可复现

        current_price *= (1 + daily_change + random.uniform(-0.01, 0.01))
        pred_date = base_date + timedelta(days=i+1)

        predictions.append({
            'date': pred_date.strftime('%Y-%m-%d'),
            'predicted_price': round(current_price, 2),
            'actual_price': None
        })

    return predictions


def _generate_fallback_future_predictions(train_prices: List[Dict], days: int = 5) -> List[Dict]:
    """
    改进的未来预测回退算法（使用EMA和历史波动率）
    基于EMA、历史波动率和均值回归原理
    """
    if not train_prices or len(train_prices) < 5:
        return []

    predictions = []

    # 计算EMA（指数移动平均）- 权重更大给近期数据
    ema_period = min(len(train_prices), 15)
    multiplier = 2 / (ema_period + 1)
    ema = train_prices[0]['close']  # 最新价格
    for p in train_prices[1:ema_period]:
        ema = (p['close'] - ema) * multiplier + ema

    # 计算历史波动率
    price_changes = []
    for i in range(min(len(train_prices) - 1, 14)):
        change_pct = (train_prices[i]['close'] - train_prices[i+1]['close']) / train_prices[i+1]['close']
        price_changes.append(change_pct)
    volatility = sum(abs(c) for c in price_changes) / len(price_changes) if price_changes else 0.01

    # 计算趋势强度
    recent_avg = sum(p['close'] for p in train_prices[:3]) / 3
    earlier_avg = sum(p['close'] for p in train_prices[3:8]) / 5 if len(train_prices) > 7 else recent_avg
    trend_direction = 1 if recent_avg > earlier_avg else -1
    trend_strength = abs(recent_avg - earlier_avg) / earlier_avg if earlier_avg != 0 else 0

    # 生成未来预测
    current_price = train_prices[0]['close']
    base_date = datetime.strptime(str(_get_trade_date(train_prices[0])), '%Y%m%d')

    for i in range(days):
        # 趋势衰减：随着预测时间推移，趋势影响减弱
        trend_factor = trend_direction * trend_strength * (1 - i / (days * 1.5))

        # 基于EMA预测，加上趋势修正
        predicted = ema * (1 + trend_factor)

        # 均值回归：如果偏离EMA太远，拉回一半距离
        if abs(predicted - ema) / ema > volatility * 2:
            predicted = ema + (predicted - ema) * 0.5

        # 添加小幅波动（基于历史波动率）
        import random
        random.seed(42 + i)
        noise = random.uniform(-volatility * 0.3, volatility * 0.3)
        predicted = predicted * (1 + noise)

        # 更新当前价格用于下一天预测
        current_price = predicted

        # 生成预测记录
        pred_date = base_date + timedelta(days=i+1)
        predictions.append({
            'date': pred_date.strftime('%Y-%m-%d'),
            'predicted_price': round(predicted, 2),
            'actual_price': None,
            'type': 'future'
        })

    return predictions


def _generate_future_predictions(prices: List[Dict], stock_name: str, technical: Dict,
                                 fundamental: Dict, days: int = 5) -> List[Dict]:
    """
    生成未来预测（预测未来5天）
    """
    if not prices or len(prices) < 5:
        return []

    try:
        # 使用最近的数据作为训练数据
        train_prices = prices[:15]  # 最近15天
        latest_price = train_prices[0]['close']

        if len(train_prices) < 5:
            return _generate_fallback_predictions(latest_price, latest_price, latest_price, days)

        # 计算训练数据的趋势
        ma5 = sum(p['close'] for p in train_prices[:5]) / 5
        ma10 = sum(p['close'] for p in train_prices[:min(10, len(train_prices))]) / min(10, len(train_prices))

        # 构建预测提示
        price_history = ", ".join([f"{_get_trade_date(p)}: {p['close']}" for p in train_prices[:5]])

        prompt = f"""作为专业的股票分析师，基于以下数据预测{stock_name}未来{days}天的收盘价。

训练数据（最近{len(train_prices)}天）：
- 最新价格: {latest_price}
- MA5: {ma5:.2f}
- MA10: {ma10:.2f}
- 近期价格: {price_history}
- 技术评分: {technical.get('score', 0)}/40
- 基本面评分: {fundamental.get('score', 0)}/20

请只返回JSON数组格式的预测，每天一个价格，格式如下：
[{{"day": 1, "price": 预测价格}}, {{"day": 2, "price": 预测价格}}, ...]

要求：
1. 价格应该基于当前趋势和评分合理波动
2. 只返回JSON数组，不要有其他文字
3. 确保价格为数字类型"""

        # 调用Ollama API
        ollama_model = os.getenv('OLLAMA_MODEL', 'qwen2.5:32b')
        response = requests.post('http://localhost:11434/api/generate',
            json={
                'model': ollama_model,
                'prompt': prompt,
                'stream': False,
                'options': {
                    'temperature': 0.3,
                    'num_predict': 500
                }
            },
            timeout=30
        )

        if response.status_code != 200:
            print(f"LLM未来预测失败: {response.status_code}")
            return _generate_fallback_future_predictions(train_prices, days)

        result = response.json()
        llm_response = result.get('response', '').strip()

        # 提取JSON数组
        import re
        json_match = re.search(r'\[[\s\S]*\]', llm_response)
        if not json_match:
            print("LLM未返回有效JSON，使用回退预测")
            return _generate_fallback_future_predictions(train_prices, days)

        predictions_data = json.loads(json_match.group())

        # 转换为标准格式 - 未来预测，没有实际价格
        predictions = []
        base_date = datetime.strptime(str(_get_trade_date(train_prices[0])), '%Y%m%d')

        for i, pred in enumerate(predictions_data[:days]):
            pred_price = float(pred.get('price', latest_price))
            pred_date = base_date + timedelta(days=i+1)

            predictions.append({
                'date': pred_date.strftime('%Y-%m-%d'),
                'predicted_price': round(pred_price, 2),
                'actual_price': None,
                'type': 'future'  # 标记为未来预测
            })

        return predictions

    except Exception as e:
        print(f"生成未来预测时出错: {str(e)}")
        train_prices = prices[:15] if prices else []
        return _generate_fallback_future_predictions(train_prices, days)
