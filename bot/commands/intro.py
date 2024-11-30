from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram_dialog import Window, Dialog, DialogManager, StartMode
from aiogram_dialog.widgets.kbd import Button, Column
from aiogram_dialog.widgets.text import Const

from app import dp
from commands.state_classes import AdminMenu, LogIn, SignIn, \
    Entry, AccountMainPage, MyRequests, CreateRequest
from core.text import dialogs
from repositories.user_repository import user_repository
from schemas.user import UserInit
from services.account_service import account_service
from utils.database import db_async_session_manager

intro_dialogs = dialogs['intro']


@dp.message(Command("start"))
async def start(message: Message, dialog_manager: DialogManager):
    async with db_async_session_manager() as session:
        await account_service.register_account(
            session, UserInit(
                chat_id=message.from_user.id,
                login=message.from_user.username,
                name=message.from_user.first_name
            )
        )

        user = await user_repository.get_user_by_chat_id(session, message.from_user.id)
        if user.login_status:
            await dialog_manager.start(AccountMainPage.main)
        else:
            await dialog_manager.start(AccountMainPage.main)


@dp.message(Command("admin"))
async def admin(message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(AdminMenu.admin_password, mode=StartMode.NORMAL)


async def log_in_start(callback: CallbackQuery, button: Button,
                       manager: DialogManager):
    await manager.start(LogIn.login)


async def sign_in_start(callback: CallbackQuery, button: Button,
                        manager: DialogManager):
    await manager.start(SignIn.login)


async def my_requests_start(callback: CallbackQuery, button: Button,
                            manager: DialogManager):
    async with db_async_session_manager() as session:
        user_id = (await user_repository.get_user_by_chat_id(session, callback.from_user.id)).id
    await manager.start(MyRequests.requests, data={'user_id': user_id})


async def create_request_start(callback: CallbackQuery, button: Button,
                               manager: DialogManager):
    await manager.start(CreateRequest.category)


entry_window = Window(
    Const(intro_dialogs['start']['hello']),
    Column(Button(Const(intro_dialogs['start']['sign_in']), id='sign_in',
                  on_click=sign_in_start),
           Button(Const(intro_dialogs['start']['log_in']), id='log_in',
                  on_click=log_in_start)),
    state=Entry.entry,
)

account_window = Window(
    Const('Привет, как'),
    Column(Button(Const(intro_dialogs['start']['my_requests']), id='my_requests', on_click=my_requests_start),
           Button(Const(intro_dialogs['start']['create_request']), id='create_request', on_click=create_request_start)),
    state=AccountMainPage.main,
)
entry_router = Dialog(entry_window)
account_router = Dialog(account_window)
