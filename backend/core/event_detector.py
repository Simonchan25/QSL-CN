"""
重大事件检测器
实时识别股票的重大事件，用于动态调整缓存策略
"""

import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class EventDetector:
    """重大事件检测器"""

    def __init__(self):
        # 重大事件关键词（分类和权重）
        self.event_keywords = {
            # 业绩相关 (权重高)
            'earnings': {
                'keywords': ['业绩预告', '业绩快报', '年报', '季报', '半年报',
                           '扭亏为盈', '业绩大增', '业绩大幅', '净利润增长', '营收增长',
                           '业绩爆雷', '亏损', '业绩下滑', '商誉减值'],
                'weight': 1.0
            },
            # 并购重组 (权重最高)
            'merger': {
                'keywords': ['收购', '并购', '重组', '重大资产重组', '借壳',
                           '注入资产', '股权转让', '控制权变更', '要约收购'],
                'weight': 1.5
            },
            # 股权变动
            'equity': {
                'keywords': ['增持', '减持', '股东变更', '实控人变更',
                           '大股东', '举牌', '股权激励', '回购'],
                'weight': 0.8
            },
            # 重大合同
            'contract': {
                'keywords': ['重大合同', '中标', '大订单', '战略合作',
                           '框架协议', '签约', '中标公告'],
                'weight': 0.7
            },
            # 停复牌
            'suspension': {
                'keywords': ['停牌', '复牌', '临时停牌', '紧急停牌',
                           '筹划重大事项', '核查'],
                'weight': 1.2
            },
            # 监管处罚
            'regulatory': {
                'keywords': ['处罚', '警示函', '问询函', '立案调查',
                           'ST', '退市', '违规', '监管函'],
                'weight': 1.0
            },
            # 技术突破
            'innovation': {
                'keywords': ['技术突破', '新产品发布', '专利', '研发成功',
                           '临床试验', '新药获批', '量产'],
                'weight': 0.6
            },
            # 行业政策
            'policy': {
                'keywords': ['政策利好', '政策支持', '补贴', '牌照',
                           '资质', '准入', '政策调整'],
                'weight': 0.5
            }
        }

        # 异动指标阈值（根据实际数据调整）
        self.anomaly_thresholds = {
            'price_change': 5.0,     # 涨跌幅超过5%（A股日常波动）
            'volume_ratio': 2.0,     # 量比超过2倍（明显放量）
            'turnover_rate': 5.0,    # 换手率超过5%（高换手）
            'amplitude': 7.0,        # 振幅超过7%（剧烈波动）
        }

        # 事件缓存（避免重复检测）
        self.event_cache = {}
        self.cache_ttl = 3600  # 1小时

    def detect_events(self,
                     ts_code: str,
                     announcements: Optional[List[Dict]] = None,
                     news: Optional[List[Dict]] = None,
                     price_data: Optional[Dict] = None) -> Tuple[bool, List[Dict]]:
        """
        检测重大事件

        Args:
            ts_code: 股票代码
            announcements: 最近公告列表
            news: 最近新闻列表
            price_data: 价格数据（包含涨跌幅、成交量等）

        Returns:
            (是否有重大事件, 事件列表)
        """

        # 检查缓存
        cache_key = f"{ts_code}_events"
        if cache_key in self.event_cache:
            cached_time, cached_result = self.event_cache[cache_key]
            if (datetime.now() - cached_time).seconds < self.cache_ttl:
                return cached_result

        events = []

        # 1. 检测公告中的重大事件
        if announcements:
            ann_events = self._detect_announcement_events(announcements)
            events.extend(ann_events)

        # 2. 检测新闻中的重大事件
        if news:
            news_events = self._detect_news_events(news)
            events.extend(news_events)

        # 3. 检测价格异动
        if price_data:
            price_events = self._detect_price_anomaly(price_data)
            events.extend(price_events)

        # 4. 综合判断
        has_major_event = self._evaluate_events(events)

        # 缓存结果
        result = (has_major_event, events)
        self.event_cache[cache_key] = (datetime.now(), result)

        if has_major_event:
            logger.info(f"[事件检测] {ts_code} 检测到 {len(events)} 个重大事件")

        return result

    def _detect_announcement_events(self, announcements: List[Dict]) -> List[Dict]:
        """检测公告中的重大事件"""
        events = []

        # 只检查最近3天的公告
        cutoff_date = (datetime.now() - timedelta(days=3)).strftime('%Y%m%d')

        for ann in announcements:
            title = ann.get('title', '')
            ann_date = ann.get('ann_date', '')

            # 跳过旧公告（如果日期可比较的话）
            if ann_date and len(ann_date) == 8:  # YYYYMMDD格式
                if ann_date < cutoff_date:
                    continue

            # 检查每个事件类型
            for event_type, config in self.event_keywords.items():
                for keyword in config['keywords']:
                    if keyword in title:
                        events.append({
                            'type': event_type,
                            'keyword': keyword,
                            'source': 'announcement',
                            'title': title,
                            'date': ann_date,
                            'weight': config['weight']
                        })
                        break  # 每个公告只匹配一次

        return events

    def _detect_news_events(self, news_items: List[Dict]) -> List[Dict]:
        """检测新闻中的重大事件"""
        events = []

        # 只检查最近24小时的新闻
        cutoff_time = datetime.now() - timedelta(hours=24)

        for news in news_items:
            title = news.get('title', '')
            datetime_str = news.get('datetime', '')

            # 尝试解析时间
            try:
                news_time = datetime.strptime(datetime_str[:10], '%Y-%m-%d')
                if news_time < cutoff_time:
                    continue
            except:
                pass  # 时间格式问题，继续处理

            # 检查事件关键词
            for event_type, config in self.event_keywords.items():
                for keyword in config['keywords']:
                    if keyword in title:
                        events.append({
                            'type': event_type,
                            'keyword': keyword,
                            'source': 'news',
                            'title': title,
                            'date': datetime_str,
                            'weight': config['weight'] * 0.7  # 新闻权重略低于公告
                        })
                        break

        return events

    def _detect_price_anomaly(self, price_data: Dict) -> List[Dict]:
        """检测价格异动"""
        events = []

        # 涨跌幅异常
        price_change = abs(price_data.get('pct_chg', 0))
        if price_change > self.anomaly_thresholds['price_change']:
            events.append({
                'type': 'price_anomaly',
                'keyword': f"涨跌幅{price_change:.1f}%",
                'source': 'market',
                'title': f"股价异动：{'涨' if price_data.get('pct_chg', 0) > 0 else '跌'}{price_change:.1f}%",
                'date': datetime.now().strftime('%Y-%m-%d'),
                'weight': 1.0
            })

        # 成交量异常
        volume_ratio = price_data.get('volume_ratio', 0)
        if volume_ratio > self.anomaly_thresholds['volume_ratio']:
            events.append({
                'type': 'volume_anomaly',
                'keyword': f"量比{volume_ratio:.1f}",
                'source': 'market',
                'title': f"成交异常：量比达{volume_ratio:.1f}倍",
                'date': datetime.now().strftime('%Y-%m-%d'),
                'weight': 0.8
            })

        # 换手率异常
        turnover = price_data.get('turnover_rate', 0)
        if turnover > self.anomaly_thresholds['turnover_rate']:
            events.append({
                'type': 'turnover_anomaly',
                'keyword': f"换手率{turnover:.1f}%",
                'source': 'market',
                'title': f"换手异常：换手率{turnover:.1f}%",
                'date': datetime.now().strftime('%Y-%m-%d'),
                'weight': 0.7
            })

        return events

    def _evaluate_events(self, events: List[Dict]) -> bool:
        """
        综合评估是否构成重大事件

        规则：
        1. 任何并购重组事件 -> True
        2. 任何停复牌事件 -> True
        3. 权重总和 > 1.5 -> True
        4. 多个事件（>= 3个）-> True
        """
        if not events:
            return False

        # 检查高权重事件
        for event in events:
            if event['type'] in ['merger', 'suspension']:
                return True

        # 计算总权重
        total_weight = sum(e['weight'] for e in events)
        if total_weight >= 1.5:
            return True

        # 检查事件数量
        if len(events) >= 3:
            return True

        return False

    def get_event_summary(self, events: List[Dict]) -> str:
        """生成事件摘要"""
        if not events:
            return "无重大事件"

        # 按权重排序
        events.sort(key=lambda x: x['weight'], reverse=True)

        # 生成摘要
        summary_parts = []
        seen_types = set()

        for event in events[:3]:  # 只取前3个
            if event['type'] not in seen_types:
                summary_parts.append(f"{event['keyword']}")
                seen_types.add(event['type'])

        return "、".join(summary_parts)


# 单例模式
_detector_instance = None

def get_event_detector() -> EventDetector:
    """获取事件检测器单例"""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = EventDetector()
    return _detector_instance


def has_major_event_smart(ts_code: str,
                         announcements: Optional[List[Dict]] = None,
                         news: Optional[List[Dict]] = None,
                         price_data: Optional[Dict] = None) -> bool:
    """
    智能判断是否有重大事件

    这是对外的简化接口，供cache_config.py调用
    """
    detector = get_event_detector()
    has_event, events = detector.detect_events(ts_code, announcements, news, price_data)
    return has_event