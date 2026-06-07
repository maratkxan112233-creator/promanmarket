from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
)

from app.config.settings import settings


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)
