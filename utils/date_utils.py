from datetime import datetime, timedelta
from typing import Optional


def datetime_to_str(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    تبدیل شیء datetime به رشته

    :param dt: شیء datetime
    :param format_str: قالب رشته خروجی
    :return: رشته تاریخ و زمان
    """
    return dt.strftime(format_str)


def str_to_datetime(date_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> Optional[datetime]:
    """
    تبدیل رشته به شیء datetime

    :param date_str: رشته تاریخ و زمان
    :param format_str: قالب رشته ورودی
    :return: شیء datetime یا None در صورت خطا
    """
    try:
        return datetime.strptime(date_str, format_str)
    except ValueError:
        return None


def get_yesterday() -> datetime:
    """
    دریافت تاریخ دیروز

    :return: شیء datetime برای دیروز (با زمان 00:00:00)
    """
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    return today - timedelta(days=1)


def get_week_ago() -> datetime:
    """
    دریافت تاریخ یک هفته قبل

    :return: شیء datetime برای یک هفته قبل
    """
    return datetime.now() - timedelta(days=7)


def get_month_ago() -> datetime:
    """
    دریافت تاریخ یک ماه قبل (تقریبی، 30 روز)

    :return: شیء datetime برای یک ماه قبل
    """
    return datetime.now() - timedelta(days=30)


def get_time_diff_str(dt1: datetime, dt2: datetime) -> str:
    """
    محاسبه اختلاف زمانی بین دو تاریخ به صورت رشته فارسی

    :param dt1: تاریخ اول
    :param dt2: تاریخ دوم
    :return: رشته اختلاف زمانی به فارسی
    """
    diff = abs(dt1 - dt2)

    # تبدیل به ثانیه
    seconds = diff.total_seconds()

    if seconds < 60:
        return f"{int(seconds)} ثانیه"

    # تبدیل به دقیقه
    minutes = seconds / 60
    if minutes < 60:
        return f"{int(minutes)} دقیقه"

    # تبدیل به ساعت
    hours = minutes / 60
    if hours < 24:
        return f"{int(hours)} ساعت"

    # تبدیل به روز
    days = hours / 24
    if days < 30:
        return f"{int(days)} روز"

    # تبدیل به ماه (تقریبی)
    months = days / 30
    if months < 12:
        return f"{int(months)} ماه"

    # تبدیل به سال
    years = months / 12
    return f"{int(years)} سال"


def is_same_day(dt1: datetime, dt2: datetime) -> bool:
    """
    بررسی آیا دو تاریخ در یک روز هستند

    :param dt1: تاریخ اول
    :param dt2: تاریخ دوم
    :return: True اگر در یک روز باشند
    """
    return (
            dt1.year == dt2.year and
            dt1.month == dt2.month and
            dt1.day == dt2.day
    )


def is_same_week(dt1: datetime, dt2: datetime) -> bool:
    """
    بررسی آیا دو تاریخ در یک هفته هستند

    :param dt1: تاریخ اول
    :param dt2: تاریخ دوم
    :return: True اگر در یک هفته باشند
    """
    # تعیین اولین روز هفته برای هر تاریخ (دوشنبه: 0، یکشنبه: 6)
    dt1_week_start = dt1 - timedelta(days=dt1.weekday())
    dt2_week_start = dt2 - timedelta(days=dt2.weekday())

    return (
            dt1_week_start.year == dt2_week_start.year and
            dt1_week_start.month == dt2_week_start.month and
            dt1_week_start.day == dt2_week_start.day
    )


def is_same_month(dt1: datetime, dt2: datetime) -> bool:
    """
    بررسی آیا دو تاریخ در یک ماه هستند

    :param dt1: تاریخ اول
    :param dt2: تاریخ دوم
    :return: True اگر در یک ماه باشند
    """
    return (
            dt1.year == dt2.year and
            dt1.month == dt2.month
    )