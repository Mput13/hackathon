import operator
from datetime import datetime, timedelta
from typing import Any

from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram_dialog import Window, Dialog, DialogManager, DialogProtocol, StartMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Column, Cancel, Select
from aiogram_dialog.widgets.text import Const, Format
from sqlalchemy import select, func

from app import dp
from commands.my_requests import start_comments, start_answers
from commands.state_classes import AdminMenu, AccountMainPage
from core.constants import APP_TOKEN, LOGIN, PASSWORD, VALUES_STATUS
from core.text import dialogs
from models import AdminPassword, Request, User
from models.request import RequestStatus
from repositories.request_repository import request_repository
from utils.api_requests import init_session, get_info_ticket, kill_session
from utils.database import db_async_session_manager
from utils.utils import check_password, create_url

admin_dialogs = dialogs['admin']
admin_router = Router(name='admin_router')

async def password_sent(message: Message, dialog: DialogProtocol, manager: DialogManager):
    async with db_async_session_manager() as session:
        hashed_password = await session.scalar(select(AdminPassword).where(AdminPassword.id == 1))
    if check_password(hashed_password.password, message.text):
        await message.delete()
        await manager.next()


async def insert_days(message: Message, dialog: DialogProtocol, manager: DialogManager):
    if message.text.isdigit():
        n = int(message.text)
        manager.dialog_data['days'] = n
        time_threshold = datetime.now() - timedelta(days=n)
        async with db_async_session_manager() as session:
            requests = await session.execute(
                select(Request).where(func.to_timestamp(func.extract('epoch', Request.created_at)) >= time_threshold)
            )
            requests = requests.scalars().all()
            for el in requests:
                print(vars(el))
            successful_requests = [el for el in requests if el.status == RequestStatus.SUCCESSFUL]
            escalation_requests = [el for el in requests if el.status == RequestStatus.ESCALATION]
            users = await session.execute(
                select(User).where(func.to_timestamp(func.extract('epoch', User.created_at)) >= time_threshold)
            )
            users = users.scalars().all()
            manager.dialog_data['new_users'] = len(users)
            manager.dialog_data['requests'] = len(requests)
            manager.dialog_data['successful_requests'] = len(successful_requests)
            manager.dialog_data['escalation_requests'] = len(escalation_requests)

        await manager.next()
    else:
        await message.answer("Отправьте число")


async def escalation_requests_start(callback, button, manager):
    await manager.start(AdminMenu.requests_choose)


async def main_menu(callback: CallbackQuery, button: Button,
                    manager: DialogManager):
    await manager.start(AccountMainPage.main, mode=StartMode.RESET_STACK)


async def on_request_selected(callback: CallbackQuery, widget: Any,
                              manager: DialogManager, item_id: str):
    request = manager.dialog_data['transition'][int(item_id)]
    manager.dialog_data['request'] = vars(request)
    index = manager.dialog_data['request']['system_id']
    # TODO: тут сделай запрос в апишку по поводу статуса заявки, положи в переменную status
    url_init = await create_url("init_session")
    url_info = await create_url("ticket_info", index)
    url_kill = await create_url("kill_session")
    token = (await init_session(url_init, APP_TOKEN, LOGIN, PASSWORD))["session_token"]
    state = (await get_info_ticket(url_info, APP_TOKEN, token))["status"]
    kill = await kill_session(url_kill, APP_TOKEN, token)
    status = VALUES_STATUS[state]
    manager.dialog_data['text'] = f"{manager.dialog_data['request']['question']}\nСтатус заявки: {status}"
    await manager.next()


async def get_data(**kwargs):
    manager = kwargs['dialog_manager']
    async with db_async_session_manager() as session:
        requests_obj = await request_repository.get_escalated_requests(session)
        requests = []
        manager.dialog_data['transition'] = []
        for i, request in enumerate(requests_obj):
            manager.dialog_data['transition'].append(request)
            requests.append((request.question, i))
        return {
            "requests": requests,
            "count": len(requests),
        }


kbd = Select(
    Format("{item[0]}"),  # E.g `✓ Apple (1/4)`
    id="s_request_questions",
    item_id_getter=operator.itemgetter(1),
    # each item is a tuple with id on a first position
    items="requests",  # we will use items from window data at a key `fruits`
    on_click=on_request_selected,
)
admin_dialog = Dialog(Window(
    Const(admin_dialogs['password']),
    Cancel(Const("Главное меню🏠")),
    MessageInput(password_sent),
    state=AdminMenu.admin_password
), Window(Const('За сколько дней вы хотите получить статистику?'), MessageInput(insert_days), state=AdminMenu.days),
    Window(Format(
        'Новых пользователей: {dialog_data[new_users]}\nВсего запросов: {dialog_data[requests]}\nУспешных запросов: {dialog_data[successful_requests]}\nЭскалаций: {dialog_data[escalation_requests]}'),
        Column(
            Button(Const('Эскалационные запросы'), id='escalation_requests', on_click=escalation_requests_start),
            Button(Const("Главное меню🏠"), id="main_menu", on_click=main_menu)),
        state=AdminMenu.admin_menu), Window(Const("Запросы пользователей"),
                                            Column(kbd,
                                                   Cancel(Const("Главное меню🏠"))), state=AdminMenu.requests_choose,
                                            getter=get_data),
    Window(Format('{dialog_data[text]}'),
           Button(Const("Ответы"), id='answers', on_click=start_answers),
           Button(Const("Комментарии к заявке"), id='lamba', on_click=start_comments),
           Cancel(Const("Меню администратора")), state=AdminMenu.request
           ))
dp.include_router(admin_dialog)
