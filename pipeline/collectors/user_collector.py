import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from core.config import config
from data_sources.twitter.scraper import TwitterScraper
from pipeline.storage.tweet_store import TweetStore

logger = logging.getLogger(__name__)


class UserCollector:
    """جمع‌آوری کننده توییت‌های کاربران خاص"""

    def __init__(self, twitter_scraper: TwitterScraper, tweet_store: TweetStore):
        """
        مقداردهی اولیه جمع‌آوری کننده کاربر

        :param twitter_scraper: نمونه کلاس استخراج‌کننده توییتر
        :param tweet_store: نمونه کلاس ذخیره‌کننده توییت
        """
        self.scraper = twitter_scraper
        self.store = tweet_store
        self.tracked_accounts = config.get_tracked_accounts()

    async def collect_for_user(self, username: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        جمع‌آوری توییت‌های یک کاربر خاص

        :param username: نام کاربری
        :param limit: حداکثر تعداد توییت‌ها
        :return: لیست دیکشنری‌های توییت‌های جمع‌آوری شده
        """
        logger.info(f"شروع جمع‌آوری توییت‌های کاربر: {username}")

        # دریافت توییت‌های کاربر
        tweets = await self.scraper.get_user_tweets(username, limit=limit)

        if not tweets:
            logger.info(f"هیچ توییتی برای کاربر {username} یافت نشد.")
            return []

        logger.info(f"تعداد {len(tweets)} توییت برای کاربر {username} یافت شد.")

        # تبدیل توییت‌ها به فرمت قابل ذخیره‌سازی
        processed_tweets = []
        for tweet in tweets:
            # تبدیل توییت به دیکشنری
            tweet_dict = self._convert_tweet_to_dict(tweet)

            # علامت‌گذاری توییت‌های مدیران
            is_manager = self._is_manager_account(username)
            if is_manager:
                # افزودن کلیدواژه ویژه برای توییت‌های مدیر
                tweet_dict["keywords"] = ["manager_tweet"]

            processed_tweets.append(tweet_dict)

        # ذخیره توییت‌ها در دیتابیس
        saved_ids = self.store.save_tweets(processed_tweets)

        logger.info(f"تعداد {len(saved_ids)} توییت برای کاربر {username} با موفقیت ذخیره شد.")

        return processed_tweets

    async def collect_for_all_tracked_users(self, limit_per_user: int = 100) -> Dict[str, int]:
        """
        جمع‌آوری توییت‌ها برای تمام کاربران تحت پیگیری

        :param limit_per_user: حداکثر تعداد توییت برای هر کاربر
        :return: دیکشنری تعداد توییت‌های جمع‌آوری شده برای هر کاربر
        """
        results = {}

        for account in self.tracked_accounts:
            username = account["username"]

            tweets = await self.collect_for_user(username, limit=limit_per_user)
            results[username] = len(tweets)

            # مکث کوتاه بین درخواست‌ها برای جلوگیری از مسدود شدن
            await asyncio.sleep(2)

        return results

    async def collect_user_interactions(self, username: str, tweet_limit: int = 20, reply_limit: int = 50) -> Dict[
        str, Any]:
        """
        جمع‌آوری تعاملات کاربر (توییت‌ها و پاسخ‌های آن‌ها)

        :param username: نام کاربری
        :param tweet_limit: حداکثر تعداد توییت‌های کاربر
        :param reply_limit: حداکثر تعداد پاسخ برای هر توییت
        :return: دیکشنری نتایج
        """
        logger.info(f"جمع‌آوری تعاملات کاربر {username}")

        # ابتدا توییت‌های کاربر را دریافت کنید
        tweets = await self.scraper.get_user_tweets(username, limit=tweet_limit)

        if not tweets:
            logger.info(f"هیچ توییتی برای کاربر {username} یافت نشد.")
            return {"tweets": [], "replies": {}, "total_replies": 0}

        # ذخیره توییت‌ها
        processed_tweets = []
        for tweet in tweets:
            tweet_dict = self._convert_tweet_to_dict(tweet)
            processed_tweets.append(tweet_dict)

        self.store.save_tweets(processed_tweets)

        # جمع‌آوری پاسخ‌ها برای هر توییت
        all_replies = {}
        total_replies = 0

        for tweet in tweets:
            tweet_id = tweet.id

            # دریافت پاسخ‌ها
            replies = await self.scraper.get_replies(tweet_id, limit=reply_limit)

            if replies:
                # پردازش و ذخیره پاسخ‌ها
                processed_replies = []
                for reply in replies:
                    reply_dict = self._convert_tweet_to_dict(reply)
                    processed_replies.append(reply_dict)

                self.store.save_tweets(processed_replies)

                # افزودن به نتایج
                all_replies[tweet_id] = len(processed_replies)
                total_replies += len(processed_replies)

                logger.info(f"تعداد {len(processed_replies)} پاسخ برای توییت {tweet_id} یافت و ذخیره شد.")

            # مکث کوتاه بین درخواست‌ها
            await asyncio.sleep(1)

        return {
            "tweets": len(processed_tweets),
            "replies": all_replies,
            "total_replies": total_replies
        }

    def _convert_tweet_to_dict(self, tweet) -> Dict[str, Any]:
        """
        تبدیل آبجکت توییت به دیکشنری

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
            "media": self._extract_media(tweet),
            "json_data": tweet.json()
        }

    def _extract_media(self, tweet) -> List[Dict[str, Any]]:
        """
        استخراج اطلاعات رسانه از توییت

        :param tweet: آبجکت توییت
        :return: لیست دیکشنری‌های رسانه
        """
        media_items = []

        if hasattr(tweet, 'media') and tweet.media:
            for media in tweet.media:
                media_item = {
                    "type": media.type,
                    "url": media.url if hasattr(media, 'url') else None,
                    "alt_text": media.altText if hasattr(media, 'altText') else None
                }
                media_items.append(media_item)

        return media_items

    def _is_manager_account(self, username: str) -> bool:
        """
        بررسی آیا کاربر جزو مدیران است

        :param username: نام کاربری
        :return: True اگر کاربر مدیر باشد
        """
        for account in self.tracked_accounts:
            if account["username"].lower() == username.lower() and account.get("role") == "manager":
                return True

        return False