import logging
import sys
from pathlib import Path
from datetime import datetime
from rich.logging import RichHandler

from core.config import config


def setup_logging():
    """راه‌اندازی سیستم لاگ‌گیری برنامه"""
    # ایجاد پوشه لاگ اگر وجود نداشته باشد
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # تنظیم نام فایل لاگ با تاریخ فعلی
    current_date = datetime.now().strftime("%Y-%m-%d")
    log_file = log_dir / f"twitter_monitor_{current_date}.log"

    # تنظیم سطح لاگ‌گیری از تنظیمات
    log_level_str = config.get('general', 'log_level', 'INFO')
    log_level = getattr(logging, log_level_str.upper())

    # تنظیمات اصلی لاگر
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            RichHandler(rich_tracebacks=True, markup=True),
            logging.FileHandler(log_file, encoding='utf-8')
        ]
    )

    # تنظیم لاگر کتابخانه‌های خارجی
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)

    # ثبت شروع برنامه
    logger = logging.getLogger("twitter_monitor")
    logger.info("سیستم پایش هوشمند رسانه‌های اجتماعی راه‌اندازی شد.")

    return logger