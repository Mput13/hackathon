import asyncio
import logging

from aiogram import Bot
from aiogram.utils.callback_answer import CallbackAnswerMiddleware
from aiogram_dialog import setup_dialogs

from app import dp, bot
from commands.admin_menu import admin_router
from commands.create_request import create_request_router
# from commands.get_stats import stats_router
from commands.intro import entry_router, account_router
from commands.log_in import log_in_router
from commands.my_requests import my_requests_router
from commands.sign_in import sign_in_router
from core.config import config
from utils.utils import setup_logging

logger = logging.getLogger('startup')


async def check_user_request_status(bot: Bot):
    while True:
        pass

        await asyncio.sleep(100)


async def main(bot) -> None:
    logger.info('Starting the bot')
    setup_logging(level=config.log_level)
    dp.include_routers(
        entry_router,
        sign_in_router,
        log_in_router,
        admin_router,
        create_request_router,
        account_router,
        my_requests_router
    )
    dp.callback_query.middleware(CallbackAnswerMiddleware())
    setup_dialogs(dp)

    asyncio.create_task(check_user_request_status(bot))

    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main(bot))
