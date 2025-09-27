# Tushare新闻API优化总结

## 优化背景
用户积分: 5000积分
问题: 新闻接口使用不当，未充分利用5000积分权限的高级功能

## 主要优化内容

### 1. news接口优化
- **发现**: news接口在5000积分权限下支持`ts_code`参数，可直接获取特定股票的新闻
- **修复**: 恢复使用`ts_code`参数获取公司新闻
- **处理**: 添加了对`title`字段为`None`的处理，从`content`字段提取标题

### 2. major_news接口优化
- **问题**: 未传入日期参数，导致获取数据不准确
- **修复**: 添加`start_date`和`end_date`参数
- **改进**: 增加错误日志输出

### 3. cctv_news接口优化
- **权限**: 需要5000积分权限
- **优化**: 改进错误处理，明确提示权限要求
- **功能**: 获取最近几天的新闻联播文字稿

### 4. 数据结构修复
- **问题**: disclosure_date接口返回的是财报披露日期，不是公告内容
- **现状**: anns函数需要使用其他API获取真实公告内容（待后续优化）

## API使用权限总结

| API接口 | 积分要求 | 5000积分权限特性 |
|---------|----------|-----------------|
| news | 基础权限 | 支持ts_code参数获取公司新闻 |
| major_news | 基础权限 | 更高频率调用 |
| cctv_news | 5000积分 | 可访问新闻联播数据 |
| disclosure_date | 2000积分 | 财报披露日期（非公告内容） |

## 验证结果
所有优化的API接口均已通过测试：
- ✅ news接口支持ts_code参数
- ✅ major_news接口正确传入日期参数
- ✅ cctv_news接口成功获取数据

## 注意事项
1. news接口返回的数据中，`title`字段可能为`None`，实际内容在`content`字段
2. API调用频率限制：5000积分权限为每分钟500次
3. 严格模式已开启，不使用过期缓存数据

## 文件修改清单
- `/backend/core/news.py` - 优化新闻获取逻辑
- `/backend/core/tushare_client.py` - API调用基础（未修改，已正确实现）
- `/backend/core/advanced_data_client.py` - 高级数据客户端（未修改，已包含cctv_news）

## 测试文件
- `test_news_api.py` - 完整API测试
- `test_api_detailed.py` - 数据结构详细测试
- `quick_verify.py` - 快速验证脚本
- `verify_news_final.py` - 最终验证脚本

更新日期: 2025-09-26