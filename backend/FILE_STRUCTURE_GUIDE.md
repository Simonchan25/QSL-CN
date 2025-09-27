# 文件结构和功能说明

## 核心模块功能划分

### 数据获取层
- **tushare_client.py** - Tushare API封装，所有数据获取的基础
- **advanced_data_client.py** - 高级数据客户端（5000积分特有功能）
- **cache_config.py** - 缓存配置（已优化TTL时间）

### 概念管理
- **concept_manager.py** - 概念股票映射管理（已优化映射规则）
- ~~concept_detail相关功能已整合到concept_manager~~

### 股票筛选
- **stock_picker.py** - 主要股票筛选逻辑
- **data_filter_optimizer.py** - 新的智能筛选优化器（推荐使用）

### 热点分析
- **enhanced_hotspot_analyzer.py** - 增强版热点分析器（推荐使用）
- **hotspot.py** - 旧版热点分析（建议废弃）
- **ths_sector_analysis.py** - 同花顺板块分析

### 市场分析
- **market.py** - 市场概况基础功能
- **market_ai_analyzer.py** - AI增强的市场分析
- **analyze.py** - 基础分析功能
- **practical_analyzer.py** - 实用分析工具

### 报告生成
- **professional_report_generator_v2.py** - 专业报告生成器V2（当前版本）
- **insight_builder.py** - 洞察构建器

### 辅助功能
- **trading_date_helper.py** - 交易日期辅助
- **trading_plan.py** - 交易计划生成
- **indicators.py** - 技术指标计算
- **fundamentals.py** - 基本面分析
- **sentiment.py** - 情绪分析
- **news.py** - 新闻处理
- **macro.py** - 宏观数据

## 推荐使用方式

### 1. 股票筛选
```python
# 使用新的优化器（推荐）
from core.data_filter_optimizer import data_filter_optimizer
stocks = data_filter_optimizer.smart_stock_filter(keyword="芯片", limit=20)

# 或使用原有筛选器
from core.stock_picker import get_top_picks
picks = get_top_picks(limit=10)
```

### 2. 热点分析
```python
# 使用增强版分析器
from core.enhanced_hotspot_analyzer import enhanced_hotspot_analyzer
result = enhanced_hotspot_analyzer.comprehensive_hotspot_analysis("新能源")

# 或使用优化器的热点分析
from core.data_filter_optimizer import data_filter_optimizer
hotspot = data_filter_optimizer.smart_hotspot_filter("储能")
```

### 3. 市场报告
```python
from core.professional_report_generator_v2 import ProfessionalReportGeneratorV2
generator = ProfessionalReportGeneratorV2()

# 生成早报
morning_report = generator.generate_professional_morning_report()

# 生成综合市场报告
market_report = generator.generate_comprehensive_market_report()
```

## 待清理文件（建议）

以下文件功能重复，建议清理：
1. **hotspot.py** - 功能已被enhanced_hotspot_analyzer.py替代
2. 考虑合并analyze.py和practical_analyzer.py

## 数据准确性保证

### 已优化的部分
1. **概念映射更精确** - concept_manager.py中的映射规则已优化
2. **缓存时间缩短** - 概念数据从24小时缩短到3-6小时
3. **多源数据融合** - data_filter_optimizer.py支持多数据源

### 确保数据实时性
1. 使用`force=True`参数强制刷新：
```python
df = daily_basic(trade_date='20241219', force=True)
```

2. 交易时间内自动缩短缓存时间（已实现）

3. 关键数据使用短缓存：
- 实时数据: 2-10分钟
- 热点数据: 15分钟
- 概念数据: 3-6小时

## 最佳实践

1. **优先使用优化器**
   - data_filter_optimizer提供了最完善的筛选和容错机制

2. **定期清理缓存**
```bash
rm -rf ~/.qsl_cache/*
rm -rf backend/.cache/*
```

3. **监控API调用**
   - 5000积分每分钟500次限制
   - 已内置0.12秒延迟

4. **数据验证**
   - 使用test_accuracy.py定期验证数据准确性
   - 使用quick_test.py快速检查

## 问题排查

如果数据不准确：
1. 检查缓存是否过期
2. 使用force=True强制刷新
3. 查看概念映射是否正确
4. 确认API权限和积分