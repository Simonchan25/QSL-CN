# QSL-CN - 智能量化投资分析系统

<div align="center">

[English](README.md) | [简体中文](README_CN.md)

</div>

## 📊 项目简介

QSL-CN 是一个基于人工智能的A股市场分析系统，提供实时市场数据分析、智能投资建议和专业的市场研报生成功能。系统集成了多维度的市场分析能力，包括宏观经济分析、技术指标分析、市场情绪监测等，为投资者提供全方位的决策支持。

## ✨ 核心功能

### 1. 市场概览
- **实时行情监控**：实时跟踪沪深主要指数、板块动态
- **市场热点分析**：智能识别市场热点板块和概念
- **资金流向监测**：北向资金、主力资金流向实时追踪
- **交互式图表**：K线图和技术分析可视化

### 2. 智能分析
- **多维度评分系统**：基于技术、基本面、市场情绪等多维度的综合评分
- **AI驱动的市场解读**：利用大语言模型（Ollama）进行深度市场分析
- **Kronos股价预测**：集成Kronos时序模型进行个股价格预测，提供历史回测验证
- **个股诊断**：提供包含AI预测的个股全面分析报告
- **增强热点分析器**：智能板块轮动和热点追踪

### 3. 专业研报
- **自动化研报生成**：每日自动生成专业市场研报
- **RGTI风格深度分析**：专业级分析报告，包含量化指标
- **历史报告管理**：完整的历史报告存档和查询功能
- **图表自动生成**：自动生成技术指标图表

### 4. 智能交互
- **AI助手对话**：通过自然语言与AI助手进行投资咨询
- **实时数据查询**：快速获取市场数据和分析结果
- **个性化推荐**：基于市场情况的智能选股推荐

## 🛠 技术架构

### 前端技术栈
- **React 18.3**：现代化的用户界面框架
- **Vite 5.4**：高性能的前端构建工具
- **React Markdown**：支持Markdown格式的研报展示
- **ECharts**：交互式数据可视化

### 后端技术栈
- **Python 3.8+ Flask**：轻量级Web框架
- **Tushare API**：专业的金融数据接口
- **Ollama**：本地部署的大语言模型，用于AI分析
- **Kronos**：基于Transformer架构的时序预测模型，用于股价预测
- **高级缓存策略**：智能多层数据缓存机制

### 核心模块

#### 后端核心 (`backend/core/`)
- `market.py`：市场数据获取与处理
- `analyze_optimized.py`：优化的综合分析引擎
- `professional_report_generator_v2.py`：专业研报生成器V2
- `enhanced_hotspot_analyzer.py`：增强型热点分析
- `enhanced_smart_matcher.py`：智能新闻-个股匹配
- `sentiment.py`：市场情绪分析
- `technical.py`：技术指标计算
- `fundamentals.py`：基本面分析
- `stock_picker.py`：智能选股
- `chart_generator.py`：自动图表生成
- `kronos_predictor.py`：Kronos时序预测服务，提供回测验证
- `professional_report_enhancer.py`：AI增强型报告生成，集成Kronos预测
- `north_money_helper.py`：北向资金分析
- `concept_manager.py`：市场概念管理

#### 前端组件 (`frontend/src/components/`)
- `MarketOverview.jsx`：市场概览仪表板
- `ReportRenderer.jsx`：专业报告渲染器
- `ReportHistory.jsx`：历史报告管理
- `FloatingChat.jsx`：AI助手聊天界面
- `InteractiveKLineChart.jsx`：交互式K线图
- `HotspotAnalysis.jsx`：热点分析展示
- `StockChart.jsx`：股票图表可视化

## 🚀 快速开始

### 环境要求
- Python 3.8+
- Node.js 16+
- Ollama（用于本地AI模型）

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/Simonchan25/QSL-CN.git
cd QSL-CN
```

2. **安装后端依赖**
```bash
cd backend
pip install -r requirements.txt
```

3. **安装前端依赖**
```bash
cd frontend
npm install
```

4. **配置环境变量**
```bash
# 复制示例环境变量文件
cp .env.example .env

