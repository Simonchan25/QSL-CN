import os
import json
import requests

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:latest")
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "4096"))
STRIP_THINK = os.getenv("OLLAMA_STRIP_THINK", "1") == "1"

SYS_PROMPT = (
    "你是A股投研助理。基于提供的TuShare数据，输出七段："
    "【公司概况】【基本面】【技术面】【公告/新闻】【宏观与风险】【投资策略建议】【结论与建议】。"
    "其中【投资策略建议】部分必须包含："
    "1. 长线投资策略（1-3年）：基于基本面分析、估值水平、业绩增长等给出具体建议和理由"
    "2. 短线/波段策略：基于技术指标、市场情绪、成交量等给出操作建议和支撑阻力位"
    "3. 价格目标：基于PE、PB、DCF等估值方法给出合理价格区间"
    "4. 仓位建议：根据风险评估给出具体仓位配置建议"
    "5. 买卖时点：结合技术面和基本面给出具体的买入、持有或卖出建议"
    "要求：基于数据给出有理有据的投资建议，包括具体的价格预测和操作指令；数据缺失要明确标注，不编造数据。"
)


def _strip_think(text: str) -> str:
    try:
        if not text:
            return text
        # deepseek-r1 格式通常为 <think>... </think> 正文
        end_tag = "</think>"
        if end_tag in text:
            after = text.split(end_tag, 1)[1]
            return after.strip() or text
        return text
    except Exception:
        return text


def summarize(chunks: dict) -> str:
    body = {
        "model": OLLAMA_MODEL,
        "prompt": SYS_PROMPT + "\n\n" + json.dumps(chunks, ensure_ascii=False, indent=2),
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_ctx": 8192,
            "num_predict": OLLAMA_NUM_PREDICT,
            "stop": None
        },
    }
    try:
        print(f"[LLM] 开始调用Ollama: model={OLLAMA_MODEL}, url={OLLAMA_URL}")
        r = requests.post(f"{OLLAMA_URL}/api/generate", json=body, timeout=300)
        r.raise_for_status()
        resp = r.json().get("response", "").strip()
        print(f"[LLM] 响应长度: {len(resp)}")
        return _strip_think(resp) if STRIP_THINK else resp
    except requests.exceptions.Timeout:
        return "[LLM超时] 模型响应时间过长，请稍后重试"
    except Exception as e:
        print(f"[LLM错误] {e}")
        return f"[LLM错误] {e}"


def summarize_hotspot(hotspot_data: dict) -> str:
    """分析热点概念数据"""
    HOTSPOT_PROMPT = (
        "你是A股热点分析师。基于提供的数据分析热点概念，输出："
        "【热点概述】简述该概念的市场热度和新闻动态\n"
        "【龙头标的】列出综合评分最高的3-5个股票及理由\n"
        "【行业分布】分析相关股票的行业集中度\n"
        "【投资机会】基于技术面和基本面数据给出客观分析\n"
        "【风险提示】提示可能的风险因素\n"
        "限制：只基于数据分析，不预测价格，不给投资建议。"
    )
    
    body = {
        "model": OLLAMA_MODEL,
        "prompt": HOTSPOT_PROMPT + "\n\n" + json.dumps(hotspot_data, ensure_ascii=False, indent=2),
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_ctx": 8192,
            "num_predict": OLLAMA_NUM_PREDICT,
            "stop": None
        },
    }
    try:
        print(f"[LLM] 开始调用Ollama分析热点: model={OLLAMA_MODEL}")
        r = requests.post(f"{OLLAMA_URL}/api/generate", json=body, timeout=300)
        r.raise_for_status()
        resp = r.json().get("response", "").strip()
        print(f"[LLM] 热点分析响应长度: {len(resp)}")
        return _strip_think(resp) if STRIP_THINK else resp
    except requests.exceptions.Timeout:
        return "[LLM超时] 模型响应时间过长，请稍后重试"
    except Exception as e:
        print(f"[LLM错误] {e}")
        return f"[LLM错误] {e}"


