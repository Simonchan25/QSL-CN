"""
概念库管理器 - 精准匹配概念成分股
"""
import pandas as pd
from typing import List, Dict, Set
from .tushare_client import _call_api
from .mock_data import is_mock_mode
import json
import os
from datetime import datetime, timedelta

class ConceptManager:
    """概念股管理器"""
    
    def __init__(self):
        self.cache_path = os.path.join(os.path.dirname(__file__), '../.cache/concepts.json')
        self.cache_ttl = 86400  # 概念库缓存1天
        self._concept_map = None
        self._load_cache()
    
    def _load_cache(self):
        """加载缓存的概念库"""
        try:
            if os.path.exists(self.cache_path):
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                    if datetime.now().timestamp() - cache.get('timestamp', 0) < self.cache_ttl:
                        self._concept_map = cache.get('data', {})
                        print(f"[概念库] 加载缓存: {len(self._concept_map)}个概念")
        except Exception as e:
            print(f"[概念库] 缓存加载失败: {e}")
    
    def _save_cache(self):
        """保存概念库到缓存"""
        try:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': datetime.now().timestamp(),
                    'data': self._concept_map
                }, f, ensure_ascii=False, indent=2)
            print(f"[概念库] 缓存已保存")
        except Exception as e:
            print(f"[概念库] 缓存保存失败: {e}")
    
    def refresh_concepts(self) -> Dict[str, List[str]]:
        """
        刷新概念库
        返回: {概念名: [股票代码列表]}
        """
        if is_mock_mode():
            # 模拟数据模式
            self._concept_map = self._get_mock_concepts()
            return self._concept_map
        
        try:
            # 获取概念列表
            concepts_df = _call_api('concept')
            if concepts_df.empty:
                return self._get_mock_concepts()
            
            concept_map = {}
            
            # 获取每个概念的成分股
            for _, row in concepts_df.iterrows():
                concept_code = row.get('code')
                concept_name = row.get('name')
                
                if not concept_code or not concept_name:
                    continue
                
                try:
                    # 获取概念成分股
                    members_df = _call_api('concept_detail', id=concept_code)
                    if not members_df.empty:
                        stock_list = members_df['ts_code'].tolist()
                        concept_map[concept_name] = stock_list
                        print(f"[概念库] {concept_name}: {len(stock_list)}只成分股")
                except Exception as e:
                    print(f"[概念库] 获取{concept_name}成分股失败: {e}")
            
            # 获取同花顺概念
            try:
                ths_concepts = _call_api('ths_index')
                for _, row in ths_concepts.iterrows():
                    concept_name = row.get('name')
                    if concept_name and '概念' in concept_name:
                        # 获取同花顺概念成分股
                        try:
                            ths_members = _call_api('ths_member', ts_code=row.get('ts_code'))
                            if not ths_members.empty:
                                stock_list = ths_members['code'].tolist()
                                # 转换为ts_code格式
                                stock_list = [self._to_ts_code(code) for code in stock_list]
                                concept_map[concept_name] = stock_list
                        except:
                            pass
            except:
                pass
            
            self._concept_map = concept_map
            self._save_cache()
            return concept_map
            
        except Exception as e:
            print(f"[概念库] 刷新失败，使用模拟数据: {e}")
            return self._get_mock_concepts()
    
    def _to_ts_code(self, code: str) -> str:
        """转换股票代码为ts_code格式"""
        if '.' in code:
            return code
        if code.startswith('6'):
            return f"{code}.SH"
        else:
            return f"{code}.SZ"
    
    def _get_mock_concepts(self) -> Dict[str, List[str]]:
        """获取模拟概念库"""
        return {
            "人工智能": ["002230.SZ", "002410.SZ", "000977.SZ", "300454.SZ"],
            "脑机接口": ["300775.SZ", "688066.SH", "002382.SZ"],
            "新能源车": ["300750.SZ", "002594.SZ", "002460.SZ"],
            "半导体": ["002371.SZ", "688981.SH", "688012.SH"],
            "白酒": ["600519.SH", "000858.SZ", "000568.SZ"],
            "医药生物": ["002382.SZ", "300122.SZ", "000538.SZ"],
            "游戏": ["002555.SZ", "002624.SZ", "002558.SZ"],
            "5G": ["000063.SZ", "000733.SZ", "002396.SZ"],
            "区块链": ["002537.SZ", "300468.SZ", "002657.SZ"],
            "元宇宙": ["002624.SZ", "300031.SZ", "002555.SZ"],
            "ChatGPT": ["002230.SZ", "300454.SZ", "002410.SZ"],
            "算力": ["000977.SZ", "002368.SZ", "603019.SH"],
            "光伏": ["601012.SH", "002129.SZ", "300274.SZ"],
            "储能": ["300750.SZ", "002074.SZ", "002709.SZ"],
            "氢能源": ["000723.SZ", "002639.SZ", "300228.SZ"]
        }
    
    def find_concept_stocks(self, keyword: str) -> Dict[str, List[str]]:
        """
        根据关键词查找相关概念及其成分股
        返回: {匹配的概念名: [股票代码列表]}
        """
        if not self._concept_map:
            self.refresh_concepts()
        
        matched = {}
        keyword_lower = keyword.lower()
        
        # 精确匹配和模糊匹配
        for concept_name, stocks in self._concept_map.items():
            # 精确匹配
            if keyword in concept_name or concept_name in keyword:
                matched[concept_name] = stocks
            # 模糊匹配（关键词相似）
            elif self._is_similar(keyword_lower, concept_name.lower()):
                matched[concept_name] = stocks
        
        return matched
    
    def _is_similar(self, keyword: str, concept: str) -> bool:
        """判断关键词和概念是否相似"""
        # 简单的相似度判断
        similar_map = {
            "ai": ["人工智能", "智能", "机器学习", "深度学习"],
            "脑机": ["脑机接口", "bci", "神经接口"],
            "新能源": ["新能源车", "电动车", "锂电池", "储能"],
            "芯片": ["半导体", "集成电路", "芯片"],
            "酒": ["白酒", "啤酒", "葡萄酒"],
            "医药": ["医药生物", "生物医药", "创新药", "中药"],
            "游戏": ["游戏", "手游", "网游", "电竞"],
            "5g": ["5g", "通信", "基站"],
            "元宇宙": ["元宇宙", "vr", "ar", "虚拟现实"],
            "gpt": ["chatgpt", "大模型", "生成式ai"],
        }
        
        for key, values in similar_map.items():
            if key in keyword:
                for v in values:
                    if v in concept:
                        return True
        
        return False
    
    def extract_concepts_from_news(self, news_text: str) -> Set[str]:
        """
        从新闻文本中提取概念关键词
        返回: 概念关键词集合
        """
        concepts = set()
        
        if not self._concept_map:
            self.refresh_concepts()
        
        # 遍历所有概念，查找在新闻中出现的
        for concept_name in self._concept_map.keys():
            if concept_name in news_text:
                concepts.add(concept_name)
        
        # 额外的关键词提取规则
        keywords_map = {
            "人工智能": ["AI", "人工智能", "机器学习", "深度学习", "神经网络"],
            "脑机接口": ["脑机", "BCI", "脑电", "神经接口", "马斯克"],
            "新能源车": ["新能源", "电动车", "特斯拉", "比亚迪", "理想", "蔚来"],
            "半导体": ["芯片", "半导体", "晶圆", "光刻", "封测"],
            "元宇宙": ["元宇宙", "VR", "AR", "虚拟现实", "增强现实"],
            "储能": ["储能", "电池", "锂电", "钠电池"],
        }
        
        for concept, keywords in keywords_map.items():
            for kw in keywords:
                if kw in news_text:
                    concepts.add(concept)
                    break
        
        return concepts
    
    def get_hot_concepts(self, limit: int = 10) -> List[Dict]:
        """
        获取热门概念
        返回: [{name: 概念名, stock_count: 成分股数量}]
        """
        if not self._concept_map:
            self.refresh_concepts()
        
        hot_concepts = []
        for name, stocks in self._concept_map.items():
            hot_concepts.append({
                'name': name,
                'stock_count': len(stocks)
            })
        
        # 按成分股数量排序
        hot_concepts.sort(key=lambda x: x['stock_count'], reverse=True)
        return hot_concepts[:limit]

# 单例模式
_concept_manager = None

def get_concept_manager() -> ConceptManager:
    """获取概念管理器单例"""
    global _concept_manager
    if _concept_manager is None:
        _concept_manager = ConceptManager()
    return _concept_manager