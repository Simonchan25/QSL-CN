"""
数据筛选优化器 - 解决数据不匹配问题
提供更智能的股票、热点、市场数据筛选
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from .tushare_client import (
    _call_api, stock_basic, daily, daily_basic,
    moneyflow_dc, limit_list_d, top_list,
    concept, concept_detail, ths_hot,
    news, major_news, anns
)
from .trading_date_helper import get_recent_trading_dates


class DataFilterOptimizer:
    """数据筛选优化器"""
    
    def __init__(self):
        self.cache_dir = os.path.join(os.path.dirname(__file__), '../.cache/filters')
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # 加载股票基础信息
        self.stock_info = self._load_stock_info()
        
        # 加载增强版概念映射
        self.concept_map = self._load_enhanced_concept_map()
        
        # 市场环境自适应权重
        self.adaptive_weights = self._initialize_adaptive_weights()
    
    def _load_stock_info(self) -> Dict[str, Dict]:
        """加载并缓存股票基础信息"""
        cache_file = os.path.join(self.cache_dir, 'stock_info.json')
        
        # 尝试从缓存加载
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    # 检查缓存时效（24小时）
                    if time.time() - cache_data.get('timestamp', 0) < 86400:
                        return cache_data.get('data', {})
            except:
                pass
        
        # 重新加载
        stock_info = {}
        try:
            df = stock_basic()
            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    stock_info[row['ts_code']] = {
                        'name': row['name'],
                        'area': row.get('area', ''),
                        'industry': row.get('industry', ''),
                        'market': row.get('market', ''),
                        'list_date': row.get('list_date', '')
                    }
                
                # 保存缓存
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'timestamp': time.time(),
                        'data': stock_info
                    }, f, ensure_ascii=False)
        except Exception as e:
            print(f"[优化器] 加载股票信息失败: {e}")
        
        return stock_info
    
    def _load_enhanced_concept_map(self) -> Dict[str, List[str]]:
        """加载增强版概念映射 - 使用多数据源融合"""
        concept_map = {}
        
        try:
            # 1. 获取同花顺概念板块
            print("[优化器] 加载同花顺概念板块...")
            ths_concepts = self._get_ths_concepts()
            concept_map.update(ths_concepts)
            
            # 2. 获取tushare概念板块
            print("[优化器] 加载tushare概念板块...")
            ts_concepts = self._get_ts_concepts()
            concept_map.update(ts_concepts)
            
            # 3. 构建行业-概念映射
            print("[优化器] 构建行业概念映射...")
            industry_concepts = self._build_industry_concepts()
            concept_map.update(industry_concepts)
            
            # 4. 添加自定义热点概念映射
            print("[优化器] 添加自定义概念映射...")
            custom_concepts = self._get_custom_concepts()
            concept_map.update(custom_concepts)
            
        except Exception as e:
            print(f"[优化器] 加载概念映射失败: {e}")
        
        print(f"[优化器] 成功加载 {len(concept_map)} 个概念")
        return concept_map
    
    def _get_ths_concepts(self) -> Dict[str, List[str]]:
        """获取同花顺概念 - 优化版"""
        concepts = {}
        
        try:
            # 获取同花顺概念列表
            ths_df = _call_api('ths_index', type='N', exchange='A')
            if ths_df is not None and not ths_df.empty:
                # 分批处理，避免频率限制
                batch_size = 20
                for i in range(0, min(200, len(ths_df)), batch_size):  # 增加到200个概念
                    batch = ths_df.iloc[i:i+batch_size]
                    
                    for _, row in batch.iterrows():
                        try:
                            # 获取成分股
                            members = _call_api('ths_member', ts_code=row['ts_code'])
                            if members is not None and not members.empty:
                                stocks = members['con_code'].tolist()
                                if stocks:
                                    concepts[row['name']] = stocks
                        except:
                            continue
                    
                    # 避免频率限制
                    time.sleep(0.5)
        except Exception as e:
            print(f"[优化器] 获取同花顺概念失败: {e}")
        
        return concepts
    
    def _get_ts_concepts(self) -> Dict[str, List[str]]:
        """获取tushare概念 - 优化版"""
        concepts = {}
        
        try:
            # 获取概念列表
            concept_list = concept()
            if concept_list is not None and not concept_list.empty:
                # 获取前50个活跃概念的成分股
                for _, row in concept_list.head(50).iterrows():
                    try:
                        detail = concept_detail(ts_code=row['ts_code'])
                        if detail is not None and not detail.empty:
                            stocks = detail['con_code'].tolist()
                            if stocks:
                                concepts[row['name']] = stocks
                    except:
                        continue
                    time.sleep(0.2)  # 避免频率限制
        except Exception as e:
            print(f"[优化器] 获取tushare概念失败: {e}")
        
        return concepts
    
    def _build_industry_concepts(self) -> Dict[str, List[str]]:
        """基于行业构建概念映射"""
        industry_map = {}
        
        # 定义行业-概念映射规则
        industry_concepts = {
            '电子': ['芯片', '半导体', '集成电路', '消费电子'],
            '计算机': ['人工智能', '云计算', '大数据', '网络安全'],
            '通信': ['5G', '通信设备', '物联网'],
            '汽车': ['新能源车', '智能驾驶', '汽车零部件'],
            '医药生物': ['创新药', '医疗器械', '生物医药', '中药'],
            '机械设备': ['工业机器人', '智能制造', '工程机械'],
            '新能源': ['光伏', '风电', '储能', '氢能源'],
            '军工': ['军工电子', '航空航天', '军工材料'],
            '传媒': ['游戏', '影视', '广告营销'],
            '食品饮料': ['白酒', '乳制品', '调味品']
        }
        
        # 根据股票行业分类构建概念
        for ts_code, info in self.stock_info.items():
            industry = info.get('industry', '')
            
            # 查找匹配的概念
            for ind_key, concepts in industry_concepts.items():
                if ind_key in industry:
                    for concept in concepts:
                        if concept not in industry_map:
                            industry_map[concept] = []
                        industry_map[concept].append(ts_code)
        
        return industry_map
    
    def _get_custom_concepts(self) -> Dict[str, List[str]]:
        """自定义热点概念映射 - 解决特定概念匹配问题"""
        custom = {
            '脑机接口': self._find_stocks_by_keywords(['脑机', '神经', 'BCI', '脑电', '意念控制']),
            '人工智能': self._find_stocks_by_keywords(['AI', '人工智能', '机器学习', '深度学习', 'GPT']),
            '新能源车': self._find_stocks_by_keywords(['新能源汽车', '电动车', '特斯拉', '比亚迪', '充电桩']),
            '光伏': self._find_stocks_by_keywords(['光伏', '太阳能', '硅片', '组件']),
            '半导体': self._find_stocks_by_keywords(['芯片', '半导体', '集成电路', 'IC设计']),
            '医药': self._find_stocks_by_keywords(['创新药', '医疗', '生物医药', '疫苗']),
            '消费': self._find_stocks_by_keywords(['白酒', '食品', '零售', '消费品']),
            '军工': self._find_stocks_by_keywords(['国防', '军工', '航天', '导弹'])
        }
        
        return {k: v for k, v in custom.items() if v}
    
    def _find_stocks_by_keywords(self, keywords: List[str]) -> List[str]:
        """根据关键词查找股票"""
        matched = set()
        
        for ts_code, info in self.stock_info.items():
            name = info.get('name', '')
            industry = info.get('industry', '')
            
            # 检查关键词匹配
            for keyword in keywords:
                if keyword in name or keyword in industry:
                    matched.add(ts_code)
                    break
        
        return list(matched)
    
    def _initialize_adaptive_weights(self) -> Dict[str, float]:
        """初始化自适应权重 - 根据市场环境动态调整"""
        # 默认权重
        return {
            'valuation': 0.25,
            'momentum': 0.25,
            'capital': 0.25,
            'technical': 0.15,
            'sentiment': 0.10
        }
    
    def smart_stock_filter(self, 
                          keyword: Optional[str] = None,
                          limit: int = 20,
                          date: Optional[str] = None) -> List[Dict[str, Any]]:
        """智能股票筛选 - 多策略融合"""
        print(f"[优化器] 开始智能股票筛选: keyword={keyword}, date={date}")
        
        results = []
        
        # 策略1: 基于概念的筛选
        if keyword:
            concept_stocks = self._filter_by_concept(keyword)
            results.extend(concept_stocks)
        
        # 策略2: 基于技术指标的筛选
        technical_stocks = self._filter_by_technical(date)
        results.extend(technical_stocks)
        
        # 策略3: 基于资金流的筛选
        capital_stocks = self._filter_by_capital(date)
        results.extend(capital_stocks)
        
        # 策略4: 基于市场热度的筛选  
        hot_stocks = self._filter_by_heat(date)
        results.extend(hot_stocks)
        
        # 去重并评分排序
        unique_stocks = self._merge_and_score(results)
        
        # 返回前N只
        return unique_stocks[:limit]
    
    def _filter_by_concept(self, keyword: str) -> List[Dict[str, Any]]:
        """基于概念筛选股票 - 多重匹配策略"""
        matched_stocks = set()
        
        # 1. 精确匹配概念
        for concept, stocks in self.concept_map.items():
            if keyword.lower() in concept.lower():
                matched_stocks.update(stocks)
        
        # 2. 模糊匹配（使用相似度）
        if not matched_stocks:
            similar_concepts = self._find_similar_concepts(keyword)
            for concept in similar_concepts:
                if concept in self.concept_map:
                    matched_stocks.update(self.concept_map[concept])
        
        # 3. 关键词直接匹配股票名称
        if not matched_stocks:
            matched_stocks = set(self._find_stocks_by_keywords([keyword]))
        
        # 获取股票详细信息
        results = []
        for ts_code in matched_stocks:
            if ts_code in self.stock_info:
                results.append({
                    'ts_code': ts_code,
                    'name': self.stock_info[ts_code]['name'],
                    'match_type': 'concept',
                    'score': 80  # 概念匹配基础分
                })
        
        return results
    
    def _find_similar_concepts(self, keyword: str) -> List[str]:
        """查找相似概念 - 使用同义词和关联词"""
        # 定义概念同义词映射
        synonyms = {
            '脑机': ['脑机接口', 'BCI', '神经接口', '脑电'],
            '人工智能': ['AI', '机器学习', '深度学习', '算法'],
            '新能源车': ['电动车', '新能源汽车', 'EV', '充电'],
            '芯片': ['半导体', '集成电路', 'IC', '晶圆'],
            '光伏': ['太阳能', '硅片', '光电'],
            '医药': ['医疗', '制药', '生物医药', '创新药']
        }
        
        similar = []
        keyword_lower = keyword.lower()
        
        # 查找同义词
        for key, values in synonyms.items():
            if keyword_lower == key or keyword_lower in values:
                similar.append(key)
                similar.extend(values)
        
        # 查找包含关键词的概念
        for concept in self.concept_map.keys():
            if keyword_lower in concept.lower() and concept not in similar:
                similar.append(concept)
        
        return similar
    
    def _filter_by_technical(self, date: Optional[str]) -> List[Dict[str, Any]]:
        """基于技术指标筛选"""
        results = []
        
        try:
            # 获取涨幅榜
            top_df = top_list(trade_date=date)
            if top_df is not None and not top_df.empty:
                for _, row in top_df.head(30).iterrows():
                    results.append({
                        'ts_code': row['ts_code'],
                        'name': row.get('name', ''),
                        'match_type': 'technical',
                        'score': 70 + min(row.get('pct_chg', 0), 10)  # 涨幅加分
                    })
        except:
            pass
        
        return results
    
    def _filter_by_capital(self, date: Optional[str]) -> List[Dict[str, Any]]:
        """基于资金流筛选"""
        results = []
        
        try:
            # 获取资金流数据
            flow_df = moneyflow_dc(trade_date=date)
            if flow_df is not None and not flow_df.empty:
                # 按净流入排序
                flow_df = flow_df.sort_values('net_amount', ascending=False)
                
                for _, row in flow_df.head(20).iterrows():
                    results.append({
                        'ts_code': row['ts_code'],
                        'name': self.stock_info.get(row['ts_code'], {}).get('name', ''),
                        'match_type': 'capital',
                        'score': 75  # 资金流入基础分
                    })
        except:
            pass
        
        return results
    
    def _filter_by_heat(self, date: Optional[str]) -> List[Dict[str, Any]]:
        """基于市场热度筛选"""
        results = []
        
        try:
            # 获取同花顺热门股票
            hot_df = ths_hot(trade_date=date)
            if hot_df is not None and not hot_df.empty:
                hot_stocks = hot_df[hot_df['data_type'] == '热股']
                
                for _, row in hot_stocks.head(20).iterrows():
                    results.append({
                        'ts_code': row['ts_code'],
                        'name': row.get('name', ''),
                        'match_type': 'heat',
                        'score': 85  # 热度基础分
                    })
        except:
            pass
        
        return results
    
    def _merge_and_score(self, stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """合并去重并综合评分"""
        # 按ts_code分组
        stock_map = {}
        
        for stock in stocks:
            ts_code = stock['ts_code']
            if ts_code not in stock_map:
                stock_map[ts_code] = {
                    'ts_code': ts_code,
                    'name': stock['name'],
                    'match_types': [],
                    'scores': [],
                    'final_score': 0
                }
            
            stock_map[ts_code]['match_types'].append(stock['match_type'])
            stock_map[ts_code]['scores'].append(stock['score'])
        
        # 计算综合评分
        for ts_code, data in stock_map.items():
            # 基础分：各维度得分的平均值
            base_score = sum(data['scores']) / len(data['scores'])
            
            # 加分项：多维度匹配
            multi_match_bonus = len(set(data['match_types'])) * 5
            
            # 最终得分
            data['final_score'] = min(base_score + multi_match_bonus, 100)
            data['match_types'] = list(set(data['match_types']))
        
        # 排序返回
        sorted_stocks = sorted(stock_map.values(), 
                              key=lambda x: x['final_score'], 
                              reverse=True)
        
        return sorted_stocks
    
    def smart_hotspot_filter(self, keyword: str) -> Dict[str, Any]:
        """智能热点筛选 - 多维度分析"""
        print(f"[优化器] 开始智能热点筛选: {keyword}")
        
        # 1. 获取相关股票
        stocks = self.smart_stock_filter(keyword=keyword, limit=50)
        
        if not stocks:
            return {
                'keyword': keyword,
                'status': 'no_match',
                'message': '未找到相关股票',
                'stocks': []
            }
        
        # 2. 分析热点强度
        hotspot_strength = self._analyze_hotspot_strength(stocks, keyword)
        
        # 3. 获取相关新闻
        related_news = self._get_related_news(keyword)
        
        # 4. 分析市场情绪
        market_sentiment = self._analyze_market_sentiment(stocks)
        
        return {
            'keyword': keyword,
            'status': 'success',
            'hotspot_strength': hotspot_strength,
            'top_stocks': stocks[:10],
            'related_news': related_news,
            'market_sentiment': market_sentiment,
            'recommendation': self._generate_recommendation(hotspot_strength, market_sentiment)
        }
    
    def _analyze_hotspot_strength(self, stocks: List[Dict], keyword: str) -> Dict[str, Any]:
        """分析热点强度"""
        # 统计匹配类型分布
        match_types = {}
        for stock in stocks:
            for mt in stock.get('match_types', []):
                match_types[mt] = match_types.get(mt, 0) + 1
        
        # 计算综合强度
        strength_score = min(len(stocks) * 2, 100)  # 相关股票数量
        
        if 'heat' in match_types:
            strength_score = min(strength_score + 20, 100)  # 有热度加分
        
        if 'capital' in match_types:
            strength_score = min(strength_score + 15, 100)  # 有资金流入加分
        
        return {
            'score': strength_score,
            'level': self._get_strength_level(strength_score),
            'match_distribution': match_types,
            'stock_count': len(stocks)
        }
    
    def _get_strength_level(self, score: int) -> str:
        """获取强度级别"""
        if score >= 80:
            return '极强'
        elif score >= 60:
            return '强'
        elif score >= 40:
            return '中等'
        elif score >= 20:
            return '弱'
        else:
            return '极弱'
    
    def _get_related_news(self, keyword: str) -> List[Dict[str, str]]:
        """获取相关新闻"""
        news_list = []
        
        try:
            # 获取新闻
            news_df = news(limit=50)
            if news_df is not None and not news_df.empty:
                for _, row in news_df.iterrows():
                    title = row.get('title', '')
                    content = row.get('content', '')
                    
                    # 检查关键词
                    if keyword in title or keyword in content:
                        news_list.append({
                            'title': title,
                            'content': content[:200] + '...',
                            'datetime': row.get('datetime', '')
                        })
                        
                        if len(news_list) >= 5:  # 最多5条
                            break
        except:
            pass
        
        return news_list
    
    def _analyze_market_sentiment(self, stocks: List[Dict]) -> Dict[str, Any]:
        """分析市场情绪"""
        # 基于股票得分分布判断情绪
        avg_score = sum(s['final_score'] for s in stocks) / len(stocks) if stocks else 0
        
        if avg_score >= 80:
            sentiment = '极度乐观'
        elif avg_score >= 65:
            sentiment = '乐观'
        elif avg_score >= 50:
            sentiment = '中性偏乐观'
        elif avg_score >= 35:
            sentiment = '中性偏谨慎'
        else:
            sentiment = '谨慎'
        
        return {
            'sentiment': sentiment,
            'score': avg_score,
            'stock_count': len(stocks)
        }
    
    def _generate_recommendation(self, strength: Dict, sentiment: Dict) -> str:
        """生成投资建议"""
        strength_score = strength['score']
        sentiment_score = sentiment['score']
        
        avg_score = (strength_score + sentiment_score) / 2
        
        if avg_score >= 70:
            return "强烈建议关注，热点强度高，市场情绪积极"
        elif avg_score >= 50:
            return "建议适度关注，有一定热度，可择机参与"
        elif avg_score >= 30:
            return "谨慎观察，热度一般，等待更多信号"
        else:
            return "暂不建议参与，热度较低，风险较大"
    
    def smart_market_filter(self, date: Optional[str] = None) -> Dict[str, Any]:
        """智能市场报告数据筛选"""
        print(f"[优化器] 开始智能市场数据筛选: {date}")
        
        # 1. 获取市场主线
        main_themes = self._identify_market_themes(date)
        
        # 2. 获取板块轮动
        sector_rotation = self._analyze_sector_rotation(date)
        
        # 3. 获取异动股票
        unusual_stocks = self._find_unusual_stocks(date)
        
        # 4. 获取重要公告
        important_anns = self._filter_important_announcements(date)
        
        # 5. 生成市场观点
        market_view = self._generate_market_view(main_themes, sector_rotation)
        
        return {
            'date': date or datetime.now().strftime('%Y-%m-%d'),
            'main_themes': main_themes,
            'sector_rotation': sector_rotation,
            'unusual_stocks': unusual_stocks,
            'important_announcements': important_anns,
            'market_view': market_view
        }
    
    def _identify_market_themes(self, date: Optional[str]) -> List[Dict[str, Any]]:
        """识别市场主线"""
        themes = []
        
        # 统计涨停板主题
        try:
            limit_df = limit_list_d(trade_date=date, limit_type='U')
            if limit_df is not None and not limit_df.empty:
                # 按概念统计
                concept_count = {}
                
                for _, row in limit_df.iterrows():
                    ts_code = row['ts_code']
                    # 查找股票所属概念
                    for concept, stocks in self.concept_map.items():
                        if ts_code in stocks:
                            concept_count[concept] = concept_count.get(concept, 0) + 1
                
                # 排序获取主题
                sorted_concepts = sorted(concept_count.items(), 
                                        key=lambda x: x[1], 
                                        reverse=True)
                
                for concept, count in sorted_concepts[:5]:  # 前5个主题
                    themes.append({
                        'theme': concept,
                        'strength': count,
                        'type': 'limit_up_theme'
                    })
        except:
            pass
        
        return themes
    
    def _analyze_sector_rotation(self, date: Optional[str]) -> List[Dict[str, Any]]:
        """分析板块轮动"""
        rotations = []
        
        # 这里可以添加更复杂的板块轮动分析逻辑
        # 暂时返回简化版本
        
        return rotations
    
    def _find_unusual_stocks(self, date: Optional[str]) -> List[Dict[str, Any]]:
        """查找异动股票"""
        unusual = []
        
        try:
            # 获取龙虎榜数据
            top_inst_df = _call_api('top_inst', trade_date=date)
            if top_inst_df is not None and not top_inst_df.empty:
                for _, row in top_inst_df.head(10).iterrows():
                    unusual.append({
                        'ts_code': row['ts_code'],
                        'name': row.get('name', ''),
                        'reason': row.get('reason', '异动'),
                        'change': row.get('pct_change', 0)
                    })
        except:
            pass
        
        return unusual
    
    def _filter_important_announcements(self, date: Optional[str]) -> List[Dict[str, str]]:
        """筛选重要公告"""
        important = []
        
        try:
            # 获取公告
            anns_df = anns(start_date=date, end_date=date)
            if anns_df is not None and not anns_df.empty:
                # 重要关键词
                keywords = ['重大', '收购', '重组', '合并', '投资', '合作', '中标']
                
                for _, row in anns_df.iterrows():
                    title = row.get('title', '')
                    # 检查是否包含重要关键词
                    if any(kw in title for kw in keywords):
                        important.append({
                            'ts_code': row['ts_code'],
                            'title': title,
                            'ann_date': row.get('ann_date', '')
                        })
                        
                        if len(important) >= 10:  # 最多10条
                            break
        except:
            pass
        
        return important
    
    def _generate_market_view(self, themes: List[Dict], rotation: List[Dict]) -> str:
        """生成市场观点"""
        if not themes:
            return "市场缺乏明确主线，建议谨慎观察"
        
        main_theme = themes[0]['theme'] if themes else "均衡配置"
        
        return f"市场主线围绕{main_theme}展开，建议重点关注相关板块机会"


# 全局实例
data_filter_optimizer = DataFilterOptimizer()