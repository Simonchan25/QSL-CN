# QSL-CN - Intelligent Quantitative Investment Analysis System

## 📊 Project Overview

QSL-CN is an AI-powered analysis system for the Chinese A-share market, providing real-time market data analysis, intelligent investment recommendations, and professional market report generation. The system integrates multi-dimensional market analysis capabilities, including macroeconomic analysis, technical indicator analysis, and market sentiment monitoring, offering comprehensive decision support for investors.

## ✨ Core Features

### 1. Market Overview
- **Real-time Market Monitoring**: Track major Shanghai and Shenzhen indices and sector dynamics in real-time
- **Market Hotspot Analysis**: Intelligently identify hot sectors and concepts in the market
- **Fund Flow Monitoring**: Real-time tracking of northbound funds and main capital flows

### 2. Intelligent Analysis
- **Multi-dimensional Scoring System**: Comprehensive scoring based on technical, fundamental, and market sentiment dimensions
- **AI-Driven Market Interpretation**: Deep market analysis using large language models
- **Individual Stock Diagnosis**: Provide comprehensive analysis reports for individual stocks

### 3. Professional Reports
- **Automated Report Generation**: Automatically generate daily market reports
- **Customized Analysis Reports**: Generate specialized analysis reports based on user needs
- **Historical Report Management**: Complete historical report archiving and query functionality

### 4. Smart Interaction
- **AI Assistant Dialogue**: Investment consultation through natural language with AI assistant
- **Real-time Data Query**: Quickly obtain market data and analysis results
- **Personalized Recommendations**: Intelligent recommendations based on user preferences

## 🛠 Technical Architecture

### Frontend Technology Stack
- **React 18.3**: Modern user interface framework
- **Vite 5.4**: High-performance frontend build tool
- **React Markdown**: Support for Markdown format report display

### Backend Technology Stack
- **Python Flask**: Lightweight web framework
- **Tushare API**: Professional financial data interface
- **Ollama**: Locally deployed large language model
- **Caching Strategy**: Intelligent data caching mechanism

### Core Modules
- `market.py`: Market data acquisition and processing
- `analyze.py`: Comprehensive analysis engine
- `professional_report_generator_v2.py`: Professional report generator
- `market_ai_analyzer.py`: AI market analysis module
- `sentiment.py`: Market sentiment analysis
- `technical.py`: Technical indicator calculation
- `fundamentals.py`: Fundamental analysis

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
cd ../frontend
npm install
```

4. **Configure API keys**
Configure your Tushare API token in `backend/core/tushare_client.py`

5. **Start backend service**
```bash
cd backend
python app.py
```

6. **Start frontend service**
```bash
cd frontend
npm run dev
```

7. **Access the application**
Open your browser and navigate to `http://localhost:5173`

## 📝 Usage Guide

### Market Overview
Upon entering the homepage, you can view the real-time market overview, including:
- Major index movements
- Popular sector rankings
- Fund flow analysis
- Market sentiment indicators

### Generate Reports
1. Click the "Generate Report" button
2. The system will automatically analyze current market data
3. Generate professional reports containing market analysis and investment recommendations
4. Support download and sharing features

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
- Locally deployed AI models ensure data privacy
- Regular security updates and vulnerability fixes

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