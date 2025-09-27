"""
数据源健康检查模块
"""
import time
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class HealthCheckResult:
    def __init__(self, name: str, status: str, message: str = "", response_time: float = 0.0):
        self.name = name
        self.status = status  # "healthy", "degraded", "unhealthy"
        self.message = message
        self.response_time = response_time
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "response_time": self.response_time,
            "timestamp": self.timestamp.isoformat()
        }


class HealthChecker:
    def __init__(self):
        self.checks: List[HealthCheckResult] = []
        self.last_check_time = None
    
    def check_tushare_api(self) -> HealthCheckResult:
        """检查TuShare API健康状态"""
        try:
            from .tushare_client import _call_api
            start_time = time.time()
            
            # 简单API调用测试
            result = _call_api("stock_basic", list_status="L", limit=1)
            
            response_time = time.time() - start_time
            
            if result is not None and not result.empty:
                return HealthCheckResult("tushare", "healthy", "API响应正常", response_time)
            else:
                return HealthCheckResult("tushare", "degraded", "API返回空数据", response_time)
                
        except Exception as e:
            error_msg = str(e)
            if "权限" in error_msg or "频控" in error_msg:
                return HealthCheckResult("tushare", "degraded", f"API访问受限: {error_msg}")
            else:
                return HealthCheckResult("tushare", "unhealthy", f"API调用失败: {error_msg}")
    
    def check_ollama_service(self) -> HealthCheckResult:
        """检查Ollama服务健康状态"""
        try:
            from nlp.ollama_client import OLLAMA_URL
            import requests
            start_time = time.time()
            
            # 检查Ollama服务状态
            response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                return HealthCheckResult("ollama", "healthy", "服务运行正常", response_time)
            else:
                return HealthCheckResult("ollama", "degraded", f"服务响应异常: {response.status_code}", response_time)
                
        except requests.exceptions.ConnectionError:
            return HealthCheckResult("ollama", "unhealthy", "无法连接到Ollama服务")
        except Exception as e:
            return HealthCheckResult("ollama", "unhealthy", f"服务检查失败: {str(e)}")
    
    def check_cache_system(self) -> HealthCheckResult:
        """检查缓存系统健康状态"""
        try:
            from .tushare_client import _get_any_cached_df, _save_df_cache
            import pandas as pd
            start_time = time.time()
            
            # 测试缓存读写
            test_key = "health_check_test"
            test_df = pd.DataFrame({"test": [1, 2, 3]})
            
            # 写入测试
            _save_df_cache(test_key, test_df)
            
            # 读取测试
            cached_df = _get_any_cached_df(test_key)
            
            response_time = time.time() - start_time
            
            if cached_df is not None and not cached_df.empty:
                return HealthCheckResult("cache", "healthy", "缓存系统正常", response_time)
            else:
                return HealthCheckResult("cache", "degraded", "缓存读取异常", response_time)
                
        except Exception as e:
            return HealthCheckResult("cache", "unhealthy", f"缓存系统错误: {str(e)}")
    
    def run_all_checks(self) -> Dict[str, Any]:
        """运行所有健康检查"""
        start_time = time.time()
        
        checks = [
            self.check_tushare_api(),
            self.check_ollama_service(), 
            self.check_cache_system()
        ]
        
        self.checks = checks
        self.last_check_time = datetime.now()
        
        # 计算总体健康状态
        healthy_count = sum(1 for check in checks if check.status == "healthy")
        degraded_count = sum(1 for check in checks if check.status == "degraded")
        unhealthy_count = sum(1 for check in checks if check.status == "unhealthy")
        
        if unhealthy_count > 0:
            overall_status = "unhealthy"
            overall_message = f"{unhealthy_count}个服务不健康"
        elif degraded_count > 0:
            overall_status = "degraded"
            overall_message = f"{degraded_count}个服务性能降级"
        else:
            overall_status = "healthy"
            overall_message = "所有服务运行正常"
        
        total_time = time.time() - start_time
        
        return {
            "overall_status": overall_status,
            "overall_message": overall_message,
            "check_time": total_time,
            "timestamp": self.last_check_time.isoformat(),
            "checks": [check.to_dict() for check in checks],
            "summary": {
                "healthy": healthy_count,
                "degraded": degraded_count,
                "unhealthy": unhealthy_count,
                "total": len(checks)
            }
        }


# 全局健康检查实例
health_checker = HealthChecker()