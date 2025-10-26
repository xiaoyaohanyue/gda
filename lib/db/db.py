from .base import ManagedBase
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker
from lib.conf.config import settings
from .model import ListItem
from typing import AsyncGenerator



bot_engine: AsyncEngine = create_async_engine(
    settings.db_url,
    echo=False,              # 调试时可 True
    pool_pre_ping=True,      # 避免 MySQL 连接闲置断开
    pool_recycle=1800,       # 秒，避免 "MySQL server has gone away"
)

async_session = sessionmaker(
    bot_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session

async def run_db_session(fn, *args, **kwargs):
    async with async_session() as session:
        return await fn(session, *args, **kwargs)

async def init_db() -> None:
    async with bot_engine.begin() as conn:
        await conn.run_sync(ManagedBase.metadata.create_all)
