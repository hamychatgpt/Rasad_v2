import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from core.config import config
from data_sources.twitter.scraper import TwitterScraper
from pipeline.storage.tweet_store import TweetStore
from utils.date_utils import datetime_to_str, str_to_datetime
from utils.text_utils import extract_keywords

logger = logging.getLogger(__name__)


class KeywordCollector:
    """جمع‌آوری کننده توییت‌ها بر اساس کلیدواژه‌ها"""

    def __init__(self, twitter_scraper: TwitterScraper, tweet_store: TweetStore):
        """
        مقداردهی اولیه جمع‌آوری کننده کلیدواژه

        :param twitter_scraper: نمونه کلاس استخراج‌کننده توییتر
        :param tweet_store: نمونه کلاس ذخیره‌کننده توییت
        """
        self.scraper = twitter_scraper
        self.store = tweet_store
        self.keywords = config.get_keywords()

    async def collect_for_keyword(
            self,
            keyword: str,
            limit: int = 100,
            since_id: Optional[str] = None,
            until_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        جمع‌آوری توییت‌ها برای یک کلیدواژه

        :param keyword: کلیدواژه مورد نظر
        :param limit: حداکثر تعداد توییت‌ها
        :param since_id: شناسه توییت شروع (اختیاری)
        :param until_date: تاریخ پایان جستجو (اختیاری)
        :return: لیست دیکشنری‌های توییت‌های جمع‌آوری شده
        """
        logger.info(f"شروع جمع‌آوری توییت‌ها برای کلیدواژه: {keyword}")

        # جستجو برای کلیدواژه
        tweets = await self.scraper.search_tweets(
            keyword,
            limit=limit,
            since_id=since_id,
            until_date=until_date
        )

        if not tweets:
            logger.info(f"هیچ توییتی برای کلیدواژه {keyword} یافت نشد.")
            return []

        logger.info(f"تعداد {len(tweets)} توییت برای کلیدواژه {keyword} یافت شد.")

        # تبدیل توییت‌ها به فرمت قابل ذخیره‌سازی
        processed_tweets = []
        for tweet in tweets:
            # تبدیل توییت به دیکشنری
            tweet_dict = self._convert_tweet_to_dict(tweet)

            # افزودن کلیدواژه‌های یافت شده به توییت
            tweet_dict["keywords"] = [keyword]  # کلیدواژه اصلی

            # استخراج کلیدواژه‌های اضافی از متن
            additional_keywords = extract_keywords(tweet.rawContent)
            if additional_keywords:
                tweet_dict["keywords"].extend(additional_keywords)

            processed_tweets.append(tweet_dict)

        # ذخیره توییت‌ها در دیتابیس
        saved_ids = self.store.save_tweets(processed_tweets)

        logger.info(f"تعداد {len(saved_ids)} توییت برای کلیدواژه {keyword} با موفقیت ذخیره شد.")

        return processed_tweets

    async def collect_for_all_keywords(self, limit_per_keyword: int = 100) -> Dict[str, int]:
        """
        جمع‌آوری توییت‌ها برای تمام کلیدواژه‌های فعال

        :param limit_per_keyword: حداکثر تعداد توییت برای هر کلیدواژه
        :return: دیکشنری تعداد توییت‌های جمع‌آوری شده برای هر کلیدواژه
        """
        results = {}

        for keyword_info in self.keywords:
            keyword = keyword_info["text"]

            tweets = await self.collect_for_keyword(keyword, limit=limit_per_keyword)
            results[keyword] = len(tweets)

            # مکث کوتاه بین درخواست‌ها برای جلوگیری از مسدود شدن
            await asyncio.sleep(2)

        return results

    async def archive_for_keyword(self, keyword: str, days_back: int = 7, limit: int = 500) -> List[Dict[str, Any]]:
        """
        تکمیل آرشیو توییت‌ها برای یک کلیدواژه (توییت‌های قدیمی‌تر)

        :param keyword: کلیدواژه مورد نظر
        :param days_back: تعداد روزهای قبل برای جستجو
        :param limit: حداکثر تعداد توییت‌ها
        :return: لیست دیکشنری‌های توییت‌های جمع‌آوری شده
        """
        # دریافت قدیمی‌ترین توییت ذخیره شده برای این کلیدواژه
        oldest_tweet = self.store.get_oldest_tweet_for_keyword(keyword)

        if not oldest_tweet:
            logger.info(f"هیچ توییت قبلی برای کلیدواژه {keyword} یافت نشد. شروع از زمان فعلی.")
            return await self.collect_for_keyword(keyword, limit=limit)

        # تاریخ قدیمی‌ترین توییت
        oldest_date = oldest_tweet["created_at"]
        end_date = oldest_date - timedelta(days=days_back)

        logger.info(
            f"تکمیل آرشیو برای کلیدواژه {keyword} از تاریخ {datetime_to_str(oldest_date)} تا {datetime_to_str(end_date)}")

        # جمع‌آوری توییت‌های قدیمی‌تر
        tweets = await self.collect_for_keyword(
            keyword,
            limit=limit,
            until_date=oldest_date
        )

        return tweets

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