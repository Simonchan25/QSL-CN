# QSL-CN - Intelligent Quantitative Investment Analysis System

<div align="center">

[English](README.md) | [简体中文](README_CN.md)

</div>

## 📊 Project Overview

QSL-CN is a personal learning project for observing and analyzing the Chinese A-share market. It fetches real-time and historical market data from Tushare API, performs data cleaning and multi-dimensional factor scoring (technical + sentiment + fundamentals), and uses locally deployed LLM (Qwen2.5 via Ollama) for market interpretation. The system automatically generates daily morning reports including hotspots, recommendations, and charts, helping to understand market rotation patterns and sentiment rhythms.

## ✨ Core Features

### 1. Market Overview
- **Real-time Market Monitoring**: Track major Shanghai and Shenzhen indices and sector dynamics in real-time
- **Market Hotspot Analysis**: Intelligently identify hot sectors and concepts in the market
- **Fund Flow Monitoring**: Real-time tracking of northbound funds and main capital flows
- **Interactive Charts**: K-line charts and technical analysis visualizations

### 2. Intelligent Analysis
- **Multi-dimensional Scoring System**: Comprehensive scoring based on technical, fundamental, and market sentiment dimensions
- **AI-Driven Market Interpretation**: Deep market analysis using large language models (Ollama)
- **Kronos Stock Price Prediction**: Integrate Kronos time-series model for individual stock price forecasting with historical backtesting validation
- **Individual Stock Diagnosis**: Provide comprehensive analysis reports for individual stocks with AI predictions
- **Enhanced Hotspot Analyzer**: Intelligent sector rotation and hotspot tracking

### 3. Professional Reports
- **Morning Report Generation**: Automatically generate daily morning reports with 7 sections (pre-market hotspots, announcements, global markets, board analysis, institutional activity, new highs, popularity rankings)
- **Comprehensive Market Analysis**: Full A-share market coverage (5400+ stocks) with deep quantitative metrics
- **Historical Report Management**: Complete historical report archiving and query functionality
- **Chart Generation**: Automated chart generation with technical indicators

### 4. Smart Interaction
- **AI Assistant Dialogue**: Investment consultation through natural language with AI assistant
- **Real-time Data Query**: Quickly obtain market data and analysis results
- **Personalized Recommendations**: Intelligent stock recommendations based on market conditions

## 🛠 Technical Architecture

### Frontend Technology Stack
- **React 18.3**: Modern user interface framework
- **Vite 5.4**: High-performance frontend build tool
- **React Markdown**: Support for Markdown format report display
- **ECharts**: Interactive data visualization

### Backend Technology Stack
- **Python 3.8+ Flask**: Lightweight web framework
- **Tushare API**: Professional financial data interface
- **Ollama**: Locally deployed large language model for AI analysis
- **Kronos**: Time-series forecasting model based on Transformer architecture for stock price prediction
- **Advanced Caching Strategy**: Intelligent multi-layer data caching mechanism

### Core Modules

#### Backend Core (`backend/core/`)
- `market.py`: Market data acquisition and processing
- `analyze_optimized.py`: Optimized comprehensive analysis engine
- `professional_report_generator_v2.py`: Professional report generator V2
- `enhanced_hotspot_analyzer.py`: Enhanced hotspot analysis
- `enhanced_smart_matcher.py`: Smart news-stock matching
- `sentiment.py`: Market sentiment analysis
- `technical.py`: Technical indicator calculation
- `fundamentals.py`: Fundamental analysis
- `stock_picker.py`: Intelligent stock selection
- `chart_generator.py`: Automated chart generation
- `kronos_predictor.py`: Kronos time-series prediction service with backtesting validation
- `professional_report_enhancer.py`: AI-enhanced report generation with Kronos predictions
- `north_money_helper.py`: Northbound funds analysis
- `concept_manager.py`: Market concept management

#### Frontend Components (`frontend/src/components/`)
- `MarketOverview.jsx`: Market overview dashboard
- `ReportRenderer.jsx`: Professional report renderer
- `ReportHistory.jsx`: Historical reports management
- `FloatingChat.jsx`: AI assistant chat interface
- `InteractiveKLineChart.jsx`: Interactive K-line chart
- `HotspotAnalysis.jsx`: Hotspot analysis display
- `StockChart.jsx`: Stock chart visualization

