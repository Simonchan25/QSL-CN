"""
公司简称自动学习器
通过分析新闻和公告，自动学习每个公司的常用简称和别名
"""

import re
import json
from typing import Dict, List, Set, Optional, Tuple, Any
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class NicknameLearner:
    """公司简称学习器"""

    def __init__(self, cache_dir: str = "data/nickname_cache"):
        """
        初始化

        Args:
            cache_dir: 简称缓存目录
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # 简称缓存
        self.nickname_cache = self._load_cache()

        # 简称提取模式
        self.extraction_patterns = [
            # 括号内简称
            (r'{company_name}[（(](?:以下)?(?:简称|下称)[：:"\'"]?(.+?)[）)]', 1.0),
            (r'{company_name}[（(](?:股票)?(?:简称|代码)[：:](.+?)[）)]', 0.9),
            (r'[（(](?:以下)?(?:简称|下称)[：:"\'"]?{company_name}[）)]', 0.8),

            # 引号内简称
            (r'{company_name}.*?[""\'「」](.{2,6})[""\'」」]', 0.6),

            # "即"模式
            (r'(.+?)[，,]即{company_name}', 0.8),
            (r'{company_name}[，,]即(.+?)(?:[，。,.]|$)', 0.7),

            # 英文缩写
            (r'{company_name}[（(]([A-Z]{{2,6}})[）)]', 0.9),
        ]

        # 行业特定简称规则
        self.industry_rules = {
            '银行': [
                ('银行', '行'),  # 招商银行 -> 招行
                ('银行', '银'),  # 民生银行 -> 民银（较少用）
            ],
            '保险': [
                ('人寿保险', '人寿'),  # 中国人寿保险 -> 中国人寿
                ('财产保险', '财险'),  # 人保财产保险 -> 人保财险
                ('保险', '保'),  # 中国人保 -> 人保
            ],
            '证券': [
                ('证券', '证'),  # 中信证券 -> 中信证
            ],
            '汽车': [
                ('汽车', ''),  # 比亚迪汽车 -> 比亚迪
                ('集团', ''),  # 吉利集团 -> 吉利
            ],
            '地产': [
                ('地产', ''),  # 万科地产 -> 万科
                ('置业', ''),  # 碧桂园置业 -> 碧桂园
            ],
            '科技': [
                ('科技', ''),  # 大华科技 -> 大华
                ('技术', ''),  # 海康威视技术 -> 海康威视
            ],
        }

        # 常见英文缩写映射
        self.known_abbreviations = {
            '中国银行': ['BOC', '中行'],
            '工商银行': ['ICBC', '工行'],
            '建设银行': ['CCB', '建行'],
            '农业银行': ['ABC', '农行'],
            '交通银行': ['BCM', '交行'],
            '招商银行': ['CMB', '招行'],
            '中国平安': ['PING AN', '平安'],
            '中国人寿': ['CHINA LIFE', '国寿'],
            '比亚迪': ['BYD'],
            '宁德时代': ['CATL'],
            '腾讯控股': ['TENCENT', '腾讯'],
            '阿里巴巴': ['ALIBABA', 'BABA', '阿里'],
            '京东': ['JD'],
            '美团': ['MEITUAN'],
            '小米': ['MI', 'XIAOMI'],
        }

        # 验证规则
        self.validation_rules = {
            'min_length': 2,  # 最小长度
            'max_length': 8,  # 最大长度
            'min_frequency': 2,  # 最小出现频率
            'confidence_threshold': 0.5,  # 置信度阈值
        }

    def learn_nicknames(self,
                       ts_code: str,
                       company_name: str,
                       news_items: List[Dict[str, Any]],
                       announcements: Optional[List[Dict[str, Any]]] = None,
                       industry: Optional[str] = None) -> Dict[str, float]:
        """
        学习公司简称

        Args:
            ts_code: 股票代码
            company_name: 公司全称
            news_items: 新闻列表
            announcements: 公告列表
            industry: 行业分类

        Returns:
            简称字典 {简称: 置信度}
        """
        # 检查缓存
        cache_key = f"{ts_code}_nicknames"
        if cache_key in self.nickname_cache:
            cached_time, cached_data = self.nickname_cache[cache_key]
            # 缓存7天
            if (datetime.now() - cached_time).days < 7:
                logger.info(f"[简称学习] 使用缓存的简称 {company_name}")
                return cached_data

        nicknames = {}

        # 1. 从已知映射获取
        known_nicknames = self._get_known_nicknames(company_name)
        for nick in known_nicknames:
            nicknames[nick] = 1.0

        # 2. 基于规则生成
        rule_nicknames = self._generate_by_rules(company_name, industry)
        for nick, conf in rule_nicknames.items():
            if nick not in nicknames:
                nicknames[nick] = conf

        # 3. 从新闻中提取
        news_nicknames = self._extract_from_news(company_name, news_items)
        for nick, conf in news_nicknames.items():
            if nick not in nicknames:
                nicknames[nick] = conf
            else:
                # 增强置信度
                nicknames[nick] = min(1.0, nicknames[nick] + 0.1)

        # 4. 从公告中提取
        if announcements:
            ann_nicknames = self._extract_from_announcements(company_name, announcements)
            for nick, conf in ann_nicknames.items():
                if nick not in nicknames:
                    nicknames[nick] = conf
                else:
                    nicknames[nick] = min(1.0, nicknames[nick] + 0.2)

        # 5. 统计验证
        validated_nicknames = self._validate_nicknames(company_name, nicknames, news_items)

        # 缓存结果
        self.nickname_cache[cache_key] = (datetime.now(), validated_nicknames)
        self._save_cache()

        logger.info(f"[简称学习] {company_name} 学习到 {len(validated_nicknames)} 个简称")
        return validated_nicknames

    def _get_known_nicknames(self, company_name: str) -> List[str]:
        """获取已知的简称"""
        return self.known_abbreviations.get(company_name, [])

    def _generate_by_rules(self, company_name: str, industry: Optional[str]) -> Dict[str, float]:
        """基于规则生成简称"""
        nicknames = {}

        # 1. 行业特定规则
        if industry:
            # 汽车行业特殊处理
            if '汽车' in industry or '新能源' in industry:
                # 比亚迪 -> BYD
                if company_name == '比亚迪':
                    nicknames['BYD'] = 0.9
                    nicknames['比亚'] = 0.7
                elif company_name == '宁德时代':
                    nicknames['CATL'] = 0.9
                    nicknames['宁德'] = 0.7
                elif '汽车' in company_name:
                    # 去掉汽车后缀
                    nickname = company_name.replace('汽车', '')
                    if nickname and nickname != company_name:
                        nicknames[nickname] = 0.7

            # 其他行业规则
            if industry in self.industry_rules:
                for old_suffix, new_suffix in self.industry_rules[industry]:
                    if old_suffix in company_name:
                        nickname = company_name.replace(old_suffix, new_suffix)
                        if nickname != company_name and len(nickname) >= 2:
                            nicknames[nickname] = 0.7

        # 2. 通用规则
        # 去除常见后缀
        suffixes = ['股份有限公司', '股份公司', '有限公司', '集团', '股份', '控股']
        temp_name = company_name
        for suffix in suffixes:
            if temp_name.endswith(suffix):
                nickname = temp_name[:-len(suffix)]
                if len(nickname) >= 2 and nickname not in nicknames:
                    nicknames[nickname] = 0.6
                    temp_name = nickname

        # 3. 提取英文缩写
        # 提取大写字母组合
        upper_letters = ''.join(c for c in company_name if c.isupper())
        if 2 <= len(upper_letters) <= 6:
            nicknames[upper_letters] = 0.5

        # 4. 常见简称（基于公司名特点）
        if len(company_name) <= 4:
            # 短名称公司直接使用
            pass
        elif len(company_name) >= 4:
            # 两字简称（智能选择）
            # 如果是3个字，取前两个
            if len(company_name) == 3:
                two_char = company_name[:2]
                if two_char not in nicknames:
                    nicknames[two_char] = 0.5
            # 如果是4个字或更长
            else:
                # 优先取前两个字（如果有意义）
                two_char = company_name[:2]
                if not any(c in two_char for c in '中国大新'):  # 排除太通用的前缀
                    nicknames[two_char] = 0.4

        return nicknames

    def _extract_from_news(self, company_name: str, news_items: List[Dict[str, Any]]) -> Dict[str, float]:
        """从新闻中提取简称"""
        extracted = Counter()

        # 特殊处理：如果公司名太长，也尝试其部分匹配
        company_keywords = [company_name]
        if len(company_name) > 4:
            # 去除常见后缀后的名称
            for suffix in ['股份有限公司', '股份公司', '有限公司', '集团', '股份', '控股']:
                if company_name.endswith(suffix):
                    short_name = company_name[:-len(suffix)]
                    if short_name and short_name not in company_keywords:
                        company_keywords.append(short_name)

        for news in news_items:
            # 处理TuShare新闻格式：title可能为None，实际内容在content中
            title = news.get('title') or ''
            content = news.get('content') or ''

            # 限制长度但确保不丢失重要信息
            if len(content) > 1000:
                content = content[:1000]

            full_text = f"{title} {content}"

            # 检查是否包含公司关键词
            contains_company = False
            for keyword in company_keywords:
                if keyword in full_text:
                    contains_company = True
                    # 直接记录这个关键词作为可能的简称
                    if keyword != company_name and len(keyword) >= 2:
                        extracted[keyword] += 0.7
                    break

            if not contains_company:
                continue

            # 应用提取模式
            for pattern_template, confidence in self.extraction_patterns:
                pattern = pattern_template.replace('{company_name}', re.escape(company_name))
                matches = re.findall(pattern, full_text, re.IGNORECASE)
                for match in matches:
                    nickname = self._clean_nickname(match)
                    if nickname and nickname != company_name:
                        extracted[nickname] += confidence

        # 转换为置信度字典
        result = {}
        for nickname, score in extracted.items():
            # 根据出现频率计算置信度
            confidence = min(1.0, score / 3.0)  # 3次以上视为高置信度
            result[nickname] = confidence

        return result

    def _extract_from_announcements(self, company_name: str,
                                   announcements: List[Dict[str, Any]]) -> Dict[str, float]:
        """从公告中提取简称（公告中的简称通常更正式）"""
        extracted = Counter()

        for ann in announcements[:10]:  # 只看最近10个公告
            title = ann.get('title', '')

            # 公告标题中的简称模式
            # 如：比亚迪：关于...  或  BYD：公告
            if '：' in title or ':' in title:
                parts = re.split('[：:]', title)
                if len(parts) > 1:
                    potential_nickname = parts[0].strip()
                    if len(potential_nickname) <= 8 and potential_nickname != company_name:
                        extracted[potential_nickname] += 1

        # 转换为置信度字典
        result = {}
        for nickname, count in extracted.items():
            if count >= 2:  # 至少出现2次
                result[nickname] = min(1.0, 0.5 + count * 0.1)

        return result

    def _clean_nickname(self, nickname: str) -> Optional[str]:
        """清理简称"""
        if not nickname:
            return None

        # 去除引号和空白
        nickname = nickname.strip().strip('"\'""''')

        # 去除特殊字符
        nickname = re.sub(r'[《》「」『』【】〔〕]', '', nickname)

        # 验证长度
        if len(nickname) < self.validation_rules['min_length']:
            return None
        if len(nickname) > self.validation_rules['max_length']:
            return None

        # 排除纯数字或纯符号
        if nickname.isdigit() or not any(c.isalnum() for c in nickname):
            return None

        # 排除通用词
        exclude_words = ['公司', '企业', '集团', '股票', '代码', '简称', '以下', '上述']
        if any(word == nickname for word in exclude_words):
            return None

        return nickname

    def _validate_nicknames(self, company_name: str,
                           nicknames: Dict[str, float],
                           news_items: List[Dict[str, Any]]) -> Dict[str, float]:
        """验证简称的有效性"""
        validated = {}

        for nickname, confidence in nicknames.items():
            # 置信度过滤
            if confidence < self.validation_rules['confidence_threshold']:
                continue

            # 相似度检查（简称不应该和全称太相似）
            if nickname == company_name:
                continue

            # 长度检查
            if len(nickname) < self.validation_rules['min_length']:
                continue
            if len(nickname) > self.validation_rules['max_length']:
                continue

            # 验证在新闻中的出现频率
            frequency = self._check_frequency(nickname, news_items)
            if frequency >= self.validation_rules['min_frequency']:
                # 根据频率调整置信度
                final_confidence = min(1.0, confidence + frequency * 0.05)
                validated[nickname] = final_confidence

        return validated

    def _check_frequency(self, nickname: str, news_items: List[Dict[str, Any]]) -> int:
        """检查简称在新闻中的出现频率"""
        count = 0
        for news in news_items:
            title = news.get('title') or ''
            content = news.get('content') or ''
            if len(content) > 500:
                content = content[:500]
            text = f"{title} {content}"
            # 使用单词边界匹配，避免部分匹配
            if re.search(r'\b' + re.escape(nickname) + r'\b', text):
                count += 1
        return count

    def _load_cache(self) -> Dict:
        """加载缓存"""
        cache_file = self.cache_dir / "nickname_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 转换时间字符串为datetime对象
                    cache = {}
                    for key, (time_str, nicknames) in data.items():
                        cache[key] = (datetime.fromisoformat(time_str), nicknames)
                    return cache
            except Exception as e:
                logger.error(f"[简称学习] 加载缓存失败: {e}")
        return {}

    def _save_cache(self):
        """保存缓存"""
        cache_file = self.cache_dir / "nickname_cache.json"
        try:
            # 转换datetime对象为字符串
            data = {}
            for key, (time_obj, nicknames) in self.nickname_cache.items():
                data[key] = (time_obj.isoformat(), nicknames)

            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"[简称学习] 保存缓存失败: {e}")

    def get_all_nicknames(self, ts_code: str, company_name: str,
                         min_confidence: float = 0.6) -> List[str]:
        """
        获取所有简称（用于新闻匹配）

        Args:
            ts_code: 股票代码
            company_name: 公司名称
            min_confidence: 最小置信度

        Returns:
            简称列表
        """
        cache_key = f"{ts_code}_nicknames"
        if cache_key in self.nickname_cache:
            _, nicknames = self.nickname_cache[cache_key]
            return [nick for nick, conf in nicknames.items() if conf >= min_confidence]

        # 如果没有缓存，返回基础简称
        basic_nicknames = []

        # 添加已知简称
        basic_nicknames.extend(self.known_abbreviations.get(company_name, []))

        # 添加简单规则生成的
        if '股份' in company_name:
            basic_nicknames.append(company_name.replace('股份有限公司', '').replace('股份', ''))
        if '集团' in company_name:
            basic_nicknames.append(company_name.replace('集团', ''))

        return list(set(basic_nicknames))


# 单例模式
_learner_instance = None

def get_nickname_learner() -> NicknameLearner:
    """获取简称学习器单例"""
    global _learner_instance
    if _learner_instance is None:
        _learner_instance = NicknameLearner()
    return _learner_instance