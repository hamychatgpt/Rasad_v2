import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from core.config import config
from models.tweet import MonitoringSchedule, Keyword
from core.database import get_db_session

logger = logging.getLogger(__name__)


class DynamicScheduler:
    """کلاس زمان‌بندی پویا برای جمع‌آوری داده"""

    def __init__(self):
        """مقداردهی اولیه زمان‌بندی پویا"""
        self.normal_intervals = {}  # فواصل زمانی عادی
        self.critical_intervals = {}  # فواصل زمانی بحرانی
        self.current_status = {}  # وضعیت فعلی هر کلیدواژه
        self.load_settings()

    def load_settings(self):
        """بارگذاری تنظیمات از دیتابیس یا پیکربندی"""
        # بارگذاری تنظیمات از پیکربندی
        self.default_normal_interval = config.get('scraping', 'default_interval', 1200)  # 20 دقیقه
        self.default_critical_interval = config.get('scraping', 'critical_interval', 300)  # 5 دقیقه
        self.default_archive_interval = config.get('scraping', 'archive_interval', 3600)  # 1 ساعت

        # بارگذاری کلمات کلیدی
        keywords = config.get_keywords()

        # تنظیم فواصل زمانی برای هر کلیدواژه
        for keyword_info in keywords:
            keyword = keyword_info["text"]
            importance = keyword_info.get("importance", 5)

            # تنظیم فاصله زمانی بر اساس اهمیت (کلمات مهم‌تر باید با فاصله کمتری بررسی شوند)
            self.normal_intervals[keyword] = self._calculate_interval(importance, self.default_normal_interval)
            self.critical_intervals[keyword] = self._calculate_interval(importance, self.default_critical_interval)

            # وضعیت اولیه: عادی
            self.current_status[keyword] = "normal"

        # بارگذاری تنظیمات از دیتابیس
        self._load_from_database()

    def _load_from_database(self):
        """بارگذاری تنظیمات از دیتابیس"""
        session = get_db_session()

        try:
            # بازیابی زمان‌بندی‌های موجود
            schedules = session.query(MonitoringSchedule).join(
                Keyword, MonitoringSchedule.keyword_id == Keyword.id
            ).all()

            for schedule in schedules:
                keyword_text = schedule.keyword.text

                self.normal_intervals[keyword_text] = schedule.normal_interval
                self.critical_intervals[keyword_text] = schedule.critical_interval
                self.current_status[keyword_text] = "critical" if schedule.is_critical else "normal"
        except Exception as e:
            logger.error(f"خطا در بارگذاری تنظیمات زمان‌بندی از دیتابیس: {e}")
        finally:
            session.close()

    def _calculate_interval(self, importance: int, base_interval: int) -> int:
        """
        محاسبه فاصله زمانی بر اساس اهمیت

        :param importance: میزان اهمیت (1-10)
        :param base_interval: فاصله زمانی پایه
        :return: فاصله زمانی محاسبه شده
        """
        # مقادیر کمتر برای کلمات مهم‌تر
        factor = 1 - (importance / 10)
        return int(base_interval * (0.5 + factor * 0.5))

    def get_interval(self, keyword: str) -> int:
        """
        دریافت فاصله زمانی فعلی برای یک کلیدواژه

        :param keyword: کلیدواژه مورد نظر
        :return: فاصله زمانی (ثانیه)
        """
        if keyword not in self.current_status:
            return self.default_normal_interval

        if self.current_status[keyword] == "critical":
            return self.critical_intervals.get(keyword, self.default_critical_interval)
        else:
            return self.normal_intervals.get(keyword, self.default_normal_interval)

    def set_critical_status(self, keyword: str, is_critical: bool):
        """
        تنظیم وضعیت بحرانی برای یک کلیدواژه

        :param keyword: کلیدواژه مورد نظر
        :param is_critical: آیا در وضعیت بحرانی است
        """
        if keyword not in self.current_status:
            return

        previous_status = self.current_status[keyword]
        self.current_status[keyword] = "critical" if is_critical else "normal"

        # به‌روزرسانی در دیتابیس
        self._update_db_status(keyword, is_critical)

        # لاگ تغییر وضعیت
        if previous_status != self.current_status[keyword]:
            logger.info(f"وضعیت کلیدواژه '{keyword}' به {self.current_status[keyword]} تغییر یافت.")

    def _update_db_status(self, keyword: str, is_critical: bool):
        """
        به‌روزرسانی وضعیت در دیتابیس

        :param keyword: کلیدواژه مورد نظر
        :param is_critical: آیا در وضعیت بحرانی است
        """
        session = get_db_session()

        try:
            # ابتدا کلیدواژه را پیدا کنید
            keyword_obj = session.query(Keyword).filter_by(text=keyword).first()

            if not keyword_obj:
                logger.warning(f"کلیدواژه '{keyword}' در دیتابیس یافت نشد.")
                return

            # بررسی وجود زمان‌بندی
            schedule = session.query(MonitoringSchedule).filter_by(keyword_id=keyword_obj.id).first()

            if schedule:
                # به‌روزرسانی زمان‌بندی موجود
                schedule.is_critical = is_critical
                schedule.last_check = datetime.now()
            else:
                # ایجاد زمان‌بندی جدید
                schedule = MonitoringSchedule(
                    keyword_id=keyword_obj.id,
                    normal_interval=self.normal_intervals.get(keyword, self.default_normal_interval),
                    critical_interval=self.critical_intervals.get(keyword, self.default_critical_interval),
                    last_check=datetime.now(),
                    is_critical=is_critical
                )
                session.add(schedule)

            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"خطا در به‌روزرسانی وضعیت زمان‌بندی در دیتابیس: {e}")
        finally:
            session.close()

    def manager_tweeted(self):
        """تغییر وضعیت تمام کلیدواژه‌ها به بحرانی پس از توییت مدیر"""
        for keyword in self.current_status:
            self.set_critical_status(keyword, True)

        logger.info("وضعیت تمام کلیدواژه‌ها پس از توییت مدیر به بحرانی تغییر یافت.")