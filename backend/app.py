import os
import json
import threading
import queue
import logging
import time
import datetime as dt
from pathlib import Path
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import re
import math
from dotenv import load_dotenv
import pandas as pd

# 先加载 .env，避免下游模块在导入时读取不到环境变量
load_dotenv()

from core.analyze import run_pipeline, resolve_by_name
from core.market import fetch_market_overview
from core.hotspot import analyze_hotspot
from core.market_ai_analyzer import get_enhanced_market_ai_analyzer
from core.stock_picker import get_top_picks
from core.professional_report_generator_v2 import ProfessionalReportGeneratorV2
from core.advanced_data_client import advanced_client
from core.kronos_predictor import get_kronos_service
from nlp.ollama_client import OLLAMA_URL, OLLAMA_MODEL, OLLAMA_NUM_PREDICT, OLLAMA_TIMEOUT
import requests


# 简单的内存缓存
_api_cache = {}
_cache_lock = threading.Lock()

def get_cached_response(key: str, ttl_seconds: int = 60):
    """获取缓存的响应"""
    with _cache_lock:
        if key in _api_cache:
            data, timestamp = _api_cache[key]
            if time.time() - timestamp < ttl_seconds:
                return data
    return None

def set_cached_response(key: str, data: Any):
    """设置缓存的响应"""
    with _cache_lock:
        _api_cache[key] = (data, time.time())


# 业务异常类
class BusinessException(Exception):
    def __init__(self, message: str, status_code: int = 400, error_code: str = "BUSINESS_ERROR"):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)

class DataSourceException(BusinessException):
    def __init__(self, message: str):
        super().__init__(message, 503, "DATA_SOURCE_ERROR")

class ValidationException(BusinessException):
    def __init__(self, message: str):
        super().__init__(message, 400, "VALIDATION_ERROR")

class RateLimitException(BusinessException):
    def __init__(self, message: str):
        super().__init__(message, 429, "RATE_LIMIT_ERROR")

# 智能预警系统的None值处理
def safe_compare(value, threshold):
    """安全的数值比较，处理None值"""
    if value is None or threshold is None:
        return False
    try:
        return float(value) < float(threshold)
    except (ValueError, TypeError):
        return False


app = FastAPI(
    title="QSL-CN A股智能分析系统API",
    description="基于TuShare数据和Ollama AI的A股智能分析平台，提供个股分析、热点概念追踪、专业报告生成等功能",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 全局异常处理器
@app.exception_handler(BusinessException)
async def business_exception_handler(request, exc: BusinessException):
    logger.warning(f"Business exception: {exc.error_code} - {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "timestamp": dt.datetime.now().isoformat()
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "服务器内部错误，请稍后重试",
            "timestamp": dt.datetime.now().isoformat()
        }
    )