# 编辑 .env 文件，添加您的 Tushare token
# 从 https://tushare.pro/ 获取您的 token
nano .env
```

5. **安装并启动 Ollama**
```bash
# 从 https://ollama.ai 安装 Ollama
# 拉取所需模型
ollama pull qwen2.5:7b
```

6. **启动后端服务**
```bash
cd backend
python app.py
# 后端运行在 http://localhost:8001
```

7. **启动前端服务**
```bash
cd frontend
npm run dev
# 前端运行在 http://localhost:5173
```

8. **访问应用**
打开浏览器访问 `http://localhost:5173`

## 📁 项目结构

```
QSL-CN/
├── backend/
│   ├── app.py                 # Flask主应用
│   ├── core/                  # 核心模块
│   │   ├── market.py         # 市场数据
│   │   ├── analyze_optimized.py
│   │   ├── professional_report_generator_v2.py
│   │   ├── enhanced_hotspot_analyzer.py
│   │   ├── chart_generator.py
│   │   └── ...
│   ├── nlp/                   # NLP模块
│   │   └── ollama_client.py  # Ollama集成
│   └── data/                  # 数据存储
│       └── nickname_cache/   # 股票昵称缓存
├── frontend/
│   ├── src/
│   │   ├── components/       # React组件
│   │   ├── App.jsx          # 主应用
│   │   └── main.jsx         # 入口文件
│   ├── index.html
│   └── package.json
└── README.md
```

## 📝 使用指南

### 市场概览
进入首页即可查看实时市场概览，包括：
- 主要指数涨跌情况（沪指、深成指、创业板）
- 热门板块排行及实时变化
- 资金流向分析（北向资金）
- 市场情绪指标
- 交互式K线图

### 生成研报
1. 点击"生成专业研报"按钮
2. 系统将自动分析当前市场数据
3. 生成包含以下内容的综合报告：
   - 市场概览和主要指数分析
   - 板块热点分析
   - 推荐个股及评分
   - Kronos AI股价预测及历史回测准确率
   - 技术分析和趋势预测
   - 风险提示和投资建议
4. 在报告历史区域查看历史报告

### Kronos AI预测
系统集成Kronos时序模型进行股价预测：
- **历史回测**：使用历史数据验证模型准确率
- **未来价格预测**：预测未来5-10个交易日的价格走势
- **置信度分析**：基于历史准确率提供预测置信度
- **智能策略**：根据AI预测生成可操作的交易策略
- 所有预测均包含详细的准确率指标和风险提示

### AI助手
1. 点击右下角的AI助手图标
2. 输入您的投资问题或查询需求
3. AI将基于实时数据提供专业回答
4. 支持连续对话和上下文理解

## 📊 数据源

- **Tushare**：提供A股市场实时和历史数据
- **新浪财经**：补充市场新闻和公告信息
- **东方财富**：板块和概念数据

## 🔐 安全性

- 所有API密钥使用环境变量管理
- 本地部署的AI模型（Ollama）确保数据隐私
- 多层缓存机制减少API调用，提升性能
- 不存储或传输用户数据到外部服务器

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建您的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启一个 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 👥 作者

- **Simon Chan** - *Initial work* - [Simonchan25](https://github.com/Simonchan25)

## 🙏 致谢

- 感谢 Tushare 提供优质的金融数据服务
- 感谢 Ollama 团队提供本地化的AI解决方案
- 感谢所有贡献者的支持与帮助

## 📞 联系方式

- GitHub Issues: [https://github.com/Simonchan25/QSL-CN/issues](https://github.com/Simonchan25/QSL-CN/issues)
- Email: [请通过GitHub联系]

---

⭐ 如果这个项目对您有帮助，请给我们一个 Star！
