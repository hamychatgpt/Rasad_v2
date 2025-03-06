from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy_utils import database_exists, create_database
from urllib.parse import quote_plus

from core.config import config

# ایجاد کلاس پایه برای همه مدل‌ها
Base = declarative_base()


# تابع ایجاد موتور دیتابیس بر اساس تنظیمات
def create_db_engine():
    """ایجاد موتور دیتابیس SQLAlchemy بر اساس تنظیمات"""
    db_config = config.get('database')
    db_type = db_config.get('type', 'sqlite')  # تعریف اولیه db_type

    # اگر connection_string به صورت مستقیم تعریف شده باشد
    if 'connection_string' in db_config:
        connection_string = db_config['connection_string']
    else:
        # در غیر این صورت، ساخت connection string بر اساس پارامترها
        host = db_config.get('host', 'localhost')
        port = db_config.get('port', 5432)
        user = db_config.get('user', 'postgres')
        password = quote_plus(db_config.get('password', ''))
        db_name = db_config.get('name', 'twitter_monitor')

        if db_type == 'postgresql':
            connection_string = f"postgresql://{user}:{password}@{host}:{port}/{db_name}"
        elif db_type == 'sqlite':
            connection_string = f"sqlite:///{db_name}.db"
        else:
            raise ValueError(f"نوع دیتابیس نامعتبر: {db_type}")

    # ایجاد موتور SQLAlchemy
    engine = create_engine(connection_string, echo=False)

    # بررسی وجود دیتابیس و ایجاد آن در صورت نیاز
    if not database_exists(engine.url) and db_type != 'sqlite':
        create_database(engine.url)

    return engine

# ایجاد و راه‌اندازی موتور دیتابیس
engine = create_db_engine()

# ایجاد کلاس Session برای استفاده در برنامه
SessionFactory = sessionmaker(bind=engine)
Session = scoped_session(SessionFactory)


def get_db_session():
    """ایجاد یک نشست دیتابیس"""
    return Session()


def init_db():
    """ایجاد تمام جداول تعریف شده در مدل‌ها"""
    Base.metadata.create_all(engine)


def close_db_connection():
    """بستن اتصال دیتابیس"""
    Session.remove()