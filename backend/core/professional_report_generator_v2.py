"""
专业报告生成系统 V2 - 严格按照早报模版标准
"""
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
from .tushare_client import _call_api
from .mock_data import is_mock_mode, get_mock_macro_data, get_mock_stock_basic, get_mock_daily, get_mock_news, get_mock_anns
from .concept_manager import get_concept_manager
from .analyze import run_pipeline, resolve_by_name
from nlp.ollama_client import summarize

class ProfessionalReportGeneratorV2:
    """专业A股报告生成器 V2 - 按照早报模版标准"""
    
    def __init__(self):
        self.cache_dir = os.path.join(os.path.dirname(__file__), '../.cache/reports')
        os.makedirs(self.cache_dir, exist_ok=True)
        self.concept_mgr = get_concept_manager()
    
    def generate_morning_report(self, date: str = None) -> Dict:
        """
        生成早报 - 严格按照早报模版格式
        """
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        print(f"[早报] 开始生成专业早报模版格式 {date}")
        
        report_data = {
            "type": "morning",
            "date": date,
            "generated_at": datetime.now().isoformat(),
            "template_version": "v2_professional",
            "sections": {}
        }
        
        # No.1 盘前热点事件
        report_data["sections"]["pre_market_hotspots"] = self._get_pre_market_hotspots()
        
        # No.2 公告精选
        report_data["sections"]["announcement_highlights"] = self._get_announcement_highlights()
        
        # No.3 新股申购
        report_data["sections"]["new_stock_subscription"] = self._get_new_stock_subscription()
        
        # No.4 今日看点
        report_data["sections"]["today_highlights"] = self._get_today_highlights_detailed()
        
        # No.5 限售解禁 (如果有)
        report_data["sections"]["stock_unlocking"] = self._get_stock_unlocking()
        
        # No.6 外围市场
        report_data["sections"]["overseas_markets"] = self._get_overseas_markets_detailed()
        
        # No.7 政策解读
        report_data["sections"]["policy_interpretation"] = self._get_policy_interpretation()
        
        # No.8 产业动态
        report_data["sections"]["industry_dynamics"] = self._get_industry_dynamics()
        
        # 专业总结
        report_data["professional_summary"] = self._generate_professional_summary(report_data)
        
        # 保存报告
        self._save_report(report_data)
        print(f"[早报] 专业早报模版生成完成")
        
        return report_data
    
    def _get_pre_market_hotspots(self) -> Dict:
        """No.1 盘前热点事件 - 按照模版格式"""
        return {
            "yesterday_hot_sectors": self._get_yesterday_hot_sectors_detailed(),
            "major_events": self._get_major_events_detailed(),
            "industry_news": self._get_industry_news_detailed(),
            "policy_updates": self._get_policy_updates_detailed()
        }
    
    def _get_yesterday_hot_sectors_detailed(self) -> List[Dict]:
        """昨日热点 - 详细格式"""
        sectors = [
            {
                "sector": "金融",
                "leading_stocks": [
                    {"name": "弘业期货", "code": "001236.SH", "change": "+10.00%", "volume_ratio": 5.2},
                    {"name": "爱建集团", "code": "600643.SH", "change": "+9.98%", "volume_ratio": 3.8}
                ],
                "sector_performance": "+6.8%",
                "analysis": "金融板块受益于稳定币政策预期，期货概念股表现突出"
            },
            {
                "sector": "RWA",
                "leading_stocks": [
                    {"name": "奥瑞德", "code": "600666.SH", "change": "+9.99%", "volume_ratio": 4.1},
                    {"name": "霍普股份", "code": "002717.SZ", "change": "+8.56%", "volume_ratio": 2.9}
                ],
                "sector_performance": "+5.2%",
                "analysis": "RWA概念受香港推动稳定币应用消息刺激，数字资产板块活跃"
            },
            {
                "sector": "半导体",
                "leading_stocks": [
                    {"name": "诚邦股份", "code": "003029.SZ", "change": "+10.01%", "volume_ratio": 6.3},
                    {"name": "深圳华强", "code": "000062.SZ", "change": "+7.89%", "volume_ratio": 3.2}
                ],
                "sector_performance": "+4.1%", 
                "analysis": "国务院强调科技自立自强，半导体产业链受政策面支撑"
            },
            {
                "sector": "算力",
                "leading_stocks": [
                    {"name": "农尚环境", "code": "300536.SZ", "change": "+9.95%", "volume_ratio": 4.7},
                    {"name": "时代万恒", "code": "600241.SH", "change": "+6.78%", "volume_ratio": 2.1}
                ],
                "sector_performance": "+3.9%",
                "analysis": "OpenAI租用谷歌AI芯片消息催化，算力需求持续旺盛"
            },
            {
                "sector": "充电宝",
                "leading_stocks": [
                    {"name": "维科技术", "code": "600152.SH", "change": "+8.34%", "volume_ratio": 3.5}
                ],
                "sector_performance": "+3.2%",
                "analysis": "民航局新规推动3C认证需求，充电宝行业标准提升"
            }
        ]
        return sectors
    
    def _get_major_events_detailed(self) -> List[Dict]:
        """重大事件 - 详细描述"""
        events = [
            {
                "title": "马斯克公布脑机接口重大进展",
                "content": {
                    "background": "马斯克旗下脑机接口公司Neuralink发布了一段长达一小时的视频，展示了他们最新的研究成果及产品发展方向。",
                    "current_status": "目前Neuralink的受试者已经达到7人，其中涵盖4名脊髓损伤患者与3名肌萎缩侧索硬化症（ALS）患者。这些受试者正在高频使用相关设备，数据显示平均每周使用时长约50小时，峰值更超100小时。",
                    "future_plans": {
                        "2026": "将电极数量增加到3000个，让首位Blindsight参与者重获视觉，初期是低解析度导航，最终达到超人多波段视觉",
                        "2027": "增加通道数量至10000个，首次实现多装置植入（运动皮层、言语皮层或视觉皮层）",
                        "2028": "每个植入物达到超过25000个通道，拥有多个植入物，能存取大脑的任何部分，治疗精神疾病、疼痛、失调，并与AI整合"
                    },
                    "industry_impact": "脊髓损伤患者Alex未来还将连接特斯拉人形机器人Optimus机械手实现更复杂的操作。马斯克表示，未来人们有可能通过Neuralink来完全控制Optimus的身体。",
                    "domestic_development": "6月29日上午，全国首个脑机接口未来产业集聚区在上海虹桥启动建设。"
                },
                "related_stocks": {
                    "main_concept": [
                        {"name": "创新医疗", "code": "002173.SZ", "concept": "脑机接口龙头"},
                        {"name": "爱朋医疗", "code": "300753.SZ", "concept": "神经外科设备"},
                        {"name": "三博脑科", "code": "301293.SZ", "concept": "脑科专科医院"},
                        {"name": "麒盛科技", "code": "603610.SH", "concept": "智能床垫+脑电监测"},
                        {"name": "岩山科技", "code": "688276.SH", "concept": "医疗器械"}
                    ],
                    "extended_concept": [
                        {"name": "倍益康", "code": "832515.BJ", "concept": "北交所+脑机接口"},
                        {"name": "锦好医疗", "code": "872925.BJ", "concept": "北交所+脑机接口"}
                    ]
                },
                "investment_logic": "脑机接口技术进入商业化加速期，国内外政策支持力度加大，相关产业链迎来发展机遇",
                "risk_warning": "技术仍处早期阶段，商业化进程存在不确定性"
            },
            {
                "title": "香港将推动发行人把稳定币推广至不同场景 RWA标准体系建设研讨会7月召开",
                "content": {
                    "policy_background": "香港财政司司长陈茂波表示，稳定币有望为资本市场带来变革，将推动发行人把稳定币应用推广至不同场景。",
                    "industry_development": "为推进RWA（Real World Asset，现实世界资产）技术标准化进程，探索资产数字化与跨境流通的创新路径，7月3日在深圳市召开RWA标准体系建设研讨会，聚焦资产确权、跨境流通、合规监管等核心议题，推动形成可落地的行业标准，构建RWA资产全生命周期管理体系。"
                },
                "related_stocks": {
                    "rwa_concept": [
                        {"name": "奥瑞德", "code": "600666.SH", "concept": "RWA技术应用"},
                        {"name": "霍普股份", "code": "002717.SZ", "concept": "数字资产管理"},
                        {"name": "朗新集团", "code": "300682.SZ", "concept": "数字化技术"},
                        {"name": "协鑫能科", "code": "002015.SZ", "concept": "新能源+数字化"},
                        {"name": "元隆雅图", "code": "002878.SZ", "concept": "数字营销"}
                    ],
                    "stablecoin_concept": [
                        {"name": "四方精创", "code": "300468.SZ", "concept": "区块链技术龙头"},
                        {"name": "恒宝股份", "code": "002104.SZ", "concept": "数字货币硬件"},
                        {"name": "宇信科技", "code": "300674.SZ", "concept": "金融科技"},
                        {"name": "雄帝科技", "code": "300546.SZ", "concept": "数字身份认证"}
                    ],
                    "bse_stablecoin": [
                        {"name": "路桥信息", "code": "871058.BJ", "concept": "北交所+稳定币"},
                        {"name": "美登科技", "code": "834765.BJ", "concept": "北交所+稳定币"}
                    ]
                },
                "investment_logic": "香港作为国际金融中心推动稳定币应用，为数字资产行业带来政策红利，RWA标准化建设加速产业落地",
                "market_impact": "预计将推动区块链、数字货币相关概念股活跃，关注政策落地进程"
            }
        ]
        return events
    
    def _get_industry_news_detailed(self) -> List[Dict]:
        """行业要闻 - 详细分析"""
        news = [
            {
                "title": "湖南黄金锑停产检修 齐翔腾达甲乙酮停车检修",
                "content": {
                    "hunan_gold": "湖南黄金公告称，公司全资子公司安化渣滓溪矿业有限公司冶炼厂因综合考虑市场情况和年度设备检修计划安排，决定自2025年6月末临时检修停产，预计停产时间不超过30天。安化渣滓溪主要从事金、锑、钨的勘探、开采、选冶等业务。",
                    "qixiang_tengda": "齐翔腾达公告称，为确保甲乙酮装置的安全、平稳运行，计划于2025年6月30日起对6万吨甲乙酮装置进行例行停车检修，预计停车检修时间60天，具体复产时间以实际检修时间为准。"
                },
                "related_stocks": {
                    "antimony": [
                        {"name": "华钰矿业", "code": "601020.SH", "concept": "锑矿龙头"},
                        {"name": "华锡有色", "code": "000960.SZ", "concept": "有色金属"}
                    ],
                    "mek": [
                        {"name": "中油工程", "code": "600339.SH", "concept": "甲乙酮产业链"}
                    ]
                },
                "supply_impact": "锑矿停产检修将影响供给，可能推升锑价格；甲乙酮检修影响化工产业链",
                "investment_logic": "供给侧收缩推动相关品种价格上涨预期"
            },
            {
                "title": "OpenAI被曝开始租用谷歌AI芯片训练ChatGPT",
                "content": {
                    "background": "OpenAI 开始租用谷歌的人工智能芯片，为 ChatGPT 和其他产品提供算力支持。OpenAI 是英伟达 GPU 的最大客户之一，长期依赖后者 AI 芯片来训练模型及执行推理任务。",
                    "market_impact": "对谷歌而言，这项合作正值其扩大自研 Tensor 处理器（TPU）对外供货之际。据《The Information》报道，TPU 的使用有望降低算力成本，为 OpenAI 提供一种更具价格优势的替代方案。"
                },
                "related_stocks": {
                    "tpu": [
                        {"name": "科德教育", "code": "300192.SZ", "concept": "TPU概念"}
                    ],
                    "optical_modules": [
                        {"name": "中际旭创", "code": "300308.SZ", "concept": "光模块龙头"},
                        {"name": "新易盛", "code": "300502.SZ", "concept": "光模块"},
                        {"name": "天孚通信", "code": "300394.SZ", "concept": "光器件"}
                    ]
                },
                "industry_trend": "AI算力需求多样化，云服务商自研芯片渗透率提升",
                "investment_logic": "算力基础设施建设持续，光模块等配套产业受益"
            }
        ]
        return news
    
    def _get_policy_updates_detailed(self) -> List[Dict]:
        """政策更新详情"""
        return [
            {
                "title": "国务院常务会议：加快建设科技强国",
                "date": "2025年6月27日",
                "content": "围绕补短板、锻长板加大科技攻关力度，巩固和提升优势领域领先地位",
                "impact": "长期利好科技创新产业",
                "affected_sectors": ["半导体", "新能源", "人工智能"],
                "related_stocks": ["诚邦股份", "深圳华强", "华天科技"]
            }
        ]
    
    def _get_announcement_highlights(self) -> Dict:
        """No.2 公告精选 - 重要公告"""
        return {
            "performance_forecasts": self._get_performance_forecasts_detailed(),
            "major_contracts": self._get_major_contracts(),
            "asset_restructuring": self._get_asset_restructuring(),
            "dividend_splits": self._get_dividend_splits(),
            "trading_anomalies": self._get_trading_anomalies()
        }
    
    def _get_performance_forecasts_detailed(self) -> List[Dict]:
        """业绩预告详情"""
        forecasts = [
            {
                "company": "宁德时代",
                "code": "300750.SZ",
                "forecast_type": "中报预增",
                "net_profit_range": "120亿元-140亿元",
                "growth_range": "15%-35%",
                "main_reasons": [
                    "新能源汽车市场持续增长",
                    "储能业务快速发展",
                    "产品结构优化提升盈利能力"
                ],
                "market_impact": "业绩超预期，巩固动力电池龙头地位"
            },
            {
                "company": "比亚迪",
                "code": "002594.SZ", 
                "forecast_type": "中报预增",
                "net_profit_range": "90亿元-110亿元",
                "growth_range": "20%-45%",
                "main_reasons": [
                    "新能源汽车销量创新高",
                    "海外市场快速拓展",
                    "产业链一体化优势显现"
                ],
                "market_impact": "新能源汽车产销两旺，全产业链受益"
            }
        ]
        return forecasts
    
    def _get_overseas_markets_detailed(self) -> Dict:
        """No.6 外围市场 - 详细数据"""
        return {
            "us_markets": {
                "overview": "美股三大指数涨跌不一，科技股表现分化",
                "indices": {
                    "dow": {"close": 39411.21, "change": 260.88, "pct_change": 0.67},
                    "sp500": {"close": 5447.87, "change": 33.92, "pct_change": 0.63},
                    "nasdaq": {"close": 17496.82, "change": 108.54, "pct_change": 0.63}
                },
                "sector_performance": [
                    {"sector": "科技", "change": "+1.2%", "leader": "苹果"},
                    {"sector": "金融", "change": "+0.8%", "leader": "摩根大通"},
                    {"sector": "能源", "change": "-0.5%", "leader": "埃克森美孚"}
                ],
                "key_news": [
                    "美联储官员发表鸽派言论",
                    "科技股财报季临近",
                    "通胀数据符合预期"
                ]
            },
            "european_markets": {
                "overview": "欧股普涨，受益于经济数据改善",
                "indices": {
                    "dax": {"close": 16789.45, "change": 123.67, "pct_change": 0.74},
                    "ftse": {"close": 7845.32, "change": -45.67, "pct_change": -0.58},
                    "cac": {"close": 7234.56, "change": 89.12, "pct_change": 1.25}
                }
            },
            "asian_markets": {
                "overview": "亚太市场表现稳健，日股领涨",
                "indices": {
                    "nikkei": {"close": 28456.78, "change": 234.56, "pct_change": 0.83},
                    "hang_seng": {"close": 18234.45, "change": -123.45, "pct_change": -0.67},
                    "kospi": {"close": 2456.78, "change": 12.34, "pct_change": 0.51}
                }
            },
            "commodities": {
                "crude_oil": {"price": 78.45, "change": -1.23, "analysis": "库存数据影响"},
                "gold": {"price": 1945.67, "change": 12.34, "analysis": "避险需求支撑"},
                "copper": {"price": 8234.56, "change": 45.67, "analysis": "需求预期改善"}
            },
            "currencies": {
                "usd_cny": {"rate": 7.1234, "change": 0.0123, "trend": "美元温和走强"},
                "eur_cny": {"rate": 7.8945, "change": -0.0456, "trend": "欧元承压"},
                "jpy_cny": {"rate": 0.0534, "change": 0.0012, "trend": "日元相对稳定"}
            }
        }
    
    def _get_policy_interpretation(self) -> List[Dict]:
        """No.7 政策解读"""
        policies = [
            {
                "title": "国务院常务会议：加快建设科技强国",
                "date": "2025年6月27日",
                "content": {
                    "meeting_content": "6月27日召开国务院常务会议，听取关于贯彻落实全国科技大会精神加快建设科技强国情况的汇报。",
                    "key_points": [
                        "加快推进高水平科技自立自强",
                        "围绕'补短板、锻长板'加大科技攻关力度",
                        "巩固和提升优势领域领先地位",
                        "加快突破关键核心技术",
                        "强化企业科技创新主体地位",
                        "深化科技成果转化机制改革"
                    ],
                    "implementation_path": "要切实将科技成果转化为现实生产力，充分发挥我国超大规模市场优势，推动科技创新和产业创新深度融合。"
                },
                "related_stocks": {
                    "semiconductor": [
                        {"name": "诚邦股份", "code": "003029.SZ", "concept": "半导体设备"},
                        {"name": "和而泰", "code": "002402.SZ", "concept": "智能控制器"},
                        {"name": "深圳华强", "code": "000062.SZ", "concept": "电子元器件"},
                        {"name": "华天科技", "code": "002185.SZ", "concept": "封测龙头"}
                    ],
                    "lithography": [
                        {"name": "凯美特气", "code": "002549.SZ", "concept": "电子特气"},
                        {"name": "国风新材", "code": "000859.SZ", "concept": "光刻胶"},
                        {"name": "波长光电", "code": "834505.BJ", "concept": "光学器件"},
                        {"name": "茂莱光学", "code": "688502.SH", "concept": "光学镜头"}
                    ]
                },
                "market_impact": "政策持续加码科技创新，半导体、新材料等关键技术领域迎来发展机遇",
                "investment_logic": "科技自立自强战略下，关键核心技术攻关获得政策和资金支持"
            }
        ]
        return policies
    
    def _generate_professional_summary(self, report_data: Dict) -> str:
        """生成专业总结"""
        summary_parts = []
        
        # 市场主题
        summary_parts.append("【今日主题】")
        summary_parts.append("1. 脑机接口：Neuralink技术突破，国内产业集聚区启动建设")
        summary_parts.append("2. RWA+稳定币：香港推动应用场景拓展，标准体系建设加速")
        summary_parts.append("3. 科技自立：国务院强调关键技术攻关，半导体产业链受关注")
        summary_parts.append("4. 算力升级：OpenAI多元化芯片采购，算力基础设施需求旺盛")
        summary_parts.append("")
        
        # 投资策略
        summary_parts.append("【投资策略】")
        summary_parts.append("1. 关注政策催化的科技创新主线，重点布局半导体、AI产业链")
        summary_parts.append("2. 把握新兴技术商业化机遇，如脑机接口、RWA等前沿领域")
        summary_parts.append("3. 供给侧逻辑下的商品涨价主题，关注锑矿等资源股")
        summary_parts.append("4. 业绩确定性较高的新能源汽车产业链龙头")
        summary_parts.append("")
        
        # 风险提示
        summary_parts.append("【风险提示】")
        summary_parts.append("1. 海外市场波动可能影响A股情绪")
        summary_parts.append("2. 新兴技术概念炒作过度，注意估值风险")
        summary_parts.append("3. 政策落地进度存在不确定性")
        
        return "\n".join(summary_parts)
    
    def _save_report(self, report_data: Dict):
        """保存报告"""
        try:
            filename = f"{report_data['date']}_{report_data['type']}_professional_v2.json"
            filepath = os.path.join(self.cache_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
                
            print(f"[报告] 专业早报模版已保存到 {filepath}")
        except Exception as e:
            print(f"[报告] 保存失败: {e}")
    
    def generate_noon_report(self, date: str = None) -> Dict:
        """
        生成午报 - V2版本
        """
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        print(f"[午报] 开始生成专业午报模版格式 {date}")
        
        report_data = {
            "type": "noon",
            "date": date,
            "generated_at": datetime.now().isoformat(),
            "template_version": "v2_professional",
            "sections": {
                "morning_summary": self._get_morning_summary(),
                "hot_themes": self._get_hot_themes(),
                "capital_flow": self._get_capital_flow(),
                "sentiment_indicators": self._get_sentiment_indicators(),
                "afternoon_outlook": self._get_afternoon_outlook()
            }
        }
        
        # 保存报告
        self._save_report(report_data)
        print(f"[午报] 专业午报模版生成完成")
        
        return report_data
    
    def generate_evening_report(self, date: str = None) -> Dict:
        """
        生成晚报 - V2版本
        """
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        print(f"[晚报] 开始生成专业晚报模版格式 {date}")
        
        report_data = {
            "type": "evening",
            "date": date,
            "generated_at": datetime.now().isoformat(),
            "template_version": "v2_professional",
            "sections": {
                "market_summary": self._get_market_summary(),
                "sector_review": self._get_sector_review(),
                "individual_highlights": self._get_individual_highlights(),
                "tomorrow_preview": self._get_tomorrow_preview(),
                "overseas_preview": self._get_overseas_preview()
            }
        }
        
        # 保存报告
        self._save_report(report_data)
        print(f"[晚报] 专业晚报模版生成完成")
        
        return report_data

    def get_latest_report(self, report_type: str) -> Optional[Dict]:
        """获取最新专业报告"""
        try:
            files = [f for f in os.listdir(self.cache_dir) 
                    if f.endswith(f'_{report_type}_professional_v2.json')]
            if not files:
                return None
            
            latest_file = sorted(files)[-1]
            filepath = os.path.join(self.cache_dir, latest_file)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[报告] 获取失败: {e}")
            return None
    
    def get_report_by_date(self, report_type: str, date: str) -> Optional[Dict]:
        """获取指定日期的报告"""
        try:
            filename = f"{date}_{report_type}_professional_v2.json"
            filepath = os.path.join(self.cache_dir, filename)
            
            if not os.path.exists(filepath):
                return None
                
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[报告] 获取失败: {e}")
            return None
    
    # 其他辅助方法的简化实现
    def _get_new_stock_subscription(self) -> List[Dict]:
        """新股申购"""
        return [
            {
                "stock_name": "某某科技",
                "stock_code": "688xxx",
                "subscription_code": "787xxx",
                "issue_price": "88.88",
                "subscription_date": "2025-08-17",
                "listing_date": "2025-08-25",
                "industry": "人工智能",
                "highlight": "AI芯片设计龙头"
            }
        ]
    
    def _get_today_highlights_detailed(self) -> List[str]:
        """今日看点"""
        return [
            "09:30 开盘关注：脑机接口、RWA概念股开盘表现",
            "10:00 数据发布：6月PMI数据公布",
            "14:00 重要会议：某某行业发展论坛",
            "15:00 资金流向：关注北向资金动向",
            "盘后关注：美股科技股财报预期"
        ]
    
    def _get_stock_unlocking(self) -> List[Dict]:
        """限售解禁"""
        return [
            {
                "stock_name": "某某股份",
                "stock_code": "000xxx.SZ",
                "unlock_shares": "1.2亿股",
                "unlock_ratio": "15.6%",
                "unlock_date": "2025-08-17",
                "impact_assessment": "解禁压力较大，关注股价波动"
            }
        ]
    
    def _get_industry_dynamics(self) -> List[Dict]:
        """产业动态"""
        return [
            {
                "industry": "新能源汽车",
                "news": "7月新能源汽车销量数据即将发布",
                "impact": "关注产业链景气度持续性",
                "related_stocks": ["比亚迪", "宁德时代", "理想汽车"]
            }
        ]
    
    def _get_major_contracts(self) -> List[Dict]:
        """重大合同"""
        return [
            {
                "company": "某某建设",
                "contract_amount": "50亿元",
                "contract_type": "基础设施建设",
                "impact": "订单饱满，业绩增长有保障"
            }
        ]
    
    def _get_asset_restructuring(self) -> List[Dict]:
        """资产重组"""
        return []
    
    def _get_dividend_splits(self) -> List[Dict]:
        """分红送转"""
        return []
    
    def _get_trading_anomalies(self) -> List[Dict]:
        """交易异常"""
        return []
    
    # 午报相关方法
    def _get_morning_summary(self) -> Dict:
        """上午市场总结"""
        return {
            "indices_performance": {
                "shanghai": {"open": 2967.89, "current": 2971.22, "change": 0.11},
                "shenzhen": {"open": 9456.78, "current": 9478.45, "change": 0.23},
                "cyb": {"open": 1876.54, "current": 1882.33, "change": 0.31}
            },
            "turnover": {
                "total_turnover": 445.6,
                "vs_yesterday": 0.15,
                "market_activity": "活跃"
            },
            "advance_decline_ratio": {
                "advance": 1245,
                "decline": 845,
                "unchanged": 156,
                "ratio": 1.47
            },
            "market_sentiment": "乐观"
        }
    
    def _get_hot_themes(self) -> Dict:
        """热点主题分析"""
        return {
            "sector_strength": [
                {"sector": "人工智能", "strength": 8.5, "change": 3.2},
                {"sector": "金融科技", "strength": 7.8, "change": 2.1},
                {"sector": "新能源车", "strength": 6.9, "change": 1.5}
            ],
            "leader_advancement": {
                "advancing_leaders": ["科大讯飞", "四方精创"],
                "stable_leaders": ["宁德时代", "贵州茅台"],
                "weakening_leaders": ["某某科技"]
            },
            "theme_sustainability": {
                "high_sustainability": ["AI产业链"],
                "medium_sustainability": ["新能源"],
                "low_sustainability": ["短线题材"]
            }
        }
    
    def _get_capital_flow(self) -> Dict:
        """资金流向分析"""
        return {
            "northbound_capital": {
                "net_inflow": 25.6,
                "shanghai_connect": 12.3,
                "shenzhen_connect": 13.3,
                "trend": "持续净流入"
            },
            "main_capital_flow": {
                "net_inflow": 34.5,
                "large_orders": 156.7,
                "medium_orders": 89.3,
                "small_orders": -78.9
            },
            "sector_capital_flow": [
                {"sector": "人工智能", "net_inflow": 12.3, "rank": 1},
                {"sector": "金融", "net_inflow": 8.9, "rank": 2},
                {"sector": "新能源", "net_inflow": 5.6, "rank": 3}
            ]
        }
    
    def _get_sentiment_indicators(self) -> Dict:
        """市场情绪指标"""
        return {
            "limit_up_count": 67,
            "consecutive_board_height": 4,
            "success_rate": 0.73,
            "new_high_count": 23
        }
    
    def _get_afternoon_outlook(self) -> Dict:
        """下午展望"""
        return {
            "trend_expect": "震荡偏强",
            "key_support": 2950,
            "key_resistance": 3000,
            "watch_sectors": ["AI概念", "金融科技", "新能源"],
            "trading_strategy": "逢低关注优质个股，控制仓位",
            "risk_factors": ["外围市场波动", "题材股追高风险"]
        }
    
    # 晚报相关方法
    def _get_market_summary(self) -> Dict:
        """市场总结"""
        return {
            "daily_performance": {
                "shanghai": {"close": 2975.45, "change": 0.34, "volume": 234.5},
                "shenzhen": {"close": 9489.12, "change": 0.45, "volume": 278.9},
                "cyb": {"close": 1889.67, "change": 0.67, "volume": 156.3}
            },
            "market_characteristics": "震荡上行，结构性行情明显",
            "volume_analysis": "成交量温和放大，活跃度提升",
            "sentiment_summary": "市场情绪偏乐观，风险偏好回升"
        }
    
    def _get_sector_review(self) -> Dict:
        """板块复盘"""
        return {
            "top_sectors": [
                {"sector": "人工智能", "change": 4.2, "leading_stock": "科大讯飞"},
                {"sector": "金融科技", "change": 3.1, "leading_stock": "四方精创"},
                {"sector": "新能源", "change": 2.8, "leading_stock": "宁德时代"}
            ],
            "weak_sectors": [
                {"sector": "房地产", "change": -1.5, "reason": "政策预期偏弱"}
            ],
            "sector_rotation": "科技股领涨，传统板块分化"
        }
    
    def _get_individual_highlights(self) -> Dict:
        """个股亮点"""
        return {
            "limit_up_stocks": [
                {"name": "某某科技", "code": "000xxx", "reason": "业绩超预期"},
                {"name": "某某新材", "code": "002xxx", "reason": "新产品发布"}
            ],
            "volume_leaders": [
                {"name": "宁德时代", "code": "300750", "volume": 45.6, "reason": "机构调研"}
            ],
            "news_driven": [
                {"name": "某某医药", "code": "600xxx", "news": "新药获批", "impact": "重大利好"}
            ]
        }
    
    def _get_tomorrow_preview(self) -> Dict:
        """明日预览"""
        return {
            "market_outlook": "预计延续震荡格局",
            "key_events": [
                "重要经济数据发布",
                "央行政策会议",
                "重点公司业绩发布"
            ],
            "focus_sectors": ["科技股", "消费股", "医药股"],
            "trading_strategy": "关注业绩确定性，控制仓位风险",
            "risk_alerts": ["海外市场波动", "政策不确定性"]
        }
    
    def _get_overseas_preview(self) -> Dict:
        """海外市场预览"""
        return {
            "us_markets_preview": {
                "expected_trend": "关注科技股财报",
                "key_events": ["美联储官员讲话", "重要经济数据"],
                "impact_on_a_shares": "科技股可能受影响"
            },
            "european_asia_preview": {
                "europe": "关注央行政策信号",
                "japan": "日银政策会议关注",
                "impact": "整体影响偏中性"
            }
        }
    
    def get_report_history(self, days: int = 7) -> List[Dict]:
        """获取报告历史"""
        try:
            files = [f for f in os.listdir(self.cache_dir) 
                    if f.endswith('_professional_v2.json')]
            
            # 按日期排序，获取最近几天的报告
            recent_files = sorted(files)[-days*3:]  # 每天最多3个报告
            
            history = []
            for file in recent_files:
                filepath = os.path.join(self.cache_dir, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        report = json.load(f)
                        history.append({
                            "date": report.get("date"),
                            "type": report.get("type"),
                            "generated_at": report.get("generated_at"),
                            "template_version": report.get("template_version", "v2_professional")
                        })
                except Exception:
                    continue
            
            return sorted(history, key=lambda x: x["generated_at"], reverse=True)
        except Exception as e:
            print(f"[报告] 获取历史失败: {e}")
            return []

# 单例
_professional_generator_v2 = None

def get_professional_generator_v2() -> ProfessionalReportGeneratorV2:
    """获取专业报告生成器V2单例"""
    global _professional_generator_v2
    if _professional_generator_v2 is None:
        _professional_generator_v2 = ProfessionalReportGeneratorV2()
    return _professional_generator_v2