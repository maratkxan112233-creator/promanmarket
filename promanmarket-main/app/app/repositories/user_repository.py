from sqlalchemy import select

from app.database.models.user import User
from app.database.session import AsyncSessionLocal


class UserRepository:

    @staticmethod
    async def get_by_telegram_id(
        telegram_id: int
    ):
        async with AsyncSessionLocal() as session:

            result = await session.execute(
                select(User).where(
                    User.telegram_id == telegram_id
                )
            )

            return result.scalar_one_or_none()

    @staticmethod
    async def create(
        telegram_id: int,
        username: str | None,
        full_name: str,
        role: str = "buyer"
    ):
        async with AsyncSessionLocal() as session:

            user = User(
                telegram_id=telegram_id,
                username=username,
                full_name=full_name,
                role=role
            )

            session.add(user)

            await session.commit()

            await session.refresh(user)

            return user
