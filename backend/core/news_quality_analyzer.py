"""
新闻质量分析器 - 评估新闻覆盖率和实时性
"""
from typing import Dict, List, Any
from datetime import datetime, timedelta


class NewsQualityAnalyzer:
    """新闻质量和覆盖率分析"""

    def analyze_news_quality(self, ts_code: str, news_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析新闻质量和覆盖率

        Returns:
            质量评估报告
        """
        stock_news = news_data.get('stock_news', [])

        # 1. 数量分析
        total_count = len(stock_news)
        direct_count = sum(1 for n in stock_news if n.get('relevance_type') == 'direct')
        competitor_count = sum(1 for n in stock_news if n.get('relevance_type') == 'competitor')
        industry_count = sum(1 for n in stock_news if n.get('relevance_type') == 'industry')

        # 2. 时效性分析
        freshness = self._analyze_freshness(stock_news)

        # 3. 质量评分
        quality_score = self._calculate_quality_score(
            total_count, direct_count, freshness['days_since_latest']
        )

        # 4. 覆盖率评级
        coverage_level = self._get_coverage_level(total_count, direct_count)

        # 5. 建议
        recommendations = self._generate_recommendations(
            coverage_level, freshness, direct_count
        )

        return {
            'ts_code': ts_code,
            'statistics': {
                'total': total_count,
                'direct': direct_count,
                'competitor': competitor_count,
                'industry': industry_count,
                'public_announcements': sum(1 for n in stock_news if n.get('src') == 'ann')
            },
            'freshness': freshness,
            'quality_score': quality_score,
            'coverage_level': coverage_level,
            'recommendations': recommendations,
            'is_reliable': quality_score >= 60 and freshness['days_since_latest'] <= 3
        }

    def _analyze_freshness(self, news_list: List[Dict]) -> Dict[str, Any]:
        """分析新闻时效性"""
        if not news_list:
            return {
                'latest_date': None,
                'days_since_latest': 999,
                'freshness_level': 'no_data'
            }

        # 找到最新的新闻日期
        latest_date = None
        for news in news_list:
            date_str = news.get('datetime', '')
            if date_str and len(date_str) >= 10:
                try:
                    # 处理不同格式的日期
                    if '-' in date_str[:10]:
                        news_date = datetime.strptime(date_str[:10], '%Y-%m-%d')
                    else:
                        news_date = datetime.strptime(date_str[:8], '%Y%m%d')

                    if latest_date is None or news_date > latest_date:
                        latest_date = news_date
                except:
                    continue

        if latest_date:
            days_old = (datetime.now() - latest_date).days

            if days_old <= 1:
                level = 'excellent'
            elif days_old <= 3:
                level = 'good'
            elif days_old <= 7:
                level = 'acceptable'
            elif days_old <= 30:
                level = 'stale'
            else:
                level = 'very_stale'

            return {
                'latest_date': latest_date.strftime('%Y-%m-%d'),
                'days_since_latest': days_old,
                'freshness_level': level
            }

        return {
            'latest_date': None,
            'days_since_latest': 999,
            'freshness_level': 'no_valid_dates'
        }

    def _calculate_quality_score(self, total: int, direct: int, days_old: int) -> float:
        """计算质量分数（0-100）"""
        # 数量分数（40分）
        quantity_score = min(total * 2, 40)  # 20条新闻满分

        # 相关性分数（30分）
        if total > 0:
            relevance_score = (direct / total) * 30
        else:
            relevance_score = 0

        # 时效性分数（30分）
        if days_old <= 1:
            freshness_score = 30
        elif days_old <= 3:
            freshness_score = 25
        elif days_old <= 7:
            freshness_score = 15
        elif days_old <= 30:
            freshness_score = 5
        else:
            freshness_score = 0

        return round(quantity_score + relevance_score + freshness_score, 1)

    def _get_coverage_level(self, total: int, direct: int) -> str:
        """评估覆盖率水平"""
        if direct >= 10:
            return 'excellent'
        elif direct >= 5:
            return 'good'
        elif direct >= 2:
            return 'fair'
        elif total >= 10:
            return 'indirect_only'
        elif total >= 5:
            return 'minimal'
        else:
            return 'insufficient'

    def _generate_recommendations(self, coverage: str, freshness: Dict, direct: int) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 覆盖率建议
        if coverage in ['insufficient', 'minimal']:
            recommendations.append("新闻覆盖率低，建议：")
            recommendations.append("- 该股票可能是小盘股或关注度较低")
            recommendations.append("- 主要依赖公司公告和行业新闻")
            recommendations.append("- 建议关注同行业龙头动态作为参考")

        # 时效性建议
        if freshness['days_since_latest'] > 7:
            recommendations.append("新闻时效性差，建议：")
            recommendations.append("- 数据可能不够实时，谨慎参考")
            recommendations.append("- 检查是否为停牌或退市股票")

        # 直接相关性建议
        if direct < 3:
            recommendations.append("直接相关新闻少，建议：")
            recommendations.append("- 扩大监控范围，包含产业链上下游")
            recommendations.append("- 关注行业政策和宏观经济影响")

        if not recommendations:
            recommendations.append("新闻覆盖良好，数据可靠性高")

        return recommendations


def get_stock_tier(ts_code: str) -> str:
    """
    判断股票层级

    Returns:
        'blue_chip': 蓝筹股
        'large_cap': 大盘股
        'mid_cap': 中盘股
        'small_cap': 小盘股
        'st': ST股票
    """
    try:
        from .tushare_client import stock_basic

        df = stock_basic()
        if df is not None and not df.empty:
            stock = df[df['ts_code'] == ts_code]
            if not stock.empty:
                name = stock.iloc[0]['name']

                # 判断ST
                if 'ST' in name or '*ST' in name:
                    return 'st'

                # 判断板块
                market = stock.iloc[0].get('market', '')
                if market == '主板':
                    # 简化判断：代码前缀
                    if ts_code[:3] in ['000', '001', '600', '601', '603']:
                        if ts_code[:3] in ['000', '600']:  # 主要指数成分股
                            return 'blue_chip'
                        return 'large_cap'
                elif market == '创业板':
                    return 'mid_cap'
                elif market == '科创板':
                    return 'mid_cap'
                else:
                    return 'small_cap'
    except:
        pass

    return 'unknown'


# 全局实例
news_quality_analyzer = NewsQualityAnalyzer()