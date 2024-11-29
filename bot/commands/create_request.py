import operator
from typing import Any

from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram_dialog import DialogManager, Dialog, Window, DialogProtocol, StartMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Back, Cancel, Button, Row, Next, Select, Column
from aiogram_dialog.widgets.text import Const, Format

from app import dp
from commands.state_classes import AccountMainPage, CreateRequest
from core.constants import APP_TOKEN, LOGIN, PASSWORD
from core.text import dialogs
from repositories.request_repository import request_repository
from repositories.user_repository import user_repository
from schemas.request import RequestScheme
from utils.ai_stuff import get_categories, get_ai_answer
from utils.api_requests import init_session, create_ticket, kill_session
from utils.database import db_async_session_manager
from utils.utils import create_url

create_request_router = Router(name='create_request_router')

request_creating_text = dialogs['creating_request']


async def insert_question(message: Message, dialog: DialogProtocol, manager: DialogManager):
    if manager.dialog_data.get('category'):
        manager.dialog_data['answer'] = await get_ai_answer(message.text, category=manager.dialog_data.get('category'))
    else:
        manager.dialog_data['answer'] = await get_ai_answer(message.text)
    manager.dialog_data['question'] = message.text
    await manager.next()


async def return_to_main_page_success(callback: CallbackQuery, button: Button,
                                      manager: DialogManager):
    async with db_async_session_manager() as session:
        user_id = (await user_repository.get_user_by_chat_id(session, callback.from_user.id)).id
        await request_repository.create_request(
            session, RequestScheme(
                question=manager.dialog_data['question'],
                system_id=None,
                answer=manager.dialog_data['answer'],
                user_id=user_id,
                status='successful'

            )
        )
    await manager.start(AccountMainPage.main, mode=StartMode.RESET_STACK)


async def return_to_main_page_unsuccess(callback: CallbackQuery, button: Button,
                                        manager: DialogManager):
    async with db_async_session_manager() as session:
        user_id = (await user_repository.get_user_by_chat_id(session, callback.from_user.id)).id
        await request_repository.create_request(
            session, RequestScheme(
                question=manager.dialog_data['question'],
                system_id=None,
                answer=manager.dialog_data['answer'],
                user_id=user_id,
                status='unsuccessful'

            )
        )
    await manager.start(AccountMainPage.main, mode=StartMode.RESET_STACK)


async def return_to_main_page_escalation(callback: CallbackQuery, button: Button,
                                         manager: DialogManager):
    await manager.start(AccountMainPage.main, mode=StartMode.RESET_STACK)


async def start_escolation(callback: CallbackQuery, button: Button,
                           manager: DialogManager):
    #     TODO: тут запрос в апи, где брать данные смотри по тому где беру их я для бд в коде ниже
    url_init = await create_url("init_session")
    url_create = await create_url("ticket_create_update")
    url_kill = await create_url("kill_session")
    token = (await init_session(url_init, APP_TOKEN, LOGIN, PASSWORD))["session_token"]
    id = (await create_ticket(url_create, APP_TOKEN, token, manager.dialog_data['question'],
                              manager.dialog_data['question']))["id"]
    kill = await kill_session(url_kill, APP_TOKEN, token)

    async with db_async_session_manager() as session:
        user_id = (await user_repository.get_user_by_chat_id(session, callback.from_user.id)).id
        await request_repository.create_request(
            session, RequestScheme(
                question=manager.dialog_data['question'],
                system_id=id,  # TODO: да это айдишник со СКИТа там много где его надо
                answer=manager.dialog_data['answer'],
                user_id=user_id,
                status='escalation'

            )
        )


async def get_data(**kwargs):
    manager = kwargs['dialog_manager']
    categories_prep = (await get_categories())[:10]
    categories = []
    manager.dialog_data['transition'] = []
    for i, category in enumerate(categories_prep):
        manager.dialog_data['transition'].append(category)
        categories.append((category, i))
    return {
        "categories": categories,
        "count": len(categories),
    }


async def on_category_selected(callback: CallbackQuery, widget: Any,
                               manager: DialogManager, item_id: str):
    category = manager.dialog_data['transition'][int(item_id)]
    manager.dialog_data['category'] = category
    await manager.next()


async def skip_category(callback: CallbackQuery, button: Button,
                        manager: DialogManager):
    pass


kbd = Select(
    Format("{item[0]}"),  # E.g `✓ Apple (1/4)`
    id="s_category",
    item_id_getter=operator.itemgetter(1),
    # each item is a tuple with id on a first position
    items="categories",  # we will use items from window data at a key `fruits`
    on_click=on_category_selected,
)
dialog = Dialog(
    Window(Const('Выберите категорию или нажмите далее, если ее нет в списке'), Column(kbd, Next(Const('далее')),
                                                                                       Cancel(Const(
                                                                                           "Главное меню🏠"))),
           state=CreateRequest.category, getter=get_data),
    Window(Const(request_creating_text['request_start']),
           Cancel(Const("Отмена❌")),
           MessageInput(insert_question), state=CreateRequest.question),
    Window(Format('{dialog_data[answer]}'),
           Row(Button(Const('👍'), id='success', on_click=return_to_main_page_success),
               Next(Const('👎'), on_click=start_escolation)),
           Back(Const("Назад⬅️")),
           Cancel(Const("Отмена❌")),
           state=CreateRequest.answer),
    Window(Const('Ваш запрос отправлен, ждите ответа'),
           Button(Const('На главный экран'), id='after_escalation_sent',
                  on_click=return_to_main_page_escalation),
           state=CreateRequest.escalation))

dp.include_router(dialog)
