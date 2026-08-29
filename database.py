from sqlalchemy.ext.asyncio import create_async_engine,AsyncSession,async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime
from sqlalchemy import func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from geoalchemy2.shape import to_shape#二进制编码 → 转成 Python 的点 / 线 / 面对象

from config import settings



# 用户基类
class Base(DeclarativeBase):
    __abstract__ = True

    create_time: Mapped[datetime] = mapped_column(
        insert_default=func.now(),
        comment="创建时间"
    )
    update_time: Mapped[datetime] = mapped_column(
        insert_default=func.now(),
        onupdate=func.now(),
        comment="更新时间"
    )

# 数据库连接由 FastAPI 依赖注入统一管理：
# create_async_engine 建立数据库连接池并生成异步引擎，
# async_sessionmaker 将引擎封装为会话工厂 AsyncSessionLocal；
# 每个请求抵达时，get_db 从工厂创建一个独立的 AsyncSession 供接口使用，请求结束自动归还连接池。

# 数据库依赖注入
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            # await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# 异步引擎创建
async_engine = create_async_engine(
    settings.ASYNC_DATABASE_URI,
    echo=settings.ECHO_SQL,
    pool_size=settings.POOL_SIZE,
    max_overflow=settings.MAX_OVERFLOW
)

# 异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)

# 建表函数
async def create_tables():
    """应用启动时自动创建所有表"""
    async with async_engine.begin() as conn:
        #创建一个带事务的连接，执行完自动提交
        #begin()如果一件事本就只发生一次（启动建表、定时扫描、关停清场），写成"直接调用"
        await conn.run_sync(Base.metadata.create_all)