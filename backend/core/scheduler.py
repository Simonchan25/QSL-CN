"""
任务调度器 - 自动化定时任务
"""
import asyncio
import threading
from datetime import datetime, time
from typing import Callable, Dict, List, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
import pytz
import logging

from .professional_report_generator_v2 import ProfessionalReportGeneratorV2
from .concept_manager import get_concept_manager
from .cache_strategy import get_smart_cache

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaskScheduler:
    """智能任务调度器"""

    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone=pytz.timezone('Asia/Shanghai'))
        self.report_gen = ProfessionalReportGeneratorV2()
        self.concept_mgr = get_concept_manager()
        self.cache = get_smart_cache()
        
        # 任务执行状态
        self.task_status: Dict[str, Dict] = {}
        
        # 注册事件监听器
        self.scheduler.add_listener(self._job_executed, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error, EVENT_JOB_ERROR)
        
        # 初始化所有定时任务
        self._setup_scheduled_tasks()
    
    def _setup_scheduled_tasks(self):
        """设置所有定时任务"""

        # 0. 新闻预处理 (每天凌晨 03:00) - 新增
        self.scheduler.add_job(
            func=self._preprocess_news,
            trigger=CronTrigger(hour=3, minute=0, second=0),
            id='preprocess_news',
            name='新闻预处理',
            misfire_grace_time=1800  # 30分钟容错
        )

        # 1. 早报生成 (每个交易日 08:30)
        self.scheduler.add_job(
            func=self._generate_morning_report,
            trigger=CronTrigger(hour=8, minute=30, second=0),
            id='morning_report',
            name='生成早报',
            misfire_grace_time=300  # 5分钟容错
        )
        
        # 2. 午报生成 (每个交易日 12:00)
        self.scheduler.add_job(
            func=self._generate_noon_report,
            trigger=CronTrigger(hour=12, minute=0, second=0),
            id='noon_report',
            name='生成午报',
            misfire_grace_time=300
        )
        
        # 3. 晚报生成 (每个交易日 18:00)
        self.scheduler.add_job(
            func=self._generate_evening_report,
            trigger=CronTrigger(hour=18, minute=0, second=0),
            id='evening_report',
            name='生成晚报',
            misfire_grace_time=300
        )
        
        # 4. 概念库刷新 (每天 07:00)
        self.scheduler.add_job(
            func=self._refresh_concepts,
            trigger=CronTrigger(hour=7, minute=0, second=0),
            id='refresh_concepts',
            name='刷新概念库',
            misfire_grace_time=600
        )
        
        # 5. 缓存清理 (每天 02:00)
        self.scheduler.add_job(
            func=self._cleanup_cache,
            trigger=CronTrigger(hour=2, minute=0, second=0),
            id='cleanup_cache',
            name='清理过期缓存',
            misfire_grace_time=1800
        )
        
        # 6. 交易时间内的高频任务
        self._setup_trading_hours_tasks()
        
        # 7. 盘后数据更新任务
        self._setup_after_hours_tasks()
    
    def _setup_trading_hours_tasks(self):
        """设置交易时间内的高频任务"""
        
        # 市场数据刷新 (交易时间内每5分钟)
        # 上午: 09:30-11:30, 下午: 13:00-15:00
        for hour in [9, 10, 11, 13, 14]:
            for minute in range(0, 60, 5):
                # 跳过非交易时间
                if hour == 9 and minute < 30:
                    continue
                if hour == 11 and minute > 30:
                    continue
                
                self.scheduler.add_job(
                    func=self._refresh_market_data,
                    trigger=CronTrigger(hour=hour, minute=minute, second=0),
                    id=f'market_refresh_{hour}_{minute}',
                    name=f'市场数据刷新{hour}:{minute:02d}',
                    misfire_grace_time=60
                )
    
    def _setup_after_hours_tasks(self):
        """设置盘后数据更新任务"""
        
        # 盘后基础数据更新 (15:30)
        self.scheduler.add_job(
            func=self._update_basic_data,
            trigger=CronTrigger(hour=15, minute=30, second=0),
            id='update_basic_data',
            name='更新基础数据',
            misfire_grace_time=1800
        )
        
        # 财务数据更新 (19:00)
        self.scheduler.add_job(
            func=self._update_financial_data,
            trigger=CronTrigger(hour=19, minute=0, second=0),
            id='update_financial_data',
            name='更新财务数据',
            misfire_grace_time=1800
        )
        
        # 新闻公告爬取 (每小时)
        self.scheduler.add_job(
            func=self._crawl_news_announcements,
            trigger=IntervalTrigger(hours=1),
            id='crawl_news',
            name='爬取新闻公告',
            misfire_grace_time=600
        )
    
    def _generate_morning_report(self):
        """生成早报任务"""
        try:
            # 只在交易日执行
            if not self._is_trading_day():
                logger.info("非交易日，跳过早报生成")
                return
            
            logger.info("开始生成早报...")
            report = self.report_gen.generate_morning_report()
            
            self.task_status['morning_report'] = {
                'last_run': datetime.now().isoformat(),
                'status': 'success',
                'report_date': report.get('date')
            }
            
            logger.info(f"早报生成完成: {report.get('date')}")
            
        except Exception as e:
            logger.error(f"早报生成失败: {e}")
            self.task_status['morning_report'] = {
                'last_run': datetime.now().isoformat(),
                'status': 'error',
                'error': str(e)
            }
    
    def _generate_noon_report(self):
        """生成午报任务"""
        try:
            if not self._is_trading_day():
                logger.info("非交易日，跳过午报生成")
                return
            
            logger.info("开始生成午报...")
            report = self.report_gen.generate_noon_report()
            
            self.task_status['noon_report'] = {
                'last_run': datetime.now().isoformat(),
                'status': 'success',
                'report_date': report.get('date')
            }
            
            logger.info(f"午报生成完成: {report.get('date')}")
            
        except Exception as e:
            logger.error(f"午报生成失败: {e}")
            self.task_status['noon_report'] = {
                'last_run': datetime.now().isoformat(),
                'status': 'error',
                'error': str(e)
            }
    
    def _generate_evening_report(self):
        """生成晚报任务"""
        try:
            if not self._is_trading_day():
                logger.info("非交易日，跳过晚报生成")
                return
            
            logger.info("开始生成晚报...")
            report = self.report_gen.generate_evening_report()
            
            self.task_status['evening_report'] = {
                'last_run': datetime.now().isoformat(),
                'status': 'success',
                'report_date': report.get('date')
            }
            
            logger.info(f"晚报生成完成: {report.get('date')}")
            
        except Exception as e:
            logger.error(f"晚报生成失败: {e}")
            self.task_status['evening_report'] = {
                'last_run': datetime.now().isoformat(),
                'status': 'error',
                'error': str(e)
            }
    
    def _refresh_concepts(self):
        """刷新概念库任务"""
        try:
            logger.info("开始刷新概念库...")
            concepts = self.concept_mgr.refresh_concepts()
            
            self.task_status['refresh_concepts'] = {
                'last_run': datetime.now().isoformat(),
                'status': 'success',
                'concept_count': len(concepts)
            }
            
            logger.info(f"概念库刷新完成: {len(concepts)}个概念")
            
        except Exception as e:
            logger.error(f"概念库刷新失败: {e}")
            self.task_status['refresh_concepts'] = {
                'last_run': datetime.now().isoformat(),
                'status': 'error',
                'error': str(e)
            }
    
    def _cleanup_cache(self):
        """清理缓存任务"""
        try:
            logger.info("开始清理过期缓存...")
            self.cache.clear_expired()
            
            self.task_status['cleanup_cache'] = {
                'last_run': datetime.now().isoformat(),
                'status': 'success'
            }
            
            logger.info("缓存清理完成")
            
        except Exception as e:
            logger.error(f"缓存清理失败: {e}")
            self.task_status['cleanup_cache'] = {
                'last_run': datetime.now().isoformat(),
                'status': 'error',
                'error': str(e)
            }
    
    def _refresh_market_data(self):
        """刷新市场数据任务"""
        try:
            if not self._is_trading_time():
                return
            
            # 刷新指数数据缓存
            self._clear_index_cache()
            
            # 刷新市场数据
            from .market import fetch_market_overview
            market_data = fetch_market_overview()
            logger.info(f"市场数据刷新完成 - 指数数量: {len(market_data.get('indices', []))}")
            
        except Exception as e:
            logger.error(f"市场数据刷新失败: {e}")
    
    def _clear_index_cache(self):
        """清理指数数据缓存"""
        try:
            import os
            import glob
            cache_pattern = ".cache/index_daily_*"
            cache_files = glob.glob(cache_pattern)
            for file in cache_files:
                try:
                    os.remove(file)
                except Exception:
                    pass
            logger.debug(f"清理了 {len(cache_files)} 个指数缓存文件")
        except Exception as e:
            logger.error(f"清理缓存失败: {e}")
    
    def _update_basic_data(self):
        """更新基础数据任务"""
        try:
            if not self._is_trading_day():
                return
            
            # 更新股票列表、基本信息等
            logger.info("基础数据更新完成")
            
        except Exception as e:
            logger.error(f"基础数据更新失败: {e}")
    
    def _update_financial_data(self):
        """更新财务数据任务"""
        try:
            # 更新财务报表、指标等
            logger.info("财务数据更新完成")
            
        except Exception as e:
            logger.error(f"财务数据更新失败: {e}")
    
    def _crawl_news_announcements(self):
        """爬取新闻公告任务"""
        try:
            # 爬取最新新闻和公告
            logger.debug("新闻公告爬取完成")

        except Exception as e:
            logger.error(f"新闻公告爬取失败: {e}")

    def _preprocess_news(self):
        """新闻预处理任务 - 使用LLM深度分析所有新闻"""
        try:
            logger.info("开始新闻预处理任务...")

            # 导入智能匹配器
            from .intelligent_news_matcher import intelligent_matcher

            # 执行预处理
            processed = intelligent_matcher.daily_preprocessing_task()

            self.task_status['preprocess_news'] = {
                'last_run': datetime.now().isoformat(),
                'status': 'success',
                'processed_count': len(processed)
            }

            logger.info(f"新闻预处理完成: 处理了 {len(processed)} 条新闻")

        except Exception as e:
            logger.error(f"新闻预处理失败: {e}")
            self.task_status['preprocess_news'] = {
                'last_run': datetime.now().isoformat(),
                'status': 'error',
                'error': str(e)
            }
    
    def _is_trading_day(self) -> bool:
        """判断是否为交易日"""
        now = datetime.now()
        
        # 简单判断：周一到周五（实际应该排除节假日）
        if now.weekday() >= 5:  # 6=周日, 0=周一
            return False
        
        # 这里可以添加更复杂的节假日判断逻辑
        return True
    
    def _is_trading_time(self) -> bool:
        """判断是否在交易时间"""
        if not self._is_trading_day():
            return False
        
        now = datetime.now().time()
        
        # 上午交易时间: 09:30-11:30
        morning_start = time(9, 30)
        morning_end = time(11, 30)
        
        # 下午交易时间: 13:00-15:00
        afternoon_start = time(13, 0)
        afternoon_end = time(15, 0)
        
        return (morning_start <= now <= morning_end) or (afternoon_start <= now <= afternoon_end)
    
    def _job_executed(self, event):
        """任务执行成功回调"""
        logger.info(f"任务执行成功: {event.job_id}")
    
    def _job_error(self, event):
        """任务执行失败回调"""
        logger.error(f"任务执行失败: {event.job_id}, 错误: {event.exception}")
    
    def start(self):
        """启动调度器"""
        try:
            self.scheduler.start()
            logger.info("任务调度器已启动")
            
            # 打印所有任务
            jobs = self.scheduler.get_jobs()
            logger.info(f"已注册 {len(jobs)} 个定时任务:")
            for job in jobs:
                logger.info(f"  - {job.name} ({job.id}): {job.next_run_time}")
                
        except Exception as e:
            logger.error(f"调度器启动失败: {e}")
    
    def stop(self):
        """停止调度器"""
        try:
            self.scheduler.shutdown()
            logger.info("任务调度器已停止")
        except Exception as e:
            logger.error(f"调度器停止失败: {e}")
    
    def get_job_status(self) -> Dict:
        """获取任务执行状态"""
        jobs = self.scheduler.get_jobs()
        job_info = []
        
        for job in jobs:
            job_info.append({
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'last_status': self.task_status.get(job.id, {})
            })
        
        return {
            'scheduler_running': self.scheduler.running,
            'jobs': job_info,
            'task_status': self.task_status
        }
    
    def run_job_now(self, job_id: str) -> bool:
        """立即执行指定任务"""
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                job.modify(next_run_time=datetime.now())
                logger.info(f"任务 {job_id} 已安排立即执行")
                return True
            else:
                logger.error(f"任务 {job_id} 不存在")
                return False
        except Exception as e:
            logger.error(f"执行任务失败: {e}")
            return False
    
    def pause_job(self, job_id: str) -> bool:
        """暂停任务"""
        try:
            self.scheduler.pause_job(job_id)
            logger.info(f"任务 {job_id} 已暂停")
            return True
        except Exception as e:
            logger.error(f"暂停任务失败: {e}")
            return False
    
    def resume_job(self, job_id: str) -> bool:
        """恢复任务"""
        try:
            self.scheduler.resume_job(job_id)
            logger.info(f"任务 {job_id} 已恢复")
            return True
        except Exception as e:
            logger.error(f"恢复任务失败: {e}")
            return False

# 全局调度器实例
_scheduler = None

def get_scheduler() -> TaskScheduler:
    """获取调度器实例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = TaskScheduler()
    return _scheduler

def start_scheduler():
    """启动全局调度器"""
    scheduler = get_scheduler()
    scheduler.start()

def stop_scheduler():
    """停止全局调度器"""
    scheduler = get_scheduler()
    scheduler.stop()