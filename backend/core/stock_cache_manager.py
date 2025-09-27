"""
股票数据缓存管理器
定时从TuShare获取完整股票列表并缓存到本地
"""
import os
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from .tushare_client import stock_basic


class StockCacheManager:
    """股票数据缓存管理器"""
    
    def __init__(self):
        self.cache_dir = os.path.join(os.path.dirname(__file__), '../.cache')
        os.makedirs(self.cache_dir, exist_ok=True)
        self.stock_list_file = os.path.join(self.cache_dir, 'stock_list_cache.json')
        self.alias_file = os.path.join(os.path.dirname(__file__), 'symbol_map.json')
        
    def _load_aliases(self) -> Dict[str, str]:
        """加载别名映射"""
        try:
            with open(self.alias_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            aliases = {}
            for item in data:
                for alias in item.get('aliases', []):
                    aliases[alias] = item['ts_code']
            return aliases
        except Exception as e:
            print(f"[缓存] 别名加载失败: {e}")
            return {}
    
    def _is_cache_fresh(self) -> bool:
        """检查缓存是否新鲜（24小时内）"""
        try:
            if not os.path.exists(self.stock_list_file):
                return False
                
            stat = os.stat(self.stock_list_file)
            cache_time = datetime.fromtimestamp(stat.st_mtime)
            return datetime.now() - cache_time < timedelta(hours=24)
        except Exception:
            return False
    
    def update_stock_cache(self, force: bool = False) -> bool:
        """更新股票缓存"""
        if not force and self._is_cache_fresh():
            print("[缓存] 股票列表缓存仍然新鲜，跳过更新")
            return True
            
        print("[缓存] 开始更新股票列表缓存...")
        try:
            # 从TuShare获取完整股票列表
            df = stock_basic(force=True)
            if df is None or df.empty:
                print("[缓存] 无法获取股票数据")
                return False
            
            # 转换为字典列表格式，保持所有字段
            stock_list = []
            for _, row in df.iterrows():
                stock_info = row.to_dict()
                # 处理NaN值
                for key, value in stock_info.items():
                    if pd.isna(value):
                        stock_info[key] = None
                stock_list.append(stock_info)
            
            # 保存到缓存文件
            cache_data = {
                'update_time': datetime.now().isoformat(),
                'total_count': len(stock_list),
                'stocks': stock_list
            }
            
            with open(self.stock_list_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            print(f"[缓存] 股票列表缓存更新完成，共{len(stock_list)}只股票")
            return True
            
        except Exception as e:
            print(f"[缓存] 股票列表缓存更新失败: {e}")
            return False
    
    def get_stock_by_name(self, name_keyword: str) -> Optional[Dict]:
        """通过名称搜索股票（优先使用缓存）"""
        # 确保缓存是最新的
        if not self.update_stock_cache():
            print("[缓存] 缓存更新失败，回退到直接API调用")
            return self._fallback_search(name_keyword)
        
        try:
            # 加载缓存数据
            with open(self.stock_list_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            stock_list = cache_data.get('stocks', [])
            aliases = self._load_aliases()
            
            kw = str(name_keyword).strip()
            candidates = []
            
            # 1. 检查别名映射
            if kw in aliases:
                target_ts_code = aliases[kw]
                for stock in stock_list:
                    if stock.get('ts_code') == target_ts_code:
                        candidates.append((stock, 0))  # 别名匹配，优先级最高
                        break
            
            # 2. 精确名称匹配
            if not candidates:
                for stock in stock_list:
                    stock_name = stock.get('name', '')
                    if stock_name == kw:
                        candidates.append((stock, 1))
            
            # 3. 部分名称匹配
            if not candidates:
                for stock in stock_list:
                    stock_name = stock.get('name', '')
                    if kw in stock_name or stock_name in kw:
                        name_diff = abs(len(stock_name) - len(kw))
                        candidates.append((stock, 2 + name_diff))
            
            if not candidates:
                print(f"[缓存] 未找到匹配的股票: {kw}")
                return None
            
            # 按优先级排序，返回最佳匹配
            candidates.sort(key=lambda x: x[1])
            best_match = candidates[0][0]
            
            # 添加兼容性字段
            if 'list_status' not in best_match:
                best_match['list_status'] = 'L'
            
            print(f"[缓存] 找到股票: {best_match.get('name')} ({best_match.get('ts_code')})")
            return best_match
            
        except Exception as e:
            print(f"[缓存] 缓存搜索失败: {e}，回退到直接API调用")
            return self._fallback_search(name_keyword)
    
    def _fallback_search(self, name_keyword: str) -> Optional[Dict]:
        """回退到直接API搜索"""
        try:
            df = stock_basic(force=False)
            if df is None or df.empty:
                return None
                
            kw = str(name_keyword).strip()
            name_col = pd.Series(df["name"], dtype="string")
            name_mask = name_col.str.contains(kw, case=False, regex=False, na=False)
            hit = df[name_mask]
            
            if hit.empty:
                return None
                
            result = hit.iloc[0].to_dict()
            # 处理NaN值
            for key, value in result.items():
                if pd.isna(value):
                    result[key] = None
            
            if 'list_status' not in result:
                result['list_status'] = 'L'
                
            return result
            
        except Exception as e:
            print(f"[缓存] 回退搜索也失败: {e}")
            return None
    
    def get_cache_info(self) -> Dict:
        """获取缓存信息"""
        try:
            if not os.path.exists(self.stock_list_file):
                return {"status": "no_cache", "message": "缓存文件不存在"}
            
            with open(self.stock_list_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            update_time = cache_data.get('update_time')
            total_count = cache_data.get('total_count', 0)
            
            return {
                "status": "ok",
                "update_time": update_time,
                "total_count": total_count,
                "is_fresh": self._is_cache_fresh()
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}


# 全局实例
_cache_manager = None

def get_cache_manager() -> StockCacheManager:
    """获取缓存管理器单例"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = StockCacheManager()
    return _cache_manager