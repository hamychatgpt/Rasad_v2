import re
from typing import List, Optional

# تلاش برای وارد کردن کتابخانه هضم - غیرفعال شده
hazm_available = False  # مستقیماً به False تنظیم کنید

def extract_keywords(text: str) -> List[str]:
    """
    استخراج کلمات کلیدی از متن توییت - نسخه ساده‌شده

    :param text: متن توییت
    :return: لیست کلمات کلیدی استخراج شده
    """
    keywords = []

    # استخراج هشتگ‌ها
    hashtags = extract_hashtags(text)
    if hashtags:
        keywords.extend(hashtags)

    # حذف تکرارها و استانداردسازی
    unique_keywords = list(set([k.lower() for k in keywords]))

    return unique_keywords


def extract_hashtags(text: str) -> List[str]:
    """
    استخراج هشتگ‌ها از متن

    :param text: متن توییت
    :return: لیست هشتگ‌ها
    """
    if not text:
        return []

    # الگوی یافتن هشتگ
    hashtag_pattern = r'#(\w+)'

    # جستجو برای هشتگ‌ها
    hashtags = re.findall(hashtag_pattern, text)

    return hashtags


def extract_keywords_with_hazm(text: str) -> List[str]:
    """
    استخراج کلمات کلیدی - نسخه ساده‌شده

    :param text: متن توییت
    :return: لیست کلمات کلیدی
    """
    # بازگشت لیست خالی - غیرفعال شده
    return []


def clean_text(text: str) -> str:
    """
    پاکسازی و استانداردسازی متن - نسخه ساده‌شده

    :param text: متن ورودی
    :return: متن پاکسازی شده
    """
    if not text:
        return ""

    # حذف لینک‌ها
    text = re.sub(r'https?://\S+', '', text)

    # حذف منشن‌ها
    text = re.sub(r'@\w+', '', text)

    # حذف کاراکترهای خاص و فاصله‌های اضافی
    text = re.sub(r'[^\w\s\u0600-\u06FF]', ' ', text)  # حفظ کاراکترهای فارسی
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def detect_sentiment(text: str) -> Optional[float]:
    """
    تشخیص احساسات متن - نسخه ساده‌شده

    :param text: متن ورودی
    :return: امتیاز احساسات (0 برای همه موارد)
    """
    # همیشه خنثی (0) برمی‌گرداند - غیرفعال شده
    return 0