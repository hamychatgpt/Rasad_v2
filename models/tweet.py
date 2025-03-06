from sqlalchemy import Column, String, Integer, DateTime, Boolean, JSON, ForeignKey, Text, Float
from sqlalchemy.orm import relationship

from core.database import Base


class Tweet(Base):
    """مدل دیتابیس برای توییت‌ها"""

    __tablename__ = "tweets"

    id = Column(Integer, primary_key=True)
    tweet_id = Column(String(64), unique=True, nullable=False, index=True)
    user_id = Column(String(64), ForeignKey("users.user_id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, index=True)
    retweet_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    reply_count = Column(Integer, default=0)
    quote_count = Column(Integer, default=0)
    lang = Column(String(10))
    source = Column(String(256))

    # ارتباط‌ها
    is_retweet = Column(Boolean, default=False)
    is_reply = Column(Boolean, default=False)
    in_reply_to_tweet_id = Column(String(64), nullable=True)
    in_reply_to_user_id = Column(String(64), nullable=True)
    quoted_tweet_id = Column(String(64), nullable=True)

    # تحلیل احساسات
    sentiment_score = Column(Float, nullable=True)  # -1 (منفی) تا 1 (مثبت)

    # داده‌های اضافی
    json_data = Column(JSON, nullable=True)

    # ارتباط با سایر جداول
    user = relationship("User", back_populates="tweets")
    hashtags = relationship("TweetHashtag", back_populates="tweet")
    mentions = relationship("Mention", back_populates="tweet")
    media_items = relationship("MediaItem", back_populates="tweet")
    keywords = relationship("TweetKeyword", back_populates="tweet")

    def __repr__(self):
        return f"<Tweet {self.tweet_id}>"


class User(Base):
    """مدل دیتابیس برای کاربران توییتر"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    user_id = Column(String(64), unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=False, index=True)
    display_name = Column(String(255))
    bio = Column(Text, nullable=True)
    followers_count = Column(Integer, default=0)
    following_count = Column(Integer, default=0)
    tweet_count = Column(Integer, default=0)
    created_at = Column(DateTime, nullable=True)
    profile_image_url = Column(String(512), nullable=True)
    verified = Column(Boolean, default=False)

    # پیگیری ویژه
    is_tracked = Column(Boolean, default=False, index=True)
    importance = Column(Integer, default=0)  # 0-10
    influence_score = Column(Float, default=0.0)  # 0-100

    # تحلیل احساسات
    sentiment_category = Column(String(20), nullable=True)  # "positive", "negative", "neutral"

    # داده‌های اضافی
    json_data = Column(JSON, nullable=True)

    # ارتباط با سایر جداول
    tweets = relationship("Tweet", back_populates="user")
    mentions = relationship("Mention", back_populates="mentioned_user")

    def __repr__(self):
        return f"<User {self.username}>"


class Hashtag(Base):
    """مدل دیتابیس برای هشتگ‌ها"""

    __tablename__ = "hashtags"

    id = Column(Integer, primary_key=True)
    text = Column(String(255), unique=True, nullable=False, index=True)
    first_seen = Column(DateTime, nullable=False)
    last_seen = Column(DateTime, nullable=False)
    usage_count = Column(Integer, default=1)

    # ارتباط با سایر جداول
    tweets = relationship("TweetHashtag", back_populates="hashtag")

    def __repr__(self):
        return f"<Hashtag {self.text}>"


class TweetHashtag(Base):
    """جدول ارتباطی بین توییت‌ها و هشتگ‌ها"""

    __tablename__ = "tweet_hashtags"

    id = Column(Integer, primary_key=True)
    tweet_id = Column(Integer, ForeignKey("tweets.id"), nullable=False)
    hashtag_id = Column(Integer, ForeignKey("hashtags.id"), nullable=False)

    # ارتباط با سایر جداول
    tweet = relationship("Tweet", back_populates="hashtags")
    hashtag = relationship("Hashtag", back_populates="tweets")

    def __repr__(self):
        return f"<TweetHashtag {self.tweet_id}:{self.hashtag_id}>"


class Mention(Base):
    """مدل دیتابیس برای منشن‌ها در توییت‌ها"""

    __tablename__ = "mentions"

    id = Column(Integer, primary_key=True)
    tweet_id = Column(Integer, ForeignKey("tweets.id"), nullable=False)
    mentioned_user_id = Column(String(64), ForeignKey("users.user_id"), nullable=False)

    # ارتباط با سایر جداول
    tweet = relationship("Tweet", back_populates="mentions")
    mentioned_user = relationship("User", back_populates="mentions")

    def __repr__(self):
        return f"<Mention {self.tweet_id}:{self.mentioned_user_id}>"


class MediaItem(Base):
    """مدل دیتابیس برای رسانه‌های توییت‌ها (تصاویر، ویدیوها و...)"""

    __tablename__ = "media_items"

    id = Column(Integer, primary_key=True)
    tweet_id = Column(Integer, ForeignKey("tweets.id"), nullable=False)
    media_type = Column(String(64), nullable=False)  # "photo", "video", "link", etc.
    media_url = Column(String(512), nullable=True)
    alt_text = Column(Text, nullable=True)

    # ارتباط با سایر جداول
    tweet = relationship("Tweet", back_populates="media_items")

    def __repr__(self):
        return f"<MediaItem {self.tweet_id}:{self.media_type}>"


class Keyword(Base):
    """مدل دیتابیس برای کلمات کلیدی مورد پایش"""

    __tablename__ = "keywords"

    id = Column(Integer, primary_key=True)
    text = Column(String(255), unique=True, nullable=False, index=True)
    category = Column(String(64), nullable=True)
    importance = Column(Integer, default=5)  # 1-10
    created_at = Column(DateTime, nullable=False)
    last_used = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    # ارتباط با سایر جداول
    tweets = relationship("TweetKeyword", back_populates="keyword")
    waves = relationship("CriticalWave", back_populates="keyword")
    schedules = relationship("MonitoringSchedule", back_populates="keyword")

    def __repr__(self):
        return f"<Keyword {self.text}>"


class TweetKeyword(Base):
    """جدول ارتباطی بین توییت‌ها و کلمات کلیدی"""

    __tablename__ = "tweet_keywords"

    id = Column(Integer, primary_key=True)
    tweet_id = Column(Integer, ForeignKey("tweets.id"), nullable=False)
    keyword_id = Column(Integer, ForeignKey("keywords.id"), nullable=False)

    # ارتباط با سایر جداول
    tweet = relationship("Tweet", back_populates="keywords")
    keyword = relationship("Keyword", back_populates="tweets")

    def __repr__(self):
        return f"<TweetKeyword {self.tweet_id}:{self.keyword_id}>"


class CriticalWave(Base):
    """مدل دیتابیس برای موج‌های انتقادی"""

    __tablename__ = "critical_waves"

    id = Column(Integer, primary_key=True)
    keyword_id = Column(Integer, ForeignKey("keywords.id"), nullable=False)
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=True)  # NULL برای موج‌های فعال
    intensity = Column(Float, default=0.0)  # 0-100
    sentiment = Column(Float, default=0.0)  # -1 تا 1
    status = Column(String(20), default="active")  # "active", "ended"
    description = Column(Text, nullable=True)

    # ارتباط با سایر جداول
    keyword = relationship("Keyword", back_populates="waves")
    reports = relationship("Report", back_populates="related_wave")

    def __repr__(self):
        return f"<CriticalWave {self.id}>"


class MonitoringSchedule(Base):
    """مدل دیتابیس برای زمان‌بندی پایش کلمات کلیدی"""

    __tablename__ = "monitoring_schedules"

    id = Column(Integer, primary_key=True)
    keyword_id = Column(Integer, ForeignKey("keywords.id"), nullable=False)
    normal_interval = Column(Integer, default=1200)  # بازه زمانی عادی (ثانیه)
    critical_interval = Column(Integer, default=300)  # بازه زمانی بحرانی (ثانیه)
    last_check = Column(DateTime, nullable=True)
    is_critical = Column(Boolean, default=False)  # وضعیت بحرانی

    # ارتباط با سایر جداول
    keyword = relationship("Keyword", back_populates="schedules")

    def __repr__(self):
        return f"<MonitoringSchedule {self.keyword_id}>"


class Report(Base):
    """مدل دیتابیس برای گزارش‌ها"""

    __tablename__ = "reports"

    id = Column(Integer, primary_key=True)
    report_type = Column(String(64), nullable=False)  # "daily", "weekly", "alert"
    generated_at = Column(DateTime, nullable=False)
    related_wave_id = Column(Integer, ForeignKey("critical_waves.id"), nullable=True)
    content = Column(Text, nullable=True)
    sent_status = Column(String(20), default="pending")  # "pending", "sent", "failed"

    # ارتباط با سایر جداول
    related_wave = relationship("CriticalWave", back_populates="reports")

    def __repr__(self):
        return f"<Report {self.id} {self.report_type}>"