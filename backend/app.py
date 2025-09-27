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
import re
import math
from dotenv import load_dotenv

# 先加载 .env，避免下游模块在导入时读取不到环境变量
load_dotenv()

from core.analyze import run_pipeline, resolve_by_name
from core.market import fetch_market_overview
from core.hotspot import analyze_hotspot
from core.market_ai_analyzer import get_enhanced_market_ai_analyzer
from core.stock_picker import get_top_picks
from core.professional_report_generator_v2 import ProfessionalReportGeneratorV2
from core.advanced_data_client import advanced_client
from nlp.ollama_client import OLLAMA_URL, OLLAMA_MODEL, OLLAMA_NUM_PREDICT, OLLAMA_TIMEOUT
import requests


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

# NaN值处理函数
def clean_nan_values(obj):
    """递归清理对象中的NaN值，替换为None或合理的默认值"""
    if isinstance(obj, dict):
        return {k: clean_nan_values(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nan_values(item) for item in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    return obj

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
    allow_origins=[
        "http://localhost:2345",
        "http://127.0.0.1:2345",
        "http://192.168.110.42:2345",  # 添加你的本机IP
        "http://192.168.110.142:2345"   # 添加你提到的另一个IP
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"],
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
        result = fetch_market_overview()
        return clean_nan_values(result)
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
        return clean_nan_values(result)
    except Exception as e:
        logger.error(f"增强版市场分析失败: {e}")
        raise HTTPException(500, detail=f"增强版分析失败: {str(e)}")


@app.get("/market/fear-greed-index")
def get_fear_greed_index():
    """单独获取恐慌贪婪指数"""
    try:
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
        return clean_nan_values(result)
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
                """递归清理NaN值"""
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

            # 使用RGTI风格深度分析报告
            if isinstance(result, dict) and deep_analysis_summary:
                enhanced_result["text"] = deep_analysis_summary
            elif isinstance(result, dict) and result.get("summary"):
                enhanced_result["text"] = result.get("summary")
            else:
                # 备用的结构化报告
                text_parts = []
                text_parts.append(f"## {name} 专业分析报告\n")
                
                # 数据源完整性
                text_parts.append("### 数据源覆盖情况")
                for key, status in enhanced_result["professional_analysis"]["data_sources"].items():
                    text_parts.append(f"- {key}: {status}")
                
                # 关键指标
                text_parts.append("\n### 关键指标")
                for key, value in enhanced_result["professional_analysis"]["key_metrics"].items():
                    text_parts.append(f"- {key}: {value}")
                
                enhanced_result["text"] = "\n".join(text_parts)
            
            # 添加专业评分
            enhanced_result["professional_score"] = professional_score
            if isinstance(professional_score, dict):
                enhanced_result["score"] = {
                    "total": professional_score.get("total", 0),
                    "details": professional_score.get("scores", {}),
                    "rating": professional_score.get("rating", "N/A")
                }
                # 添加用于前端展示的json数据
                enhanced_result["json"] = {
                    "scoring": professional_score.get("scores", {})
                }
            else:
                enhanced_result["score"] = {
                    "total": 0,
                    "details": {},
                    "rating": "N/A"
                }
                enhanced_result["json"] = {
                    "scoring": {}
                }

            # 添加LLM分析
            enhanced_result["llm_analysis"] = llm_analysis

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
            """递归清理NaN值"""
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
            quick_summary = result.get("summary", "")

            # 如果摘要不存在，尝试从其他字段获取
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
        
        # 添加用于前端展示的json数据
        enhanced_result["json"] = {
            "scoring": result.get("scorecard", {}) if isinstance(result, dict) else {}
        }
        
        # 再次清理整个结果
        enhanced_result = clean_nan_values(enhanced_result)
        
        return enhanced_result
        
    except Exception as e:
        logger.error(f"专业版分析失败: {e}")
        raise HTTPException(500, detail=str(e))


@app.post("/reports/{report_type}")
def generate_report(report_type: str):
    """生成专业报告（早报/午报/晚报）"""
    try:
        generator = ProfessionalReportGeneratorV2()

        if report_type == "morning":
            # 使用专业早报生成方法，按照早报模板的7个部分生成
            report = generator.generate_professional_morning_report()
        elif report_type == "noon":
            # 暂时使用相同的方法，以后可以创建专门的午报方法
            report = generator.generate_professional_morning_report()
        elif report_type == "evening":
            # 暂时使用相同的方法，以后可以创建专门的晚报方法
            report = generator.generate_professional_morning_report()
        else:
            raise HTTPException(400, detail=f"不支持的报告类型: {report_type}")
        
        # 清理NaN值的函数
        def clean_nan_values(obj):
            """递归清理NaN值"""
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
        
        # 清理报告中的NaN值
        report = clean_nan_values(report)
        
        return {
            "success": True,
            "report": report,
            "type": report_type,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"生成{report_type}报告失败: {e}")
        raise HTTPException(500, detail=f"生成报告失败: {str(e)}")


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
                        if len(parts) >= 3 and parts[1] == "comprehensive":
                            report_type = "comprehensive_market"  # 综合市场报告
                        else:
                            report_type = parts[1]  # 早报等其他类型

                        # 检查日期是否在范围内
                        try:
                            file_date = datetime.strptime(date_str, "%Y-%m-%d")
                            if start_date <= file_date <= end_date:
                                # 读取文件获取摘要
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    report_data = json.load(f)

                                # 根据报告类型生成不同的标题和预览
                                if report_type == "comprehensive_market":
                                    title = f"{date_str} 综合市场报告"
                                    preview = (report_data.get("ai_summary", "") or
                                             report_data.get("professional_summary", "") or
                                             report_data.get("summary", "") or
                                             "暂无摘要")[:100]
                                else:
                                    title = f"{date_str} {report_type}报"
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
        generator = ProfessionalReportGeneratorV2()
        
        if report_type not in ["morning", "noon", "evening", "comprehensive_market"]:
            raise HTTPException(400, detail=f"不支持的报告类型: {report_type}")
            
        # 尝试从缓存文件中获取最新报告
        import glob
        from pathlib import Path

        cache_dir = Path(__file__).parent / ".cache" / "reports"

        if date:
            # 查找特定日期的报告
            pattern = f"{date}_comprehensive_market_professional_v2.json"
            report_file = cache_dir / pattern
        else:
            # 查找最新的报告
            pattern = "*_comprehensive_market_professional_v2.json"
            files = list(cache_dir.glob(pattern))
            if files:
                # 按修改时间排序，获取最新的
                report_file = max(files, key=lambda x: x.stat().st_mtime)
            else:
                report_file = None

        report = None
        if report_file and report_file.exists():
            try:
                with open(report_file, 'r', encoding='utf-8') as f:
                    report = json.load(f)
            except Exception as e:
                logger.error(f"读取报告文件失败: {e}")
                report = None
        
        if not report:
            raise HTTPException(404, detail=f"未找到{date or '今日'}的{report_type}报告")
        
        return {
            "success": True,
            "report": report,
            "type": report_type
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取{report_type}报告失败: {e}")
        raise HTTPException(500, detail=f"获取报告失败: {str(e)}")



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
    if not req.keyword:
        raise HTTPException(400, detail="keyword 不能为空")
    try:
        def _progress(step: str, payload: Optional[Dict[str, Any]]):
            try:
                logger.info("HOTSPOT %s %s", step, json.dumps(payload or {}, ensure_ascii=False))
            except Exception:
                logger.info("HOTSPOT %s", step)
        
        result = analyze_hotspot(req.keyword, req.force)
        
        # 添加LLM分析
        from nlp.ollama_client import summarize_hotspot
        llm_summary = summarize_hotspot(result)
        result["llm_summary"] = llm_summary
        
        return clean_nan_values(result)
    except Exception as e:
        msg = str(e)
        if "每分钟最多访问" in msg or "每小时最多访问" in msg or "权限" in msg:
            raise HTTPException(429, detail=msg)
        raise HTTPException(500, detail=msg)


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
    if not keyword:
        raise HTTPException(400, detail="keyword 不能为空")
    
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
            # 使用带进度回调的新版本
            from core.hotspot import analyze_hotspot_with_progress

            # 创建进度回调函数
            def progress_callback(progress, message, data):
                q.put(("progress", {
                    "step": "analysis",
                    "progress": progress,
                    "message": message,
                    "payload": data
                }))

            result = analyze_hotspot_with_progress(keyword, force, progress_callback)
            logger.info(f"热点分析完成，返回了 {len(result.get('stocks', []))} 只股票")

            # 添加LLM分析
            from nlp.ollama_client import summarize_hotspot
            q.put(("progress", {
                "step": "llm:hotspot:start",
                "progress": 95,
                "message": "生成AI总结...",
                "payload": {}
            }))
            llm_summary = summarize_hotspot(result)
            result["llm_summary"] = llm_summary
            q.put(("progress", {
                "step": "llm:hotspot:done",
                "progress": 100,
                "message": "分析完成",
                "payload": {"length": len(llm_summary or "")}
            }))

            result_box["result"] = result
            logger.info(f"热点分析结果已准备完成，包含{len(result.get('stocks', []))}只股票")
        except Exception as e:
            logger.error(f"热点分析失败: {e}", exc_info=True)
            q.put(("error", {"message": str(e)}))
        finally:
            final_result = result_box.get("result")
            logger.debug(f"准备发送最终结果: {final_result is not None}")
            q.put(("result", final_result if final_result is not None else {}))
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


if __name__ == "__main__":
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SERVER_PORT", 8000))
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

        result = {
            "basic": stock_info,
            "timestamp": datetime.now().isoformat(),
            "quick_data": {
                "price": float(latest['close']),
                "change": float(latest.get('pct_chg', 0)),
                "volume": float(latest.get('vol', 0)),
                "amount": float(latest.get('amount', 0)) * 1000,
                "trade_date": str(latest.get('trade_date', ''))
            },
            "text": f"""# {stock_name} 快速分析

**当前价格**: {float(latest['close'])}元
**今日涨跌**: {float(latest.get('pct_chg', 0)):+.2f}%
**成交量**: {float(latest.get('vol', 0))/10000:.1f}万手

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
