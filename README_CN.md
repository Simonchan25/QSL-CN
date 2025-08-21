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

### 2. 智能分析
- **多维度评分系统**：基于技术、基本面、市场情绪等多维度的综合评分
- **AI驱动的市场解读**：利用大语言模型进行深度市场分析
- **个股诊断**：提供个股的全面分析报告

### 3. 专业研报
- **自动化研报生成**：每日自动生成市场研报
- **定制化分析报告**：根据用户需求生成专属分析报告
- **历史报告管理**：完整的历史报告存档和查询功能

### 4. 智能交互
- **AI助手对话**：通过自然语言与AI助手进行投资咨询
- **实时数据查询**：快速获取市场数据和分析结果
- **个性化推荐**：基于用户偏好的智能推荐

## 🛠 技术架构

### 前端技术栈
- **React 18.3**：现代化的用户界面框架
- **Vite 5.4**：高性能的前端构建工具
- **React Markdown**：支持Markdown格式的研报展示

### 后端技术栈
- **Python Flask**：轻量级Web框架
- **Tushare API**：专业的金融数据接口
- **Ollama**：本地部署的大语言模型
- **缓存策略**：智能的数据缓存机制

### 核心模块
- `market.py`：市场数据获取与处理
- `analyze.py`：综合分析引擎
- `professional_report_generator_v2.py`：专业研报生成器
- `market_ai_analyzer.py`：AI市场分析模块
- `sentiment.py`：市场情绪分析
- `technical.py`：技术指标计算
- `fundamentals.py`：基本面分析

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
cd ../frontend
npm install
```

4. **配置API密钥**
在 `backend/core/tushare_client.py` 中配置您的 Tushare API token

5. **启动后端服务**
```bash
cd backend
python app.py
```

6. **启动前端服务**
```bash
cd frontend
npm run dev
```

7. **访问应用**
打开浏览器访问 `http://localhost:5173`

## 📝 使用指南

### 市场概览
进入首页即可查看实时市场概览，包括：
- 主要指数涨跌情况
- 热门板块排行
- 资金流向分析
- 市场情绪指标

### 生成研报
1. 点击"生成研报"按钮
2. 系统将自动分析当前市场数据
3. 生成包含市场分析、投资建议的专业研报
4. 支持下载和分享功能

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
- 本地部署的AI模型确保数据隐私
- 定期的安全更新和漏洞修复

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