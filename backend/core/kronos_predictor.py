"""
Kronos K线预测服务模块
集成Kronos模型进行股票K线预测，使用Tushare数据源
"""
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

# 添加Kronos模块路径
KRONOS_PATH = Path(__file__).parent.parent.parent / "Kronos-master"

# 验证Kronos目录是否存在
if not KRONOS_PATH.exists():
    logging.warning(f"Kronos directory not found at {KRONOS_PATH}")
    logging.warning("Kronos prediction features will be disabled")
    Kronos = None
    KronosTokenizer = None
    KronosPredictor = None
else:
    sys.path.insert(0, str(KRONOS_PATH))
    try:
        from model import Kronos, KronosTokenizer, KronosPredictor
        logging.info(f"Kronos model loaded successfully from {KRONOS_PATH}")
    except ImportError as e:
        logging.error(f"Failed to import Kronos model: {e}")
        logging.error("Kronos prediction features will be disabled")
        Kronos = None
        KronosTokenizer = None
        KronosPredictor = None

from .tushare_client import daily

logger = logging.getLogger(__name__)


def is_kronos_available() -> bool:
    """
    检查Kronos模型是否可用

    Returns:
        bool: Kronos模型是否可用
    """
    return all([Kronos is not None, KronosTokenizer is not None, KronosPredictor is not None])


