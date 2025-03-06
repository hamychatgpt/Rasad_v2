import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.database import get_db_session
from models.tweet import (
    Tweet, User, Hashtag, TweetHashtag, Mention,
    MediaItem, Keyword, TweetKeyword
)

logger = logging.getLogger(__name__)


class TweetStore:
    """کلاس ذخیره‌سازی توییت‌ها در دیتابیس"""

    def __init__(self):
        """مقداردهی اولیه ذخیره‌کننده توییت"""
        pass

    def save_tweet(self, tweet_data: Dict[str, Any]) -> Optional[int]:
        """
        ذخیره یک توییت در دیتابیس

        :param tweet_data: دیکشنری حاوی اطلاعات توییت
        :return: شناسه توییت ذخیره شده یا None در صورت خطا
        """
        session = get_db_session()

        try:
            # بررسی وجود توییت قبلی
            existing_tweet = session.query(Tweet).filter_by(tweet_id=tweet_data["tweet_id"]).first()
            if existing_tweet:
                logger.debug(f"توییت با شناسه {tweet_data['tweet_id']} قبلاً در دیتابیس وجود دارد.")
                session.close()
                return existing_tweet.id

            # ابتدا کاربر را ذخیره یا به‌روز کنید
            user_id = self._save_or_update_user(session, {
                "user_id": tweet_data["user_id"],
                "username": tweet_data["username"],
                "display_name": tweet_data["full_name"],
                # سایر فیلدهای کاربر اگر در tweet_data موجود باشد
            })

            # ایجاد آبجکت توییت
            tweet = Tweet(
                tweet_id=tweet_data["tweet_id"],
                user_id=tweet_data["user_id"],
                content=tweet_data["content"],
                created_at=tweet_data["created_at"],
                retweet_count=tweet_data.get("retweet_count", 0),
                like_count=tweet_data.get("like_count", 0),
                reply_count=tweet_data.get("reply_count", 0),
                quote_count=tweet_data.get("quote_count", 0),
                lang=tweet_data.get("lang"),
                is_retweet=tweet_data.get("is_retweet", False),
                is_reply=tweet_data.get("is_reply", False),
                in_reply_to_tweet_id=tweet_data.get("in_reply_to_tweet_id"),
                in_reply_to_user_id=tweet_data.get("in_reply_to_user_id"),
                quoted_tweet_id=tweet_data.get("quoted_tweet_id"),
                json_data=tweet_data.get("json_data")
            )

            # افزودن توییت به دیتابیس
            session.add(tweet)
            session.flush()  # به‌روزرسانی شناسه توییت

            # ذخیره هشتگ‌ها
            if "hashtags" in tweet_data and tweet_data["hashtags"]:
                self._save_hashtags(session, tweet.id, tweet_data["hashtags"])

            # ذخیره منشن‌ها
            if "mentions" in tweet_data and tweet_data["mentions"]:
                self._save_mentions(session, tweet.id, tweet_data["mentions"], tweet_data["created_at"])

            # ذخیره رسانه‌ها
            if "media" in tweet_data and tweet_data["media"]:
                self._save_media(session, tweet.id, tweet_data["media"])

            # ارتباط با کلمات کلیدی (اگر داده شده باشد)
            if "keywords" in tweet_data and tweet_data["keywords"]:
                self._save_tweet_keywords(session, tweet.id, tweet_data["keywords"])

            # تأیید تراکنش
            session.commit()
            logger.info(f"توییت با شناسه {tweet_data['tweet_id']} با موفقیت ذخیره شد.")
            return tweet.id

        except Exception as e:
            session.rollback()
            logger.error(f"خطا در ذخیره توییت: {e}")
            return None
        finally:
            session.close()

    def save_tweets(self, tweets_data: List[Dict[str, Any]]) -> List[int]:
        """
        ذخیره چندین توییت در دیتابیس

        :param tweets_data: لیستی از دیکشنری‌های حاوی اطلاعات توییت‌ها
        :return: لیستی از شناسه‌های توییت‌های ذخیره شده
        """
        saved_ids = []
        for tweet_data in tweets_data:
            tweet_id = self.save_tweet(tweet_data)
            if tweet_id:
                saved_ids.append(tweet_id)

        logger.info(f"تعداد {len(saved_ids)} توییت از {len(tweets_data)} با موفقیت ذخیره شد.")
        return saved_ids

    def _save_or_update_user(self, session: Session, user_data: Dict[str, Any]) -> str:
        """
        ذخیره یا به‌روزرسانی اطلاعات کاربر

        :param session: نشست دیتابیس
        :param user_data: دیکشنری حاوی اطلاعات کاربر
        :return: شناسه کاربر
        """
        user = session.query(User).filter_by(user_id=user_data["user_id"]).first()

        if user:
            # به‌روزرسانی اطلاعات کاربر
            user.username = user_data["username"]
            user.display_name = user_data["display_name"]

            if "bio" in user_data:
                user.bio = user_data["bio"]

            if "followers_count" in user_data:
                user.followers_count = user_data["followers_count"]

            if "following_count" in user_data:
                user.following_count = user_data["following_count"]

            if "tweet_count" in user_data:
                user.tweet_count = user_data["tweet_count"]

            if "profile_image_url" in user_data:
                user.profile_image_url = user_data["profile_image_url"]

            if "verified" in user_data:
                user.verified = user_data["verified"]

            if "json_data" in user_data:
                user.json_data = user_data["json_data"]
        else:
            # ایجاد کاربر جدید
            user = User(
                user_id=user_data["user_id"],
                username=user_data["username"],
                display_name=user_data["display_name"],
                bio=user_data.get("bio"),
                followers_count=user_data.get("followers_count", 0),
                following_count=user_data.get("following_count", 0),
                tweet_count=user_data.get("tweet_count", 0),
                created_at=user_data.get("created_at"),
                profile_image_url=user_data.get("profile_image_url"),
                verified=user_data.get("verified", False),
                is_tracked=user_data.get("is_tracked", False),
                importance=user_data.get("importance", 0),
                json_data=user_data.get("json_data")
            )
            session.add(user)
            session.flush()

        # بررسی آیا کاربر باید به صورت ویژه پیگیری شود
        tracked_accounts = self._get_tracked_accounts()
        if user.username in tracked_accounts:
            account_info = tracked_accounts[user.username]
            user.is_tracked = True
            user.importance = account_info.get("importance", 5)

        return user.user_id

    def _save_hashtags(self, session: Session, tweet_id: int, hashtags: List[str]):
        """
        ذخیره هشتگ‌های یک توییت

        :param session: نشست دیتابیس
        :param tweet_id: شناسه توییت
        :param hashtags: لیست هشتگ‌ها
        """
        now = datetime.now()

        for tag_text in hashtags:
            # استانداردسازی هشتگ (حذف # و تبدیل به حروف کوچک)
            tag_text = tag_text.lower().strip("#")

            # بررسی وجود هشتگ
            hashtag = session.query(Hashtag).filter_by(text=tag_text).first()

            if hashtag:
                # به‌روزرسانی هشتگ موجود
                hashtag.last_seen = now
                hashtag.usage_count += 1
            else:
                # ایجاد هشتگ جدید
                hashtag = Hashtag(
                    text=tag_text,
                    first_seen=now,
                    last_seen=now,
                    usage_count=1
                )
                session.add(hashtag)
                session.flush()

            # ایجاد ارتباط بین توییت و هشتگ
            tweet_hashtag = TweetHashtag(
                tweet_id=tweet_id,
                hashtag_id=hashtag.id
            )
            session.add(tweet_hashtag)

    def _save_mentions(self, session: Session, tweet_id: int, mentions: List[str], tweet_date: datetime):
        """
        ذخیره منشن‌های یک توییت

        :param session: نشست دیتابیس
        :param tweet_id: شناسه توییت
        :param mentions: لیست نام‌های کاربری منشن شده
        :param tweet_date: تاریخ توییت
        """
        for username in mentions:
            # استانداردسازی نام کاربری
            username = username.lower().strip("@")

            # بررسی وجود کاربر
            user = session.query(User).filter_by(username=username).first()

            if not user:
                # ایجاد کاربر جدید با اطلاعات حداقلی
                user = User(
                    user_id=f"mention_{username}",  # یک شناسه موقت
                    username=username,
                    display_name=username,
                    created_at=tweet_date
                )
                session.add(user)
                session.flush()

            # ایجاد ارتباط منشن
            mention = Mention(
                tweet_id=tweet_id,
                mentioned_user_id=user.user_id
            )
            session.add(mention)

    def _save_media(self, session: Session, tweet_id: int, media_items: List[Dict[str, Any]]):
        """
        ذخیره رسانه‌های یک توییت

        :param session: نشست دیتابیس
        :param tweet_id: شناسه توییت
        :param media_items: لیست آیتم‌های رسانه
        """
        for media_item in media_items:
            media = MediaItem(
                tweet_id=tweet_id,
                media_type=media_item.get("type", "unknown"),
                media_url=media_item.get("url"),
                alt_text=media_item.get("alt_text")
            )
            session.add(media)

    def _save_tweet_keywords(self, session: Session, tweet_id: int, keywords: List[str]):
        """
        ایجاد ارتباط بین توییت و کلمات کلیدی

        :param session: نشست دیتابیس
        :param tweet_id: شناسه توییت
        :param keywords: لیست کلمات کلیدی
        """
        now = datetime.now()

        for keyword_text in keywords:
            # بررسی وجود کلیدواژه
            keyword = session.query(Keyword).filter_by(text=keyword_text).first()

            if not keyword:
                # ایجاد کلیدواژه جدید
                keyword = Keyword(
                    text=keyword_text,
                    created_at=now,
                    last_used=now,
                    is_active=True
                )
                session.add(keyword)
                session.flush()
            else:
                # به‌روزرسانی زمان آخرین استفاده
                keyword.last_used = now

            # ایجاد ارتباط بین توییت و کلیدواژه
            tweet_keyword = TweetKeyword(
                tweet_id=tweet_id,
                keyword_id=keyword.id
            )
            session.add(tweet_keyword)

    def _get_tracked_accounts(self) -> Dict[str, Dict[str, Any]]:
        """
        دریافت لیست اکانت‌های تحت پیگیری ویژه

        :return: دیکشنری اکانت‌ها با کلید نام کاربری
        """
        from core.config import config
        tracked_accounts = config.get_tracked_accounts()

        # تبدیل به دیکشنری با کلید نام کاربری
        return {account["username"]: account for account in tracked_accounts}

    def find_tweet_by_id(self, tweet_id: str) -> Optional[Dict[str, Any]]:
        """
        جستجوی یک توییت با شناسه آن

        :param tweet_id: شناسه توییت
        :return: دیکشنری اطلاعات توییت یا None در صورت عدم یافتن
        """
        session = get_db_session()

        try:
            tweet = session.query(Tweet).filter_by(tweet_id=tweet_id).first()

            if not tweet:
                return None

            # تبدیل به دیکشنری
            return {
                "id": tweet.id,
                "tweet_id": tweet.tweet_id,
                "user_id": tweet.user_id,
                "content": tweet.content,
                "created_at": tweet.created_at,
                "retweet_count": tweet.retweet_count,
                "like_count": tweet.like_count,
                "reply_count": tweet.reply_count,
                "quote_count": tweet.quote_count,
                "is_retweet": tweet.is_retweet,
                "is_reply": tweet.is_reply,
                "json_data": tweet.json_data
            }
        finally:
            session.close()

    def find_tweets_by_keyword(
            self,
            keyword: str,
            start_time: Optional[datetime] = None,
            end_time: Optional[datetime] = None,
            limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        جستجوی توییت‌ها بر اساس کلیدواژه

        :param keyword: کلیدواژه مورد نظر
        :param start_time: زمان شروع جستجو (اختیاری)
        :param end_time: زمان پایان جستجو (اختیاری)
        :param limit: حداکثر تعداد نتایج
        :return: لیست توییت‌های یافت شده
        """
        session = get_db_session()

        try:
            # ابتدا کلیدواژه را پیدا کنید
            keyword_obj = session.query(Keyword).filter_by(text=keyword).first()

            if not keyword_obj:
                return []

            # ساخت کوئری پایه
            query = session.query(Tweet).join(
                TweetKeyword, Tweet.id == TweetKeyword.tweet_id
            ).filter(
                TweetKeyword.keyword_id == keyword_obj.id
            )

            # اعمال فیلترهای زمانی
            if start_time:
                query = query.filter(Tweet.created_at >= start_time)

            if end_time:
                query = query.filter(Tweet.created_at <= end_time)

            # مرتب‌سازی بر اساس زمان (جدیدترین اول)
            query = query.order_by(Tweet.created_at.desc())

            # اعمال محدودیت تعداد
            query = query.limit(limit)

            # اجرای کوئری و تبدیل نتایج به دیکشنری
            results = []
            for tweet in query.all():
                results.append({
                    "id": tweet.id,
                    "tweet_id": tweet.tweet_id,
                    "user_id": tweet.user_id,
                    "content": tweet.content,
                    "created_at": tweet.created_at,
                    "retweet_count": tweet.retweet_count,
                    "like_count": tweet.like_count,
                    "reply_count": tweet.reply_count,
                    "quote_count": tweet.quote_count,
                    "is_retweet": tweet.is_retweet,
                    "is_reply": tweet.is_reply,
                    "json_data": tweet.json_data
                })

            return results
        finally:
            session.close()

    def get_oldest_tweet_for_keyword(self, keyword: str) -> Optional[Dict[str, Any]]:
        """
        دریافت قدیمی‌ترین توییت برای یک کلیدواژه

        :param keyword: کلیدواژه مورد نظر
        :return: دیکشنری اطلاعات توییت یا None در صورت عدم یافتن
        """
        session = get_db_session()

        try:
            # ابتدا کلیدواژه را پیدا کنید
            keyword_obj = session.query(Keyword).filter_by(text=keyword).first()

            if not keyword_obj:
                return None

            # جستجوی قدیمی‌ترین توییت
            tweet = session.query(Tweet).join(
                TweetKeyword, Tweet.id == TweetKeyword.tweet_id
            ).filter(
                TweetKeyword.keyword_id == keyword_obj.id
            ).order_by(
                Tweet.created_at.asc()
            ).first()

            if not tweet:
                return None

            # تبدیل به دیکشنری
            return {
                "id": tweet.id,
                "tweet_id": tweet.tweet_id,
                "user_id": tweet.user_id,
                "content": tweet.content,
                "created_at": tweet.created_at,
                "retweet_count": tweet.retweet_count,
                "like_count": tweet.like_count,
                "reply_count": tweet.reply_count,
                "quote_count": tweet.quote_count,
                "is_retweet": tweet.is_retweet,
                "is_reply": tweet.is_reply,
                "json_data": tweet.json_data
            }
        finally:
            session.close()