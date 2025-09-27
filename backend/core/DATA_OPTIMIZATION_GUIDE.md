# 数据筛选优化方案说明

## 问题诊断

### 核心问题
1. **数据不匹配**: 概念映射不准确，导致无法精准找到相关股票
2. **API限制**: 频繁调用导致超出频率限制
3. **筛选过于严格**: 单一数据源失败导致整体失败

## 优化方案

### 1. 多源数据融合 (已实现)
```python
from backend.core.data_filter_optimizer import data_filter_optimizer

# 智能股票筛选 - 融合多个数据源
stocks = data_filter_optimizer.smart_stock_filter(
    keyword="脑机",  # 支持模糊匹配
    limit=20,
    date="20241219"
)
```

**特性**:
- 融合同花顺(ths_index/ths_member)和tushare(concept/concept_detail)概念数据
- 支持同义词和关联词匹配
- 多策略并行筛选（概念、技术、资金、热度）
- 智能评分排序

### 2. 概念映射优化 (已实现)

**改进的概念映射策略**:
```python
# 自定义概念映射表
concept_mappings = {
    "脑机": ["脑机接口", "BCI", "神经接口", "脑电"],
    "人工智能": ["AI", "机器学习", "深度学习", "算法"],
    "新能源车": ["电动车", "新能源汽车", "EV", "充电"],
    # ... 更多映射
}
```

**行业-概念自动映射**:
- 根据股票行业属性自动归类到相关概念
- 减少手动维护概念的工作量

### 3. 降级容错机制 (已实现)

```python
# 热点筛选 - 带容错机制
hotspot = data_filter_optimizer.smart_hotspot_filter(
    keyword="新能源"
)

# 即使部分数据源失败，仍能返回有效结果
# 返回结构包含:
# - status: 状态（success/no_match）
# - top_stocks: 相关股票
# - hotspot_strength: 热点强度评估
# - recommendation: 投资建议
```

### 4. 市场报告数据优化 (已实现)

```python
# 智能市场数据筛选
market_data = data_filter_optimizer.smart_market_filter(
    date="20241219"
)

# 返回结构化的市场数据:
# - main_themes: 市场主线
# - sector_rotation: 板块轮动
# - unusual_stocks: 异动股票
# - important_announcements: 重要公告
```

## 使用指南

### 快速开始

1. **导入优化器**:
```python
from backend.core.data_filter_optimizer import data_filter_optimizer
```

2. **股票筛选**:
```python
# 基于概念筛选
stocks = data_filter_optimizer.smart_stock_filter(keyword="芯片")

# 基于多条件筛选
stocks = data_filter_optimizer.smart_stock_filter(
    keyword="光伏",
    limit=30,
    date="20241219"
)
```

3. **热点分析**:
```python
# 分析特定热点
hotspot = data_filter_optimizer.smart_hotspot_filter("储能")

# 获取热点强度
strength = hotspot['hotspot_strength']['score']  # 0-100分

# 获取投资建议
advice = hotspot['recommendation']
```

4. **市场分析**:
```python
# 获取市场全景数据
market = data_filter_optimizer.smart_market_filter()

# 识别市场主题
themes = market['main_themes']

# 查找异动股票
unusual = market['unusual_stocks']
```

### 集成到现有系统

#### 1. 更新股票筛选模块
```python
# backend/core/stock_picker.py
from .data_filter_optimizer import data_filter_optimizer

def get_top_picks(trade_date: str = None, limit: int = 10):
    # 使用优化器进行筛选
    stocks = data_filter_optimizer.smart_stock_filter(
        limit=limit,
        date=trade_date
    )

    # 转换为原有格式
    picks = []
    for stock in stocks:
        picks.append({
            'ts_code': stock['ts_code'],
            'name': stock['name'],
            'score': stock['final_score'],
            # ...
        })

    return picks
```

#### 2. 更新热点分析模块
```python
# backend/core/enhanced_hotspot_analyzer.py
from .data_filter_optimizer import data_filter_optimizer

class EnhancedHotspotAnalyzer:
    def comprehensive_hotspot_analysis(self, keyword: str):
        # 使用优化器
        result = data_filter_optimizer.smart_hotspot_filter(keyword)

        # 增强结果
        return {
            'keyword': keyword,
            'comprehensive_score': result['hotspot_strength']['score'],
            'top_stocks': result['top_stocks'],
            'investment_advice': {
                'recommendation_level': result['recommendation'],
                # ...
            }
        }
```

#### 3. 更新报告生成模块
```python
# backend/core/professional_report_generator_v2.py
from .data_filter_optimizer import data_filter_optimizer

def _get_yesterday_hot_sectors(self, date: str):
    # 使用优化器获取市场主题
    market_data = data_filter_optimizer.smart_market_filter(date)

    sectors = []
    for theme in market_data['main_themes']:
        # 获取主题相关股票
        stocks = data_filter_optimizer.smart_stock_filter(
            keyword=theme['theme'],
            limit=5
        )

        sectors.append({
            'sector': theme['theme'],
            'sector_performance': f"+{theme['strength']}%",
            'leading_stocks': stocks[:3],
            # ...
        })

    return sectors
```

## 性能优化建议

### 1. 缓存策略
- 股票基础信息缓存24小时
- 概念映射缓存24小时
- 实时数据缓存10分钟

### 2. 并发控制
- 使用ThreadPoolExecutor控制并发数
- API调用间隔控制在0.12秒（5000积分权限）

### 3. 数据量控制
- 概念数量限制在200个以内
- 每个概念最多获取前50只活跃股票
- 批量处理时每批20个请求

## 监控与调试

### 日志输出
```python
# 查看优化器日志
[优化器] 开始智能股票筛选: keyword=芯片
[优化器] 加载同花顺概念板块...
[优化器] 加载tushare概念板块...
[优化器] 成功加载 250 个概念
```

### 错误处理
```python
try:
    stocks = data_filter_optimizer.smart_stock_filter("test")
except Exception as e:
    print(f"筛选失败: {e}")
    # 使用默认数据或缓存数据
```

## 常见问题

### Q1: 概念匹配不准确怎么办？
**A**: 可以在`_get_custom_concepts()`方法中添加自定义映射规则

### Q2: API频率限制怎么处理？
**A**: 优化器已内置频率控制，如仍遇到限制，可调整`time.sleep()`参数

### Q3: 数据为空怎么办？
**A**: 优化器会自动尝试多个数据源，如全部失败会返回空列表而不是报错

### Q4: 如何添加新的筛选维度？
**A**: 在`smart_stock_filter()`中添加新的筛选策略方法，并在`_merge_and_score()`中调整权重

## 后续优化方向

1. **机器学习增强**
   - 使用历史数据训练概念分类模型
   - 动态调整筛选权重

2. **实时数据集成**
   - 接入Level2数据源
   - 实时监控异动

3. **智能推荐系统**
   - 基于用户偏好推荐股票
   - 个性化热点推送

4. **数据质量监控**
   - 自动检测数据异常
   - 数据完整性验证

## 联系支持

如有问题或建议，请联系技术支持团队。