class KronosPredictorService:
    """Kronos K线预测服务"""

    def __init__(self, device: str = "cpu"):
        """
        初始化Kronos预测服务

        Args:
            device: 计算设备 ("cpu", "cuda:0", "mps" 等)
        """
        self.device = device
        self.model = None
        self.tokenizer = None
        self.predictor = None
        self._initialized = False

        # 模型路径配置 - 使用HuggingFace Hub或本地路径
        # 优先使用HuggingFace Hub上的预训练模型
        self.tokenizer_path = "NeoQuasar/Kronos-Tokenizer-base"
        self.model_path = "NeoQuasar/Kronos-base"

        logger.info(f"KronosPredictorService initialized with device: {device}")

    def _lazy_load(self):
        """延迟加载模型（首次调用时加载）"""
        if self._initialized:
            return

        if not is_kronos_available():
            raise RuntimeError(
                "Kronos模型未正确安装或Kronos-master目录不存在。\n"
                "请确保:\n"
                "1. Kronos-master目录存在于项目根目录\n"
                "2. 已安装torch和transformers依赖\n"
                "预测功能将不可用。"
            )

        try:
            logger.info("Loading Kronos tokenizer...")
            self.tokenizer = KronosTokenizer.from_pretrained(self.tokenizer_path)

            logger.info("Loading Kronos model...")
            self.model = Kronos.from_pretrained(self.model_path)

            logger.info("Creating Kronos predictor...")
            self.predictor = KronosPredictor(
                self.model,
                self.tokenizer,
                device=self.device,
                max_context=512
            )

            self._initialized = True
            logger.info("Kronos model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load Kronos model: {e}")
            raise RuntimeError(f"Kronos模型加载失败: {str(e)}")

    def fetch_kline_data(
        self,
        ts_code: str,
        lookback: int = 400,
        end_date: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        从Tushare获取K线数据

        Args:
            ts_code: 股票代码（如 "600000.SH"）
            lookback: 回看天数
            end_date: 结束日期（YYYYMMDD格式），默认为今天

        Returns:
            包含OHLCV数据的DataFrame，按时间升序排列
        """
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")

        # 计算开始日期（考虑节假日，多取一些数据）
        start_date = (datetime.strptime(end_date, "%Y%m%d") - timedelta(days=lookback * 2)).strftime("%Y%m%d")

        try:
            # 使用daily函数获取日线数据
            df = daily(ts_code=ts_code, start_date=start_date, end_date=end_date)

            if df is None or df.empty:
                logger.warning(f"No data fetched for {ts_code}")
                return None

            # 按日期升序排序
            df = df.sort_values('trade_date').reset_index(drop=True)

            # 选择最近的lookback条数据
            if len(df) > lookback:
                df = df.tail(lookback).reset_index(drop=True)

            # 转换为Kronos所需格式
            # Tushare字段: open, high, low, close, vol(成交量，手), amount(成交额，千元)
            # Kronos需要: open, high, low, close, volume, amount
            kronos_df = pd.DataFrame({
                'open': df['open'],
                'high': df['high'],
                'low': df['low'],
                'close': df['close'],
                'volume': df['vol'] * 100,  # 手转换为股
                'amount': df['amount'] * 1000,  # 千元转换为元
            })

            # 添加时间戳
            kronos_df['timestamps'] = pd.to_datetime(df['trade_date'])

            logger.info(f"Fetched {len(kronos_df)} records for {ts_code}")
            return kronos_df

        except Exception as e:
            logger.error(f"Error fetching data for {ts_code}: {e}")
            return None

    def predict_kline(
        self,
        ts_code: str,
        pred_len: int = 30,
        lookback: int = 400,
        T: float = 1.0,
        top_p: float = 0.9,
        sample_count: int = 3,
        end_date: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        预测K线数据

        Args:
            ts_code: 股票代码
            pred_len: 预测未来的天数
            lookback: 回看天数（历史数据长度）
            T: 温度参数（控制随机性，建议1.0-1.5）
            top_p: Nucleus采样概率（建议0.9-1.0）
            sample_count: 样本数量（建议2-3）
            end_date: 结束日期（YYYYMMDD格式）

        Returns:
            预测结果字典，包含历史数据和预测数据
        """
        # 延迟加载模型
        self._lazy_load()

        # 获取历史K线数据
        df = self.fetch_kline_data(ts_code, lookback, end_date)
        if df is None or len(df) < 50:
            logger.error(f"Insufficient data for {ts_code}")
            return None

        try:
            # 准备预测输入
            x_df = df[['open', 'high', 'low', 'close', 'volume', 'amount']]
            x_timestamp = df['timestamps']

            # 生成未来日期序列（仅工作日）
            last_date = x_timestamp.iloc[-1]
            future_dates = []
            current_date = last_date

            while len(future_dates) < pred_len:
                current_date += timedelta(days=1)
                # 跳过周末
                if current_date.weekday() < 5:  # 0-4代表周一到周五
                    future_dates.append(current_date)

            y_timestamp = pd.Series(future_dates)

            # 执行预测
            logger.info(f"Predicting {pred_len} days for {ts_code}...")
            pred_df = self.predictor.predict(
                df=x_df,
                x_timestamp=x_timestamp,
                y_timestamp=y_timestamp,
                pred_len=pred_len,
                T=T,
                top_p=top_p,
                sample_count=sample_count,
                verbose=True
            )

            # 组织返回结果
            result = {
                'ts_code': ts_code,
                'prediction_date': datetime.now().isoformat(),
                'historical_data': {
                    'dates': x_timestamp.dt.strftime('%Y-%m-%d').tolist(),
                    'open': x_df['open'].tolist(),
                    'high': x_df['high'].tolist(),
                    'low': x_df['low'].tolist(),
                    'close': x_df['close'].tolist(),
                    'volume': x_df['volume'].tolist(),
                },
                'predicted_data': {
                    'dates': y_timestamp.dt.strftime('%Y-%m-%d').tolist(),
                    'open': pred_df['open'].tolist(),
                    'high': pred_df['high'].tolist(),
                    'low': pred_df['low'].tolist(),
                    'close': pred_df['close'].tolist(),
                    'volume': pred_df['volume'].tolist(),
                },
                'parameters': {
                    'lookback': lookback,
                    'pred_len': pred_len,
                    'temperature': T,
                    'top_p': top_p,
                    'sample_count': sample_count,
                }
            }

            logger.info(f"Prediction completed for {ts_code}")
            return result

        except Exception as e:
            logger.error(f"Prediction failed for {ts_code}: {e}", exc_info=True)
            return None

    def predict_batch(
        self,
        ts_codes: List[str],
        pred_len: int = 30,
        **kwargs
    ) -> Dict[str, Any]:
        """
        批量预测多只股票

        Args:
            ts_codes: 股票代码列表
            pred_len: 预测天数
            **kwargs: 其他预测参数

        Returns:
            批量预测结果字典
        """
        results = {}
        for ts_code in ts_codes:
            result = self.predict_kline(ts_code, pred_len=pred_len, **kwargs)
            if result:
                results[ts_code] = result

        return results


# 全局单例
_kronos_service: Optional[KronosPredictorService] = None


def get_kronos_service(device: str = "cpu") -> KronosPredictorService:
    """
    获取Kronos预测服务单例

    Args:
        device: 计算设备

    Returns:
        KronosPredictorService实例
    """
    global _kronos_service
    if _kronos_service is None:
        _kronos_service = KronosPredictorService(device=device)
    return _kronos_service
