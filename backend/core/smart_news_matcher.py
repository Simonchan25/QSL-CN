"""
智能分层新闻匹配系统 - 增强版
支持所有A股股票，自动识别行业，分层匹配相关新闻
集成LLM竞品识别、简称学习、动态缓存
"""

import re
import jieba
from typing import List, Dict, Any, Tuple, Set, Optional
from dataclasses import dataclass
import pandas as pd
import logging

# 导入新功能模块
try:
    from .llm_competitor_analyzer import get_competitor_analyzer
    from .nickname_learner import get_nickname_learner
    from .cache_config import get_dynamic_ttl, is_hot_stock, has_major_event
    ENHANCED_FEATURES = True
except ImportError:
    ENHANCED_FEATURES = False
    print("[警告] 增强功能模块未找到，使用基础功能")

logger = logging.getLogger(__name__)


@dataclass
class NewsMatch:
    """新闻匹配结果"""
    news_item: Dict[str, Any]
    relevance_type: str  # 'direct'(直接相关), 'competitor'(竞品相关), 'industry'(行业相关), 'sector'(板块相关)
    match_score: float
    matched_terms: List[str]
    confidence: str


class SmartNewsMatcher:
    """智能新闻匹配器 - 支持所有A股"""

    def __init__(self, use_enhanced_features: bool = True):
        """
        初始化

        Args:
            use_enhanced_features: 是否使用增强功能（LLM、简称学习等）
        """
        self.use_enhanced = use_enhanced_features and ENHANCED_FEATURES

        # 从完整的行业关键词映射文件导入
        try:
            from .industry_keywords_map import INDUSTRY_KEYWORDS
            self.industry_keywords = INDUSTRY_KEYWORDS
        except ImportError:
            print("[警告] 无法加载行业关键词映射，使用默认配置")
            self.industry_keywords = {}

        # 初始化增强功能模块
        if self.use_enhanced:
            self.competitor_analyzer = get_competitor_analyzer()
            self.nickname_learner = get_nickname_learner()
            logger.info("[智能匹配] 已启用增强功能")
        else:
            self.competitor_analyzer = None
            self.nickname_learner = None

        # 定义主要竞品关系（基础版本）
        self.competitors = {
            '贵州茅台': ['五粮液', '洋河股份', '泸州老窖', '山西汾酒', '古井贡酒', '水井坊', '舍得酒业'],
            '五粮液': ['贵州茅台', '洋河股份', '泸州老窖', '山西汾酒', '古井贡酒'],
            '招商银行': ['平安银行', '兴业银行', '浦发银行', '民生银行', '中信银行', '光大银行'],
            '工商银行': ['建设银行', '农业银行', '中国银行', '交通银行', '邮储银行'],
            '中国平安': ['中国人寿', '中国太保', '新华保险', '中国人保'],
            '比亚迪': ['特斯拉', '蔚来', '理想汽车', '小鹏汽车', '长城汽车', '吉利汽车'],
            '宁德时代': ['比亚迪', '亿纬锂能', '国轩高科', '欣旺达', '孚能科技'],
            '腾讯控股': ['阿里巴巴', '美团', '京东', '拼多多', '字节跳动'],
            '阿里巴巴': ['腾讯控股', '京东', '拼多多', '美团'],
        }

        # 加载股票基本信息（用于自动获取行业）
        self._load_stock_info()

    def _load_stock_info(self):
        """加载A股股票基本信息"""
        try:
            from .tushare_client import stock_basic
            df = stock_basic()
            if df is not None and not df.empty:
                # 创建股票代码到行业的映射
                self.stock_industry_map = {}
                for _, row in df.iterrows():
                    ts_code = row.get('ts_code', '')
                    industry = row.get('industry', '')
                    name = row.get('name', '')
                    if ts_code:
                        self.stock_industry_map[ts_code] = {
                            'name': name,
                            'industry': industry
                        }
            else:
                self.stock_industry_map = {}
        except Exception as e:
            print(f"[警告] 加载股票信息失败: {e}")
            self.stock_industry_map = {}

    def get_stock_info(self, ts_code: str) -> Dict[str, str]:
        """获取股票信息"""
        return self.stock_industry_map.get(ts_code, {'name': '', 'industry': ''})

    def match_news(self,
                   ts_code: str,
                   news_items: List[Dict[str, Any]],
                   include_competitor: bool = True,
                   include_industry: bool = True,
                   include_sector: bool = False,
                   announcements: Optional[List[Dict[str, Any]]] = None,
                   use_llm: bool = True) -> List[NewsMatch]:
        """
        智能匹配新闻

        Args:
            ts_code: 股票代码
            news_items: 新闻列表
            include_industry: 是否包含行业相关新闻
            include_sector: 是否包含板块相关新闻

        Returns:
            匹配结果列表
        """
        stock_info = self.get_stock_info(ts_code)
        stock_name = stock_info.get('name', '')
        industry = stock_info.get('industry', '')
        symbol = ts_code.split('.')[0] if ts_code else ''

        print(f"[智能匹配] 股票: {stock_name}({symbol}), 行业: {industry}")

        matched_results = []

        # 使用增强功能获取更精准的关键词
        if self.use_enhanced:
            # 1. 学习简称
            if self.nickname_learner:
                nicknames = self.nickname_learner.learn_nicknames(
                    ts_code, stock_name, news_items, announcements, industry
                )
                logger.info(f"[智能匹配] 学习到简称: {list(nicknames.keys())}")
            else:
                nicknames = {}

            # 2. 识别真实竞争对手
            if self.competitor_analyzer and use_llm:
                competitors = self.competitor_analyzer.analyze_competitors(
                    ts_code, stock_name, news_items, announcements, use_llm=True
                )
                enhanced_competitor_keywords = self.competitor_analyzer.get_competitor_keywords(competitors)
                logger.info(f"[智能匹配] LLM识别竞品: {enhanced_competitor_keywords[:5]}")
            else:
                enhanced_competitor_keywords = []
        else:
            nicknames = {}
            enhanced_competitor_keywords = []

        # 第一层：直接相关匹配（包含学习到的简称）
        direct_keywords = self._get_direct_keywords(stock_name, symbol)

        # 添加学习到的简称
        if nicknames:
            for nickname, confidence in nicknames.items():
                if confidence > 0.6:  # 只使用高置信度简称
                    if nickname not in direct_keywords.get('strong', []):
                        direct_keywords.setdefault('strong', []).append(nickname)

        # 第二层：竞品相关匹配（优先使用LLM识别的竞品）
        if include_competitor:
            if enhanced_competitor_keywords:
                competitor_keywords = enhanced_competitor_keywords
            else:
                competitor_keywords = self._get_competitor_keywords(stock_name)
        else:
            competitor_keywords = []

        # 第三层：行业相关匹配
        industry_keywords = self._get_industry_keywords(industry) if include_industry else {}

        # 第四层：板块相关匹配（可选）
        sector_keywords = self._get_sector_keywords(industry) if include_sector else {}

        for news_item in news_items:
            title = news_item.get('title', '')
            content = news_item.get('content', '')[:1000]  # 只检查前1000字

            # 1. 检查直接相关
            direct_match = self._check_direct_match(title, content, direct_keywords)
            if direct_match['matched']:
                matched_results.append(NewsMatch(
                    news_item=news_item,
                    relevance_type='direct',
                    match_score=direct_match['score'],
                    matched_terms=direct_match['terms'],
                    confidence='high' if direct_match['score'] > 80 else 'medium'
                ))
                continue

            # 2. 检查竞品相关（如果启用）
            if include_competitor and competitor_keywords:
                competitor_match = self._check_competitor_match(title, content, competitor_keywords)
                if competitor_match['matched']:
                    matched_results.append(NewsMatch(
                        news_item=news_item,
                        relevance_type='competitor',
                        match_score=competitor_match['score'],
                        matched_terms=competitor_match['terms'],
                        confidence='medium' if competitor_match['score'] > 40 else 'low'
                    ))
                    continue

            # 3. 检查行业相关（如果启用）
            if include_industry and industry_keywords:
                industry_match = self._check_industry_match(title, content, industry_keywords)
                if industry_match['matched']:
                    matched_results.append(NewsMatch(
                        news_item=news_item,
                        relevance_type='industry',
                        match_score=industry_match['score'],
                        matched_terms=industry_match['terms'],
                        confidence='medium' if industry_match['score'] > 30 else 'low'
                    ))
                    continue

            # 4. 检查板块相关（如果启用）
            if include_sector and sector_keywords:
                sector_match = self._check_sector_match(title, content, sector_keywords)
                if sector_match['matched']:
                    matched_results.append(NewsMatch(
                        news_item=news_item,
                        relevance_type='sector',
                        match_score=sector_match['score'],
                        matched_terms=sector_match['terms'],
                        confidence='low'
                    ))

        # 统计并打印结果
        direct_count = len([m for m in matched_results if m.relevance_type == 'direct'])
        competitor_count = len([m for m in matched_results if m.relevance_type == 'competitor'])
        industry_count = len([m for m in matched_results if m.relevance_type == 'industry'])
        sector_count = len([m for m in matched_results if m.relevance_type == 'sector'])

        print(f"[智能匹配] 结果: 直接相关{direct_count}条, 竞品相关{competitor_count}条, 行业相关{industry_count}条, 板块相关{sector_count}条")

        return matched_results

    def _get_direct_keywords(self, stock_name: str, symbol: str) -> Dict[str, List[str]]:
        """获取直接相关的关键词"""
        keywords = {
            'exact': [],  # 精确匹配词
            'strong': [],  # 强相关词
            'normal': []   # 一般相关词
        }

        if stock_name:
            keywords['exact'].append(stock_name)

            # 生成常见简称
            if '银行' in stock_name:
                short_name = stock_name.replace('银行', '')
                if len(short_name) >= 2:
                    keywords['strong'].append(short_name + '行')  # 如"招行"
                    # 添加英文缩写（如果存在）
                    if short_name in ['招商', '工商', '建设', '农业', '交通', '中国']:
                        abbr_map = {
                            '招商': 'CMB',
                            '工商': 'ICBC',
                            '建设': 'CCB',
                            '农业': 'ABC',
                            '交通': 'BCM',
                            '中国': 'BOC'
                        }
                        if short_name in abbr_map:
                            keywords['strong'].append(abbr_map[short_name])

            if '集团' in stock_name:
                keywords['strong'].append(stock_name.replace('集团', ''))

            if '股份' in stock_name:
                keywords['strong'].append(stock_name.replace('股份有限公司', '').replace('股份', ''))

            # 对于知名公司的特殊处理
            special_cases = {
                '贵州茅台': ['茅台', '茅台酒', '茅台集团'],
                '五粮液': ['五粮液集团', '五粮液酒'],
                '比亚迪': ['BYD', '比亚迪汽车'],
                '宁德时代': ['CATL', '宁德'],
                '中国平安': ['平安', '平安集团'],
                '腾讯控股': ['腾讯', 'Tencent'],
                '阿里巴巴': ['阿里', 'Alibaba']
            }

            if stock_name in special_cases:
                keywords['strong'].extend(special_cases[stock_name])

        if symbol:
            keywords['exact'].append(symbol)
            # 添加带交易所后缀的完整代码
            if '.' not in symbol:
                keywords['normal'].append(f"{symbol}.SH")
                keywords['normal'].append(f"{symbol}.SZ")

        return keywords

    def _get_competitor_keywords(self, stock_name: str) -> List[str]:
        """获取竞品关键词"""
        competitors = []

        # 从预定义的竞品关系获取
        if stock_name in self.competitors:
            competitors = self.competitors[stock_name]

        # 基于行业动态识别竞品
        # 如果同行业的其他主要公司
        if stock_name and not competitors:
            # 可以从同行业TOP公司中选择
            stock_info = None
            for code, info in self.stock_industry_map.items():
                if info.get('name') == stock_name:
                    stock_info = info
                    break

            if stock_info:
                industry = stock_info.get('industry', '')
                # 找同行业的其他主要公司
                same_industry = []
                for code, info in self.stock_industry_map.items():
                    if info.get('industry') == industry and info.get('name') != stock_name:
                        same_industry.append(info.get('name'))
                # 取前5个作为潜在竞品
                competitors = same_industry[:5]

        return competitors

    def _check_competitor_match(self, title: str, content: str, competitor_names: List[str]) -> Dict:
        """检查竞品匹配"""
        matched_terms = []
        total_score = 0
        content_preview = content[:500] if content else ""

        for comp_name in competitor_names:
            if comp_name and self._is_term_in_text(comp_name, title):
                matched_terms.append(f"{comp_name}(竞品-标题)")
                total_score += 70  # 竞品在标题中权重较高
            elif comp_name and self._is_term_in_text(comp_name, content_preview):
                matched_terms.append(f"{comp_name}(竞品-内容)")
                total_score += 35  # 竞品在内容中权重中等

        return {
            'matched': total_score > 0,
            'score': min(total_score, 100),
            'terms': matched_terms
        }

    def _get_industry_keywords(self, industry: str) -> Dict[str, Any]:
        """获取行业相关的关键词"""
        if not industry:
            return {}

        # 尝试从完整映射中获取
        try:
            from .industry_keywords_map import get_industry_keywords
            return get_industry_keywords(industry)
        except ImportError:
            pass

        # 后备方案：精确匹配
        if industry in self.industry_keywords:
            return self.industry_keywords[industry]

        # 模糊匹配
        for ind_name, ind_data in self.industry_keywords.items():
            if ind_name in industry or industry in ind_name:
                return ind_data

        # 默认返回
        return {
            'keywords': [f'{industry}行业', f'{industry}板块'],
            'exclude': []
        }

    def _get_sector_keywords(self, industry: str) -> Dict[str, List[str]]:
        """获取板块相关的关键词"""
        # 这里可以定义更大的板块概念
        sector_map = {
            '银行': ['金融板块', '大金融'],
            '保险': ['金融板块', '大金融'],
            '证券': ['金融板块', '大金融'],
            '白酒': ['消费板块', '大消费', '食品饮料'],
            '食品': ['消费板块', '大消费', '食品饮料'],
            '家电': ['消费板块', '大消费'],
            '医药': ['医药板块', '大健康'],
            '汽车': ['汽车板块', '新能源车产业链'],
            '房地产': ['地产板块', '基建'],
            '半导体': ['科技板块', '芯片概念'],
            '软件': ['科技板块', 'TMT'],
            '光伏': ['新能源板块', '碳中和'],
            '风电': ['新能源板块', '碳中和']
        }

        for sector_key, sector_keywords in sector_map.items():
            if sector_key in industry:
                return {'keywords': sector_keywords}

        return {}

    def _check_direct_match(self, title: str, content: str, keywords: Dict[str, List[str]]) -> Dict:
        """检查直接匹配"""
        matched_terms = []
        total_score = 0

        # 限制内容搜索长度，避免噪音
        content_preview = content[:500] if content else ""

        # 精确匹配（最高分）
        for term in keywords.get('exact', []):
            if term and self._is_term_in_text(term, title):
                matched_terms.append(f"{term}(标题)")
                total_score += 100
            elif term and self._is_term_in_text(term, content_preview):
                matched_terms.append(f"{term}(内容)")
                total_score += 60

        # 强相关词
        for term in keywords.get('strong', []):
            if term and self._is_term_in_text(term, title):
                matched_terms.append(f"{term}(标题)")
                total_score += 80
            elif term and self._is_term_in_text(term, content_preview):
                matched_terms.append(f"{term}(内容)")
                total_score += 40

        # 一般相关词
        for term in keywords.get('normal', []):
            if term and self._is_term_in_text(term, title):
                matched_terms.append(f"{term}(标题)")
                total_score += 50
            elif term and self._is_term_in_text(term, content_preview):
                matched_terms.append(f"{term}(内容)")
                total_score += 25

        return {
            'matched': total_score > 0,
            'score': min(total_score, 100),  # 限制最高分为100
            'terms': matched_terms
        }

    def _check_industry_match(self, title: str, content: str, industry_data: Dict) -> Dict:
        """检查行业匹配"""
        if not industry_data:
            return {'matched': False, 'score': 0, 'terms': []}

        keywords = industry_data.get('keywords', [])
        exclude = industry_data.get('exclude', [])

        # 先检查排除词
        for ex_term in exclude:
            if self._is_term_in_text(ex_term, title) or self._is_term_in_text(ex_term, content[:200]):
                return {'matched': False, 'score': 0, 'terms': []}

        matched_terms = []
        total_score = 0

        for term in keywords:
            if self._is_term_in_text(term, title):
                matched_terms.append(f"{term}(行业-标题)")
                total_score += 50
            elif self._is_term_in_text(term, content):
                matched_terms.append(f"{term}(行业-内容)")
                total_score += 20

        return {
            'matched': total_score > 0,
            'score': total_score,
            'terms': matched_terms
        }

    def _check_sector_match(self, title: str, content: str, sector_data: Dict) -> Dict:
        """检查板块匹配"""
        if not sector_data:
            return {'matched': False, 'score': 0, 'terms': []}

        keywords = sector_data.get('keywords', [])
        matched_terms = []
        total_score = 0

        for term in keywords:
            if self._is_term_in_text(term, title):
                matched_terms.append(f"{term}(板块-标题)")
                total_score += 30
            elif self._is_term_in_text(term, content):
                matched_terms.append(f"{term}(板块-内容)")
                total_score += 10

        return {
            'matched': total_score > 0,
            'score': total_score,
            'terms': matched_terms
        }

    def _is_term_in_text(self, term: str, text: str) -> bool:
        """检查词语是否在文本中"""
        if not term or not text:
            return False

        term = term.strip()

        # 对于股票代码（6位数字），需要精确匹配
        if re.match(r'^\d{6}$', term):
            # 检查是否作为独立的代码出现
            patterns = [
                rf'\b{term}\b',  # 独立数字
                rf'{term}\.S[HZ]',  # 带交易所后缀
                rf'\({term}\)',  # 括号中
                rf'（{term}）',  # 中文括号
            ]
            for pattern in patterns:
                if re.search(pattern, text):
                    return True
            return False

        # 对于英文/数字混合，使用词边界
        if re.match(r'^[a-zA-Z0-9\.]+$', term):
            return bool(re.search(rf'\b{re.escape(term)}\b', text, re.IGNORECASE))

        # 对于中文，直接包含匹配但要避免部分匹配造成误判
        # 例如"中国银行"不应匹配"中国建设银行"
        if any('\u4e00' <= c <= '\u9fff' for c in term):
            # 如果是短词（2-3个字），需要更严格的匹配
            if len(term) <= 3:
                # 检查是否被其他银行名包含
                if '行' in term or '银' in term:
                    # 银行类需要特别处理
                    exclusions = ['建设', '工商', '农业', '交通', '招商', '中信', '民生', '光大', '华夏', '兴业']
                    for ex in exclusions:
                        if ex not in term and ex in text and term in text:
                            # 如果文本中同时包含其他银行名和当前词，可能是误匹配
                            idx = text.find(term)
                            if idx > 0:
                                # 检查前后文
                                context = text[max(0, idx-2):min(len(text), idx+len(term)+2)]
                                if any(ex in context for ex in exclusions):
                                    return False

            return term.lower() in text.lower()

        # 默认情况
        return term.lower() in text.lower()

    def format_results(self, matches: List[NewsMatch], max_items: int = 50) -> Dict[str, Any]:
        """格式化匹配结果"""
        # 按相关性和分数排序
        sorted_matches = sorted(matches,
                              key=lambda x: (
                                  {'direct': 4, 'competitor': 3, 'industry': 2, 'sector': 1}.get(x.relevance_type, 0),
                                  x.match_score
                              ),
                              reverse=True)

        # 转换为字典格式
        results = []
        for match in sorted_matches[:max_items]:
            item = match.news_item.copy()
            item.update({
                'relevance_type': match.relevance_type,
                'match_score': match.match_score,
                'matched_terms': match.matched_terms,
                'confidence': match.confidence
            })
            results.append(item)

        # 统计信息
        stats = {
            'total': len(matches),
            'direct': len([m for m in matches if m.relevance_type == 'direct']),
            'competitor': len([m for m in matches if m.relevance_type == 'competitor']),
            'industry': len([m for m in matches if m.relevance_type == 'industry']),
            'sector': len([m for m in matches if m.relevance_type == 'sector']),
            'high_confidence': len([m for m in matches if m.confidence == 'high']),
            'medium_confidence': len([m for m in matches if m.confidence == 'medium']),
            'low_confidence': len([m for m in matches if m.confidence == 'low'])
        }

        return {
            'news': results,
            'stats': stats
        }


# 创建全局实例
smart_matcher = SmartNewsMatcher()