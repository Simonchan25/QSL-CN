"""
增强版智能新闻匹配器 - 提高匹配准确性
"""
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import re
from datetime import datetime, timedelta


@dataclass
class NewsMatch:
    """新闻匹配结果"""
    news: Dict[str, Any]
    relevance_type: str  # direct, competitor, industry, macro
    match_score: float
    matched_terms: List[str]
    confidence: str  # high, medium, low
    reasons: List[str]


class EnhancedSmartNewsMatcher:
    """增强版智能新闻匹配器"""

    def __init__(self):
        self._init_stock_database()
        self._init_matching_rules()
        self._init_negative_filters()

    def _init_stock_database(self):
        """初始化股票数据库"""
        try:
            from .tushare_client import stock_basic
            df = stock_basic()
            if df is not None and not df.empty:
                # 建立股票映射
                self.stock_db = {}
                self.industry_stocks = {}
                self.name_to_code = {}

                for _, row in df.iterrows():
                    ts_code = row['ts_code']
                    name = row['name']
                    industry = row.get('industry', '')

                    self.stock_db[ts_code] = {
                        'name': name,
                        'industry': industry,
                        'area': row.get('area', ''),
                        'market': row.get('market', '')
                    }

                    self.name_to_code[name] = ts_code

                    if industry:
                        if industry not in self.industry_stocks:
                            self.industry_stocks[industry] = []
                        self.industry_stocks[industry].append({
                            'ts_code': ts_code,
                            'name': name
                        })
            else:
                self.stock_db = {}
                self.industry_stocks = {}
                self.name_to_code = {}
        except Exception as e:
            print(f"[匹配器] 初始化股票数据失败: {e}")
            self.stock_db = {}
            self.industry_stocks = {}
            self.name_to_code = {}

    def _init_matching_rules(self):
        """初始化匹配规则"""
        # 直接相关的强信号词
        self.direct_signals = {
            '公告': 100,
            '发布': 90,
            '披露': 90,
            '回应': 85,
            '澄清': 85,
            '签约': 80,
            '中标': 80,
            '收购': 75,
            '增持': 75,
            '减持': 70,
            '投资': 65
        }

        # 竞争关系映射（更精确）
        self.competitor_map = {
            '贵州茅台': ['五粮液', '泸州老窖', '洋河股份', '山西汾酒', '水井坊'],
            '五粮液': ['贵州茅台', '泸州老窖', '洋河股份', '山西汾酒'],
            '招商银行': ['平安银行', '兴业银行', '浦发银行', '民生银行', '中信银行'],
            '平安银行': ['招商银行', '兴业银行', '浦发银行', '民生银行'],
            '比亚迪': ['特斯拉', '蔚来', '理想汽车', '小鹏汽车', '长城汽车', '吉利汽车'],
            '宁德时代': ['比亚迪', '亿纬锂能', '国轩高科', '欣旺达', '孚能科技'],
            '中国平安': ['中国人寿', '中国太保', '新华保险', '中国人保'],
            '万科A': ['保利发展', '金地集团', '招商蛇口', '华润置地'],
            '格力电器': ['美的集团', '海尔智家', '海信家电'],
            '美的集团': ['格力电器', '海尔智家', '海信家电'],
        }

        # 产业链关系（上下游）
        self.supply_chain_map = {
            '新能源车': {
                '上游': ['锂矿', '钴矿', '稀土', '电池材料'],
                '中游': ['动力电池', '电机', '电控', '充电桩'],
                '下游': ['整车', '运营', '充电服务']
            },
            '光伏': {
                '上游': ['硅料', '硅片'],
                '中游': ['电池片', '组件', '逆变器'],
                '下游': ['电站', '运维']
            },
            '半导体': {
                '上游': ['硅片', '光刻胶', '电子气体'],
                '中游': ['芯片设计', '芯片制造', '封装测试'],
                '下游': ['消费电子', '汽车电子', '工业控制']
            }
        }

        # 行业特征词（更精确）
        self.industry_keywords = {
            '银行': {
                'must': ['央行', '利率', '存款', '贷款', '不良', '净息差', '拨备'],
                'optional': ['金融', '信贷', '资产质量', '资本充足率'],
                'exclude': ['投资银行', '世界银行', '数据银行']
            },
            '白酒': {
                'must': ['白酒', '酱香', '浓香', '清香', '高端酒', '次高端'],
                'optional': ['提价', '动销', '渠道', '经销商'],
                'exclude': ['啤酒', '葡萄酒', '洋酒']
            },
            '新能源': {
                'must': ['新能源', '电动', '充电', '电池', '光伏', '风电'],
                'optional': ['碳中和', '绿电', '储能', '补贴'],
                'exclude': ['石油', '煤炭', '天然气']
            }
        }

    def _init_negative_filters(self):
        """初始化负面过滤器 - 排除不相关新闻"""
        # 明确不相关的来源标记
        self.irrelevant_sources = ['广告', '推广', '赞助']

        # 需要排除的内容类型
        self.exclude_patterns = [
            r'本文不构成投资建议',
            r'风险提示',
            r'免责声明',
            r'点击查看更多',
            r'扫码关注'
        ]

    def match_news(self, ts_code: str, news_items: List[Dict[str, Any]],
                   include_competitor: bool = True,
                   include_industry: bool = True,
                   include_macro: bool = False) -> List[Dict[str, Any]]:
        """
        智能匹配新闻

        Args:
            ts_code: 股票代码
            news_items: 新闻列表
            include_competitor: 是否包含竞品新闻
            include_industry: 是否包含行业新闻
            include_macro: 是否包含宏观新闻

        Returns:
            匹配结果列表
        """
        if ts_code not in self.stock_db:
            print(f"[匹配器] 未找到股票信息: {ts_code}")
            return []

        stock_info = self.stock_db[ts_code]
        stock_name = stock_info['name']
        stock_industry = stock_info['industry']

        # 获取竞争对手
        competitors = self._get_competitors(stock_name)

        # 获取简称和别名
        aliases = self._get_stock_aliases(stock_name)

        matches = []
        seen_titles = set()  # 去重

        for news in news_items:
            title = news.get('title', '')
            content = news.get('content', '')[:500]  # 只看前500字
            full_text = f"{title} {content}"

            # 去重检查
            if title in seen_titles:
                continue
            seen_titles.add(title)

            # 检查排除规则
            if self._should_exclude(full_text):
                continue

            # 1. 直接相关匹配（最高优先级）
            if self._is_direct_match(stock_name, aliases, full_text):
                score, terms, confidence = self._calculate_direct_score(stock_name, full_text)
                matches.append({
                    **news,
                    'relevance_type': 'direct',
                    'match_score': score,
                    'matched_terms': terms,
                    'confidence': confidence,
                    'match_reason': '直接提及'
                })
                continue

            # 2. 竞品相关匹配
            if include_competitor and competitors:
                competitor_match = self._match_competitors(competitors, full_text)
                if competitor_match:
                    matches.append({
                        **news,
                        'relevance_type': 'competitor',
                        'match_score': competitor_match['score'],
                        'matched_terms': competitor_match['terms'],
                        'confidence': competitor_match['confidence'],
                        'match_reason': f"竞品: {', '.join(competitor_match['terms'][:2])}"
                    })
                    continue

            # 3. 行业相关匹配（更严格）
            if include_industry and stock_industry:
                industry_match = self._match_industry_enhanced(stock_industry, full_text)
                if industry_match and industry_match['score'] >= 30:  # 提高阈值
                    matches.append({
                        **news,
                        'relevance_type': 'industry',
                        'match_score': industry_match['score'],
                        'matched_terms': industry_match['terms'],
                        'confidence': industry_match['confidence'],
                        'match_reason': f"行业: {stock_industry}"
                    })
                    continue

            # 4. 产业链相关 - 暂时禁用,准确率不高
            # if include_industry:
            #     chain_match = self._match_supply_chain(stock_name, stock_industry, full_text)
            #     if chain_match:
            #         matches.append({
            #             **news,
            #             'relevance_type': 'supply_chain',
            #             'match_score': chain_match['score'],
            #             'matched_terms': chain_match['terms'],
            #             'confidence': chain_match['confidence'],
            #             'match_reason': f"产业链: {chain_match['chain_type']}"
            #         })

        # 按分数排序
        matches.sort(key=lambda x: x['match_score'], reverse=True)

        # 限制返回数量，保证质量
        max_items = 50
        if len(matches) > max_items:
            # 保留高质量内容
            high_quality = [m for m in matches if m['confidence'] == 'high'][:30]
            medium_quality = [m for m in matches if m['confidence'] == 'medium'][:15]
            low_quality = [m for m in matches if m['confidence'] == 'low'][:5]

            matches = high_quality + medium_quality + low_quality

        return matches

    def _get_competitors(self, stock_name: str) -> List[str]:
        """获取竞争对手列表"""
        if stock_name in self.competitor_map:
            return self.competitor_map[stock_name]

        # 动态查找同行业龙头
        for stock_info in self.stock_db.values():
            if stock_info['name'] == stock_name:
                industry = stock_info['industry']
                if industry in self.industry_stocks:
                    # 返回同行业前5大市值公司（这里简化处理）
                    same_industry = [s['name'] for s in self.industry_stocks[industry]
                                     if s['name'] != stock_name]
                    return same_industry[:5]
        return []

    def _get_stock_aliases(self, stock_name: str) -> List[str]:
        """获取股票别名和简称"""
        aliases = [stock_name]

        # 去掉常见后缀
        base_name = stock_name
        for suffix in ['A', 'B', 'H', '股份', '集团', '控股', '科技', '发展']:
            base_name = base_name.replace(suffix, '')

        if base_name and base_name != stock_name:
            aliases.append(base_name)

        # 特殊简称映射
        special_aliases = {
            '贵州茅台': ['茅台', '茅台酒'],
            '五粮液': ['五粮', '五粮液酒'],
            '比亚迪': ['BYD', '比亚迪汽车'],
            '宁德时代': ['CATL', '宁德'],
            '招商银行': ['招行', 'CMB'],
            '平安银行': ['平安', '平银'],
            '中国平安': ['平安集团', '平安保险'],
        }

        if stock_name in special_aliases:
            aliases.extend(special_aliases[stock_name])

        return aliases

    def _should_exclude(self, text: str) -> bool:
        """检查是否应该排除这条新闻"""
        # 检查排除模式
        for pattern in self.exclude_patterns:
            if re.search(pattern, text):
                return True

        # 检查是否是广告
        ad_keywords = ['广告', '推广', '赞助商']
        if any(kw in text[:50] for kw in ad_keywords):
            return True

        return False

    def _is_direct_match(self, stock_name: str, aliases: List[str], text: str) -> bool:
        """检查是否直接相关"""
        for alias in aliases:
            if alias in text:
                return True
        return False

    def _calculate_direct_score(self, stock_name: str, text: str) -> Tuple[float, List[str], str]:
        """计算直接相关分数"""
        score = 100.0
        matched_terms = [stock_name]

        # 检查强信号词
        for signal, weight in self.direct_signals.items():
            if signal in text:
                score = max(score, weight)
                matched_terms.append(signal)

        # 出现次数加分
        count = text.count(stock_name)
        if count > 3:
            score = min(score + 10, 100)

        confidence = 'high' if score >= 80 else 'medium' if score >= 50 else 'low'

        return score, matched_terms, confidence

    def _match_competitors(self, competitors: List[str], text: str) -> Optional[Dict]:
        """匹配竞争对手"""
        matched = []
        for comp in competitors:
            if comp in text:
                matched.append(comp)

        if not matched:
            return None

        score = min(60 + len(matched) * 10, 85)  # 竞品最高85分
        confidence = 'medium' if len(matched) >= 2 else 'low'

        return {
            'score': score,
            'terms': matched,
            'confidence': confidence
        }

    def _match_industry_enhanced(self, industry: str, text: str) -> Optional[Dict]:
        """增强的行业匹配"""
        if industry not in self.industry_keywords:
            # 简单匹配
            if industry in text:
                return {'score': 40, 'terms': [industry], 'confidence': 'low'}
            return None

        rules = self.industry_keywords[industry]
        matched_must = []
        matched_optional = []

        # 检查排除词
        for exclude in rules.get('exclude', []):
            if exclude in text:
                return None  # 包含排除词，不匹配

        # 检查必须词
        for must in rules.get('must', []):
            if must in text:
                matched_must.append(must)

        # 检查可选词
        for opt in rules.get('optional', []):
            if opt in text:
                matched_optional.append(opt)

        if not matched_must:
            return None

        # 计算分数
        score = len(matched_must) * 20 + len(matched_optional) * 5
        score = min(score, 70)  # 行业最高70分

        confidence = 'medium' if len(matched_must) >= 2 else 'low'

        return {
            'score': score,
            'terms': matched_must + matched_optional,
            'confidence': confidence
        }

    def _match_supply_chain(self, stock_name: str, industry: str, text: str) -> Optional[Dict]:
        """匹配产业链相关"""
        # 检查是否属于某个产业链
        for chain_name, chain_info in self.supply_chain_map.items():
            if chain_name not in text and industry != chain_name:
                continue

            matched_terms = []
            chain_type = None

            for level, keywords in chain_info.items():
                for kw in keywords:
                    if kw in text:
                        matched_terms.append(kw)
                        chain_type = f"{chain_name}-{level}"

            if matched_terms:
                score = min(30 + len(matched_terms) * 10, 60)
                return {
                    'score': score,
                    'terms': matched_terms,
                    'confidence': 'low',
                    'chain_type': chain_type
                }

        return None

    def format_results(self, matches: List[Dict]) -> Dict[str, Any]:
        """格式化匹配结果"""
        # 统计
        stats = {
            'total': len(matches),
            'direct': sum(1 for m in matches if m.get('relevance_type') == 'direct'),
            'competitor': sum(1 for m in matches if m.get('relevance_type') == 'competitor'),
            'industry': sum(1 for m in matches if m.get('relevance_type') == 'industry'),
            'supply_chain': sum(1 for m in matches if m.get('relevance_type') == 'supply_chain'),
            'high_confidence': sum(1 for m in matches if m.get('confidence') == 'high'),
            'medium_confidence': sum(1 for m in matches if m.get('confidence') == 'medium'),
            'low_confidence': sum(1 for m in matches if m.get('confidence') == 'low'),
        }

        return {
            'news': matches,
            'stats': stats,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }


# 创建全局实例
enhanced_matcher = EnhancedSmartNewsMatcher()