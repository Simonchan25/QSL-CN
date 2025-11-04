"""
增强技术分析模块 - 集成stk_factor_pro专业指标
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd

from .stk_factor_pro_client import StkFactorProClient
from .indicators import compute_indicators, build_tech_signal
from .tushare_client import daily, daily_basic
from .cache_manager import cache_stock_data


@cache_stock_data(ttl=300)  # 5分钟缓存
def fetch_enhanced_technical_data(ts_code: str,
                                 stock_name: str,
                                 use_pro: bool = True) -> Dict[str, Any]:
    """
    获取增强技术数据

    Args:
        ts_code: 股票代码
        stock_name: 股票名称
        use_pro: 是否使用专业版指标（默认True）

    Returns:
        技术分析数据字典
    """
    result = {
        'status': 'success',
        'use_pro': use_pro,
        'prices': [],
        'indicators': {},
        'signals': [],
        'trend_analysis': {},
        'entry_exit': {},
        'latest_price': 0,
        'error': None
    }

    try:
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=120)).strftime('%Y%m%d')

        if use_pro:
            # 使用专业版接口
            print(f"[技术分析] 使用stk_factor_pro获取{stock_name}技术指标")

            # 获取专业技术因子数据
            factor_df = StkFactorProClient.get_stk_factor_pro(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )

            if factor_df is not None and not factor_df.empty:
                # 分析技术因子
                tech_analysis = StkFactorProClient.analyze_technical_factors(factor_df)
                result['indicators'] = tech_analysis

                # 趋势分析
                trend_analysis = StkFactorProClient.get_trend_analysis(factor_df)
                result['trend_analysis'] = trend_analysis

                # 买卖信号
                signals = StkFactorProClient.get_entry_exit_signals(factor_df)
                result['entry_exit'] = signals

                # 提取价格数据用于图表
                if len(factor_df) > 0:
                    # 转换为前端需要的格式
                    prices_data = []
                    for _, row in factor_df.iterrows():
                        prices_data.append({
                            'date': str(row['trade_date']),
                            'open': float(row.get('open_qfq', row.get('open', 0))),
                            'high': float(row.get('high_qfq', row.get('high', 0))),
                            'low': float(row.get('low_qfq', row.get('low', 0))),
                            'close': float(row.get('close_qfq', row.get('close', 0))),
                            'volume': float(row.get('vol', 0)),
                            'amount': float(row.get('amount', 0)) * 1000,
                            'pct_change': float(row.get('pct_chg', 0)),
                            # 添加关键技术指标
                            'ma5': float(row.get('ma_qfq_5', 0)) if pd.notna(row.get('ma_qfq_5')) else None,
                            'ma20': float(row.get('ma_qfq_20', 0)) if pd.notna(row.get('ma_qfq_20')) else None,
                            'ma60': float(row.get('ma_qfq_60', 0)) if pd.notna(row.get('ma_qfq_60')) else None,
                            'rsi': float(row.get('rsi_qfq_12', 0)) if pd.notna(row.get('rsi_qfq_12')) else None,
                            'macd': float(row.get('macd_qfq', 0)) if pd.notna(row.get('macd_qfq')) else None,
                            'kdj_k': float(row.get('kdj_k_qfq', 0)) if pd.notna(row.get('kdj_k_qfq')) else None,
                            'kdj_d': float(row.get('kdj_d_qfq', 0)) if pd.notna(row.get('kdj_d_qfq')) else None,
                            'boll_up': float(row.get('boll_upper_qfq', 0)) if pd.notna(row.get('boll_upper_qfq')) else None,
                            'boll_mid': float(row.get('boll_mid_qfq', 0)) if pd.notna(row.get('boll_mid_qfq')) else None,
                            'boll_down': float(row.get('boll_lower_qfq', 0)) if pd.notna(row.get('boll_lower_qfq')) else None,
                            'volume_ratio': float(row.get('volume_ratio', 1)),
                            'turnover_rate': float(row.get('turnover_rate_f', 0))
                        })

                    result['prices'] = prices_data

                    # 最新价格
                    latest = factor_df.iloc[0]
                    result['latest_price'] = float(latest.get('close_qfq', latest.get('close', 0)))

                    # 生成技术信号描述
                    if 'technical_signals' in tech_analysis:
                        result['signals'] = tech_analysis['technical_signals']

                    # 添加专业指标数据
                    pro_indicators = {
                        '市场估值': tech_analysis.get('market_valuation', {}),
                        '特殊形态': tech_analysis.get('special_patterns', []),
                        '综合评分': tech_analysis.get('comprehensive_score', 50),
                        '主趋势': trend_analysis.get('primary_trend', ''),
                        '趋势强度': trend_analysis.get('trend_strength', 0),
                        '支撑阻力': trend_analysis.get('support_resistance', {}),
                        '建议操作': signals.get('suggested_action', '观望')
                    }
                    result['pro_indicators'] = pro_indicators

                else:
                    result['error'] = '专业版数据为空'
                    use_pro = False  # 降级到普通版
            else:
                print(f"[技术分析] stk_factor_pro数据获取失败，降级到普通版")
                use_pro = False  # 降级到普通版

        # 如果不使用专业版或专业版失败，使用普通计算
        if not use_pro:
            print(f"[技术分析] 使用普通版计算{stock_name}技术指标")

            # 获取基础价格数据
            df = daily(ts_code=ts_code, start_date=start_date, end_date=end_date)

            if df is not None and not df.empty:
                # 计算技术指标
                df = compute_indicators(df)

                # 转换为前端格式
                prices_data = []
                for _, row in df.iterrows():
                    price_item = {
                        'date': str(row['trade_date']),
                        'open': float(row['open']),
                        'high': float(row['high']),
                        'low': float(row['low']),
                        'close': float(row['close']),
                        'volume': float(row['vol']),
                        'amount': float(row.get('amount', 0)) * 1000,
                        'pct_change': float(row.get('pct_chg', 0))
                    }

                    # 添加计算的技术指标
                    for col in ['ma5', 'ma10', 'ma20', 'ma60', 'rsi14',
                              'dif', 'dea', 'macd', 'kdj_k', 'kdj_d',
                              'boll_up', 'boll_mid', 'boll_dn', 'vol_ratio']:
                        if col in row and pd.notna(row[col]):
                            price_item[col] = float(row[col])

                    prices_data.append(price_item)

                result['prices'] = prices_data

                # 最新价格和指标
                if len(df) > 0:
                    latest = df.iloc[0]
                    result['latest_price'] = float(latest['close'])

                    # 生成技术信号
                    signal_text = build_tech_signal(latest)
                    result['signals'] = signal_text.split('；') if signal_text != "无明显信号" else []

                    # 基础指标数据
                    basic_indicators = {
                        'rsi': float(latest['rsi14']) if pd.notna(latest.get('rsi14')) else None,
                        'macd': {
                            'dif': float(latest['dif']) if pd.notna(latest.get('dif')) else None,
                            'dea': float(latest['dea']) if pd.notna(latest.get('dea')) else None,
                            'macd': float(latest['macd']) if pd.notna(latest.get('macd')) else None
                        },
                        'kdj': {
                            'k': float(latest['kdj_k']) if pd.notna(latest.get('kdj_k')) else None,
                            'd': float(latest['kdj_d']) if pd.notna(latest.get('kdj_d')) else None,
                            'j': float(latest['kdj_j']) if pd.notna(latest.get('kdj_j')) else None
                        },
                        'ma': {
                            'ma5': float(latest['ma5']) if pd.notna(latest.get('ma5')) else None,
                            'ma20': float(latest['ma20']) if pd.notna(latest.get('ma20')) else None,
                            'ma60': float(latest['ma60']) if pd.notna(latest.get('ma60')) else None
                        }
                    }
                    result['indicators'] = basic_indicators
            else:
                result['error'] = '价格数据获取失败'
                result['status'] = 'error'

        # 获取每日指标补充（PE、PB等）
        try:
            for days_ago in range(5):
                check_date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y%m%d')
                basic_df = daily_basic(ts_code=ts_code, trade_date=check_date)
                if basic_df is not None and not basic_df.empty:
                    latest_basic = basic_df.iloc[0]
                    market_data = {
                        'pe': float(latest_basic.get('pe', 0)) if pd.notna(latest_basic.get('pe')) else None,
                        'pe_ttm': float(latest_basic.get('pe_ttm', 0)) if pd.notna(latest_basic.get('pe_ttm')) else None,
                        'pb': float(latest_basic.get('pb', 0)) if pd.notna(latest_basic.get('pb')) else None,
                        'ps': float(latest_basic.get('ps', 0)) if pd.notna(latest_basic.get('ps')) else None,
                        'ps_ttm': float(latest_basic.get('ps_ttm', 0)) if pd.notna(latest_basic.get('ps_ttm')) else None,
                        'total_mv': float(latest_basic.get('total_mv', 0)) / 10000 if pd.notna(latest_basic.get('total_mv')) else None,
                        'circ_mv': float(latest_basic.get('circ_mv', 0)) / 10000 if pd.notna(latest_basic.get('circ_mv')) else None
                    }
                    if 'pro_indicators' in result:
                        result['pro_indicators']['市场估值'].update(market_data)
                    else:
                        result['market_data'] = market_data
                    break
        except Exception as e:
            print(f"[技术分析] 获取市场数据失败: {e}")

    except Exception as e:
        print(f"[技术分析] 错误: {e}")
        result['error'] = str(e)
        result['status'] = 'error'

    return result


def compare_technical_methods(ts_code: str, stock_name: str) -> Dict[str, Any]:
    """
    比较专业版和普通版技术分析结果

    Args:
        ts_code: 股票代码
        stock_name: 股票名称

    Returns:
        比较结果字典
    """
    comparison = {
        'ts_code': ts_code,
        'stock_name': stock_name,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    # 获取专业版分析
    pro_result = fetch_enhanced_technical_data(ts_code, stock_name, use_pro=True)
    comparison['pro_version'] = pro_result

    # 获取普通版分析
    normal_result = fetch_enhanced_technical_data(ts_code, stock_name, use_pro=False)
    comparison['normal_version'] = normal_result

    # 比较差异
    differences = []

    # 比较指标数量
    pro_indicators = len(pro_result.get('pro_indicators', {}).get('市场估值', {}))
    normal_indicators = len(normal_result.get('indicators', {}))

    if pro_indicators > normal_indicators:
        differences.append(f"专业版提供{pro_indicators}个指标，普通版仅{normal_indicators}个")

    # 比较信号数量
    pro_signals = len(pro_result.get('signals', []))
    normal_signals = len(normal_result.get('signals', []))

    if pro_signals != normal_signals:
        differences.append(f"专业版识别{pro_signals}个信号，普通版识别{normal_signals}个")

    # 检查专业版独有功能
    if pro_result.get('trend_analysis'):
        differences.append("专业版提供趋势分析和支撑阻力位")

    if pro_result.get('entry_exit'):
        differences.append("专业版提供买卖点建议")

    if pro_result.get('pro_indicators', {}).get('特殊形态'):
        differences.append("专业版识别特殊K线形态")

    comparison['differences'] = differences
    comparison['recommendation'] = "建议使用专业版以获得更全面的分析" if differences else "两版本结果相似"

    return comparison