## 🚀 Quick Start

### Requirements
- Python 3.8+
- Node.js 16+
- Ollama (for local AI model)

### Installation Steps

1. **Clone the repository**
```bash
git clone https://github.com/Simonchan25/QSL-CN.git
cd QSL-CN
```

2. **Install backend dependencies**
```bash
cd backend
pip install -r requirements.txt
```

3. **Install frontend dependencies**
```bash
cd frontend
npm install
```

4. **Configure environment variables**
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your Tushare token
# Get your token from https://tushare.pro/
nano .env
```

5. **Install and start Ollama**
```bash
# Install Ollama from https://ollama.ai
# Pull the required model
ollama pull qwen2.5:7b
```

6. **Start backend service**
```bash
cd backend
python app.py
# Backend runs on http://localhost:8001
```

7. **Start frontend service**
```bash
cd frontend
npm run dev
# Frontend runs on http://localhost:5173
```

8. **Access the application**
Open your browser and navigate to `http://localhost:5173`

## 📁 Project Structure

```
QSL-CN/
├── backend/
│   ├── app.py                 # Main Flask application
│   ├── core/                  # Core modules
│   │   ├── market.py         # Market data
│   │   ├── analyze_optimized.py
│   │   ├── professional_report_generator_v2.py
│   │   ├── enhanced_hotspot_analyzer.py
│   │   ├── chart_generator.py
│   │   └── ...
│   ├── nlp/                   # NLP modules
│   │   └── ollama_client.py  # Ollama integration
│   └── data/                  # Data storage
│       └── nickname_cache/   # Stock nickname cache
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── App.jsx          # Main application
│   │   └── main.jsx         # Entry point
│   ├── index.html
│   └── package.json
└── README.md
```

## 📝 Usage Guide

### Market Overview
Upon entering the homepage, you can view the real-time market overview, including:
- Major index movements (SSE, SZSE, ChiNext)
- Popular sector rankings with real-time changes
- Fund flow analysis (northbound funds)
- Market sentiment indicators
- Interactive K-line charts

### Generate Reports
1. Click the "Generate Professional Report" button
2. The system will automatically analyze current market data
3. Generate structured morning reports containing:
   - Pre-market hotspots and key events
   - Important announcements highlights
   - Global market overview
   - Board analysis (consecutive limit-ups, trading patterns)
   - Institutional activity and smart money movements
   - Stocks hitting new highs
   - Popularity rankings and market sentiment
4. Each report includes AI-generated professional summary and interactive charts
5. View historical reports in the report history section

### Kronos AI Predictions
The system integrates Kronos time-series model for stock price prediction:
- **Historical Backtesting**: Validates model accuracy with past data
- **Future Price Forecast**: Predicts next 5-10 trading days price movement
- **Confidence Analysis**: Provides prediction confidence levels based on historical accuracy
- **Smart Strategy**: Generates actionable trading strategies based on AI predictions
- All predictions include detailed accuracy metrics and risk warnings

### AI Assistant
1. Click the AI assistant icon in the bottom right corner
2. Enter your investment questions or query requirements
3. AI will provide professional answers based on real-time data
4. Support continuous dialogue and context understanding

## 📊 Data Sources

- **Tushare**: Provides real-time and historical data for the A-share market
- **Sina Finance**: Supplementary market news and announcement information
- **East Money**: Sector and concept data

## 🔐 Security

- All API keys are managed using environment variables
- Locally deployed AI models (Ollama) ensure data privacy
- Multi-layer caching to reduce API calls and improve performance
- No user data is stored or transmitted to external servers

## 🤝 Contributing

Issues and Pull Requests are welcome!

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details

## 👥 Author

- **Simon Chan** - *Initial work* - [Simonchan25](https://github.com/Simonchan25)

## 🙏 Acknowledgments

- Thanks to Tushare for providing quality financial data services
- Thanks to the Ollama team for providing localized AI solutions
- Thanks to all contributors for their support and help

## 📞 Contact

- GitHub Issues: [https://github.com/Simonchan25/QSL-CN/issues](https://github.com/Simonchan25/QSL-CN/issues)
- Email: [Please contact via GitHub]

---

⭐ If this project helps you, please give us a Star!
