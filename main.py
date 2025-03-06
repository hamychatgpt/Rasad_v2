import asyncio
import logging
import sys
from datetime import datetime

from core.config import config
from core.database import init_db
from core.logging_setup import setup_logging
from data_sources.twitter.account_manager import AccountManager
from data_sources.twitter.scraper import TwitterScraper
from pipeline.storage.tweet_store import TweetStore
from pipeline.collectors.keyword_collector import KeywordCollector
from pipeline.collectors.user_collector import UserCollector
from monitoring.scheduler import DynamicScheduler


async def main():
    """نقطه ورود اصلی برنامه"""
    # راه‌اندازی سیستم لاگ‌گیری
    logger = setup_logging()
    logger.info("سیستم پایش هوشمند رسانه‌های اجتماعی در حال راه‌اندازی...")

    try:
        # راه‌اندازی دیتابیس
        init_db()
        logger.info("دیتابیس با موفقیت راه‌اندازی شد.")

        # ایجاد نمونه از کلاس‌های اصلی
        account_manager = AccountManager()
        twitter_scraper = TwitterScraper(account_manager)
        tweet_store = TweetStore()

        # راه‌اندازی استخراج‌کننده توییتر
        await twitter_scraper.initialize()

        # ایجاد جمع‌آوری کننده‌ها
        keyword_collector = KeywordCollector(twitter_scraper, tweet_store)
        user_collector = UserCollector(twitter_scraper, tweet_store)

        # ایجاد زمان‌بندی پویا
        scheduler = DynamicScheduler()

        # اجرای یک چرخه نمونه
        logger.info("شروع جمع‌آوری نمونه...")

        # جمع‌آوری توییت‌ها برای تمام کلیدواژه‌ها
        keyword_results = await keyword_collector.collect_for_all_keywords(limit_per_keyword=50)
        logger.info(f"نتایج جمع‌آوری کلیدواژه‌ها: {keyword_results}")

        # جمع‌آوری توییت‌های کاربران تحت پیگیری
        user_results = await user_collector.collect_for_all_tracked_users(limit_per_user=20)
        logger.info(f"نتایج جمع‌آوری کاربران: {user_results}")

        logger.info("جمع‌آوری نمونه با موفقیت انجام شد.")

    except Exception as e:
        logger.error(f"خطا در اجرای برنامه: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # اجرای برنامه به صورت ناهمگام
    asyncio.run(main())