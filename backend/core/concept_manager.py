"""
概念库管理器 - 纯真实数据版本
"""
import pandas as pd
from typing import List, Dict, Set
from .tushare_client import _call_api
import json
import os
import time
from datetime import datetime, timedelta

class ConceptManager:
    """概念股管理器 - 使用真实数据"""
    
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
            print(f"[概念库] 加载缓存失败: {e}")
    
    def get_all_concepts(self) -> Dict[str, List[str]]:
        """
        获取所有概念及其成分股
        返回: {概念名: [股票代码列表]}
        """
        if self._concept_map is not None:
            return self._concept_map
            
        return self._refresh_concepts()
    
    def _refresh_concepts(self) -> Dict[str, List[str]]:
        """刷新概念库 - 使用同花顺API避免频率限制"""
        try:
            # 使用ths_index获取同花顺概念板块列表，type='N'表示概念指数
            concepts_df = _call_api('ths_index', type='N', exchange='A')
            if concepts_df.empty:
                print("[概念库] 同花顺概念数据为空")
                return {}

            concept_map = {}

            print(f"[概念库] 获取到 {len(concepts_df)} 个同花顺概念，开始获取成分股...")

            # 获取每个概念的成分股 - 使用ths_member API
            for i, (_, row) in enumerate(concepts_df.iterrows()):
                ts_code = row['ts_code']  # 板块指数代码
                concept_name = row['name']  # 概念名称

                # 限制处理数量，避免API频率问题（处理前200个概念以覆盖更多热点）
                if i >= 200:
                    print(f"[概念库] 为避免API频率限制，暂时只处理前200个概念")
                    break

                # 每20个概念暂停0.5秒，避免频率限制
                if i > 0 and i % 20 == 0:
                    time.sleep(0.5)

                try:
                    # 使用ths_member获取该概念板块的成分股
                    detail_df = _call_api('ths_member', ts_code=ts_code)
                    if not detail_df.empty:
                        stocks = []
                        for _, stock_row in detail_df.iterrows():
                            con_code = stock_row.get('con_code', '')  # 注意：ths_member返回的是con_code
                            if con_code:
                                stocks.append(con_code)

                        if stocks:
                            concept_map[concept_name] = stocks
                            print(f"[概念库] {concept_name}: {len(stocks)}只股票")

                except Exception as e:
                    print(f"[概念库] 获取概念 {concept_name} 成分股失败: {e}")
                    # 如果是频率限制错误，等待一段时间
                    if "频率限制" in str(e) or "frequency" in str(e).lower():
                        print("[概念库] 遇到频率限制，等待60秒后继续...")
                        time.sleep(60)
                    continue

            # 保存到缓存
            self._save_cache(concept_map)
            self._concept_map = concept_map

            print(f"[概念库] 同花顺API刷新成功: {len(concept_map)}个概念")
            return concept_map

        except Exception as e:
            print(f"[概念库] 刷新失败: {e}")
            return {}
    
    def _to_ts_code(self, code: str) -> str:
        """转换股票代码为ts_code格式"""
        if '.' in code:
            return code
        elif code.startswith('6'):
            return f"{code}.SH"
        else:
            return f"{code}.SZ"
    
    def _save_cache(self, concept_map: Dict[str, List[str]]):
        """保存概念库到缓存"""
        try:
            cache_data = {
                'timestamp': datetime.now().timestamp(),
                'data': concept_map
            }
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[概念库] 保存缓存失败: {e}")
    
    def find_stocks_by_concept(self, concept_keyword: str) -> List[str]:
        """根据概念关键词查找股票 - 改进版精确匹配 + 按需加载"""
        concept_map = self.get_all_concepts()
        matched_stocks = []
        keyword_lower = concept_keyword.lower()

        # 定义概念映射规则 - 更精确的映射
        concept_mappings = {
            "脑机": ["脑机接口"],  # 精确映射
            "脑机接口": ["脑机接口"],
            "新能源车": ["新能源汽车", "特斯拉", "充电桩", "锂电池"],
            "芯片": ["芯片概念", "集成电路", "半导体", "芯片设计"],
            "人工智能": ["人工智能", "AI", "机器学习", "AIGC"],
            "区块链": ["区块链", "数字货币", "NFT"],
            "光伏": ["光伏", "太阳能", "HJT电池"],
            "储能": ["储能", "储能技术", "电化学储能"]
        }

        # 1. 首先尝试精确映射
        target_concepts = concept_mappings.get(keyword_lower, [keyword_lower])

        # 2. 匹配概念名称
        for concept_name, stocks in concept_map.items():
            concept_name_lower = concept_name.lower()

            # 精确匹配或目标概念匹配
            if any(target in concept_name_lower for target in target_concepts):
                matched_stocks.extend(stocks)
                continue

        # 3. 如果没有匹配到，尝试按需加载该具体概念
        if not matched_stocks:
            print(f"[概念库] 未在缓存中找到 {concept_keyword}，尝试按需加载...")
            on_demand_stocks = self._load_concept_on_demand(target_concepts)
            if on_demand_stocks:
                matched_stocks.extend(on_demand_stocks)

        # 去重并返回
        return list(set(matched_stocks))
    
    def _load_concept_on_demand(self, target_concept_names: List[str]) -> List[str]:
        """按需加载特定概念的成分股"""
        try:
            # 获取所有同花顺概念
            concepts_df = _call_api('ths_index', type='N', exchange='A')
            if concepts_df.empty:
                return []

            matched_stocks = []

            # 查找目标概念
            for target_name in target_concept_names:
                matching_concepts = concepts_df[concepts_df['name'].str.contains(target_name, case=False, na=False)]

                for _, row in matching_concepts.iterrows():
                    ts_code = row['ts_code']
                    concept_name = row['name']

                    try:
                        # 获取该概念的成分股
                        detail_df = _call_api('ths_member', ts_code=ts_code)
                        if not detail_df.empty:
                            stocks = detail_df['con_code'].tolist()
                            matched_stocks.extend(stocks)
                            print(f"[概念库] 按需加载 {concept_name}: {len(stocks)}只股票")

                            # 更新到缓存
                            if self._concept_map is None:
                                self._concept_map = {}
                            self._concept_map[concept_name] = stocks

                    except Exception as e:
                        print(f"[概念库] 按需加载 {concept_name} 失败: {e}")
                        continue

            # 保存更新后的缓存
            if matched_stocks and self._concept_map:
                self._save_cache(self._concept_map)

            return matched_stocks

        except Exception as e:
            print(f"[概念库] 按需加载失败: {e}")
            return []

    def get_stock_concepts(self, ts_code: str) -> List[str]:
        """获取股票所属的概念"""
        concept_map = self.get_all_concepts()
        concepts = []
        
        for concept_name, stocks in concept_map.items():
            if ts_code in stocks:
                concepts.append(concept_name)
        
        return concepts

    def search_concepts(self, keyword: str) -> List[str]:
        """搜索包含关键词的概念，返回概念名称列表"""
        concept_map = self.get_all_concepts()
        matched_concepts = []
        keyword_lower = keyword.lower()

        for concept_name in concept_map.keys():
            if keyword_lower in concept_name.lower():
                matched_concepts.append(concept_name)

        return matched_concepts

# 全局实例
_concept_manager = None

def get_concept_manager() -> ConceptManager:
    """获取全局概念管理器实例"""
    global _concept_manager
    if _concept_manager is None:
        _concept_manager = ConceptManager()
    return _concept_manager