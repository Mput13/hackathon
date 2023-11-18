import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import User
from schemas.user import UserInit, UserShort
from utils.utils import to_snake


class UserRepository:
    """
    Отвечает за работу с данными пользователя
    """

    def __init__(self):
        self.logger = logging.getLogger(to_snake(self.__class__.__name__))

    async def create_user(self, session: AsyncSession, data: UserInit) -> UserShort:
        if existing := (await self.get_user_by_chat_id(session, data.chat_id)):
            self.logger.debug(f'User with chat_id: {data.chat_id} already exists. Skipping creation')
            return UserShort.model_validate(existing)

        self.logger.debug(f'creating user: {data}')
        user = User(**data.model_dump())
        session.add(user)
        await session.flush([user])

        return UserShort.model_validate(user)

    async def get_user_by_chat_id(self, session: AsyncSession, chat_id: int) -> UserShort | None:
        self.logger.debug(f'fetching user with chat_id: {chat_id}')
        fetched = await session.scalar(select(User).where(User.chat_id == chat_id))
        if not fetched:
            self.logger.debug(f'user not found by chat_id: {chat_id}')
            return None
        obj = UserShort.model_validate(fetched)
        self.logger.info(f'found by chat_id: {chat_id} - {obj}')
        return obj


user_repository = UserRepository()  # в случае с нормальным DI, этот объект бы создавался через него в отдельном месте, а не тут
