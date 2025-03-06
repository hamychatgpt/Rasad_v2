import os
import yaml
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional


class Config:
    """کلاس مدیریت تنظیمات برنامه"""

    def __init__(self, config_path: str = "config.yaml"):
        """
        مقداردهی اولیه کلاس تنظیمات

        :param config_path: مسیر فایل تنظیمات YAML
        """
        # بارگذاری متغیرهای محیطی از فایل .env
        load_dotenv()

        # بارگذاری تنظیمات از فایل YAML
        self.config_path = config_path
        self.config_data = self._load_config()

        # استخراج تنظیمات دیتابیس و افزودن اطلاعات حساس از متغیرهای محیطی
        self._override_with_env_vars()

    def _load_config(self) -> Dict[str, Any]:
        """بارگذاری تنظیمات از فایل YAML"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as config_file:
                return yaml.safe_load(config_file)
        except FileNotFoundError:
            print(f"خطا: فایل تنظیمات {self.config_path} یافت نشد.")
            return {}
        except yaml.YAMLError as e:
            print(f"خطا در خواندن فایل YAML: {e}")
            return {}

    def _override_with_env_vars(self):
        """جایگزینی اطلاعات حساس با متغیرهای محیطی"""
        # تنظیمات دیتابیس
        if 'database' in self.config_data:
            db_config = self.config_data['database']

            if 'password' in db_config and os.getenv('DB_PASSWORD'):
                db_config['password'] = os.getenv('DB_PASSWORD')

            if os.getenv('DB_CONNECTION_STRING'):
                db_config['connection_string'] = os.getenv('DB_CONNECTION_STRING')

        # توکن تلگرام
        if 'reporting' in self.config_data and 'telegram' in self.config_data['reporting']:
            telegram_config = self.config_data['reporting']['telegram']

            if 'token' in telegram_config and os.getenv('TELEGRAM_BOT_TOKEN'):
                telegram_config['token'] = os.getenv('TELEGRAM_BOT_TOKEN')

            if 'chat_id' in telegram_config and os.getenv('TELEGRAM_CHAT_ID'):
                telegram_config['chat_id'] = os.getenv('TELEGRAM_CHAT_ID')

    def get(self, section: str, key: Optional[str] = None, default: Any = None) -> Any:
        """
        دریافت مقدار از تنظیمات

        :param section: بخش تنظیمات مورد نظر
        :param key: کلید مورد نظر در بخش (اختیاری)
        :param default: مقدار پیش‌فرض در صورت عدم وجود
        :return: مقدار تنظیم
        """
        if section not in self.config_data:
            return default

        if key is None:
            return self.config_data[section]

        return self.config_data[section].get(key, default)

    def get_keywords(self) -> List[Dict[str, Any]]:
        """دریافت لیست کلمات کلیدی مورد پایش"""
        return self.get('keywords', default=[])

    def get_tracked_accounts(self) -> List[Dict[str, Any]]:
        """دریافت لیست اکانت‌های مورد پایش"""
        return self.get('tracked_accounts', default=[])

    def update_config(self, section: str, key: str, value: Any):
        """
        به‌روزرسانی تنظیمات و ذخیره در فایل

        :param section: بخش تنظیمات
        :param key: کلید تنظیم
        :param value: مقدار جدید
        """
        if section not in self.config_data:
            self.config_data[section] = {}

        self.config_data[section][key] = value

        # ذخیره تغییرات در فایل
        with open(self.config_path, 'w', encoding='utf-8') as config_file:
            yaml.dump(self.config_data, config_file, default_flow_style=False, allow_unicode=True)


# نمونه سازی به صورت Singleton برای استفاده در کل برنامه
config = Config()