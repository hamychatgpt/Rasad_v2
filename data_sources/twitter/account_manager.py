import logging
import asyncio
import json
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime, timedelta
import random

from core.config import config

logger = logging.getLogger(__name__)


class AccountManager:
    """مدیریت و چرخش اکانت‌های توییتر برای استخراج داده"""

    def __init__(self, accounts_file: str = "accounts.json"):
        """
        مقداردهی اولیه مدیر اکانت‌ها

        :param accounts_file: مسیر فایل اطلاعات اکانت‌ها
        """
        self.accounts_file = Path(accounts_file)
        self.accounts = self._load_accounts()
        self.active_accounts = []
        self.rate_limits = {}  # {account_username: {"reset_time": datetime, "remaining": int}}

    def _load_accounts(self) -> List[Dict[str, Any]]:
        """بارگذاری اطلاعات اکانت‌ها از فایل JSON"""
        if not self.accounts_file.exists():
            logger.warning(f"فایل اکانت‌ها {self.accounts_file} یافت نشد. از فایل نمونه استفاده می‌شود.")
            return self._create_sample_accounts_file()

        try:
            with open(self.accounts_file, 'r', encoding='utf-8') as f:
                accounts = json.load(f)
                logger.info(f"{len(accounts)} اکانت از فایل بارگذاری شد.")
                return accounts
        except json.JSONDecodeError as e:
            logger.error(f"خطا در خواندن فایل اکانت‌ها: {e}")
            return []

    def _create_sample_accounts_file(self) -> List[Dict[str, Any]]:
        """ایجاد فایل نمونه اکانت‌ها در صورت عدم وجود"""
        sample_accounts = [
            {
                "username": "sample_account1",
                "password": "REPLACE_WITH_REAL_PASSWORD",
                "email": "sample1@example.com",
                "email_password": "REPLACE_WITH_REAL_PASSWORD",
                "active": False,
                "last_used": None
            },
            {
                "username": "sample_account2",
                "password": "REPLACE_WITH_REAL_PASSWORD",
                "email": "sample2@example.com",
                "email_password": "REPLACE_WITH_REAL_PASSWORD",
                "active": False,
                "last_used": None
            }
        ]

        with open(self.accounts_file, 'w', encoding='utf-8') as f:
            json.dump(sample_accounts, f, indent=4)

        logger.info(f"فایل نمونه اکانت‌ها در {self.accounts_file} ایجاد شد. لطفاً آن را با اطلاعات واقعی پر کنید.")
        return sample_accounts

    def _save_accounts(self):
        """ذخیره تغییرات اکانت‌ها در فایل"""
        with open(self.accounts_file, 'w', encoding='utf-8') as f:
            json.dump(self.accounts, f, indent=4)

    def get_all_accounts(self) -> List[Dict[str, Any]]:
        """دریافت لیست تمام اکانت‌ها"""
        return self.accounts

    def get_active_accounts(self) -> List[Dict[str, Any]]:
        """دریافت لیست اکانت‌های فعال"""
        return [account for account in self.accounts if account.get("active", False)]

    async def get_healthy_account(self) -> Optional[Dict[str, Any]]:
        """
        انتخاب یک اکانت سالم برای استفاده

        :return: یک اکانت سالم یا None در صورت عدم وجود
        """
        active_accounts = self.get_active_accounts()

        if not active_accounts:
            logger.warning("هیچ اکانت فعالی یافت نشد.")
            return None

        # بررسی و مرتب‌سازی اکانت‌ها بر اساس محدودیت نرخ و آخرین استفاده
        now = datetime.now()
        available_accounts = []

        for account in active_accounts:
            username = account["username"]

            # بررسی محدودیت نرخ
            if username in self.rate_limits:
                rate_limit = self.rate_limits[username]

                if now < rate_limit["reset_time"] and rate_limit["remaining"] <= 0:
                    # این اکانت به محدودیت رسیده و هنوز ریست نشده
                    continue

            # محاسبه امتیاز برای انتخاب اکانت (بر اساس زمان آخرین استفاده و محدودیت باقی‌مانده)
            last_used = account.get("last_used")

            if last_used:
                last_used_time = datetime.fromisoformat(last_used)
                idle_time_minutes = (now - last_used_time).total_seconds() / 60
            else:
                idle_time_minutes = 1000  # مقدار بزرگ برای اکانت‌هایی که هرگز استفاده نشده‌اند

            remaining = self.rate_limits.get(username, {}).get("remaining", 100)

            # امتیاز بیشتر به اکانت‌هایی که مدت طولانی‌تری استفاده نشده‌اند و محدودیت بیشتری دارند
            score = idle_time_minutes * 0.7 + remaining * 0.3

            available_accounts.append((account, score))

        if not available_accounts:
            logger.warning("همه اکانت‌ها به محدودیت نرخ رسیده‌اند.")
            return None

        # مرتب‌سازی بر اساس امتیاز (نزولی)
        available_accounts.sort(key=lambda x: x[1], reverse=True)

        # انتخاب اکانت با بالاترین امتیاز
        selected_account = available_accounts[0][0]

        # به‌روزرسانی زمان آخرین استفاده
        selected_account["last_used"] = now.isoformat()
        self._save_accounts()

        logger.info(f"اکانت {selected_account['username']} برای استفاده انتخاب شد.")
        return selected_account

    def update_rate_limit(self, username: str, remaining: int, reset_time: datetime):
        """
        به‌روزرسانی اطلاعات محدودیت نرخ برای یک اکانت

        :param username: نام کاربری اکانت
        :param remaining: تعداد درخواست‌های باقی‌مانده
        :param reset_time: زمان ریست شدن محدودیت
        """
        self.rate_limits[username] = {
            "remaining": remaining,
            "reset_time": reset_time
        }
        logger.debug(f"محدودیت نرخ برای {username} به‌روز شد: {remaining} باقی‌مانده تا {reset_time}")

    def set_account_status(self, username: str, active: bool):
        """
        تغییر وضعیت فعال بودن یک اکانت

        :param username: نام کاربری اکانت
        :param active: وضعیت فعال بودن
        """
        for account in self.accounts:
            if account["username"] == username:
                account["active"] = active
                self._save_accounts()
                logger.info(f"وضعیت اکانت {username} به {'فعال' if active else 'غیرفعال'} تغییر یافت.")
                return

        logger.warning(f"اکانت {username} در لیست اکانت‌ها یافت نشد.")

    def add_account(self, username: str, password: str, email: str, email_password: str):
        """
        افزودن اکانت جدید به لیست

        :param username: نام کاربری
        :param password: رمز عبور
        :param email: آدرس ایمیل
        :param email_password: رمز عبور ایمیل
        """
        # بررسی تکراری نبودن اکانت
        for account in self.accounts:
            if account["username"] == username:
                logger.warning(f"اکانت {username} قبلاً در لیست وجود دارد.")
                return

        # افزودن اکانت جدید
        new_account = {
            "username": username,
            "password": password,
            "email": email,
            "email_password": email_password,
            "active": True,
            "last_used": None
        }

        self.accounts.append(new_account)
        self._save_accounts()
        logger.info(f"اکانت {username} با موفقیت به لیست اضافه شد.")