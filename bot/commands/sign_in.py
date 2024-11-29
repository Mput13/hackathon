from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram_dialog import DialogManager, Dialog, Window, DialogProtocol, StartMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Back, Cancel, Next, Button
from aiogram_dialog.widgets.text import Const

from app import dp
from commands.state_classes import SignIn, AccountMainPage
from core.text import dialogs
from repositories.user_repository import user_repository
from utils.database import db_async_session_manager

sign_in_router = Router(name='sign_in_router')

entry = dialogs['entry']


async def insert_login(message: Message, dialog: DialogProtocol, manager: DialogManager):
    async with db_async_session_manager() as session:
        logins = await user_repository.get_all_logins(session)
        if message.text not in logins:
            manager.dialog_data['login'] = message.text
            await manager.next()
        else:
            await message.answer(entry['login_exists'])


async def insert_password(message: Message, dialog: DialogProtocol, manager: DialogManager):
    manager.dialog_data['password'] = message.text
    await message.delete()
    await manager.next()


async def confirm_password(message: Message, dialog: DialogProtocol, manager: DialogManager):
    if message.text == manager.dialog_data['password']:
        async with db_async_session_manager() as session:
            if manager.dialog_data.get('login'):
                await user_repository.update_login_by_chat_id(session, message.chat.id, manager.dialog_data['login'])
                await user_repository.update_hashed_password_by_login(session, manager.dialog_data['login'],
                                                                      message.text)
            else:
                await user_repository.update_hashed_password_by_chat_id(session, message.chat.id, message.text)

        await message.delete()
        await user_repository.update_login_status_by_chat_id(session, message.chat.id, True)
        await manager.start(AccountMainPage.main, mode=StartMode.RESET_STACK)
    else:
        await message.answer(entry['different_passwords'])
        await message.delete()


async def no_skit(callback: CallbackQuery, button: Button,
                               manager: DialogManager):
    pass

dialog = Dialog(
    Window(Const(entry['sign_in']), Button(Const('Нет  СКИТ-аккаунта'), id='no_skit', on_click=no_skit),
           Next(Const('далее')), Cancel(Const("Отмена❌")),
           MessageInput(insert_login), state=SignIn.login),
    Window(Const(entry['password']), Back(Const("Назад⬅️")), Cancel(Const("Отмена❌")),
           MessageInput(insert_password), state=SignIn.password),
    Window(Const(entry['password_check']), Back(Const("Назад⬅️")), Cancel(Const("Отмена❌")),
           MessageInput(confirm_password), state=SignIn.password_confirm))

dp.include_router(dialog)
