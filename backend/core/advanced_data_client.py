"""
高级数据客户端 - 充分利用5000积分权限
专业级个股分析、热点概念、市场报告所需的全部数据源
"""
import pandas as pd
from typing import Dict, List, Optional, Any
import datetime as dt
from concurrent.futures import ThreadPoolExecutor, as_completed
from .tushare_client import _call_api, cached, pro
import tushare as ts
from datetime import datetime, timedelta
try:
    import talib
except ImportError:
    talib = None
import numpy as np
# 所有5000积分专属函数已整合到此文件中

class AdvancedDataClient:
    """高级数据客户端 - 5000积分专属功能"""
    
    def __init__(self):
        self.pro = pro
    
    # ===== 实时数据接口 =====

    def get_realtime_kline(self, ts_code: str, freq: str = '1min', count: int = 120) -> pd.DataFrame:
        """获取实时分钟K线数据

        Args:
            ts_code: 股票代码
            freq: 频率 (1min, 5min, 15min, 30min, 60min)
            count: 获取数据条数

        Returns:
            实时K线数据
        """
        # 暂时禁用实时K线获取，因为有频率限制
        # 改为返回空数据框，避免触发API限制
        return pd.DataFrame()

    def get_realtime_quote(self, ts_code: str) -> Dict[str, Any]:
        """获取实时行情报价

        Args:
            ts_code: 股票代码

        Returns:
            实时行情数据字典
        """
        # 改用日线数据的最新一条作为"实时"数据
        try:
            from .tushare_client import daily
            from datetime import datetime, timedelta

            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=5)).strftime('%Y%m%d')

            df = daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
            if df is not None and not df.empty:
                latest = df.iloc[0]  # 最新数据
                return {
                    'ts_code': ts_code,
                    'price': float(latest.get('close', 0)),
                    'change': float(latest.get('pct_chg', 0)),
                    'high': float(latest.get('high', 0)),
                    'low': float(latest.get('low', 0)),
                    'volume': float(latest.get('vol', 0)),
                    'amount': float(latest.get('amount', 0)) * 1000,  # 转换为元
                    'time': str(latest.get('trade_date', ''))
                }
        except Exception as e:
            print(f"获取实时行情失败: {e}")

        return {}

    def calculate_realtime_indicators(self, ts_code: str) -> Dict[str, Any]:
        """计算实时技术指标

        Args:
            ts_code: 股票代码

        Returns:
            实时技术指标字典
        """
        # 改用日线数据计算技术指标
        try:
            from .tushare_client import daily
            from datetime import datetime, timedelta

            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=60)).strftime('%Y%m%d')

            df = daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
            if df is None or df.empty or len(df) < 20:
                return {}

            # 转换为numpy数组
            close_prices = df['close'].values
            high_prices = df['high'].values
            low_prices = df['low'].values
            volume = df['vol'].values

            indicators = {
                'current_price': float(close_prices[0]),  # 最新价格在第一行
                'timestamp': str(df.iloc[0]['trade_date'])
            }

            # 如果没有talib，使用简单的计算
            if talib is None:
                # 简单RSI计算
                try:
                    changes = np.diff(close_prices)
                    gains = np.where(changes > 0, changes, 0)
                    losses = np.where(changes < 0, -changes, 0)
                    if len(gains) >= 14:
                        avg_gain = np.mean(gains[-14:])
                        avg_loss = np.mean(losses[-14:])
                        if avg_loss != 0:
                            rs = avg_gain / avg_loss
                            rsi = 100 - (100 / (1 + rs))
                            indicators['rsi'] = float(rsi)
                except:
                    pass

                # 简单移动平均线
                try:
                    if len(close_prices) >= 20:
                        indicators['moving_averages'] = {
                            'ma5': float(np.mean(close_prices[-5:])),
                            'ma10': float(np.mean(close_prices[-10:])),
                            'ma20': float(np.mean(close_prices[-20:]))
                        }
                except:
                    pass

                return indicators

            # 使用talib计算指标
            # RSI 相对强弱指标
            try:
                rsi = talib.RSI(close_prices, timeperiod=14)
                if not np.isnan(rsi[-1]):
                    indicators['rsi'] = float(rsi[-1])
            except:
                pass

            # MACD
            try:
                macd, signal, hist = talib.MACD(close_prices, fastperiod=12, slowperiod=26, signalperiod=9)
                if not (np.isnan(macd[-1]) or np.isnan(signal[-1]) or np.isnan(hist[-1])):
                    indicators['macd'] = {
                        'macd': float(macd[-1]),
                        'signal': float(signal[-1]),
                        'histogram': float(hist[-1])
                    }
            except:
                pass

            # KDJ指标
            try:
                k, d = talib.STOCH(high_prices, low_prices, close_prices,
                                  fastk_period=9, slowk_period=3, slowd_period=3)
                if not (np.isnan(k[-1]) or np.isnan(d[-1])):
                    j = 3 * k[-1] - 2 * d[-1]
                    indicators['kdj'] = {
                        'k': float(k[-1]),
                        'd': float(d[-1]),
                        'j': float(j)
                    }
            except:
                pass

            # 布林带
            try:
                upper, middle, lower = talib.BBANDS(close_prices, timeperiod=20, nbdevup=2, nbdevdn=2)
                if not (np.isnan(upper[-1]) or np.isnan(middle[-1]) or np.isnan(lower[-1])):
                    indicators['bollinger'] = {
                        'upper': float(upper[-1]),
                        'middle': float(middle[-1]),
                        'lower': float(lower[-1]),
                        'position': (close_prices[-1] - lower[-1]) / (upper[-1] - lower[-1])
                    }
            except:
                pass

            # 移动平均线
            try:
                ma5 = talib.SMA(close_prices, timeperiod=5)
                ma10 = talib.SMA(close_prices, timeperiod=10)
                ma20 = talib.SMA(close_prices, timeperiod=20)

                if not (np.isnan(ma5[-1]) or np.isnan(ma10[-1]) or np.isnan(ma20[-1])):
                    indicators['moving_averages'] = {
                        'ma5': float(ma5[-1]),
                        'ma10': float(ma10[-1]),
                        'ma20': float(ma20[-1])
                    }
            except:
                pass

            return indicators

        except Exception as e:
            print(f"计算实时技术指标失败: {e}")
            return {}

    # ===== 筹码分析接口（5000积分专属） =====
    
    @cached
    def cyq_perf(self, ts_code: str = None, trade_date: str = None, 
                 start_date: str = None, end_date: str = None, force: bool = False) -> pd.DataFrame:
        """获取A股每日筹码平均成本和胜率情况"""
        try:
            return _call_api('cyq_perf', ts_code=ts_code, trade_date=trade_date,
                           start_date=start_date, end_date=end_date)
        except Exception as e:
            print(f"获取筹码成本数据失败: {e}")
            return pd.DataFrame()
    
    @cached
    def cyq_chips(self, ts_code: str, trade_date: str, force: bool = False) -> pd.DataFrame:
        """获取A股每日筹码分布"""
        try:
            return _call_api('cyq_chips', ts_code=ts_code, trade_date=trade_date)
        except Exception as e:
            print(f"获取筹码分布数据失败: {e}")
            return pd.DataFrame()
    
    @cached
    def stk_surv(self, ts_code: str = None, start_date: str = None, 
                 end_date: str = None, force: bool = False) -> pd.DataFrame:
        """获取机构调研统计数据"""
        try:
            return _call_api('stk_surv', ts_code=ts_code, start_date=start_date, end_date=end_date)
        except Exception as e:
            print(f"获取机构调研数据失败: {e}")
            return pd.DataFrame()
    
    @cached
    def ccass_hold(self, ts_code: str = None, trade_date: str = None, 
                   start_date: str = None, end_date: str = None, force: bool = False) -> pd.DataFrame:
        """获取港资持股统计"""
        try:
            return _call_api('ccass_hold', ts_code=ts_code, trade_date=trade_date,
                           start_date=start_date, end_date=end_date)
        except Exception as e:
            print(f"获取港资持股数据失败: {e}")
            return pd.DataFrame()
    
    @cached
    def ths_index(self, ts_code: str = None, exchange: str = None, type: str = None, force: bool = False) -> pd.DataFrame:
        """获取同花顺板块指数基本信息"""
        try:
            return _call_api('ths_index', ts_code=ts_code, exchange=exchange, type=type)
        except Exception as e:
            print(f"获取同花顺指数信息失败: {e}")
            return pd.DataFrame()
    
    @cached
    def ths_daily(self, ts_code: str = None, trade_date: str = None, 
                  start_date: str = None, end_date: str = None, force: bool = False) -> pd.DataFrame:
        """获取同花顺板块指数日线行情"""
        try:
            return _call_api('ths_daily', ts_code=ts_code, trade_date=trade_date,
                           start_date=start_date, end_date=end_date)
        except Exception as e:
            print(f"获取同花顺日线数据失败: {e}")
            return pd.DataFrame()
    
    @cached
    def ths_member(self, ts_code: str, trade_date: str = None, force: bool = False) -> pd.DataFrame:
        """获取同花顺板块成分"""
        try:
            return _call_api('ths_member', ts_code=ts_code, trade_date=trade_date)
        except Exception as e:
            print(f"获取同花顺成分股失败: {e}")
            return pd.DataFrame()
    
    @cached
    def stk_factor(self, ts_code: str = None, trade_date: str = None, 
                   start_date: str = None, end_date: str = None, force: bool = False) -> pd.DataFrame:
        """获取股票技术因子"""
        try:
            return _call_api('stk_factor', ts_code=ts_code, trade_date=trade_date,
                           start_date=start_date, end_date=end_date)
        except Exception as e:
            print(f"获取技术因子失败: {e}")
            return pd.DataFrame()
    
    @cached
    def cctv_news(self, date: str = None, force: bool = False) -> pd.DataFrame:
        """获取央视新闻联播文字稿"""
        try:
            return _call_api('cctv_news', date=date)
        except Exception as e:
            print(f"获取央视新闻失败: {e}")
            return pd.DataFrame()
    
    # ===== VIP批量财务数据接口 (5000积分专属) =====
    
    @cached
    def income_vip(self, period: str, report_type: str = "1", force: bool = False) -> pd.DataFrame:
        """获取全市场利润表数据 - 5000积分专属"""
        try:
            return _call_api('income_vip', period=period, report_type=report_type)
        except Exception as e:
            print(f"获取VIP利润表数据失败: {e}")
            return pd.DataFrame()
    
    @cached
    def balancesheet_vip(self, period: str, report_type: str = "1", force: bool = False) -> pd.DataFrame:
        """获取全市场资产负债表数据 - 5000积分专属"""
        try:
            return _call_api('balancesheet_vip', period=period, report_type=report_type)
        except Exception as e:
            print(f"获取VIP资产负债表数据失败: {e}")
            return pd.DataFrame()
    
    @cached
    def cashflow_vip(self, period: str, report_type: str = "1", force: bool = False) -> pd.DataFrame:
        """获取全市场现金流量表数据 - 5000积分专属"""
        try:
            return _call_api('cashflow_vip', period=period, report_type=report_type)
        except Exception as e:
            print(f"获取VIP现金流量表数据失败: {e}")
            return pd.DataFrame()
    
    @cached
    def fina_indicator_vip(self, period: str, force: bool = False) -> pd.DataFrame:
        """获取全市场财务指标数据 - 5000积分专属"""
        try:
            return _call_api('fina_indicator_vip', period=period)
        except Exception as e:
            print(f"获取VIP财务指标数据失败: {e}")
            return pd.DataFrame()
    
    @cached
    def forecast_vip(self, period: str, force: bool = False) -> pd.DataFrame:
        """获取全市场业绩预告数据 - 5000积分专属"""
        try:
            return _call_api('forecast_vip', period=period)
        except Exception as e:
            print(f"获取VIP业绩预告数据失败: {e}")
            return pd.DataFrame()
    
    @cached
    def express_vip(self, period: str, force: bool = False) -> pd.DataFrame:
        """获取全市场业绩快报数据 - 5000积分专属"""
        try:
            return _call_api('express_vip', period=period)
        except Exception as e:
            print(f"获取VIP业绩快报数据失败: {e}")
            return pd.DataFrame()
    
    # ===== 机构与资金数据 (5000积分高频) =====
    
    @cached
    def fund_portfolio(self, ts_code: str, force: bool = False) -> pd.DataFrame:
        """获取公募基金持仓数据 - 5000积分高频"""
        try:
            return _call_api('fund_portfolio', ts_code=ts_code)
        except Exception as e:
            print(f"获取基金持仓数据失败: {e}")
            return pd.DataFrame()
    
    @cached
    def top10_holders_enhanced(self, ts_code: str, force: bool = False) -> pd.DataFrame:
        """获取增强版前十大股东数据 - 5000积分高频"""
        try:
            # 获取最近4个季度的股东数据
            holders_data = []
            current_date = dt.date.today()
            
            for i in range(4):
                year = current_date.year if i < 2 else current_date.year - 1
                quarter_dates = [
                    f"{year}0331", f"{year}0630", 
                    f"{year}0930", f"{year}1231"
                ]
                quarter = (current_date.month - 1) // 3 - i
                if quarter < 0:
                    quarter += 4
                    year -= 1
                
                period = quarter_dates[quarter % 4]
                df = _call_api('top10_holders', ts_code=ts_code, period=period)
                if not df.empty:
                    df['query_period'] = period
                    holders_data.append(df)
            
            return pd.concat(holders_data, ignore_index=True) if holders_data else pd.DataFrame()
        except Exception as e:
            print(f"获取增强股东数据失败: {e}")
            return pd.DataFrame()
    
    @cached
    def top10_floatholders_enhanced(self, ts_code: str, force: bool = False) -> pd.DataFrame:
        """获取增强版前十大流通股东数据 - 5000积分高频"""
        try:
            holders_data = []
            current_date = dt.date.today()
            
            for i in range(4):
                year = current_date.year if i < 2 else current_date.year - 1
                quarter_dates = [
                    f"{year}0331", f"{year}0630", 
                    f"{year}0930", f"{year}1231"
                ]
                quarter = (current_date.month - 1) // 3 - i
                if quarter < 0:
                    quarter += 4
                    year -= 1
                
                period = quarter_dates[quarter % 4]
                df = _call_api('top10_floatholders', ts_code=ts_code, period=period)
                if not df.empty:
                    df['query_period'] = period
                    holders_data.append(df)
            
            return pd.concat(holders_data, ignore_index=True) if holders_data else pd.DataFrame()
        except Exception as e:
            print(f"获取增强流通股东数据失败: {e}")
            return pd.DataFrame()
    
    # ===== 期权与衍生品数据 (5000积分专属) =====
    
    @cached
    def opt_basic(self, exchange: str = None, force: bool = False) -> pd.DataFrame:
        """获取期权基本信息 - 5000积分专属"""
        try:
            params = {}
            if exchange:
                params['exchange'] = exchange
            return _call_api('opt_basic', **params)
        except Exception as e:
            print(f"获取期权基本信息失败: {e}")
            return pd.DataFrame()
    
    @cached
    def opt_daily(self, ts_code: str = None, trade_date: str = None, 
                  start_date: str = None, end_date: str = None, force: bool = False) -> pd.DataFrame:
        """获取期权日线行情 - 5000积分专属"""
        try:
            params = {}
            if ts_code: params['ts_code'] = ts_code
            if trade_date: params['trade_date'] = trade_date
            if start_date: params['start_date'] = start_date
            if end_date: params['end_date'] = end_date
            return _call_api('opt_daily', **params)
        except Exception as e:
            print(f"获取期权日线数据失败: {e}")
            return pd.DataFrame()
    
    # ===== 指数增强数据 =====
    
    @cached
    def index_weight(self, index_code: str, trade_date: str = None, force: bool = False) -> pd.DataFrame:
        """获取指数权重数据"""
        try:
            return _call_api('index_weight', index_code=index_code, trade_date=trade_date)
        except Exception as e:
            print(f"获取指数权重失败: {e}")
            return pd.DataFrame()
    
    @cached
    def index_dailybasic(self, ts_code: str = None, trade_date: str = None, 
                        start_date: str = None, end_date: str = None, force: bool = False) -> pd.DataFrame:
        """获取指数日线基础数据"""
        try:
            params = {}
            if ts_code: params['ts_code'] = ts_code
            if trade_date: params['trade_date'] = trade_date
            if start_date: params['start_date'] = start_date
            if end_date: params['end_date'] = end_date
            return _call_api('index_dailybasic', **params)
        except Exception as e:
            print(f"获取指数基础数据失败: {e}")
            return pd.DataFrame()
    
    # ===== 实时数据接口（5000积分专属） =====

    @cached
    def limit_list_d(self, trade_date: str = None, limit_type: str = None, force: bool = False) -> pd.DataFrame:
        """
        获取A股每日涨跌停、炸板数据（5000积分专属）
        limit_type: U涨停 D跌停 Z炸板
        """
        try:
            params = {}
            if trade_date:
                params['trade_date'] = trade_date
            if limit_type:
                params['limit_type'] = limit_type
            return _call_api('limit_list_d', **params)
        except Exception as e:
            print(f"获取涨跌停列表失败: {e}")
            return pd.DataFrame()

    @cached
    def stk_limit(self, ts_code: str = None, trade_date: str = None, force: bool = False) -> pd.DataFrame:
        """
        获取每日涨跌停价格（每日8:40更新）
        """
        try:
            params = {}
            if ts_code:
                params['ts_code'] = ts_code
            if trade_date:
                params['trade_date'] = trade_date
            return _call_api('stk_limit', **params)
        except Exception as e:
            print(f"获取涨跌停价格失败: {e}")
            return pd.DataFrame()

    def get_realtime_market_mood(self, trade_date: str = None) -> Dict[str, Any]:
        """获取实时市场情绪指标"""
        import datetime as dt
        from .trading_date_helper import get_latest_trading_date

        if not trade_date:
            # 如果是非交易日，自动使用最新交易日
            if dt.date.today().weekday() >= 5:  # 周末
                trade_date = get_latest_trading_date()
            else:
                trade_date = dt.date.today().strftime("%Y%m%d")

        # 获取涨跌停数据
        up_limit = self.limit_list_d(trade_date=trade_date, limit_type='U')
        down_limit = self.limit_list_d(trade_date=trade_date, limit_type='D')
        broken_limit = self.limit_list_d(trade_date=trade_date, limit_type='Z')

        # 格式化显示日期
        formatted_date = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:8]}"
        is_latest_trading_day = trade_date == get_latest_trading_date()

        mood = {
            'trade_date': trade_date,
            'formatted_date': formatted_date,
            'is_latest_trading_day': is_latest_trading_day,
            'data_source': f'最新交易日({formatted_date})' if is_latest_trading_day else f'历史数据({formatted_date})',
            'up_limit_count': len(up_limit),
            'down_limit_count': len(down_limit),
            'broken_limit_count': len(broken_limit),
            'up_limit_stocks': up_limit.head(10).to_dict('records') if not up_limit.empty else [],
            'down_limit_stocks': down_limit.head(10).to_dict('records') if not down_limit.empty else [],
            'broken_stocks': broken_limit.head(10).to_dict('records') if not broken_limit.empty else []
        }

        # 计算市场强度
        total_limit = mood['up_limit_count'] + mood['down_limit_count']
        if total_limit > 0:
            mood['market_strength'] = round(mood['up_limit_count'] / total_limit * 100, 2)
        else:
            mood['market_strength'] = 50

        # 计算炸板率
        total_up = mood['up_limit_count'] + mood['broken_limit_count']
        if total_up > 0:
            mood['broken_rate'] = round(mood['broken_limit_count'] / total_up * 100, 2)
        else:
            mood['broken_rate'] = 0

        return mood

    # ===== 综合分析方法 =====
    
    def get_comprehensive_stock_data(self, ts_code: str) -> Dict[str, Any]:
        """获取股票的全方位数据 - 5000积分专业版"""
        print(f"[高级数据] 开始获取 {ts_code} 的全方位专业数据...")
        
        data = {}
        
        # 并行获取数据
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                'chip_analysis': executor.submit(self._get_chip_analysis, ts_code),
                'institution_data': executor.submit(self._get_institution_data, ts_code),
                'holders_analysis': executor.submit(self._get_holders_analysis, ts_code),
                'technical_factors': executor.submit(self._get_technical_factors, ts_code),
                'fund_holdings': executor.submit(self._get_fund_holdings, ts_code),
                'options_data': executor.submit(self._get_related_options, ts_code),
            }
            
            for key, future in futures.items():
                try:
                    data[key] = future.result(timeout=30)
                    print(f"[高级数据] ✓ {key} 数据获取完成")
                except Exception as e:
                    print(f"[高级数据] ✗ {key} 数据获取失败: {e}")
                    data[key] = {}
        
        print(f"[高级数据] {ts_code} 全方位数据获取完成")
        return data
    
    def _get_chip_analysis(self, ts_code: str) -> Dict[str, Any]:
        """获取筹码分析数据"""
        try:
            # 筹码成本和胜率
            cyq_perf_data = self.cyq_perf(ts_code=ts_code)
            
            # 筹码分布
            import datetime as dt
            today = dt.date.today().strftime("%Y%m%d")
            cyq_chips_data = self.cyq_chips(ts_code=ts_code, trade_date=today)
            
            return {
                'cyq_perf': cyq_perf_data.to_dict('records') if not cyq_perf_data.empty else [],
                'cyq_chips': cyq_chips_data.to_dict('records') if not cyq_chips_data.empty else [],
                'has_data': not cyq_perf_data.empty or not cyq_chips_data.empty
            }
        except Exception as e:
            print(f"筹码分析数据获取失败: {e}")
            return {'has_data': False}
    
    def _get_institution_data(self, ts_code: str) -> Dict[str, Any]:
        """获取机构数据"""
        try:
            # 机构调研
            survey_data = self.stk_surv(ts_code=ts_code)
            
            # 港资持股
            ccass_data = self.ccass_hold(ts_code=ts_code)
            
            return {
                'surveys': survey_data.to_dict('records') if not survey_data.empty else [],
                'ccass_holdings': ccass_data.to_dict('records') if not ccass_data.empty else [],
                'has_data': not survey_data.empty or not ccass_data.empty
            }
        except Exception as e:
            print(f"机构数据获取失败: {e}")
            return {'has_data': False}
    
    def _get_holders_analysis(self, ts_code: str) -> Dict[str, Any]:
        """获取股东分析数据"""
        try:
            # 增强版股东数据
            top10_holders = self.top10_holders_enhanced(ts_code)
            floatholders = self.top10_floatholders_enhanced(ts_code)
            
            return {
                'top10_holders': top10_holders.to_dict('records') if not top10_holders.empty else [],
                'floatholders': floatholders.to_dict('records') if not floatholders.empty else [],
                'has_data': not top10_holders.empty or not floatholders.empty
            }
        except Exception as e:
            print(f"股东数据获取失败: {e}")
            return {'has_data': False}
    
    def _get_technical_factors(self, ts_code: str) -> Dict[str, Any]:
        """获取技术因子数据"""
        try:
            # 35个技术因子
            factors_data = self.stk_factor(ts_code=ts_code)
            
            # 31个备用指标 - 暂时注释掉不存在的API
            # bak_data = bak_daily(ts_code=ts_code)
            bak_data = pd.DataFrame()
            
            return {
                'factors': factors_data.to_dict('records') if not factors_data.empty else [],
                'backup_indicators': bak_data.to_dict('records') if not bak_data.empty else [],
                'has_data': not factors_data.empty or not bak_data.empty
            }
        except Exception as e:
            print(f"技术因子数据获取失败: {e}")
            return {'has_data': False}
    
    def _get_fund_holdings(self, ts_code: str) -> Dict[str, Any]:
        """获取基金持仓数据"""
        try:
            holdings = self.fund_portfolio(ts_code)
            return {
                'holdings': holdings.to_dict('records') if not holdings.empty else [],
                'has_data': not holdings.empty
            }
        except Exception as e:
            print(f"基金持仓数据获取失败: {e}")
            return {'has_data': False}
    
    def _get_related_options(self, ts_code: str) -> Dict[str, Any]:
        """获取相关期权数据"""
        try:
            # 获取相关期权（基于标的股票）
            opt_basic_data = self.opt_basic()
            
            # 筛选相关期权
            if not opt_basic_data.empty and 'symbol' in opt_basic_data.columns:
                # 提取股票代码的数字部分进行匹配
                stock_code = ts_code.split('.')[0]
                related_opts = opt_basic_data[
                    opt_basic_data['symbol'].str.contains(stock_code, na=False)
                ]
                
                return {
                    'related_options': related_opts.to_dict('records') if not related_opts.empty else [],
                    'has_data': not related_opts.empty
                }
            else:
                return {'has_data': False}
        except Exception as e:
            print(f"期权数据获取失败: {e}")
            return {'has_data': False}
    
    def get_market_wide_analysis(self) -> Dict[str, Any]:
        """获取全市场分析数据 - 5000积分专业版"""
        print("[高级数据] 开始获取全市场专业数据...")
        
        data = {}
        
        # 并行获取市场数据
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {
                'latest_financials': executor.submit(self._get_latest_market_financials),
                'sector_rotation': executor.submit(self._get_sector_rotation_data),
                'fund_flows': executor.submit(self._get_fund_flow_analysis),
                'options_overview': executor.submit(self._get_options_market_overview),
                'news_analysis': executor.submit(self._get_news_analysis),
            }
            
            for key, future in futures.items():
                try:
                    data[key] = future.result(timeout=60)
                    print(f"[高级数据] ✓ {key} 市场数据获取完成")
                except Exception as e:
                    print(f"[高级数据] ✗ {key} 市场数据获取失败: {e}")
                    data[key] = {}
        
        print("[高级数据] 全市场专业数据获取完成")
        return data
    
    def _get_latest_market_financials(self) -> Dict[str, Any]:
        """获取最新市场财务数据"""
        try:
            # 获取最近季度的全市场财务数据
            current_date = dt.date.today()
            
            # 确定最近的季度报告期
            if current_date.month >= 10:
                period = f"{current_date.year}0930"
            elif current_date.month >= 7:
                period = f"{current_date.year}0630"
            elif current_date.month >= 4:
                period = f"{current_date.year}0331"
            else:
                period = f"{current_date.year-1}1231"
            
            # 使用VIP接口批量获取财务数据
            income_data = self.income_vip(period=period)
            fina_data = self.fina_indicator_vip(period=period)
            forecast_data = self.forecast_vip(period=period)
            
            return {
                'period': period,
                'income_count': len(income_data) if not income_data.empty else 0,
                'indicator_count': len(fina_data) if not fina_data.empty else 0,
                'forecast_count': len(forecast_data) if not forecast_data.empty else 0,
                'has_data': not income_data.empty or not fina_data.empty
            }
        except Exception as e:
            print(f"市场财务数据获取失败: {e}")
            return {'has_data': False}
    
    def _get_sector_rotation_data(self) -> Dict[str, Any]:
        """获取板块轮动数据"""
        try:
            # 获取同花顺板块数据
            ths_indices = self.ths_index(exchange="A", type="N")
            
            # 获取最近5天的板块行情
            end_date = dt.date.today().strftime("%Y%m%d")
            start_date = (dt.date.today() - dt.timedelta(days=5)).strftime("%Y%m%d")
            
            sector_performance = []
            if not ths_indices.empty:
                for _, sector in ths_indices.head(20).iterrows():  # 前20个板块
                    ts_code = sector.get('ts_code')
                    if ts_code:
                        daily_data = self.ths_daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
                        if not daily_data.empty:
                            # 计算5日涨跌幅
                            daily_data = daily_data.sort_values('trade_date')
                            if len(daily_data) >= 2:
                                latest = daily_data.iloc[-1]
                                earliest = daily_data.iloc[0]
                                pct_chg = ((latest['close'] - earliest['close']) / earliest['close'] * 100)
                                
                                sector_performance.append({
                                    'sector_code': ts_code,
                                    'sector_name': sector.get('name'),
                                    'pct_change_5d': round(pct_chg, 2),
                                    'latest_close': latest['close']
                                })
            
            # 按涨跌幅排序
            sector_performance.sort(key=lambda x: x['pct_change_5d'], reverse=True)
            
            return {
                'sectors': sector_performance,
                'sector_count': len(sector_performance),
                'has_data': len(sector_performance) > 0
            }
        except Exception as e:
            print(f"板块轮动数据获取失败: {e}")
            return {'has_data': False}
    
    def _get_fund_flow_analysis(self) -> Dict[str, Any]:
        """获取资金流向分析"""
        try:
            # 获取最近几天的北向资金数据
            end_date = dt.date.today().strftime("%Y%m%d")
            start_date = (dt.date.today() - dt.timedelta(days=10)).strftime("%Y%m%d")
            
            # 使用正确的北向资金API调用方法
            from .tushare_client import moneyflow_hsgt
            hk_flow = moneyflow_hsgt(start_date=start_date, end_date=end_date)
            
            analysis = {
                'has_data': not hk_flow.empty,
                'days_count': len(hk_flow) if not hk_flow.empty else 0
            }
            
            if not hk_flow.empty:
                # 计算净流入统计
                total_net = hk_flow['hgt_net'].sum() + hk_flow['sgt_net'].sum()
                analysis.update({
                    'total_net_inflow': round(total_net, 2),
                    'avg_daily_inflow': round(total_net / len(hk_flow), 2),
                    'positive_days': len(hk_flow[hk_flow['hgt_net'] + hk_flow['sgt_net'] > 0])
                })
            
            return analysis
        except Exception as e:
            print(f"资金流向分析失败: {e}")
            return {'has_data': False}
    
    def _get_options_market_overview(self) -> Dict[str, Any]:
        """获取期权市场概览"""
        try:
            opt_basic_data = self.opt_basic()
            
            if not opt_basic_data.empty:
                # 按交易所统计
                exchange_stats = opt_basic_data.groupby('exchange').size().to_dict()
                
                # 按标的统计
                underlying_stats = opt_basic_data['symbol'].str[:6].value_counts().head(10).to_dict()
                
                return {
                    'total_contracts': len(opt_basic_data),
                    'exchange_distribution': exchange_stats,
                    'top_underlyings': underlying_stats,
                    'has_data': True
                }
            else:
                return {'has_data': False}
        except Exception as e:
            print(f"期权市场概览获取失败: {e}")
            return {'has_data': False}
    
    def _get_news_analysis(self) -> Dict[str, Any]:
        """获取新闻分析数据"""
        try:
            # 获取今日CCTV新闻
            today = dt.date.today().strftime("%Y%m%d")
            cctv_data = self.cctv_news(date=today)
            
            return {
                'cctv_news_count': len(cctv_data) if not cctv_data.empty else 0,
                'has_cctv_data': not cctv_data.empty,
                'latest_news': cctv_data.head(5).to_dict('records') if not cctv_data.empty else []
            }
        except Exception as e:
            print(f"新闻分析数据获取失败: {e}")
            return {'has_data': False}

    def get_full_professional_data(self, ts_code: str) -> Dict[str, Any]:
        """
        获取股票的全部专业数据（5000积分接口）
        包含：筹码分析、机构数据、股东分析、基金持仓、融资融券、大宗交易等

        Args:
            ts_code: 股票代码

        Returns:
            包含所有专业数据的字典
        """
        try:
            from datetime import datetime, timedelta

            # 设置日期范围
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')

            result = {}

            # 1. 获取股东数据
            try:
                holders = self.pro.stk_holdernumber(ts_code=ts_code, start_date=start_date, end_date=end_date)
                if holders is not None and not holders.empty:
                    result['holders_analysis'] = {
                        'holder_num': int(holders.iloc[0]['holder_num']) if 'holder_num' in holders.columns else 0,
                        'change_ratio': float(holders.iloc[0]['change_ratio']) if len(holders) > 1 and 'change_ratio' in holders.columns else 0,
                        'has_data': True
                    }
                else:
                    result['holders_analysis'] = {'has_data': False}
            except Exception as e:
                print(f"获取股东数据失败: {e}")
                result['holders_analysis'] = {'has_data': False}

            # 2. 获取资金流向数据
            try:
                moneyflow = self.pro.moneyflow(ts_code=ts_code, start_date=start_date, end_date=end_date)
                if moneyflow is not None and not moneyflow.empty:
                    latest = moneyflow.iloc[0]
                    result['moneyflow'] = {
                        'net_amount': float(latest.get('net_amount', 0)),
                        'net_amount_xl': float(latest.get('net_amount_xl', 0)),
                        'net_amount_l': float(latest.get('net_amount_l', 0)),
                        'net_amount_m': float(latest.get('net_amount_m', 0)),
                        'net_amount_s': float(latest.get('net_amount_s', 0)),
                        'has_data': True
                    }
                else:
                    result['moneyflow'] = {'has_data': False}
            except Exception as e:
                print(f"获取资金流向失败: {e}")
                result['moneyflow'] = {'has_data': False}

            # 3. 获取融资融券数据
            try:
                margin = self.pro.margin_detail(ts_code=ts_code, start_date=start_date, end_date=end_date)
                if margin is not None and not margin.empty:
                    latest = margin.iloc[0]
                    result['margin_detail'] = {
                        'rzye': float(latest.get('rzye', 0)),  # 融资余额
                        'rqye': float(latest.get('rqye', 0)),  # 融券余额
                        'rzmre': float(latest.get('rzmre', 0)),  # 融资买入额
                        'rzche': float(latest.get('rzche', 0)),  # 融资偿还额
                        'rzjme': float(latest.get('rzye', 0)) - float(latest.get('rqye', 0)) if 'rzye' in latest and 'rqye' in latest else 0,  # 融资净买入
                        'has_data': True
                    }
                else:
                    result['margin_detail'] = {'has_data': False}
            except Exception as e:
                print(f"获取融资融券失败: {e}")
                result['margin_detail'] = {'has_data': False}

            # 4. 获取大宗交易数据
            try:
                # 大宗交易需要使用交易日期查询
                block_trade = self.pro.block_trade(ts_code=ts_code, start_date=start_date, end_date=end_date)
                if block_trade is not None and not block_trade.empty:
                    result['block_trade'] = {
                        'total_count': len(block_trade),
                        'total_amount': block_trade['amount'].sum() if 'amount' in block_trade.columns else 0,
                        'avg_price': block_trade['price'].mean() if 'price' in block_trade.columns else 0,
                        'latest_trades': block_trade.head(5).to_dict('records'),
                        'has_data': True
                    }
                else:
                    result['block_trade'] = {'has_data': False}
            except Exception as e:
                print(f"获取大宗交易失败: {e}")
                result['block_trade'] = {'has_data': False}

            # 5. 获取分红数据
            try:
                dividend = self.pro.dividend(ts_code=ts_code)
                if dividend is not None and not dividend.empty:
                    result['dividend'] = {
                        'total_count': len(dividend),
                        'recent_dividends': dividend.head(5).to_dict('records'),
                        'has_data': True
                    }
                else:
                    result['dividend'] = {'has_data': False}
            except Exception as e:
                print(f"获取分红数据失败: {e}")
                result['dividend'] = {'has_data': False}

            # 6. 筹码分析（基于已有数据计算）
            result['chip_analysis'] = self._analyze_chips(result)

            # 7. 机构数据（基于已有数据）
            result['institution_data'] = self._analyze_institution(result)

            return result

        except Exception as e:
            print(f"获取完整专业数据失败: {e}")
            return {}

    def _analyze_chips(self, data: Dict) -> Dict[str, Any]:
        """分析筹码集中度"""
        try:
            chip_data = {}

            # 基于股东数据分析
            if data.get('holders_analysis', {}).get('has_data'):
                holder_num = data['holders_analysis'].get('holder_num', 0)
                change_ratio = data['holders_analysis'].get('change_ratio', 0)

                if holder_num > 0:
                    if holder_num < 30000:
                        chip_data['concentration'] = '高度集中'
                    elif holder_num < 50000:
                        chip_data['concentration'] = '相对集中'
                    else:
                        chip_data['concentration'] = '较为分散'

                    if change_ratio < -10:
                        chip_data['trend'] = '筹码集中'
                    elif change_ratio > 10:
                        chip_data['trend'] = '筹码分散'
                    else:
                        chip_data['trend'] = '相对稳定'

            # 基于资金流向分析
            if data.get('moneyflow', {}).get('has_data'):
                net_xl = data['moneyflow'].get('net_amount_xl', 0)
                net_l = data['moneyflow'].get('net_amount_l', 0)
                main_net = net_xl + net_l  # 主力资金净流入

                if main_net > 0:
                    chip_data['main_force'] = '主力流入'
                else:
                    chip_data['main_force'] = '主力流出'

                chip_data['main_net_amount'] = main_net

            return chip_data

        except Exception as e:
            print(f"筹码分析失败: {e}")
            return {}

    def _analyze_institution(self, data: Dict) -> Dict[str, Any]:
        """分析机构动向"""
        try:
            inst_data = {}

            # 基于融资融券数据
            if data.get('margin_detail', {}).get('has_data'):
                rzye = data['margin_detail'].get('rzye', 0)
                rzjme = data['margin_detail'].get('rzjme', 0)

                if rzye > 1000000000:  # 融资余额超过10亿
                    inst_data['margin_level'] = '高'
                elif rzye > 500000000:  # 5亿
                    inst_data['margin_level'] = '中'
                else:
                    inst_data['margin_level'] = '低'

                if rzjme > 0:
                    inst_data['margin_trend'] = '融资买入'
                else:
                    inst_data['margin_trend'] = '融资偿还'

            # 基于大宗交易数据
            if data.get('block_trade', {}).get('has_data'):
                block_count = data['block_trade'].get('total_count', 0)
                block_amount = data['block_trade'].get('total_amount', 0)

                if block_count > 0:
                    inst_data['block_trade_active'] = True
                    inst_data['block_trade_count'] = block_count
                    inst_data['block_trade_amount'] = block_amount
                else:
                    inst_data['block_trade_active'] = False

            return inst_data

        except Exception as e:
            print(f"机构分析失败: {e}")
            return {}


# 全局实例
advanced_client = AdvancedDataClient()