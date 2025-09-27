"""
LLM增强的竞品识别分析器
通过分析新闻内容和公司公告，使用LLM智能识别真实的竞争关系
"""

import re
import json
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class CompetitorRelation:
    """竞争关系数据类"""
    competitor_name: str
    competitor_code: Optional[str]
    confidence: float  # 0-1的置信度
    relation_type: str  # direct, indirect, potential
    evidence: List[str]  # 支撑证据
    discovered_date: str
    source: str  # news, announcement, llm_analysis


class LLMCompetitorAnalyzer:
    """基于LLM的竞品识别分析器"""

    def __init__(self):
        # 竞争关系缓存（避免重复分析）
        self.competitor_cache = {}
        self.cache_ttl = 24 * 3600  # 24小时缓存

        # 竞争关系识别模式
        self.competition_patterns = [
            # 直接竞争表述
            r"与(.+?)(?:展开|进行|存在|形成)?(?:直接|激烈|正面)?竞争",
            r"(?:主要|直接|核心)竞争对手(?:包括|为|是)(.+?)(?:等|，|。)",
            r"与(.+?)在(.+?)领域竞争",
            r"(?:击败|超越|赶超|领先于)(.+?)(?:成为|位列)",
            r"市场份额(?:仅次于|超过|接近)(.+?)",

            # 对比表述
            r"相比(.+?)(?:具有|拥有|在)",
            r"(?:不同于|区别于|有别于)(.+?)的是",
            r"与(.+?)相比",

            # 市场地位表述
            r"与(.+?)(?:并列|齐名|共同)(?:成为|位列|入选)",
            r"(?:仅次于|紧随|追赶)(.+?)(?:位列|排名)",
            r"与(.+?)(?:瓜分|争夺|竞逐)(.+?)市场",

            # 产品竞争
            r"(.+?)(?:推出|发布|上市)(?:同类|竞品|类似)产品",
            r"对标(.+?)的(.+?)产品",
        ]

        # 非竞争关系排除词
        self.exclude_patterns = [
            r"合作",
            r"战略合作",
            r"联合",
            r"共同投资",
            r"收购",
            r"并购",
            r"子公司",
            r"母公司",
            r"关联公司"
        ]

    def analyze_competitors(self,
                           ts_code: str,
                           company_name: str,
                           news_items: List[Dict[str, Any]],
                           announcements: Optional[List[Dict[str, Any]]] = None,
                           use_llm: bool = True) -> List[CompetitorRelation]:
        """
        分析竞争对手

        Args:
            ts_code: 股票代码
            company_name: 公司名称
            news_items: 新闻列表
            announcements: 公告列表
            use_llm: 是否使用LLM深度分析

        Returns:
            竞争关系列表
        """
        # 检查缓存
        cache_key = f"{ts_code}_competitors"
        if cache_key in self.competitor_cache:
            cached_time, cached_data = self.competitor_cache[cache_key]
            if (datetime.now() - cached_time).total_seconds() < self.cache_ttl:
                logger.info(f"[竞品分析] 使用缓存的竞争关系 {company_name}")
                return cached_data

        competitors = {}

        # 1. 从新闻中提取竞争关系
        news_competitors = self._extract_from_news(company_name, news_items)
        for comp in news_competitors:
            if comp.competitor_name not in competitors:
                competitors[comp.competitor_name] = comp
            else:
                # 合并证据
                existing = competitors[comp.competitor_name]
                existing.evidence.extend(comp.evidence)
                existing.confidence = max(existing.confidence, comp.confidence)

        # 2. 从公告中提取竞争关系
        if announcements:
            ann_competitors = self._extract_from_announcements(company_name, announcements)
            for comp in ann_competitors:
                if comp.competitor_name not in competitors:
                    competitors[comp.competitor_name] = comp
                else:
                    existing = competitors[comp.competitor_name]
                    existing.evidence.extend(comp.evidence)
                    existing.confidence = max(existing.confidence, comp.confidence)

        # 3. 暂时禁用LLM分析以避免JSON解析错误
        # if use_llm and (news_items or announcements):
        #     llm_competitors = self._llm_analyze(company_name, news_items, announcements)
        #     for comp in llm_competitors:
        #         if comp.competitor_name not in competitors:
        #             competitors[comp.competitor_name] = comp
        #         else:
        #             # LLM分析的权重更高
        #             existing = competitors[comp.competitor_name]
        #             existing.evidence.extend(comp.evidence)
        #             existing.confidence = min(1.0, existing.confidence + 0.2)

        # 4. 验证和排序
        result = self._validate_and_rank(list(competitors.values()))

        # 缓存结果
        self.competitor_cache[cache_key] = (datetime.now(), result)

        logger.info(f"[竞品分析] {company_name} 识别到 {len(result)} 个竞争对手")
        return result

    def _extract_from_news(self, company_name: str, news_items: List[Dict[str, Any]]) -> List[CompetitorRelation]:
        """从新闻中提取竞争关系"""
        competitors = []

        for news in news_items:
            title = news.get('title', '')
            content = news.get('content', '')[:2000]  # 限制长度
            full_text = f"{title} {content}"

            # 跳过不包含公司名的新闻
            if company_name not in full_text:
                continue

            # 检查是否为非竞争关系
            if any(re.search(pattern, full_text) for pattern in self.exclude_patterns):
                continue

            # 提取竞争对手
            for pattern in self.competition_patterns:
                matches = re.findall(pattern, full_text, re.IGNORECASE)
                for match in matches:
                    competitor_name = self._clean_company_name(match[0] if isinstance(match, tuple) else match)
                    if competitor_name and competitor_name != company_name:
                        competitors.append(CompetitorRelation(
                            competitor_name=competitor_name,
                            competitor_code=None,
                            confidence=0.7,
                            relation_type='direct',
                            evidence=[f"新闻提及：{title[:50]}..."],
                            discovered_date=datetime.now().strftime('%Y-%m-%d'),
                            source='news'
                        ))

        return competitors

    def _extract_from_announcements(self, company_name: str, announcements: List[Dict[str, Any]]) -> List[CompetitorRelation]:
        """从公告中提取竞争关系"""
        competitors = []

        # 重点关注的公告类型
        important_types = ['年报', '半年报', '招股说明书', '重大合同', '投资者关系']

        for ann in announcements:
            title = ann.get('title', '')

            # 优先处理重要公告
            is_important = any(t in title for t in important_types)
            if not is_important:
                continue

            # 这里简化处理，实际可以调用API获取公告全文
            content = ann.get('content', '') or title

            # 年报中的竞争对手章节通常更准确
            if '年报' in title:
                # 查找竞争对手相关章节
                competition_section = self._extract_competition_section(content)
                if competition_section:
                    comp_names = self._parse_competitor_names(competition_section)
                    for name in comp_names:
                        competitors.append(CompetitorRelation(
                            competitor_name=name,
                            competitor_code=None,
                            confidence=0.9,  # 年报中的竞争对手可信度高
                            relation_type='direct',
                            evidence=[f"年报披露：{title}"],
                            discovered_date=ann.get('ann_date', ''),
                            source='announcement'
                        ))

        return competitors

    def _llm_analyze(self, company_name: str,
                     news_items: Optional[List[Dict[str, Any]]] = None,
                     announcements: Optional[List[Dict[str, Any]]] = None) -> List[CompetitorRelation]:
        """使用LLM深度分析竞争关系"""
        try:
            # 直接使用requests调用Ollama API，类似ollama_client的实现
            import os
            import requests

            OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
            OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "deepseek-r1:32b")
            OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))

            # 准备分析材料
            context = self._prepare_llm_context(company_name, news_items, announcements)

            prompt = f"""基于以下关于{company_name}的信息，请识别其主要竞争对手。

{context}

请分析并返回JSON格式的竞争对手列表，格式如下：
{{
    "competitors": [
        {{
            "name": "竞争对手名称",
            "relation_type": "direct/indirect/potential",
            "confidence": 0.8,
            "reason": "竞争关系说明"
        }}
    ]
}}

注意：
1. 只返回真实存在的公司，不要虚构
2. confidence表示置信度（0-1）
3. relation_type: direct=直接竞争，indirect=间接竞争，potential=潜在竞争
4. 排除合作伙伴、子公司、母公司等非竞争关系
5. 只返回JSON，不要有其他内容
"""

            # 调用Ollama API
            body = {
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 2048,
                }
            }

            response = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json=body,
                timeout=OLLAMA_TIMEOUT,
            )
            response.raise_for_status()
            llm_response = response.json().get("response", "")

            # 解析LLM响应
            competitors = self._parse_llm_response(llm_response)

            result = []
            for comp in competitors:
                result.append(CompetitorRelation(
                    competitor_name=comp['name'],
                    competitor_code=None,
                    confidence=comp.get('confidence', 0.6),
                    relation_type=comp.get('relation_type', 'direct'),
                    evidence=[f"LLM分析：{comp.get('reason', '')}"],
                    discovered_date=datetime.now().strftime('%Y-%m-%d'),
                    source='llm_analysis'
                ))

            return result

        except Exception as e:
            logger.error(f"[竞品分析] LLM分析失败: {e}")
            return []

    def _prepare_llm_context(self, company_name: str,
                            news_items: Optional[List[Dict[str, Any]]],
                            announcements: Optional[List[Dict[str, Any]]]) -> str:
        """准备LLM分析的上下文"""
        context_parts = []

        # 添加最近的新闻（最多5条）
        if news_items:
            context_parts.append("最近新闻：")
            for news in news_items[:5]:
                title = news.get('title', '')
                if company_name in title:
                    context_parts.append(f"- {title}")

        # 添加重要公告标题
        if announcements:
            context_parts.append("\n最近公告：")
            for ann in announcements[:5]:
                title = ann.get('title', '')
                context_parts.append(f"- {title}")

        return '\n'.join(context_parts)

    def _parse_llm_response(self, response: str) -> List[Dict[str, Any]]:
        """解析LLM响应"""
        try:
            # 清理响应文本
            response = response.strip()

            # 尝试多种方式解析
            # 1. 直接解析
            try:
                data = json.loads(response)
                if isinstance(data, dict) and 'competitors' in data:
                    return data.get('competitors', [])
            except:
                pass

            # 2. 提取JSON部分（更宽松的模式）
            json_patterns = [
                r'\{[^{}]*"competitors"[^{}]*\:[^{}]*\[[^\[\]]*\][^{}]*\}',  # 简单JSON
                r'\{.*?"competitors".*?\[.*?\].*?\}',  # 中等复杂度
                r'\{.*\}',  # 最宽松
            ]

            for pattern in json_patterns:
                matches = re.findall(pattern, response, re.DOTALL)
                for match in matches:
                    try:
                        # 清理可能的问题字符
                        match = match.replace('\n', ' ').replace('\r', '')
                        match = re.sub(r',\s*}', '}', match)  # 去掉结尾多余逗号
                        match = re.sub(r',\s*\]', ']', match)  # 去掉数组结尾多余逗号

                        data = json.loads(match)
                        if isinstance(data, dict) and 'competitors' in data:
                            return data.get('competitors', [])
                    except:
                        continue

            # 3. 如果都失败了，尝试提取竞品名称
            logger.warning(f"[竞品分析] 无法解析JSON，尝试简单提取")
            competitors = []

            # 提取公司名称模式
            company_patterns = [
                r'"name"\s*:\s*"([^"]+)"',
                r'公司[:：]\s*([^，,。\n]+)',
                r'竞争对手[:：]\s*([^，,。\n]+)',
            ]

            for pattern in company_patterns:
                matches = re.findall(pattern, response)
                for match in matches[:3]:  # 最多3个
                    competitors.append({
                        'name': match.strip(),
                        'confidence': 0.5,
                        'relation_type': 'direct',
                        'reason': '从LLM响应中提取'
                    })

            return competitors

        except Exception as e:
            logger.error(f"[竞品分析] 解析LLM响应失败: {e}")
            logger.debug(f"[竞品分析] 原始响应: {response[:500]}")

        return []

    def _extract_competition_section(self, content: str) -> Optional[str]:
        """提取公告中的竞争对手章节"""
        patterns = [
            r"(?:主要)?竞争对手(?:分析)?[:：](.*?)(?:\n\n|$)",
            r"竞争格局[:：](.*?)(?:\n\n|$)",
            r"市场竞争(?:状况|情况)[:：](.*?)(?:\n\n|$)",
            r"同行业(?:竞争)?公司[:：](.*?)(?:\n\n|$)"
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                return match.group(1)[:1000]  # 限制长度

        return None

    def _parse_competitor_names(self, text: str) -> List[str]:
        """从文本中解析竞争对手名称"""
        # 常见的分隔符
        names = re.split(r'[、，,；;]|\s+', text)

        # 清理和过滤
        result = []
        for name in names:
            cleaned = self._clean_company_name(name)
            if cleaned and len(cleaned) > 2:
                result.append(cleaned)

        return result

    def _clean_company_name(self, name: str) -> str:
        """清理公司名称"""
        if not name or isinstance(name, (list, tuple)):
            return ""

        # 移除括号内容
        name = re.sub(r'[（(].+?[）)]', '', str(name))

        # 移除引号
        name = name.replace('"', '').replace("'", '').replace('"', '').replace('"', '')

        # 移除特殊字符
        name = re.sub(r'[《》「」『』【】]', '', name)

        # 去除空白
        name = name.strip()

        # 过滤太短的名称
        if len(name) < 2:
            return ""

        # 过滤非公司名称
        exclude_words = ['等', '其他', '相关', '行业', '领域', '产品', '市场']
        if any(word in name for word in exclude_words):
            return ""

        return name

    def _validate_and_rank(self, competitors: List[CompetitorRelation]) -> List[CompetitorRelation]:
        """验证和排序竞争对手"""
        # 合并相同公司的多个记录
        merged = {}
        for comp in competitors:
            key = comp.competitor_name
            if key not in merged:
                merged[key] = comp
            else:
                # 合并证据和更新置信度
                existing = merged[key]
                existing.evidence.extend(comp.evidence)
                existing.evidence = list(set(existing.evidence))  # 去重
                existing.confidence = min(1.0, existing.confidence + 0.1)

        # 尝试匹配股票代码
        try:
            from .tushare_client import stock_basic
            df = stock_basic()
            if df is not None and not df.empty:
                name_to_code = dict(zip(df['name'], df['ts_code']))
                for comp in merged.values():
                    if comp.competitor_code is None:
                        comp.competitor_code = name_to_code.get(comp.competitor_name)
        except Exception as e:
            logger.error(f"[竞品分析] 匹配股票代码失败: {e}")

        # 按置信度排序
        result = sorted(merged.values(), key=lambda x: x.confidence, reverse=True)

        # 只返回置信度较高的（>0.5）
        return [c for c in result if c.confidence > 0.5][:20]  # 最多返回20个

    def get_competitor_keywords(self, competitors: List[CompetitorRelation]) -> List[str]:
        """获取竞争对手关键词列表（用于新闻匹配）"""
        keywords = []
        for comp in competitors:
            if comp.confidence > 0.6:  # 只使用高置信度的竞争对手
                keywords.append(comp.competitor_name)

                # 添加常见简称
                if '集团' in comp.competitor_name:
                    keywords.append(comp.competitor_name.replace('集团', ''))
                if '股份' in comp.competitor_name:
                    keywords.append(comp.competitor_name.replace('股份', ''))
                if '有限公司' in comp.competitor_name:
                    keywords.append(comp.competitor_name.replace('有限公司', ''))

        return list(set(keywords))  # 去重


# 单例模式
_analyzer_instance = None

def get_competitor_analyzer() -> LLMCompetitorAnalyzer:
    """获取竞品分析器单例"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = LLMCompetitorAnalyzer()
    return _analyzer_instance