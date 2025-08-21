import os
import json
import threading
import queue
import logging
import time
from pathlib import Path
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, Callable
from dotenv import load_dotenv

# 先加载 .env，避免下游模块在导入时读取不到环境变量
load_dotenv()

from core.analyze import run_pipeline, resolve_by_name
from core.market import fetch_market_overview
from core.hotspot import analyze_hotspot
from core.market_ai_analyzer import get_enhanced_market_ai_analyzer
from nlp.ollama_client import OLLAMA_URL, OLLAMA_MODEL, OLLAMA_NUM_PREDICT
import requests


app = FastAPI(title="QStockLAB A股 MVP (TuShare + Ollama)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
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


class AnalyzeRequest(BaseModel):
    name: str
    force: bool = False


class HotspotRequest(BaseModel):
    keyword: str
    force: bool = False


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    stream: bool = False


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/resolve")
def resolve(name: str):
    # TuShare 接口可能频控，失败时返回 429 语义
    try:
        item = resolve_by_name(name)
    except Exception as e:
        raise HTTPException(429, detail=f"解析受限/失败：{e}")
    if not item:
        raise HTTPException(404, detail=f"未找到包含“{name}”的A股")
    return item
@app.get("/market")
def market():
    try:
        return fetch_market_overview()
    except Exception as e:
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
        
        return {
            "success": True,
            "timestamp": time.time(),
            "market_data": market_data,
            "insight_report": insight_report
        }
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
        
        return {
            "success": True,
            "timestamp": time.time(),
            "fear_greed_index": fear_greed_data
        }
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
        
        return {
            "success": True,
            "timestamp": time.time(),
            "alerts": alerts,
            "alert_count": len(alerts),
            "high_priority_count": len([a for a in alerts if a.get("level") == "high"])
        }
    except Exception as e:
        logger.error(f"市场预警获取失败: {e}")
        raise HTTPException(500, detail=f"市场预警获取失败: {str(e)}")



@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    # 添加force字段支持
    class AnalyzeRequest(BaseModel):
        name: str
        force: bool = False
    
    if not req.name:
        raise HTTPException(400, detail="name 不能为空")
    try:
        def _progress(step: str, payload: Optional[Dict[str, Any]]):
            # 同时写入日志文件，供前端终端面板实时查看
            try:
                logger.info("PROGRESS %s %s", step, json.dumps(payload or {}, ensure_ascii=False))
            except Exception:
                logger.info("PROGRESS %s", step)

        result = run_pipeline(req.name, force=req.force, progress=_progress)
        return result
    except Exception as e:
        msg = str(e)
        if "每分钟最多访问" in msg or "每小时最多访问" in msg or "权限" in msg:
            raise HTTPException(429, detail=msg)
        raise HTTPException(500, detail=msg)


def _sse_event(event: str, data: dict | None) -> str:
    try:
        payload = json.dumps(data or {}, ensure_ascii=False)
    except Exception:
        payload = "{}"
    return f"event: {event}\n" f"data: {payload}\n\n"


@app.get("/analyze/stream")
def analyze_stream(name: str, force: bool = False):
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
            result = run_pipeline(name, force=force, progress=_progress)
            result_box["result"] = result
        except Exception as e:
            q.put(("error", {"message": str(e)}))
        finally:
            q.put(("result", result_box.get("result")))
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


def _sse_log(event: str, text: str) -> str:
    data = json.dumps({"line": text}, ensure_ascii=False)
    return f"event: {event}\n" f"data: {data}\n\n"


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
        
        return result
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
        r = requests.post(f"{OLLAMA_URL}/api/chat", json=body, timeout=300)
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
            result = analyze_hotspot(keyword, force)
            print(f"[DEBUG] analyze_hotspot返回了 {len(result.get('stocks', []))} 只股票")
            
            # 添加LLM分析
            from nlp.ollama_client import summarize_hotspot
            q.put(("progress", {"step": "llm:hotspot:start", "payload": {}}))
            llm_summary = summarize_hotspot(result)
            result["llm_summary"] = llm_summary
            q.put(("progress", {"step": "llm:hotspot:done", "payload": {"length": len(llm_summary or "")}}))
            
            result_box["result"] = result
            print(f"[DEBUG] 结果已存入result_box, 包含{len(result.get('stocks', []))}只股票")
        except Exception as e:
            print(f"[ERROR] 热点分析出错: {e}")
            import traceback
            traceback.print_exc()
            q.put(("error", {"message": str(e)}))
        finally:
            final_result = result_box.get("result")
            print(f"[DEBUG] 准备发送最终结果: {final_result is not None}")
            q.put(("result", final_result))
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


# ================ 报告系统 API ================

@app.get("/reports/history")
def get_report_history(days: int = 7):
    """获取报告历史"""
    try:
        from core.professional_report_generator_v2 import get_professional_generator_v2
        report_gen = get_professional_generator_v2()
        return report_gen.get_report_history(days)
    except Exception as e:
        raise HTTPException(500, detail=str(e))

@app.post("/reports/{report_type}/generate")
def generate_report(report_type: str, background_tasks: BackgroundTasks):
    """生成报告"""
    if report_type not in ['morning', 'noon', 'evening']:
        raise HTTPException(400, detail="报告类型必须是 morning, noon, evening 之一")
    
    try:
        from core.professional_report_generator_v2 import get_professional_generator_v2
        report_gen = get_professional_generator_v2()
        
        # 后台生成报告
        if report_type == 'morning':
            background_tasks.add_task(report_gen.generate_morning_report)
        elif report_type == 'noon':
            background_tasks.add_task(report_gen.generate_noon_report)
        else:  # evening
            background_tasks.add_task(report_gen.generate_evening_report)
        
        return {"message": f"{report_type}报告生成任务已启动"}
    except Exception as e:
        raise HTTPException(500, detail=str(e))

@app.get("/reports/{report_type}")
def get_report(report_type: str, date: str = None):
    """获取报告（可指定日期）"""
    if report_type not in ['morning', 'noon', 'evening']:
        raise HTTPException(400, detail="报告类型必须是 morning, noon, evening 之一")
    
    try:
        from core.professional_report_generator_v2 import get_professional_generator_v2
        report_gen = get_professional_generator_v2()
        
        if date:
            # 获取指定日期的报告
            report = report_gen.get_report_by_date(report_type, date)
        else:
            # 获取最新报告
            report = report_gen.get_latest_report(report_type)
        
        if not report:
            raise HTTPException(404, detail=f"未找到{report_type}报告")
        
        return report
    except Exception as e:
        raise HTTPException(500, detail=str(e))

@app.get("/scheduler/status")
def get_scheduler_status():
    """获取调度器状态"""
    try:
        from core.scheduler import get_scheduler
        scheduler = get_scheduler()
        return scheduler.get_job_status()
    except Exception as e:
        raise HTTPException(500, detail=str(e))

@app.post("/scheduler/jobs/{job_id}/run")
def run_job_now(job_id: str):
    """立即执行任务"""
    try:
        from core.scheduler import get_scheduler
        scheduler = get_scheduler()
        success = scheduler.run_job_now(job_id)
        
        if success:
            return {"message": f"任务 {job_id} 已安排执行"}
        else:
            raise HTTPException(400, detail=f"任务 {job_id} 不存在")
    except Exception as e:
        raise HTTPException(500, detail=str(e))

@app.post("/scoring/explain")
def explain_scoring(data: dict):
    """获取评分解释"""
    try:
        from core.scoring_factors import ScoringFactors
        explained_score = ScoringFactors.calculate_explainable_score(data)
        return explained_score
    except Exception as e:
        raise HTTPException(500, detail=str(e))

@app.get("/concepts/hot")
def get_hot_concepts(limit: int = 10):
    """获取热门概念"""
    try:
        from core.concept_manager import get_concept_manager
        concept_mgr = get_concept_manager()
        return concept_mgr.get_hot_concepts(limit)
    except Exception as e:
        raise HTTPException(500, detail=str(e))

@app.get("/concepts/search")
def search_concepts(keyword: str):
    """搜索概念成分股"""
    try:
        from core.concept_manager import get_concept_manager
        concept_mgr = get_concept_manager()
        return concept_mgr.find_concept_stocks(keyword)
    except Exception as e:
        raise HTTPException(500, detail=str(e))


if __name__ == "__main__":
    # 启动调度器
    try:
        from core.scheduler import start_scheduler
        start_scheduler()
        print("任务调度器已启动")
    except Exception as e:
        print(f"调度器启动失败: {e}")
    
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SERVER_PORT", 8000))
    uvicorn.run(app, host=host, port=port)


