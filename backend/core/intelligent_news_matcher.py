"""
智能新闻匹配系统 - 预处理+缓存策略
每天定时用LLM理解所有新闻，缓存结果，实时查询使用规则匹配
"""

import json
import os
import subprocess
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import pickle

@dataclass
class ProcessedNews:
    """预处理后的新闻数据"""
    news_id: str  # 新闻唯一ID
    title: str
    content: str
    datetime: str
    source: str

    # LLM分析结果
    entities: List[str]  # 提到的公司/股票
    competitors: List[str]  # 涉及的竞争对手
    industries: List[str]  # 相关行业
    keywords: List[str]  # 关键概念
    impact_chains: List[Dict]  # 影响链 [{from: "锂价", to: "电池", impact: "成本上升"}]
    sentiment: str  # positive/negative/neutral
    importance: int  # 1-10重要度评分

    # 缓存元数据
    processed_at: str
    llm_model: str

class IntelligentNewsMatcher:
    """智能新闻匹配器 - 混合策略"""

    def __init__(self):
        self.cache_dir = "data/news_cache"
        self.ensure_cache_dir()
        self._load_stock_db()
        self.llm_model = "qwen3:8b"

    def ensure_cache_dir(self):
        """确保缓存目录存在"""
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(f"{self.cache_dir}/processed", exist_ok=True)
        os.makedirs(f"{self.cache_dir}/daily", exist_ok=True)

    def _load_stock_db(self):
        """加载股票数据库"""
        try:
            from .tushare_client import stock_basic
            df = stock_basic()
            if df is not None and not df.empty:
                self.stock_db = {}
                self.company_names = set()  # 所有公司名称
                for _, row in df.iterrows():
                    ts_code = row.get('ts_code', '')
                    name = row.get('name', '')
                    self.stock_db[ts_code] = {
                        'name': name,
                        'industry': row.get('industry', ''),
                    }
                    if name:
                        self.company_names.add(name)
        except:
            self.stock_db = {}
            self.company_names = set()

    def process_news_batch(self, news_items: List[Dict]) -> List[ProcessedNews]:
        """
        批量预处理新闻（每天定时运行）
        使用LLM深度理解每条新闻，提取所有相关信息
        """
        print(f"[预处理] 开始处理 {len(news_items)} 条新闻")
        processed = []

        for i, news in enumerate(news_items):
            if i % 10 == 0:
                print(f"[预处理] 进度: {i}/{len(news_items)}")

            # 生成唯一ID
            news_id = self._generate_news_id(news)

            # 检查是否已处理
            cached = self._load_cached_news(news_id)
            if cached:
                processed.append(cached)
                continue

            # LLM深度分析
            analysis = self._llm_deep_analysis(news)

            # 创建处理后的新闻对象
            processed_news = ProcessedNews(
                news_id=news_id,
                title=news.get('title', ''),
                content=news.get('content', ''),
                datetime=news.get('datetime', ''),
                source=news.get('src', ''),
                entities=analysis.get('entities', []),
                competitors=analysis.get('competitors', []),
                industries=analysis.get('industries', []),
                keywords=analysis.get('keywords', []),
                impact_chains=analysis.get('impact_chains', []),
                sentiment=analysis.get('sentiment', 'neutral'),
                importance=analysis.get('importance', 5),
                processed_at=datetime.now().isoformat(),
                llm_model=self.llm_model
            )

            # 缓存结果
            self._cache_processed_news(processed_news)
            processed.append(processed_news)

            # 避免请求过快
            time.sleep(0.5)

        print(f"[预处理] 完成处理 {len(processed)} 条新闻")
        return processed

    def _llm_deep_analysis(self, news: Dict) -> Dict:
        """使用LLM深度分析新闻"""
        title = news.get('title', '')
        content = news.get('content', '')[:1000]

        # 构建分析提示词 - 简化格式避免JSON解析错误
        prompt = f"""分析财经新闻：
标题：{title}
内容：{content[:500]}

返回JSON（严格格式，不要有额外文字）：
{{
  "entities": [],
  "competitors": [],
  "industries": [],
  "keywords": [],
  "impact_chains": [],
  "sentiment": "neutral",
  "importance": 5
}}

要求：
- entities: 提到的公司名
- competitors: 受影响的竞争对手
- industries: 相关行业
- sentiment: positive/negative/neutral
- importance: 1-10
"""

        try:
            # 调用LLM
            response = subprocess.run(
                ["ollama", "run", self.llm_model, prompt],
                capture_output=True,
                text=True,
                timeout=30
            ).stdout

            # 改进的JSON解析
            import re
            # 尝试多种方式提取JSON

            # 方法1: 查找最外层的{}
            json_match = re.search(r'\{[^{}]*\}', response.replace('\n', ' '))
            if not json_match:
                # 方法2: 查找包含嵌套的JSON
                json_match = re.search(r'\{.*\}', response.replace('\n', ' '), re.DOTALL)

            if json_match:
                json_str = json_match.group()
                # 清理和修复常见问题
                json_str = json_str.replace('\n', ' ').replace('\r', '')
                json_str = re.sub(r',\s*}', '}', json_str)  # 移除尾随逗号
                json_str = re.sub(r',\s*]', ']', json_str)

                try:
                    result = json.loads(json_str)
                    # 验证并修复结果
                    return self._validate_analysis_result(result)
                except json.JSONDecodeError as e:
                    print(f"[LLM分析] JSON解析失败: {e[:50]}")
                    # 尝试手动构建基本结果
                    return self._extract_basic_info(response, title)
        except subprocess.TimeoutExpired:
            print(f"[LLM分析] 超时")
        except Exception as e:
            print(f"[LLM分析] 错误: {e}")

        # 返回默认值
        return self._get_default_analysis()

    def _validate_analysis_result(self, result: Dict) -> Dict:
        """验证和修复LLM分析结果"""
        default = self._get_default_analysis()

        # 确保所有必需字段存在且类型正确
        validated = {}
        validated['entities'] = result.get('entities', []) if isinstance(result.get('entities'), list) else []
        validated['competitors'] = result.get('competitors', []) if isinstance(result.get('competitors'), list) else []
        validated['industries'] = result.get('industries', []) if isinstance(result.get('industries'), list) else []
        validated['keywords'] = result.get('keywords', []) if isinstance(result.get('keywords'), list) else []
        validated['impact_chains'] = result.get('impact_chains', []) if isinstance(result.get('impact_chains'), list) else []
        validated['sentiment'] = result.get('sentiment', 'neutral') if result.get('sentiment') in ['positive', 'negative', 'neutral'] else 'neutral'
        validated['importance'] = min(10, max(1, int(result.get('importance', 5)))) if isinstance(result.get('importance'), (int, float)) else 5

        return validated

    def _extract_basic_info(self, response: str, title: str) -> Dict:
        """从响应文本中提取基本信息"""
        result = self._get_default_analysis()

        # 尝试提取公司名（查找A股代码模式）
        import re
        stock_pattern = re.findall(r'[\u4e00-\u9fa5]{2,6}(?=[\s,，。])', title)
        if stock_pattern:
            result['entities'] = stock_pattern[:3]

        # 简单情感分析
        if any(word in response for word in ['增长', '上涨', '利好', '突破']):
            result['sentiment'] = 'positive'
        elif any(word in response for word in ['下跌', '亏损', '下降', '利空']):
            result['sentiment'] = 'negative'

        return result

    def _get_default_analysis(self) -> Dict:
        """获取默认分析结果"""
        return {
            'entities': [],
            'competitors': [],
            'industries': [],
            'keywords': [],
            'impact_chains': [],
            'sentiment': 'neutral',
            'importance': 5
        }

    def match_news_fast(self,
                       ts_code: str,
                       processed_news: List[ProcessedNews]) -> List[Dict]:
        """
        快速匹配新闻（基于预处理结果）
        不需要再调用LLM，直接使用缓存的分析结果
        """
        stock_info = self.stock_db.get(ts_code, {})
        stock_name = stock_info.get('name', '')
        stock_industry = stock_info.get('industry', '')

        matches = []

        for news in processed_news:
            score = 0
            relevance_type = 'unrelated'
            reasons = []

            # 1. 直接提及检查（最高分）
            if stock_name in news.entities:
                score = 95
                relevance_type = 'direct'
                reasons.append(f"直接提到{stock_name}")

            # 2. 竞争对手检查
            elif stock_name in news.competitors:
                score = 75
                relevance_type = 'competitor'
                reasons.append("涉及竞争影响")

            # 3. 影响链检查（供应链、上下游）
            else:
                for chain in news.impact_chains:
                    if stock_name in chain.get('to', ''):
                        score = 70
                        relevance_type = 'supply_chain'
                        reasons.append(f"{chain['from']}→{chain['impact']}")
                        break
                    # 检查行业影响
                    if stock_industry and stock_industry in chain.get('to', ''):
                        score = 50
                        relevance_type = 'industry'
                        reasons.append(f"行业影响: {chain['impact']}")

            # 4. 行业相关检查
            if score == 0 and stock_industry in news.industries:
                score = 40
                relevance_type = 'industry'
                reasons.append(f"{stock_industry}行业相关")

            # 5. 根据重要度调整分数
            score = score * (0.8 + news.importance * 0.02)  # importance影响±20%

            if score >= 30:  # 阈值
                matches.append({
                    'news': news,
                    'score': score,
                    'type': relevance_type,
                    'reasons': reasons,
                    'sentiment': news.sentiment,
                    'importance': news.importance
                })

        # 按分数排序
        matches.sort(key=lambda x: x['score'], reverse=True)

        return matches

    def get_realtime_news(self, ts_code: str) -> List[Dict]:
        """
        获取实时相关新闻（混合策略）
        1. 已预处理的新闻：直接规则匹配
        2. 新增新闻：实时LLM分析
        """
        today = datetime.now().strftime("%Y%m%d")

        # 1. 加载今日预处理的新闻
        cached_news = self._load_daily_cache(today)

        # 2. 获取最新新闻
        from .news import fetch_news_summary
        fresh_news = fetch_news_summary(ts_code, days_back=1)

        # 3. 识别哪些是新的（未处理的）
        new_items = self._find_unprocessed_news(fresh_news, cached_news)

        # 4. 实时处理新增新闻
        if new_items:
            print(f"[实时] 发现 {len(new_items)} 条新新闻，实时处理...")
            newly_processed = self.process_news_batch(new_items)
            cached_news.extend(newly_processed)

        # 5. 快速匹配
        matches = self.match_news_fast(ts_code, cached_news)

        return matches

    def daily_preprocessing_task(self):
        """
        每日预处理任务（建议凌晨运行）
        处理所有新闻源，缓存分析结果
        """
        print(f"[定时任务] 开始每日预处理 - {datetime.now()}")

        # 获取所有新闻源
        from .tushare_client import news as ts_news, major_news

        all_news = []

        # 1. 获取各源新闻
        sources = ['sina', 'wallstreetcn', '10jqka', 'eastmoney']
        for src in sources:
            try:
                df = ts_news(src=src, limit=500)
                if df is not None and not df.empty:
                    for _, row in df.iterrows():
                        all_news.append({
                            'title': row.get('title', ''),
                            'content': row.get('content', ''),
                            'datetime': row.get('datetime', ''),
                            'src': src
                        })
            except:
                pass

        # 2. 获取重大新闻
        try:
            df = major_news(limit=100)
            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    all_news.append({
                        'title': row.get('title', ''),
                        'content': row.get('content', ''),
                        'datetime': row.get('datetime', ''),
                        'src': 'major'
                    })
        except:
            pass

        print(f"[定时任务] 收集到 {len(all_news)} 条新闻")

        # 3. 批量预处理
        processed = self.process_news_batch(all_news)

        # 4. 保存到每日缓存
        today = datetime.now().strftime("%Y%m%d")
        self._save_daily_cache(today, processed)

        print(f"[定时任务] 完成处理，缓存 {len(processed)} 条")

        # 5. 清理过期缓存（保留7天）
        self._cleanup_old_cache()

        return processed

    def _generate_news_id(self, news: Dict) -> str:
        """生成新闻唯一ID"""
        import hashlib
        text = f"{news.get('title', '')}_{news.get('datetime', '')}"
        return hashlib.md5(text.encode()).hexdigest()

    def _cache_processed_news(self, news: ProcessedNews):
        """缓存处理后的新闻"""
        filepath = f"{self.cache_dir}/processed/{news.news_id}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(asdict(news), f, ensure_ascii=False, indent=2)

    def _load_cached_news(self, news_id: str) -> Optional[ProcessedNews]:
        """加载缓存的新闻"""
        filepath = f"{self.cache_dir}/processed/{news_id}.json"
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return ProcessedNews(**data)
        return None

    def _save_daily_cache(self, date: str, news_list: List[ProcessedNews]):
        """保存每日缓存"""
        filepath = f"{self.cache_dir}/daily/{date}.pkl"
        with open(filepath, 'wb') as f:
            pickle.dump(news_list, f)

    def _load_daily_cache(self, date: str) -> List[ProcessedNews]:
        """加载每日缓存"""
        filepath = f"{self.cache_dir}/daily/{date}.pkl"
        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                return pickle.load(f)
        return []

    def _find_unprocessed_news(self,
                               fresh: Dict,
                               cached: List[ProcessedNews]) -> List[Dict]:
        """找出未处理的新新闻"""
        cached_ids = {n.news_id for n in cached}
        unprocessed = []

        for key in ['flash_news', 'major_news', 'company_news']:
            for item in fresh.get(key, [])[:10]:  # 限制数量
                news_id = self._generate_news_id(item)
                if news_id not in cached_ids:
                    unprocessed.append(item)

        return unprocessed

    def _cleanup_old_cache(self, keep_days: int = 7):
        """清理过期缓存"""
        cutoff = datetime.now() - timedelta(days=keep_days)

        for filename in os.listdir(f"{self.cache_dir}/daily"):
            if filename.endswith('.pkl'):
                date_str = filename.replace('.pkl', '')
                try:
                    file_date = datetime.strptime(date_str, "%Y%m%d")
                    if file_date < cutoff:
                        os.remove(f"{self.cache_dir}/daily/{filename}")
                        print(f"[清理] 删除过期缓存: {filename}")
                except:
                    pass

# 创建全局实例
intelligent_matcher = IntelligentNewsMatcher()