app.add_middleware(
    CORSMiddleware,
    # 允许所有源(包括file://协议用于本地测试)
    allow_origins=["*"],
    allow_credentials=False,  # 使用通配符时必须设为False
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# 日志到文件 + 控制台
_LOG_PATH = Path(__file__).with_name("server.log")
logger = logging.getLogger("qsl")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    fh = logging.FileHandler(_LOG_PATH, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(sh)
    logger.addHandler(fh)


# 简化版本 - 不需要任务调度器

def clean_nan_values(obj):
    """递归清理对象中的 NaN、Inf 等无效浮点数，替换为 None"""
    if isinstance(obj, dict):
        return {k: clean_nan_values(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nan_values(item) for item in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    return obj


class AnalyzeRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=20, description="股票名称或代码")
    force: bool = Field(False, description="是否强制刷新数据")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        v = v.strip()
        if not v:
            raise ValueError('股票名称不能为空')
        # 验证股票代码格式（6位数字）或中文股票名称
        if not (re.match(r'^\d{6}$', v) or re.match(r'^[\u4e00-\u9fa5A-Za-z0-9]+', v)):
            raise ValueError('股票名称格式不正确')
        return v


class HotspotRequest(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=10, description="概念关键词")
    force: bool = Field(False, description="是否强制刷新数据")
    
    @field_validator('keyword')
    @classmethod
    def validate_keyword(cls, v):
        v = v.strip()
        if not v:
            raise ValueError('关键词不能为空')
        return v


class ChatMessage(BaseModel):
    role: str = Field(..., pattern=r'^(system|user|assistant)$', description="消息角色")
    content: str = Field(..., min_length=1, max_length=2000, description="消息内容")


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(default=..., min_length=1, max_length=20, description="对话消息列表")
    stream: bool = Field(default=False, description="是否流式响应")


class KLineRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=20, description="股票名称或代码")
    pred_len: int = Field(default=30, ge=1, le=120, description="预测天数(1-120)")
    lookback: int = Field(default=400, ge=50, le=500, description="历史回看天数(50-500)")
    temperature: float = Field(default=1.0, ge=0.1, le=2.0, description="温度参数(0.1-2.0)")
    top_p: float = Field(default=0.9, ge=0.1, le=1.0, description="Nucleus采样概率(0.1-1.0)")
    sample_count: int = Field(default=3, ge=1, le=5, description="样本数量(1-5)")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        v = v.strip()
        if not v:
            raise ValueError('股票名称不能为空')
        return v


# SSE辅助函数
def _sse_event(event: str, data: Any) -> str:
    """生成SSE事件格式字符串"""
    import json
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

def _sse_log(event: str, data: str) -> str:
    """生成SSE日志格式字符串"""
    import json
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.get("/health", 
    summary="基础健康检查",
    description="检查API服务是否正常运行",
    response_description="服务状态信息",
    tags=["系统监控"])
def health():
    return {"ok": True, "timestamp": dt.datetime.now().isoformat()}

@app.get("/health/detailed",
    summary="详细健康检查",
    description="检查所有数据源和服务的健康状态",
    response_description="健康检查报告",
    tags=["系统监控"])
def health_detailed():
    """详细健康检查"""
    try:
        from core.health_check import health_checker
        return health_checker.run_all_checks()
    except Exception as e:
        logger.error(f"健康检查失败: {e}", exc_info=True)
        return {
            "overall_status": "unhealthy",
            "overall_message": "健康检查系统故障",
            "timestamp": dt.datetime.now().isoformat()
        }


@app.get("/resolve",
    summary="股票名称解析",
    description="根据股票名称或代码解析出完整的股票信息",
    response_description="股票基本信息",
    tags=["股票查询"])
def resolve(name: str):
    if not name or not name.strip():
        raise ValidationException("股票名称不能为空")
    
    try:
        item = resolve_by_name(name.strip())
        if not item:
            raise HTTPException(404, detail=f"未找到包含'{name}'的A股")
        return item
    except ValidationException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "权限" in error_msg or "频控" in error_msg or "每分钟最多访问" in error_msg:
            raise RateLimitException(f"数据源访问受限：{error_msg}")
        else:
            raise DataSourceException(f"股票解析失败：{error_msg}")
@app.get("/market",
    summary="获取市场概况",
    description="获取A股市场实时概况，包括主要指数、板块表现、资金流向等信息",
    response_description="完整的市场数据",
    tags=["市场数据"])
def market():
    try:
        # 检查缓存（2分钟TTL）
        cache_key = "market_overview"
        cached = get_cached_response(cache_key, ttl_seconds=120)
        if cached:
            return cached

        result = fetch_market_overview()
        result = clean_nan_values(result)

        # 缓存结果
        set_cached_response(cache_key, result)
        return result
    except Exception as e:
        logger.exception("获取市场数据失败: %s", e)
        raise DataSourceException("市场数据获取失败，请稍后重试")


@app.post("/market/refresh")
def refresh_market_data():
    """手动刷新市场数据"""
    try:
        import os
        import glob

        # 清理所有市场相关的缓存
        cache_patterns = [
            ".cache/index_daily_*",
            ".cache/shibor_*",
            ".cache/major_news_*",
            ".cache/ths_hot_*",
            ".cache/moneyflow_*",
            ".cache/margin_*",
            ".cache/top_*",
            ".cache/stk_limit_*"
        ]

        total_cleared = 0
        for pattern in cache_patterns:
            cache_files = glob.glob(pattern)
            for file in cache_files:
                try:
                    os.remove(file)
                    total_cleared += 1
                except Exception:
                    pass

        # 重新获取市场数据
        market_data = fetch_market_overview()

        return {
            "success": True,
            "message": f"市场数据刷新成功，清理了 {total_cleared} 个缓存文件",
            "indices_count": len(market_data.get('indices', [])),
            "data_date": market_data.get('data_date'),
            "is_realtime": market_data.get('is_realtime'),
            "timestamp": market_data.get('timestamp')
        }
    except Exception as e:
        logger.error(f"手动刷新市场数据失败: {e}")
        raise HTTPException(500, detail=str(e))


@app.get("/market/ai-analysis")
def market_ai_analysis():
    """获取QSL-AI市场综合分析"""
    try:
        # 获取市场数据
        market_data = fetch_market_overview()
        
        # 进行AI分析
        analyzer = get_enhanced_market_ai_analyzer()
        ai_analysis = analyzer.analyze_comprehensive_market(market_data)
        
        return {
            "market_data": market_data,
            "ai_analysis": ai_analysis
        }
    except Exception as e:
        logger.exception("获取报告失败: %s", e)
        raise HTTPException(500, detail=str(e))


@app.get("/market/enhanced-analysis")
def market_enhanced_analysis():
    """获取增强版QSL-AI市场洞察报告（包含恐慌贪婪指数、智能预警等）"""
    try:
        # 检查缓存（5分钟TTL）
        cache_key = "enhanced_analysis"
        cached = get_cached_response(cache_key, ttl_seconds=300)
        if cached:
            return cached

        # 获取市场数据
        market_data = fetch_market_overview()

        # 生成增强版分析报告
        analyzer = get_enhanced_market_ai_analyzer()
        insight_report = analyzer.generate_market_insight_report(market_data)

        result = {
            "success": True,
            "timestamp": time.time(),
            "market_data": market_data,
            "insight_report": insight_report
        }
        result = clean_nan_values(result)

        # 缓存结果
        set_cached_response(cache_key, result)
        return result
    except Exception as e:
        logger.error(f"增强版市场分析失败: {e}")
        raise HTTPException(500, detail=f"增强版分析失败: {str(e)}")


@app.get("/market/fear-greed-index")
def get_fear_greed_index():
    """单独获取恐慌贪婪指数"""
    try:
        # 检查缓存（5分钟TTL）
        cache_key = "fear_greed_index"
        cached = get_cached_response(cache_key, ttl_seconds=300)
        if cached:
            return cached

        market_data = fetch_market_overview()
        analyzer = get_enhanced_market_ai_analyzer()

        # 进行基础分析以计算恐慌贪婪指数
        analysis = analyzer.analyze_comprehensive_market(market_data)
        fear_greed_data = analysis.get("fear_greed_index", {})

        result = {
            "success": True,
            "timestamp": time.time(),
            "fear_greed_index": fear_greed_data
        }
        result = clean_nan_values(result)

        # 缓存结果
        set_cached_response(cache_key, result)
        return result
    except Exception as e:
        logger.error(f"恐慌贪婪指数获取失败: {e}")
        raise HTTPException(500, detail=f"恐慌贪婪指数获取失败: {str(e)}")


@app.get("/market/alerts")
def get_market_alerts():
    """获取市场智能预警"""
    try:
        market_data = fetch_market_overview()
        analyzer = get_enhanced_market_ai_analyzer()
        
        # 进行分析获取预警信息
        analysis = analyzer.analyze_comprehensive_market(market_data)
        alerts = analysis.get("alerts", [])
        
        result = {
            "success": True,
            "timestamp": time.time(),
            "alerts": alerts,
            "alert_count": len(alerts),
            "high_priority_count": len([a for a in alerts if a.get("level") == "high"])
        }
        return clean_nan_values(result)
    except Exception as e:
        logger.error(f"市场预警获取失败: {e}")
        raise HTTPException(500, detail=f"市场预警获取失败: {str(e)}")



@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    """股票分析 - 直接返回专业分析报告（默认使用实时数据）"""
    if not req.name or not req.name.strip():
        raise ValidationException("股票名称不能为空")
    
    try:
        # 默认强制获取实时数据，除非用户明确设置force=False
        force_realtime = True if req.force is None else req.force
        return analyze_professional(req.name.strip(), force_realtime)
    except ValidationException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "权限" in error_msg or "频控" in error_msg:
            raise RateLimitException(f"分析请求受限：{error_msg}")
        else:
            raise DataSourceException(f"股票分析失败：{error_msg}")


@app.get("/analyze/stream")
def analyze_stream(name: str, force: bool = False):
    """股票分析流式接口 - 实时返回进度和结果"""
    if not name:
        raise HTTPException(400, detail="name 不能为空")
    
    q: "queue.Queue[tuple[str, dict]]" = queue.Queue()
    done = {"v": False}
    result_box: dict = {"result": None}
    
    def _progress(step: str, payload):
        try:
            q.put(("progress", {"step": step, "payload": payload or {}}))
        except Exception:
            pass
    
    def _worker():
        try:
            # 执行分析流程 - 使用优化版分析模块，包含RGTI深度分析
            from core.analyze import run_pipeline
            result = run_pipeline(name, force=force, progress=_progress)

            # 检测旧版缓存（没有score或summary字段），强制重新分析
            if isinstance(result, dict) and (not result.get('score') or not result.get('summary')) and not force:
                print(f"[WARNING] 检测到旧版缓存数据（缺少score或summary），强制重新分析")
                result = run_pipeline(name, force=True, progress=_progress)

            # 辅助函数：安全获取嵌套字典值
            def safe_get(data, *keys, default=None):
                """安全获取嵌套字典值"""
                if not isinstance(data, dict):
                    return default
                for key in keys:
                    if isinstance(data, dict):
                        data = data.get(key)
                        if data is None:
                            return default
                    else:
                        return default
                return data if data is not None else default

            # 清理NaN值的函数
            def clean_nan_values(obj):
                """递归清理NaN值，保持None不变"""
                import math
                if isinstance(obj, dict):
                    return {k: clean_nan_values(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [clean_nan_values(item) for item in obj]
                elif isinstance(obj, float):
                    if math.isnan(obj) or math.isinf(obj):
                        return None
                    return obj
                return obj

            # 清理结果中的NaN值
            result = clean_nan_values(result)

            # 提取prices数据到顶层（从technical中提取）
            if isinstance(result, dict) and 'technical' in result and isinstance(result['technical'], dict):
                tech_data = result['technical']
                if 'prices' in tech_data:
                    # 将prices从technical提取到顶层
                    result['prices'] = tech_data['prices']

            # 使用分析结果中已有的评分和摘要
            if isinstance(result, dict):
                professional_score = result.get('score', {
                    "total": 0,
                    "details": {},
                    "rating": "无评级"
                })
                # 获取RGTI风格深度分析摘要
                deep_analysis_summary = result.get('summary', '')
                print(f"[DEBUG] Summary length: {len(deep_analysis_summary) if deep_analysis_summary else 0}")
                if not deep_analysis_summary:
                    print(f"[WARNING] No summary found in result. Result keys: {result.keys()}")
            else:
                professional_score = {
                    "total": 0,
                    "details": {},
                    "rating": "无评级"
                }
                deep_analysis_summary = ''

            # 增强数据展示
            if not isinstance(result, dict):
                result = {}
            enhanced_result: dict = {
                **result,
                "professional_analysis": {
                    "data_sources": {
                        "股东数据": "已获取" if isinstance(result, dict) and result.get("holders") else "未获取",
                        "资金流向": "已获取" if isinstance(result, dict) and result.get("capital_flow") else "未获取",
                        "龙虎榜": "已获取" if isinstance(result, dict) and result.get("dragon_tiger") else "未获取",
                        "大宗交易": "已获取" if isinstance(result, dict) and result.get("block_trade") else "未获取",
                        "融资融券": "已获取" if isinstance(result, dict) and result.get("margin") else "未获取",
                        "分红历史": "已获取" if isinstance(result, dict) and result.get("dividend") else "未获取",
                    },
                    "key_metrics": {}
                }
            }

            # 添加实际存在的key_metrics
            stream_metrics = {}
            if "holders" in result and isinstance(result["holders"], dict):
                concentration = result["holders"].get("concentration")
                if concentration is not None:
                    stream_metrics["股权集中度"] = concentration

            if "capital_flow" in result and isinstance(result["capital_flow"], dict):
                tushare_flow = result["capital_flow"].get("tushare", {})
                if isinstance(tushare_flow, dict):
                    net_amount = tushare_flow.get("net_amount")
                    if net_amount is not None:
                        stream_metrics["主力净流入"] = net_amount

            if "margin" in result and isinstance(result["margin"], dict):
                rzye_change = result["margin"].get("rzye_change")
                if rzye_change is not None:
                    stream_metrics["融资余额变化"] = rzye_change

            if "block_trade" in result and isinstance(result["block_trade"], dict):
                total_amount = result["block_trade"].get("total_amount")
                if total_amount is not None:
                    stream_metrics["大宗交易总额"] = total_amount

            if "dragon_tiger" in result and isinstance(result["dragon_tiger"], dict):
                on_list = result["dragon_tiger"].get("on_list")
                if on_list is not None:
                    stream_metrics["是否上龙虎榜"] = on_list

            if "dividend" in result and isinstance(result["dividend"], dict):
                total_records = result["dividend"].get("total_records")
                if total_records is not None:
                    stream_metrics["历史分红次数"] = total_records

            enhanced_result["professional_analysis"]["key_metrics"] = stream_metrics

            # 使用RGTI风格深度分析报告 - 如果没有summary则生成基础报告
            if not deep_analysis_summary:
                print(f"[WARNING] 未找到summary字段，生成基础报告。Result keys: {list(result.keys()) if isinstance(result, dict) else 'not a dict'}")
                # 生成基础报告而不是报错
                stock_name = result.get('basic', {}).get('name', '该股票') if isinstance(result, dict) else '该股票'
                score_info = result.get('score', {}) if isinstance(result, dict) else {}
                total_score = score_info.get('total', 0)
                rating = score_info.get('rating', 'N/A')
                deep_analysis_summary = f"# {stock_name} 分析报告\n\n综合评分：{total_score}/100\n投资评级：{rating}\n\n基于技术面、基本面、资金面等多维度分析生成。"

            enhanced_result["text"] = deep_analysis_summary
            
            # 添加专业评分
            enhanced_result["professional_score"] = professional_score
            if isinstance(professional_score, dict):
                enhanced_result["score"] = {
                    "total": professional_score.get("total", 0),
                    "details": professional_score.get("details", {}),
                    "rating": professional_score.get("rating", "N/A")
                }
                # 添加用于前端展示的json数据（包含完整的result数据）
                enhanced_result["json"] = {
                    "scoring": professional_score.get("details", {}),
                    "basic": result.get("basic", {}),
                    "technical": result.get("technical", {}),
                    "fundamental": result.get("fundamental", {}),
                }
            else:
                enhanced_result["score"] = {
                    "total": 0,
                    "details": {},
                    "rating": "N/A"
                }
                enhanced_result["json"] = {
                    "scoring": {},
                    "basic": result.get("basic", {}),
                    "technical": result.get("technical", {}),
                    "fundamental": result.get("fundamental", {}),
                }

            # 添加预测数据（如果存在）
            if isinstance(result, dict) and "predictions" in result:
                enhanced_result["predictions"] = result["predictions"]  # type: ignore

            # 再次清理整个结果
            enhanced_result = clean_nan_values(enhanced_result)  # type: ignore

            result_box["result"] = enhanced_result
            
        except Exception as e:
            q.put(("error", {"message": str(e)}))
        finally:
            q.put(("result", result_box.get("result", {})))
            q.put(("done", {}))
            done["v"] = True
    
    threading.Thread(target=_worker, daemon=True).start()
    
    def _gen():
        yield _sse_event("start", {"name": name, "force": force})
        while not done["v"] or not q.empty():
            try:
                ev, data = q.get(timeout=0.5)
                yield _sse_event(ev, data)
            except queue.Empty:
                yield _sse_event("ping", {})
        yield _sse_event("end", {})
    
    return StreamingResponse(_gen(), media_type="text/event-stream")


@app.get("/analyze/professional")
def analyze_professional(name: str, force: bool = True):
    """专业版分析 - 生成实用的投资报告"""
    if not name:
        raise HTTPException(400, detail="name 不能为空")
    
    try:
        # 使用优化版分析模块，包含RGTI风格深度分析
        from core.analyze import run_pipeline

        # 获取完整分析数据（使用优化版本，自动包含深度分析）
        result = run_pipeline(name, force=force)

        # 辅助函数：安全获取嵌套字典值
        def safe_get(data, *keys, default=None):
            """安全获取嵌套字典值"""
            if not isinstance(data, dict):
                return default
            for key in keys:
                if isinstance(data, dict):
                    data = data.get(key)
                    if data is None:
                        return default
                else:
                    return default
            return data if data is not None else default

        # 清理NaN值的函数
        def clean_nan_values(obj):
            """递归清理NaN值，保持None不变"""
            import math
            if isinstance(obj, dict):
                return {k: clean_nan_values(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean_nan_values(item) for item in obj]
            elif isinstance(obj, float):
                if math.isnan(obj) or math.isinf(obj):
                    return None
                return obj
            return obj

        # 清理结果中的NaN值
        result = clean_nan_values(result)

        # 提取prices数据到顶层（从technical中提取）
        if isinstance(result, dict) and 'technical' in result and isinstance(result['technical'], dict):
            tech_data = result['technical']
            if 'prices' in tech_data:
                # 将prices从technical提取到顶层
                result['prices'] = tech_data['prices']

        # 增强数据展示
        enhanced_result = dict(result) if isinstance(result, dict) else {}
        enhanced_result.update({
            "professional_analysis": {
                "data_sources": {
                    "股东数据": "已获取" if isinstance(result, dict) and result.get("holders") else "未获取",
                    "资金流向": "已获取" if isinstance(result, dict) and result.get("capital_flow") else "未获取",
                    "龙虎榜": "已获取" if isinstance(result, dict) and result.get("dragon_tiger") else "未获取",
                    "大宗交易": "已获取" if isinstance(result, dict) and result.get("block_trade") else "未获取",
                    "融资融券": "已获取" if isinstance(result, dict) and result.get("margin") else "未获取",
                    "分红历史": "已获取" if isinstance(result, dict) and result.get("dividend") else "未获取",
                },
                "key_metrics": {}
            }
        })

        # 只添加有效数据的关键指标 - 不使用默认值
        key_metrics = {}

        # 只有当数据存在时才添加
        if isinstance(result, dict):
            if "holders" in result and isinstance(result["holders"], dict):
                concentration = result["holders"].get("concentration")
                if concentration is not None:
                    key_metrics["股权集中度"] = concentration

            if "capital_flow" in result and isinstance(result["capital_flow"], dict):
                tushare_flow = result["capital_flow"].get("tushare", {})
                if isinstance(tushare_flow, dict):
                    net_amount = tushare_flow.get("net_amount")
                    if net_amount is not None:
                        key_metrics["主力净流入"] = net_amount

            if "margin" in result and isinstance(result["margin"], dict):
                rzye_change = result["margin"].get("rzye_change")
                if rzye_change is not None:
                    key_metrics["融资余额变化"] = rzye_change

            if "block_trade" in result and isinstance(result["block_trade"], dict):
                total_amount = result["block_trade"].get("total_amount")
                if total_amount is not None:
                    key_metrics["大宗交易总额"] = total_amount

            if "dragon_tiger" in result and isinstance(result["dragon_tiger"], dict):
                on_list = result["dragon_tiger"].get("on_list")
                if on_list is not None:
                    key_metrics["是否上龙虎榜"] = on_list

            if "dividend" in result and isinstance(result["dividend"], dict):
                total_records = result["dividend"].get("total_records")
                if total_records is not None:
                    key_metrics["历史分红次数"] = total_records

        if "professional_analysis" in enhanced_result and isinstance(enhanced_result["professional_analysis"], dict):
            enhanced_result["professional_analysis"]["key_metrics"] = key_metrics
        
        # 使用RGTI风格深度分析报告
        if isinstance(result, dict):
            # 获取深度分析摘要（已包含完整的RGTI风格报告）
            practical_report = result.get("summary", "")
            quick_summary = result.get("quick_summary", result.get("summary", ""))

            # 如果摘要不存在，生成基础报告而不是空报告
            if not practical_report:
                # 只显示有效的评分数据
                report_lines = [f"# {name} 投资分析报告"]

                technical_info = result.get('technical', {})
                if isinstance(technical_info, dict):
                    tech_score = technical_info.get('technical_score')
                    if tech_score is not None:
                        report_lines.append(f"**技术面评分**：{tech_score}/100")

                fundamental_info = result.get('fundamental', {})
                if isinstance(fundamental_info, dict):
                    fund_score = fundamental_info.get('valuation_score')
                    if fund_score is not None:
                        report_lines.append(f"**基本面评分**：{fund_score}/100")

                sentiment_info = result.get('sentiment', {})
                if isinstance(sentiment_info, dict):
                    sentiment_score = sentiment_info.get('sentiment_score')
                    if sentiment_score is not None:
                        report_lines.append(f"**情绪面评分**：{sentiment_score}/100")

                industry_info = result.get('industry', {})
                if isinstance(industry_info, dict):
                    industry_score = industry_info.get('industry_score')
                    if industry_score is not None:
                        report_lines.append(f"**行业面评分**：{industry_score}/100")

                score_info = result.get('score')
                if isinstance(score_info, dict):
                    total_score = score_info.get('total')
                    rating = score_info.get('rating')
                    if total_score is not None:
                        report_lines.append(f"\n**综合评分**：{total_score}/100")
                    if rating:
                        report_lines.append(f"**投资评级**：{rating}")

                timestamp = result.get('timestamp')
                if timestamp:
                    report_lines.append(f"\n数据获取时间：{timestamp}")

                practical_report = "\n".join(report_lines)
        else:
            practical_report = "数据格式错误，无法生成报告"
            quick_summary = "数据格式错误"
        
        # 更新返回结果 - 优先使用RGTI风格深度分析
        enhanced_result["text"] = practical_report  # type: ignore
        enhanced_result["quick_summary"] = quick_summary  # type: ignore
        enhanced_result["report_type"] = "deep_analysis"  # type: ignore  # 标记为深度分析
        enhanced_result["deep_analysis"] = practical_report  # type: ignore  # 添加专门的深度分析字段
        enhanced_result["data_timestamp"] = dt.datetime.now().isoformat()  # type: ignore

        # 添加用于前端展示的json数据（包含完整的result数据）
        score_data = result.get("score", {}) if isinstance(result, dict) else {}
        enhanced_result["json"] = {
            "scoring": score_data.get("details", {}) if isinstance(score_data, dict) else {},
            "basic": result.get("basic", {}),
            "technical": result.get("technical", {}),
            "fundamental": result.get("fundamental", {}),
        }

        # 添加预测数据（如果存在）
        if isinstance(result, dict) and "predictions" in result:
            enhanced_result["predictions"] = result["predictions"]  # type: ignore

        # 再次清理整个结果
        enhanced_result = clean_nan_values(enhanced_result)

        return enhanced_result
        
    except Exception as e:
        logger.error(f"专业版分析失败: {e}")
        raise HTTPException(500, detail=str(e))


# 全局任务状态存储（生产环境应使用Redis）
report_tasks = {}

def _generate_report_task(task_id: str, report_type: str):
    """后台任务：生成报告"""
    try:
        report_tasks[task_id]['status'] = 'processing'
        report_tasks[task_id]['progress'] = 10

        generator = ProfessionalReportGeneratorV2()

        report_tasks[task_id]['progress'] = 30

        # 根据报告类型调用对应的生成方法
        if report_type == "morning":
            report = generator.generate_professional_morning_report()
            generator.save_report(report)
        elif report_type == "noon":
            report = generator.generate_professional_morning_report()
            report['type'] = 'noon'
            generator.save_report(report)
        elif report_type == "evening":
            report = generator.generate_professional_morning_report()
            report['type'] = 'evening'
            generator.save_report(report)
        elif report_type == "comprehensive_market":
            report = generator.generate_comprehensive_market_report()
        else:
            raise Exception(f"不支持的报告类型: {report_type}")

        report_tasks[task_id]['progress'] = 90

        # 清理NaN值
        import math
        def clean_nan_values(obj):
            if isinstance(obj, dict):
                return {k: clean_nan_values(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean_nan_values(item) for item in obj]
            elif isinstance(obj, float):
                if math.isnan(obj) or math.isinf(obj):
                    return None
                return obj
            return obj

        report = clean_nan_values(report)

        report_tasks[task_id]['status'] = 'completed'
        report_tasks[task_id]['progress'] = 100
        report_tasks[task_id]['result'] = report

        logger.info(f"任务{task_id}完成：{report_type}报告")

    except Exception as e:
        report_tasks[task_id]['status'] = 'failed'
        report_tasks[task_id]['error'] = str(e)
        logger.error(f"任务{task_id}失败: {e}", exc_info=True)

@app.post("/reports/{report_type}")
async def generate_report(report_type: str, background_tasks: BackgroundTasks):
    """异步生成专业报告 - 立即返回任务ID"""
    try:
        if report_type not in ["morning", "noon", "evening", "comprehensive_market"]:
            raise HTTPException(400, detail=f"不支持的报告类型: {report_type}")

        # 生成任务ID
        task_id = f"{report_type}_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 初始化任务状态
        report_tasks[task_id] = {
            'status': 'pending',
            'progress': 0,
            'type': report_type,
            'created_at': time.time()
        }

        # 添加后台任务
        background_tasks.add_task(_generate_report_task, task_id, report_type)

        logger.info(f"创建报告生成任务: {task_id}")

        return {
            "success": True,
            "task_id": task_id,
            "message": "报告正在后台生成，请使用task_id查询进度",
            "check_url": f"/reports/task/{task_id}"
        }

    except Exception as e:
        logger.error(f"创建报告任务失败: {e}")
        raise HTTPException(500, detail=f"创建任务失败: {str(e)}")

@app.get("/reports/task/{task_id}")
def get_report_task_status(task_id: str):
    """查询报告生成任务状态"""
    if task_id not in report_tasks:
        raise HTTPException(404, detail="任务不存在")

    task = report_tasks[task_id]

    response = {
        "task_id": task_id,
        "status": task['status'],
        "progress": task['progress'],
        "type": task['type']
    }

    if task['status'] == 'completed':
        response['report'] = task['result']
    elif task['status'] == 'failed':
        response['error'] = task.get('error', 'Unknown error')

    return response


@app.get("/reports/history")
def get_report_history(days: int = 30):
    """获取历史报告列表 - 真正的实现"""
    try:
        import os
        import json
        from datetime import datetime, timedelta
        from pathlib import Path

        # 真正扫描缓存目录获取历史报告
        cache_dir = Path(__file__).parent / ".cache" / "reports"
        history = []

        if cache_dir.exists():
            # 计算日期范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # 扫描所有JSON文件
            for file_path in cache_dir.glob("*.json"):
                try:
                    # 从文件名解析日期和类型
                    # 格式：2025-09-12_morning_professional_v2.json 或 2025-09-13_comprehensive_market_professional_v2.json
                    filename = file_path.stem
                    parts = filename.split("_")

                    if len(parts) >= 2:
                        date_str = parts[0]
                        # 处理不同格式的报告类型
                        # 文件名格式：
                        # 1. 2025-10-20_professional_morning_report_v3.json
                        # 2. 2025-10-20_comprehensive_market_professional_v2.json

                        if len(parts) >= 3 and parts[1] == "comprehensive":
                            report_type = "comprehensive_market"  # 综合市场报告
                        elif len(parts) >= 3 and parts[1] == "professional":
                            # professional_morning_report_v3 格式
                            report_type = parts[2] if len(parts) >= 3 else "morning"  # 取morning/noon/evening
                        else:
                            report_type = parts[1]  # 旧格式兼容

                        # 检查日期是否在范围内
                        try:
                            file_date = datetime.strptime(date_str, "%Y-%m-%d")
                            if start_date <= file_date <= end_date:
                                # 读取文件获取摘要
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    report_data = json.load(f)

                                # 根据报告类型生成不同的标题和预览
                                type_names = {
                                    "morning": "早报",
                                    "noon": "午报",
                                    "evening": "晚报",
                                    "comprehensive_market": "综合市场报告"
                                }

                                if report_type == "comprehensive_market":
                                    title = f"{date_str} {type_names.get(report_type, '市场报告')}"
                                    preview = (report_data.get("ai_summary", "") or
                                             report_data.get("professional_summary", "") or
                                             report_data.get("summary", "") or
                                             "暂无摘要")[:100]
                                else:
                                    title = f"{date_str} {type_names.get(report_type, report_type)}"
                                    preview = (report_data.get("professional_summary", "") or
                                             report_data.get("summary", "") or
                                             "暂无摘要")[:100]

                                history.append({
                                    "type": report_type,
                                    "date": date_str,
                                    "title": title,
                                    "filename": filename,
                                    "file_size": file_path.stat().st_size,
                                    "preview": preview,
                                    "generated_at": report_data.get("generated_at", date_str)
                                })
                        except (ValueError, KeyError):
                            continue

                except Exception as e:
                    logger.debug(f"解析文件{file_path}失败: {e}")
                    continue

        # 按日期倒序排序
        history.sort(key=lambda x: x["date"], reverse=True)

        return {
            "success": True,
            "history": history,
            "total": len(history),
            "cache_dir": str(cache_dir),
            "days_requested": days
        }

    except Exception as e:
        logger.error(f"获取报告历史失败: {e}", exc_info=True)
        return {
            "success": False,
            "history": [],
            "total": 0,
            "error": str(e)
        }


@app.get("/reports/{report_type}")
def get_report(report_type: str, date: str | None = None):
    """获取指定日期的报告"""
    try:
        if report_type not in ["morning", "noon", "evening", "comprehensive_market"]:
            raise HTTPException(400, detail=f"不支持的报告类型: {report_type}")

        # 尝试从缓存文件中获取报告
        from pathlib import Path

        cache_dir = Path(__file__).parent / ".cache" / "reports"
        cache_dir.mkdir(parents=True, exist_ok=True)

        report_file = None

        if date:
            # 查找特定日期的报告 - 支持不同的文件名格式
            if report_type == "comprehensive_market":
                pattern = f"{date}_comprehensive_market_professional_v2.json"
            else:
                pattern = f"{date}_professional_morning_report_v3.json"

            report_file = cache_dir / pattern

            # 如果没找到，尝试旧格式
            if not report_file.exists():
                alt_patterns = [
                    f"{date}_{report_type}_professional_v2.json",
                    f"{date}_{report_type}_report.json",
                    f"{date}_comprehensive_market_professional_v2.json"
                ]
                for alt_pattern in alt_patterns:
                    alt_file = cache_dir / alt_pattern
                    if alt_file.exists():
                        report_file = alt_file
                        break
        else:
            # 查找最新的报告 - 根据类型查找对应文件
            if report_type == "comprehensive_market":
                pattern = "*_comprehensive_market_professional_v2.json"
            else:
                pattern = f"*_professional_morning_report_v3.json"

            files = list(cache_dir.glob(pattern))

            # 如果没找到，尝试其他模式
            if not files:
                files = list(cache_dir.glob(f"*_{report_type}_*.json"))

            if files:
                # 按修改时间排序，获取最新的
                report_file = max(files, key=lambda x: x.stat().st_mtime)

        report = None
        if report_file and report_file.exists():
            try:
                with open(report_file, 'r', encoding='utf-8') as f:
                    report = json.load(f)
                logger.info(f"成功加载报告: {report_file.name}")
            except Exception as e:
                logger.error(f"读取报告文件失败: {e}")
                report = None

        if not report:
            raise HTTPException(404, detail=f"未找到{date or '最新'}的{report_type}报告")

        return {
            "success": True,
            "report": report,
            "type": report_type
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取{report_type}报告失败: {e}", exc_info=True)
        raise HTTPException(500, detail=f"获取报告失败: {str(e)}")


@app.delete("/reports/{report_type}")
def delete_report(report_type: str, date: str):
    """删除指定日期的报告"""
    try:
        from pathlib import Path
        import os

        if report_type not in ["morning", "noon", "evening", "comprehensive_market"]:
            raise HTTPException(400, detail=f"不支持的报告类型: {report_type}")

        cache_dir = Path(__file__).parent / ".cache" / "reports"

        # 查找特定日期的报告文件 - 支持多种文件名格式
        possible_patterns = []

        if report_type == "comprehensive_market":
            possible_patterns.append(f"{date}_comprehensive_market_professional_v2.json")
        else:
            possible_patterns.extend([
                f"{date}_professional_morning_report_v3.json",
                f"{date}_{report_type}_professional_v2.json",
                f"{date}_{report_type}_report.json"
            ])

        report_file = None
        for pattern in possible_patterns:
            candidate = cache_dir / pattern
            if candidate.exists():
                report_file = candidate
                break

        if not report_file or not report_file.exists():
            raise HTTPException(404, detail=f"未找到{date}的{report_type}报告")

        # 删除文件
        os.remove(report_file)
        logger.info(f"已删除报告: {report_file}")

        return {
            "success": True,
            "message": f"已删除{date}的{report_type}报告"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除{report_type}报告失败: {e}", exc_info=True)
        raise HTTPException(500, detail=f"删除报告失败: {str(e)}")


@app.get("/screening/top-picks")
def screening_top_picks(date: str | None = None, limit: int = 10):
    """量化选股Top榜（估值/动量/资金/连板/热度综合）"""
    try:
        picks = get_top_picks(trade_date=date, limit=limit)
        return {
            "trade_date": date,
            "count": len(picks),
            "picks": picks
        }
    except Exception as e:
        logger.error(f"选股失败: {e}")
        raise HTTPException(500, detail=str(e))


@app.post("/hotspot")
def hotspot(req: HotspotRequest):
    """热点概念分析 - 使用增强版分析器"""
    if not req.keyword:
        raise ValidationException("关键词不能为空")
    try:
        # 使用增强版热点分析器
        from core.enhanced_hotspot_analyzer import enhanced_hotspot_analyzer

        # 定义进度回调
        def _progress(progress: int, message: str, payload: Optional[Dict[str, Any]] = None):
            try:
                logger.info(f"HOTSPOT [{progress}%] {message} {json.dumps(payload or {}, ensure_ascii=False)}")
            except Exception:
                logger.info(f"HOTSPOT [{progress}%] {message}")

        # 执行综合热点分析（传递force参数）
        result = enhanced_hotspot_analyzer.comprehensive_hotspot_analysis(
            req.keyword,
            days=5,
            progress_callback=_progress,
            force=req.force
        )

        # 跳过基础分析和LLM总结以提高速度（与stream端点保持一致）
        # basic_result = analyze_hotspot(req.keyword, req.force)
        # result["basic_analysis"] = basic_result
        # llm_summary = summarize_hotspot(basic_result)
        # result["llm_summary"] = llm_summary

        # 生成简单摘要
        result["llm_summary"] = f"概念「{req.keyword}」综合评分 {result.get('comprehensive_score', 0)}/100，共发现{len(result.get('related_stocks', []))}只相关股票。"

        return clean_nan_values(result)
    except ValidationException:
        raise
    except Exception as e:
        msg = str(e)
        if "每分钟最多访问" in msg or "每小时最多访问" in msg or "权限" in msg:
            raise RateLimitException(msg)
        raise DataSourceException(f"热点分析失败：{msg}")


@app.post("/chat")
def chat(req: ChatRequest):
    """转发到本地 Ollama 进行对话（非流式）。

    请求体示例：
    {
      "messages": [
        {"role": "system", "content": "你是投研助手"},
        {"role": "user", "content": "RSI 是什么？"}
      ]
    }
    """
    try:
        if not req.messages:
            raise HTTPException(400, detail="messages 不能为空")

        body = {
            "model": OLLAMA_MODEL,
            "messages": [m.model_dump() for m in req.messages],
            "stream": False,
            "options": {
                "num_ctx": 8192,
                "num_predict": OLLAMA_NUM_PREDICT,
                "temperature": 0.2,
            },
        }
        r = requests.post(f"{OLLAMA_URL}/api/chat", json=body, timeout=OLLAMA_TIMEOUT)
        if r.status_code >= 400:
            try:
                detail = r.json()
            except Exception:
                detail = r.text
            raise HTTPException(502, detail=detail)
        j = r.json() or {}
        # 兼容 Ollama 响应结构：{"message": {"role": "assistant", "content": "..."}}
        message = (j.get("message") or {})
        content = message.get("content", "").strip()
        role = message.get("role", "assistant")
        return {"message": {"role": role, "content": content}}
    except HTTPException:
        raise
    except requests.exceptions.Timeout:
        raise HTTPException(504, detail="Ollama 响应超时")
    except Exception as e:
        logger.exception("聊天接口错误: %s", e)
        raise HTTPException(500, detail=str(e))


@app.get("/hotspot/stream")
def hotspot_stream(keyword: str, force: bool = False):
    """热点概念分析流式接口 - 实时返回进度"""
    if not keyword:
        raise ValidationException("关键词不能为空")

    q: "queue.Queue[tuple[str, dict]]" = queue.Queue()
    done = {"v": False}
    result_box: dict = {"result": None}

    def _progress_callback(progress: int, message: str, payload: Optional[Dict[str, Any]] = None):
        """进度回调函数"""
        try:
            q.put(("progress", {
                "progress": progress,
                "message": message,
                "payload": payload or {}
            }))
        except Exception:
            pass

    def _worker():
        try:
            # 使用增强版热点分析器
            from core.enhanced_hotspot_analyzer import enhanced_hotspot_analyzer
            from nlp.ollama_client import summarize_hotspot

            # 执行综合分析
            result = enhanced_hotspot_analyzer.comprehensive_hotspot_analysis(
                keyword,
                days=5,
                progress_callback=_progress_callback,
                force=force
            )

            # 跳过基础分析和LLM总结以提高速度（前端直接使用增强分析结果）
            # from core.hotspot import analyze_hotspot
            # basic_result = analyze_hotspot(keyword, force)
            # result["basic_analysis"] = basic_result

            logger.info(f"增强热点分析完成，综合评分: {result.get('comprehensive_score', 0)}")

            # LLM总结已在enhanced_hotspot_analyzer中生成，不需要重复生成
            # 如果没有llm_summary（缓存数据可能没有），添加简单摘要
            if not result.get('llm_summary'):
                result["llm_summary"] = f"概念「{keyword}」综合评分 {result.get('comprehensive_score', 0)}/100，共发现{len(result.get('related_stocks', []))}只相关股票。"
                logger.warning("使用简单摘要（LLM报告未生成）")

            q.put(("progress", {
                "progress": 100,
                "message": "分析完成",
                "payload": {"score": result.get('comprehensive_score', 0)}
            }))

            result_box["result"] = result
            logger.info(f"热点分析完成，综合评分: {result.get('comprehensive_score', 0)}")
        except Exception as e:
            logger.error(f"热点分析失败: {e}", exc_info=True)
            q.put(("error", {"message": str(e)}))
        finally:
            final_result = result_box.get("result")
            # 清理NaN值避免JSON序列化错误
            cleaned_result: Dict[str, Any] = {}
            if final_result:
                final_result = clean_nan_values(final_result)
                cleaned_result = final_result if isinstance(final_result, dict) else {}
            q.put(("result", cleaned_result))
            q.put(("done", {}))
            done["v"] = True

    threading.Thread(target=_worker, daemon=True).start()

    def _gen():
        yield _sse_event("start", {"keyword": keyword, "force": force})
        while not done["v"] or not q.empty():
            try:
                ev, data = q.get(timeout=0.5)
                yield _sse_event(ev, data)
            except queue.Empty:
                yield _sse_event("ping", {})
        yield _sse_event("end", {})

    return StreamingResponse(_gen(), media_type="text/event-stream")


@app.get("/hotspot/trending")
def hotspot_trending():
    """获取当前热门概念列表 - 基于真实涨停数据"""
    try:
        from core.advanced_data_client import advanced_client
        from core.tushare_client import concept_detail

        # 获取今日涨停数据
        trade_date = dt.datetime.now().strftime('%Y%m%d')
        limit_up = advanced_client.limit_list_d(trade_date=trade_date, limit_type='U')

        if limit_up.empty:
            # 如果今天没数据，尝试最近3个交易日
            for days_back in range(1, 4):
                prev_date = (dt.datetime.now() - dt.timedelta(days=days_back)).strftime('%Y%m%d')
                limit_up = advanced_client.limit_list_d(trade_date=prev_date, limit_type='U')
                if not limit_up.empty:
                    trade_date = prev_date
                    logger.info(f"使用{prev_date}的涨停数据")
                    break

        if limit_up.empty:
            raise Exception("无涨停数据")

        # 统计概念热度
        concept_heat = {}

        for _, stock in limit_up.iterrows():
            try:
                concepts = concept_detail(ts_code=stock['ts_code'])
                if not concepts.empty:
                    for concept_name in concepts['concept_name'].tolist()[:3]:
                        if concept_name not in concept_heat:
                            concept_heat[concept_name] = {
                                'stock_count': 0,
                                'limit_times_sum': 0,
                                'stocks': []
                            }
                        concept_heat[concept_name]['stock_count'] += 1
                        concept_heat[concept_name]['limit_times_sum'] += stock.get('limit_times', 1)
                        concept_heat[concept_name]['stocks'].append(stock['name'])
            except:
                continue

        # 计算热度分数：(涨停数量 * 20 + 连板数总和 * 5)，最高100分
        trending_concepts = []
        for concept, data in concept_heat.items():
            heat_score = min(100, data['stock_count'] * 20 + data['limit_times_sum'] * 5)
            trending_concepts.append({
                'concept': concept,
                'heat_score': heat_score,
                'related_stocks_count': data['stock_count'],
                'representative_stocks': data['stocks'][:3]
            })

        # 按热度排序，取前10
        trending_concepts.sort(key=lambda x: x['heat_score'], reverse=True)
        trending_concepts = trending_concepts[:10]

        logger.info(f"生成{len(trending_concepts)}个热门概念，基于{len(limit_up)}只涨停股票")

        return {
            'success': True,
            'trending_concepts': trending_concepts,
            'data_date': trade_date,
            'limit_up_count': len(limit_up),
            'timestamp': dt.datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"获取热门概念失败: {e}")
        return {
            'success': False,
            'trending_concepts': [],
            'timestamp': dt.datetime.now().isoformat(),
            'error': str(e)
        }


@app.get("/hotspot/history")
def hotspot_history(keyword: str, days: int = 30):
    """获取热点概念历史分析记录"""
    try:
        from pathlib import Path
        import glob

        cache_dir = Path(__file__).parent / ".cache" / "hotspot"
        cache_dir.mkdir(parents=True, exist_ok=True)

        history = []
        pattern = f"*{keyword}*.json"

        for file_path in cache_dir.glob(pattern):
            try:
                file_stat = file_path.stat()
                created_time = dt.datetime.fromtimestamp(file_stat.st_mtime)

                # 只返回最近N天的记录
                if (dt.datetime.now() - created_time).days <= days:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    history.append({
                        'keyword': keyword,
                        'analysis_time': created_time.isoformat(),
                        'comprehensive_score': data.get('comprehensive_score', 0),
                        'filename': file_path.name
                    })
            except Exception as e:
                logger.debug(f"读取历史文件失败 {file_path}: {e}")
                continue

        # 按时间倒序排序
        history.sort(key=lambda x: x['analysis_time'], reverse=True)

        return {
            'success': True,
            'keyword': keyword,
            'history': history,
            'total': len(history)
        }
    except Exception as e:
        logger.error(f"获取热点历史失败: {e}")
        raise HTTPException(500, detail=str(e))


@app.get("/logs/stream")
def logs_stream():
    """SSE 持续输出 server.log 的追加内容，同时先回放末尾若干行。"""
    log_path = _LOG_PATH
    tail_lines = 200

    def _gen():
        try:
            # 先输出最后 N 行作为上下文
            if log_path.exists():
                with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()[-tail_lines:]
                for ln in lines:
                    yield _sse_log("log", ln.rstrip("\n"))

            # 跟随新增
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(0, os.SEEK_END)
                while True:
                    where = f.tell()
                    line = f.readline()
                    if not line:
                        time.sleep(0.5)
                        f.seek(where)
                    else:
                        yield _sse_log("log", line.rstrip("\n"))
        except GeneratorExit:
            return
        except Exception as e:
            yield _sse_log("error", str(e))

    return StreamingResponse(_gen(), media_type="text/event-stream")


@app.get("/realtime/quote/{ts_code}",
    summary="获取实时行情",
    description="获取单只股票的实时报价信息",
    tags=["实时数据"])
def get_realtime_quote(ts_code: str):
    """获取实时行情报价"""
    try:
        quote = advanced_client.get_realtime_quote(ts_code)
        if not quote:
            return {"error": "无法获取实时数据"}
        return quote
    except Exception as e:
        logger.error(f"获取实时行情失败: {e}")
        raise HTTPException(500, detail="实时行情获取失败")

@app.get("/realtime/indicators/{ts_code}",
    summary="获取实时技术指标",
    description="获取单只股票的实时技术指标",
    tags=["实时数据"])
def get_realtime_indicators(ts_code: str):
    """获取实时技术指标"""
    try:
        indicators = advanced_client.calculate_realtime_indicators(ts_code)
        if not indicators:
            return {"error": "无法计算实时技术指标"}
        return indicators
    except Exception as e:
        logger.error(f"获取实时技术指标失败: {e}")
        raise HTTPException(500, detail="实时技术指标计算失败")

@app.get("/realtime/kline/{ts_code}",
    summary="获取实时K线数据",
    description="获取单只股票的实时分钟K线数据",
    tags=["实时数据"])
def get_realtime_kline(ts_code: str, freq: str = "1min", count: int = 60):
    """获取实时K线数据"""
    try:
        df = advanced_client.get_realtime_kline(ts_code, freq, count)
        if df.empty:
            return {"error": "无法获取K线数据"}
        return df.to_dict('records')
    except Exception as e:
        logger.error(f"获取实时K线失败: {e}")
        raise HTTPException(500, detail="实时K线获取失败")


@app.post("/predict/kline",
    summary="K线预测",
    description="使用Kronos模型预测股票K线走势",
    response_description="K线预测结果",
    tags=["股票分析"])
def predict_kline(req: KLineRequest):
    """
    K线预测接口

    使用Kronos深度学习模型预测股票未来K线走势
    - 支持自定义预测天数(1-120天)
    - 支持自定义历史回看窗口(50-500天)
    - 支持温度和采样参数调节
    """
    try:
        # 1. 解析股票信息
        stock_info = resolve_by_name(req.name)
        if not stock_info:
            raise HTTPException(404, detail=f"未找到股票: {req.name}")

        ts_code = stock_info['ts_code']
        stock_name = stock_info['name']

        logger.info(f"开始K线预测: {stock_name} ({ts_code}), 预测{req.pred_len}天")

        # 2. 获取Kronos服务
        # 检测是否有GPU可用
        import torch
        if torch.cuda.is_available():
            device = "cuda:0"
        elif torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"

        kronos = get_kronos_service(device=device)

        # 3. 执行预测
        result = kronos.predict_kline(
            ts_code=ts_code,
            pred_len=req.pred_len,
            lookback=req.lookback,
            T=req.temperature,
            top_p=req.top_p,
            sample_count=req.sample_count
        )

        if result is None:
            raise HTTPException(500, detail="预测失败，请检查数据或模型状态")

        # 4. 添加股票基本信息
        result['stock_info'] = {
            'ts_code': ts_code,
            'name': stock_name,
            'industry': stock_info.get('industry'),
            'area': stock_info.get('area')
        }

        logger.info(f"K线预测完成: {stock_name} ({ts_code})")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"K线预测失败: {e}", exc_info=True)
        raise HTTPException(500, detail=f"预测失败: {str(e)}")


@app.get("/predict/kline/{name}",
    summary="K线预测(GET)",
    description="使用默认参数快速预测K线",
    response_description="K线预测结果",
    tags=["股票分析"])
def predict_kline_get(
    name: str,
    pred_len: int = 30,
    lookback: int = 400
):
    """
    K线预测接口(GET方式，使用默认参数)

    快速预测接口，使用默认的温度和采样参数
    """
    req = KLineRequest(
        name=name,
        pred_len=pred_len,
        lookback=lookback
    )
    return predict_kline(req)


if __name__ == "__main__":
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SERVER_PORT", 3001))  # 固定默认端口为3001
    uvicorn.run(app, host=host, port=port)



@app.get("/analyze/quick")
def analyze_quick(name: str, force: bool = False):
    """快速版分析 - 只获取核心数据"""
    if not name:
        raise HTTPException(400, detail="name 不能为空")

    try:
        from core.analyze import resolve_by_name
        from core.tushare_client import daily
        from datetime import datetime, timedelta

        # 1. 解析股票基本信息
        stock_info = resolve_by_name(name, force)
        if not stock_info:
            return {"error": f"未找到股票: {name}"}

        ts_code = stock_info['ts_code']
        stock_name = stock_info['name']

        # 2. 获取最新价格（只获取最近5天）
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')
        df = daily(ts_code=ts_code, start_date=start_date, end_date=end_date)

        if df is None or df.empty:
            return {"error": "无法获取价格数据"}

        # 3. 构建快速响应
        latest = df.iloc[0]

        # 提取标量值并处理NaN - 转换为 Python 原生类型
        def safe_float(val: Any, default: float = 0.0) -> float:
            """安全地将值转换为float，处理NaN和None"""
            if val is None or pd.isna(val):
                return default
            try:
                return float(val)
            except (ValueError, TypeError):
                return default

        price = safe_float(latest['close'])
        change = safe_float(latest.get('pct_chg', 0))
        volume = safe_float(latest.get('vol', 0))
        amount = safe_float(latest.get('amount', 0)) * 1000

        result = {
            "basic": stock_info,
            "timestamp": datetime.now().isoformat(),
            "quick_data": {
                "price": price,
                "change": change,
                "volume": volume,
                "amount": amount,
                "trade_date": str(latest.get('trade_date', ''))
            },
            "text": f"""# {stock_name} 快速分析

**当前价格**: {price}元
**今日涨跌**: {change:+.2f}%
**成交量**: {volume/10000:.1f}万手

基于最新交易数据的快速分析。完整分析请使用专业版接口。

---
*快速版本 - 数据更新时间: {datetime.now().strftime('%H:%M:%S')}*""",
            "score": {"total": 50, "rating": "中性"},
            "report_type": "quick"
        }

        return result

    except Exception as e:
        print(f"快速分析错误: {e}")
        return {"error": f"分析失败: {str(e)}"}
