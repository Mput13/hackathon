import operator
from typing import Any

from aiogram import Router
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, Dialog, Window, DialogProtocol, StartMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Cancel, Select, Column, Button, Back
from aiogram_dialog.widgets.text import Const, Format

from app import dp
from commands.state_classes import MyRequests, RequestDelete, AddToRequest, AccountMainPage, Answers
from core.text import dialogs
from repositories.request_repository import request_repository
from utils.database import db_async_session_manager
from bot.core.constants import APP_TOKEN, LOGIN, PASSWORD, VALUES_STATUS

from bot.utils.api_requests import init_session, kill_session, create_comment, get_answers_for_ticket, close_ticket, \
    get_info_ticket
from bot.utils.utils import create_url

my_requests_text = dialogs['my_requests']
my_requests_router = Router(name='my_requests_router')


async def get_data(**kwargs):
    manager = kwargs['dialog_manager']
    async with db_async_session_manager() as session:
        requests_obj = await request_repository.get_requests_by_user(session, manager.start_data['user_id'])
        requests = []
        manager.dialog_data['transition'] = []
        for i, request in enumerate(requests_obj):
            manager.dialog_data['transition'].append(request)
            requests.append((request.question, i))
        return {
            "requests": requests,
            "count": len(requests),
        }


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


async def start_adding(callback: CallbackQuery, button: Button,
                       manager: DialogManager):
    await manager.start(AddToRequest.insert_question, data=manager.dialog_data)


async def start_answers(callback: CallbackQuery, button: Button,
                        manager: DialogManager):
    # TODO: запрос в апи получает ответы и соединяет их
    index = manager.dialog_data['request']['system_id']
    url_init = await create_url("init_session")
    url_answers = await create_url("get_solution", index)  # TODO сюда вместо index id из бд
    url_kill = await create_url("kill_session")
    token = (await init_session(url_init, APP_TOKEN, LOGIN, PASSWORD))["session_token"]
    answers = await get_answers_for_ticket(url_answers, APP_TOKEN,
                                           token)  # TODO Тут список словарей с ответами в каждом словаре ответ в ["content"] лежит, так что надо придумать что делать если много ответов
    kill = await kill_session(url_kill, APP_TOKEN, token)
    answer = "\n----------------------------------------\n".join([el['content'] for el in answers])
    await manager.start(Answers.answer_showing, data={"updated_answers": answer})


async def start_deleting(callback: CallbackQuery, button: Button,
                         manager: DialogManager):
    await manager.start(RequestDelete.sure, data=manager.dialog_data)


async def delete_request(callback, button, manager):
    # TODO: тут можно заодно закрыть запрос
    index = manager.start_data['request']['system_id']
    url_init = await create_url("init_session")
    url_close = await create_url("create_get_comment", index)  # TODO сюда вместо index id из бд
    url_kill = await create_url("kill_session")
    token = (await init_session(url_init, APP_TOKEN, LOGIN, PASSWORD))["session_token"]
    answer = await close_ticket(url_close, APP_TOKEN, token, index)  # TODO сюда тоже вместо index id из бд
    kill = await kill_session(url_kill, APP_TOKEN, token)
    async with db_async_session_manager() as session:
        await request_repository.delete_request_by_id(session, manager.start_data['request']['id'])
    await manager.skip_category()


async def confirm_request_question(callback, button, manager):
    async with db_async_session_manager() as session:
        await request_repository.update_request_question_by_id(session, manager.start_data['request']['id'],
                                                               manager.dialog_data['new_question'])
    await manager.start(AccountMainPage.main, mode=StartMode.RESET_STACK)


async def insert_question(message: Message, dialog: DialogProtocol, manager: DialogManager):
    manager.dialog_data[
        'new_question'] = f"{manager.start_data['request']['question']}\n---------------------\n{message.text}"
    index = manager.start_data['request']['system_id']
    # TODO: тут я возможно тебя неправильно понял, но зто добавление нового текста к запросу, типа как дополнительный уточняющий вопрос тут тоже нужна апишка
    # TODO Короче это добавления комментария к заявке типа уточняющей информации какой-нибудь, эти комментарии также можно посмотреть то есть нужна отдельная кнопочка для этого так как там могут комментировать кто-нибудь из техподдержки
    url_init = await create_url("init_session")
    url_comment = await create_url("create_get_comment", index)  # TODO сюда вместо index id из бд
    url_kill = await create_url("kill_session")
    token = (await init_session(url_init, APP_TOKEN, LOGIN, PASSWORD))["session_token"]
    answer = await create_comment(url_comment, APP_TOKEN, token, manager.dialog_data['new_question'],
                                  index)  # TODO сюда тоже вместо index id из бд
    kill = await kill_session(url_kill, APP_TOKEN, token)
    await manager.next()


kbd = Select(
    Format("{item[0]}"),  # E.g `✓ Apple (1/4)`
    id="s_request_questions",
    item_id_getter=operator.itemgetter(1),
    # each item is a tuple with id on a first position
    items="requests",  # we will use items from window data at a key `fruits`
    on_click=on_request_selected,
)

dialog = Dialog(Window(Const(my_requests_text['main_page']),
                       Column(kbd,
                              Cancel(Const("Главное меню🏠"))), state=MyRequests.requests, getter=get_data),
                Window(Format('{dialog_data[text]}'),
                       Button(Const("Дополнить"), id='add', on_click=start_adding),
                       Button(Const("Ответы"), id='answers', on_click=start_answers),
                       Button(Const("Удалить заявку"), id='delete', on_click=start_deleting),
                       Back(Const("Назад⬅️")),
                       Cancel(Const("Главное меню🏠")), state=MyRequests.request_menu
                       )
                )

delete_dialog = Dialog(Window(Const('Вы уверены?'),
                              Button(Const('Удалить'), id='delete_article', on_click=delete_request),
                              Cancel(Const("Отменить")), state=RequestDelete.sure),
                       Window(Const("Успешно!"), Cancel(Const('К моим запросам')),
                              state=RequestDelete.result))
add_to_request_dialog = Dialog(
    Window(Const('Отправьте дополнительный вопрос'), Cancel(Const("Отменить")), MessageInput(insert_question),
           state=AddToRequest.insert_question),
    Window(Format('{dialog_data[new_question]}'),
           Button(Const('Подтвердить'), id='confirm', on_click=confirm_request_question),
           Cancel(Const("Отменить")), state=AddToRequest.confirm))
answers_dialog = Dialog(
    Window(Format('{start_data[updated_answers]}'), Cancel(Const('Назад')), state=Answers.answer_showing))
dp.include_router(answers_dialog)
dp.include_router(add_to_request_dialog)
dp.include_router(delete_dialog)
dp.include_router(dialog)
