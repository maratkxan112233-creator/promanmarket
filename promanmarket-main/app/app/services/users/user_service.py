from app.app.repositories.user_repository import UserRepository


class UserService:

    @staticmethod
    async def get_or_create_user(
        telegram_id: int,
        username: str | None,
        full_name: str
    ):
        user = await UserRepository.get_by_telegram_id(
            telegram_id
        )

        if user:
            return user

        return await UserRepository.create(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name
        )
