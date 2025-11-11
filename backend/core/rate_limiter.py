"""
API限流模块
防止API过度调用，保护Tushare等外部服务
"""
import time
from collections import defaultdict, deque
from typing import Optional
from threading import Lock


class RateLimiter:
    """简单的滑动窗口限流器"""

    def __init__(self, max_calls: int = 60, time_window: int = 60):
        """
        初始化限流器

        Args:
            max_calls: 时间窗口内最大调用次数
            time_window: 时间窗口大小（秒）
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = defaultdict(deque)
        self.lock = Lock()

    def is_allowed(self, key: str = "default") -> bool:
        """
        检查是否允许调用

        Args:
            key: 限流键（如API名称、IP地址等）

        Returns:
            bool: 是否允许调用
        """
        with self.lock:
            current_time = time.time()
            call_times = self.calls[key]

            # 移除时间窗口外的记录
            while call_times and call_times[0] < current_time - self.time_window:
                call_times.popleft()

            # 检查是否超过限制
            if len(call_times) >= self.max_calls:
                return False

            # 记录本次调用
            call_times.append(current_time)
            return True

    def get_remaining_calls(self, key: str = "default") -> int:
        """
        获取剩余可用调用次数

        Args:
            key: 限流键

        Returns:
            int: 剩余调用次数
        """
        with self.lock:
            current_time = time.time()
            call_times = self.calls[key]

            # 移除时间窗口外的记录
            while call_times and call_times[0] < current_time - self.time_window:
                call_times.popleft()

            return max(0, self.max_calls - len(call_times))

    def wait_if_needed(self, key: str = "default", timeout: Optional[float] = None) -> bool:
        """
        如果超过限制则等待，直到可以调用或超时

        Args:
            key: 限流键
            timeout: 最大等待时间（秒），None表示无限等待

        Returns:
            bool: 是否成功获得调用权限
        """
        start_time = time.time()

        while not self.is_allowed(key):
            if timeout and (time.time() - start_time) >= timeout:
                return False

            # 获取最早的调用时间
            with self.lock:
                call_times = self.calls[key]
                if call_times:
                    earliest_call = call_times[0]
                    wait_time = earliest_call + self.time_window - time.time()
                    if wait_time > 0:
                        time.sleep(min(wait_time, 0.1))
                else:
                    break

        return True


class TushareRateLimiter:
    """Tushare API专用限流器，支持积分限制"""

    def __init__(self):
        # Tushare免费用户限制：120次/分钟，单接口不超过200次/天
        self.minute_limiter = RateLimiter(max_calls=100, time_window=60)  # 留20次余量
        self.daily_limiters = defaultdict(lambda: RateLimiter(max_calls=180, time_window=86400))  # 留20次余量

    def check_and_wait(self, api_name: str, timeout: float = 30.0) -> bool:
        """
        检查并等待API调用许可

        Args:
            api_name: API名称
            timeout: 最大等待时间

        Returns:
            bool: 是否成功获得调用权限
        """
        # 先检查分钟限制
        if not self.minute_limiter.wait_if_needed(key="tushare", timeout=timeout):
            return False

        # 再检查单接口每日限制
        if not self.daily_limiters[api_name].wait_if_needed(key=api_name, timeout=timeout):
            return False

        return True

    def get_stats(self) -> dict:
        """
        获取限流统计信息

        Returns:
            dict: 统计信息
        """
        return {
            "minute_remaining": self.minute_limiter.get_remaining_calls("tushare"),
            "minute_limit": self.minute_limiter.max_calls,
        }


# 全局Tushare限流器实例
_tushare_limiter: Optional[TushareRateLimiter] = None


def get_tushare_limiter() -> TushareRateLimiter:
    """获取全局Tushare限流器实例"""
    global _tushare_limiter
    if _tushare_limiter is None:
        _tushare_limiter = TushareRateLimiter()
    return _tushare_limiter
