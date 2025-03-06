import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from twscrape import API, gather
from twscrape.logger import set_log_level

from core.config import config
from data_sources.twitter.account_manager import AccountManager

logger = logging.getLogger(__name__)


class TwitterScraper:
    """
    کلاس اصلی برای استخراج داده از توییتر با استفاده از کتابخانه twscrape
    """

    def __init__(self, account_manager: AccountManager):
        """
        مقداردهی اولیه استخراج‌کننده توییتر

        :param account_manager: نمونه کلاس مدیریت اکانت
        """
        self.account_manager = account_manager
        self.api = API()
        self.initialized = False

        # تنظیم سطح لاگ twscrape
        set_log_level("INFO")

    async def initialize(self):
        """راه‌اندازی اولیه و افزودن اکانت‌ها"""
        if self.initialized:
            return

        accounts = self.account_manager.get_all_accounts()

        for account in accounts:
            if not account.get("active", False):
                logger.info(f"اکانت {account['username']} غیرفعال است و اضافه نمی‌شود.")
                continue

            try:
                await self.api.pool.add_account(
                    account["username"],
                    account["password"],
                    account["email"],
                    account["email_password"]
                )
                logger.info(f"اکانت {account['username']} با موفقیت اضافه شد.")
            except Exception as e:
                logger.error(f"خطا در افزودن اکانت {account['username']}: {e}")
                # غیرفعال کردن اکانت در صورت بروز خطا
                self.account_manager.set_account_status(account["username"], False)

        # تلاش برای ورود همه اکانت‌ها
        try:
            await self.api.pool.login_all()

            # از آنجایی که بعد از login_all حداقل یک اکانت باید فعال باشد
            # این مقدار را به عنوان معیار موفقیت در نظر می‌گیریم
            self.initialized = True
            logger.info("ورود به اکانت‌ها با موفقیت انجام شد.")

        except Exception as e:
            logger.error(f"خطا در ورود به اکانت‌ها: {e}")
            self.initialized = False

    async def search_tweets(
            self,
            query: str,
            limit: int = 100,
            since_id: Optional[str] = None,  # این پارامتر استفاده نمی‌شود
            until_date: Optional[datetime] = None
    ) -> List[Any]:
        """
        جستجوی توییت‌ها بر اساس کوئری مشخص

        :param query: عبارت جستجو
        :param limit: حداکثر تعداد توییت‌ها
        :param since_id: آیدی توییت برای شروع از آن (اختیاری، در API جدید استفاده نمی‌شود)
        :param until_date: تاریخ پایان جستجو (اختیاری)
        :return: لیستی از توییت‌های یافت شده
        """
        if not self.initialized:
            await self.initialize()
            if not self.initialized:
                logger.error("استخراج‌کننده توییتر به درستی راه‌اندازی نشده است.")
                return []

        try:
            # انتخاب یک اکانت سالم برای جستجو
            account = await self.account_manager.get_healthy_account()
            if not account:
                logger.error("هیچ اکانت سالمی برای جستجو در دسترس نیست.")
                return []

            # اصلاح کوئری با محدودیت زمانی
            original_query = query
            if until_date:
                query += f" until:{until_date.strftime('%Y-%m-%d')}"

            # انجام جستجو
            max_tweets = min(limit, config.get('scraping', 'max_tweets_per_query', 100))

            # طبق مستندات، متد search فقط پارامترهای query و limit را می‌پذیرد
            tweets = await gather(self.api.search(
                query,
                limit=max_tweets
            ))

            # به‌روزرسانی محدودیت نرخ
            self.account_manager.update_rate_limit(
                account["username"],
                remaining=85,
                reset_time=datetime.now() + timedelta(minutes=15)
            )

            logger.info(f"تعداد {len(tweets)} توییت برای کوئری '{original_query}' یافت شد.")
            return tweets

        except Exception as e:
            logger.error(f"خطا در جستجوی توییت‌ها: {e}")
            return []

    async def get_user_tweets(self, username: str, limit: int = 100) -> List[Any]:
        """
        دریافت توییت‌های یک کاربر خاص

        :param username: نام کاربری
        :param limit: حداکثر تعداد توییت‌ها
        :return: لیستی از توییت‌های کاربر
        """
        if not self.initialized:
            await self.initialize()
            if not self.initialized:
                logger.error("استخراج‌کننده توییتر به درستی راه‌اندازی نشده است.")
                return []

        try:
            # انتخاب یک اکانت سالم
            account = await self.account_manager.get_healthy_account()
            if not account:
                logger.error("هیچ اکانت سالمی برای جستجو در دسترس نیست.")
                return []

            # دریافت اطلاعات کاربر
            try:
                user = await self.api.user_by_login(username)
                if not user:
                    logger.error(f"کاربر '{username}' یافت نشد.")
                    return []
            except Exception as e:
                logger.error(f"خطا در دریافت اطلاعات کاربر '{username}': {e}")
                return []

            # دریافت توییت‌های کاربر
            max_tweets = min(limit, config.get('scraping', 'max_tweets_per_query', 100))

            # استفاده از متد صحیح user_tweets طبق مستندات
            tweets = await gather(self.api.user_tweets(user.id, limit=max_tweets))

            # به‌روزرسانی محدودیت نرخ
            self.account_manager.update_rate_limit(
                account["username"],
                remaining=90,
                reset_time=datetime.now() + timedelta(minutes=15)
            )

            logger.info(f"تعداد {len(tweets)} توییت از کاربر {username} دریافت شد.")
            return tweets
        except Exception as e:
            logger.error(f"خطا در دریافت توییت‌های کاربر {username}: {e}")
            return []

    async def get_tweet(self, tweet_id: str) -> Optional[Any]:
        """
        دریافت یک توییت خاص با شناسه آن

        :param tweet_id: شناسه توییت
        :return: آبجکت توییت یا None در صورت عدم یافتن
        """
        if not self.initialized:
            await self.initialize()
            if not self.initialized:
                return None

        try:
            # انتخاب یک اکانت سالم
            account = await self.account_manager.get_healthy_account()
            if not account:
                return None

            # استفاده از متد tweet_details طبق مستندات
            tweet = await self.api.tweet_details(tweet_id)
            return tweet
        except Exception as e:
            logger.error(f"خطا در دریافت توییت با شناسه {tweet_id}: {e}")
            return None

    async def get_replies(self, tweet_id: str, limit: int = 100) -> List[Any]:
        """
        دریافت پاسخ‌های یک توییت

        :param tweet_id: شناسه توییت
        :param limit: حداکثر تعداد پاسخ‌ها
        :return: لیستی از پاسخ‌ها
        """
        if not self.initialized:
            await self.initialize()
            if not self.initialized:
                return []

        try:
            # انتخاب یک اکانت سالم
            account = await self.account_manager.get_healthy_account()
            if not account:
                return []

            # استفاده از متد صحیح طبق مستندات
            max_tweets = min(limit, config.get('scraping', 'max_tweets_per_query', 100))
            replies = await gather(self.api.tweet_replies(tweet_id, limit=max_tweets))

            logger.info(f"تعداد {len(replies)} پاسخ مستقیم برای توییت {tweet_id} یافت شد.")
            return replies
        except Exception as e:
            logger.error(f"خطا در دریافت پاسخ‌های توییت {tweet_id}: {e}")
            return []

    async def get_retweets(self, tweet_id: str, limit: int = 100) -> List[Any]:
        """
        دریافت کاربران بازنشر‌کننده یک توییت

        :param tweet_id: شناسه توییت
        :param limit: حداکثر تعداد کاربران
        :return: لیستی از کاربران بازنشر‌کننده
        """
        if not self.initialized:
            await self.initialize()
            if not self.initialized:
                return []

        try:
            # انتخاب یک اکانت سالم
            account = await self.account_manager.get_healthy_account()
            if not account:
                return []

            # استفاده از متد صحیح طبق مستندات
            max_users = min(limit, config.get('scraping', 'max_tweets_per_query', 100))
            retweeters = await gather(self.api.retweeters(tweet_id, limit=max_users))

            logger.info(f"تعداد {len(retweeters)} بازنشر‌کننده برای توییت {tweet_id} یافت شد.")
            return retweeters
        except Exception as e:
            logger.error(f"خطا در دریافت بازنشر‌کنندگان توییت {tweet_id}: {e}")
            return []

    def _convert_tweet_to_dict(self, tweet) -> Dict[str, Any]:
        """
        تبدیل آبجکت توییت به دیکشنری برای ذخیره در دیتابیس

        :param tweet: آبجکت توییت از twscrape
        :return: دیکشنری حاوی اطلاعات توییت
        """
        return {
            "tweet_id": tweet.id,
            "user_id": tweet.user.id,
            "username": tweet.user.username,
            "full_name": tweet.user.displayname,
            "content": tweet.rawContent,
            "created_at": tweet.date,
            "retweet_count": tweet.retweetCount,
            "like_count": tweet.likeCount,
            "reply_count": tweet.replyCount,
            "quote_count": tweet.quoteCount,
            "lang": tweet.lang,
            "hashtags": [tag.text for tag in tweet.hashtags] if tweet.hashtags else [],
            "mentions": [mention.username for mention in tweet.mentionedUsers] if tweet.mentionedUsers else [],
            "urls": [url.url for url in tweet.urls] if tweet.urls else [],
            "is_retweet": tweet.isRetweet,
            "is_reply": bool(tweet.inReplyToTweetId),
            "in_reply_to_tweet_id": tweet.inReplyToTweetId,
            "in_reply_to_user_id": tweet.inReplyToUser.id if tweet.inReplyToUser else None,
            "quoted_tweet_id": tweet.quotedTweet.id if tweet.quotedTweet else None,
            "media_count": len(tweet.media) if tweet.media else 0,
            "json_data": tweet.json()  # ذخیره کل اطلاعات توییت به صورت JSON
        }
