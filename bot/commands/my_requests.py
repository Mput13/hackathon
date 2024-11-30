import operator
from typing import Any

from aiogram import Router
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, Dialog, Window, DialogProtocol, StartMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Cancel, Select, Column, Button, Back
from aiogram_dialog.widgets.text import Const, Format

from app import dp
from bot.core.constants import APP_TOKEN, LOGIN, PASSWORD, VALUES_STATUS
from bot.utils.api_requests import init_session, kill_session, create_comment, get_answers_for_ticket, close_ticket, \
    get_info_ticket, get_comments_for_ticket, recreate_ticket
from bot.utils.utils import create_url
from commands.intro import my_requests_start
from commands.state_classes import MyRequests, RequestDelete, AddToRequest, AccountMainPage, Answers, Comments, \
    RequestClose, OpenedRequest, ClosedRequest
from core.text import dialogs
from models.request import RequestStatus
from repositories.request_repository import request_repository
from utils.database import db_async_session_manager

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
    state = (await get_info_ticket(url_info, APP_TOKEN, token))
    kill = await kill_session(url_kill, APP_TOKEN, token)
    status = VALUES_STATUS[state['status']]
    if manager.dialog_data['request']['status'] == RequestStatus.ESCALATION:
        manager.dialog_data['text'] = f"{manager.dialog_data['request']['question']}\nСтатус заявки: {status}"
    else:
        manager.dialog_data['text'] = f"{manager.dialog_data['request']['question']}"
    print(status)
    if status != VALUES_STATUS[6]:
        await manager.start(OpenedRequest.request_menu, data=manager.dialog_data)
    else:
        await manager.start(ClosedRequest.request_menu, data=manager.dialog_data)


async def start_adding(callback: CallbackQuery, button: Button,
                       manager: DialogManager):
    await manager.start(AddToRequest.insert_question, data=manager.start_data)


async def start_answers(callback: CallbackQuery, button: Button,
                        manager: DialogManager):
    # TODO: запрос в апи получает ответы и соединяет их
    lst = []
    lst.append(manager.start_data['request']['answer'])
    if manager.start_data['request']['status'] == RequestStatus.ESCALATION:
        index = manager.start_data['request']['system_id']
        url_init = await create_url("init_session")
        url_answers = await create_url("get_solution", index)  # TODO сюда вместо index id из бд
        url_kill = await create_url("kill_session")
        token = (await init_session(url_init, APP_TOKEN, LOGIN, PASSWORD))["session_token"]
        answers = await get_answers_for_ticket(url_answers, APP_TOKEN,
                                               token)  # TODO Тут список словарей с ответами в каждом словаре ответ в ["content"] лежит, так что надо придумать что делать если много ответов
        kill = await kill_session(url_kill, APP_TOKEN, token)
        answer = "Ответа не получено"
        if answers:
            for el in answers:
                lst.append(el['content'])
            answer = "\n----------------------------------------\n".join(lst)
    else:
        answer = manager.dialog_data['request']['answer']
    await manager.start(Answers.answer_showing, data={"updated_answers": answer})


async def start_deleting(callback: CallbackQuery, button: Button,
                         manager: DialogManager):
    await manager.start(RequestDelete.sure, data=manager.start_data)


async def close_request_start(callback: CallbackQuery, button: Button,
                              manager: DialogManager):
    await manager.start(RequestClose.sure, data=manager.start_data)


async def reopen_request(callback: CallbackQuery, button: Button,
                         manager: DialogManager):
    index = manager.start_data['request']['system_id']
    url_init = await create_url("init_session")
    url_recreate = await create_url("create_get_comment", index)
    url_kill = await create_url("kill_session")
    token = (await init_session(url_init, APP_TOKEN, LOGIN, PASSWORD))["session_token"]
    answer = await recreate_ticket(url_recreate, APP_TOKEN, token, index)  # TODO этот id не надо нам
    kill = await kill_session(url_kill, APP_TOKEN, token)


async def start_comments(callback: CallbackQuery, button: Button,
                         manager: DialogManager):
    if manager.start_data['request']['status'] == RequestStatus.ESCALATION:
        # TODO это запрос для ответов, переделай под комментарии
        index = manager.start_data['request']['system_id']
        url_init = await create_url("init_session")
        url_comment = await create_url("create_get_comment", index)
        url_kill = await create_url("kill_session")
        token = (await init_session(url_init, APP_TOKEN, LOGIN, PASSWORD))["session_token"]
        comments = await get_comments_for_ticket(url_comment, APP_TOKEN, token)
        kill = await kill_session(url_kill, APP_TOKEN, token)
        comment_text = "Комментарии отсутствуют"
        if comments:
            comment_text = "\n----------------------------------------\n".join([el['content'] for el in comments])
    else:
        comment_text = "Комментарии отсутствуют"
    await manager.start(Comments.comment_showing, data={'text': comment_text})


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
    await manager.next()


async def close_request(callback, button, manager):
    # TODO: тут можно заодно закрыть запрос
    index = manager.start_data['request']['system_id']
    url_init = await create_url("init_session")
    url_close = await create_url("create_get_comment", index)  # TODO сюда вместо index id из бд
    url_kill = await create_url("kill_session")
    token = (await init_session(url_init, APP_TOKEN, LOGIN, PASSWORD))["session_token"]
    answer = await close_ticket(url_close, APP_TOKEN, token, index)  # TODO сюда тоже вместо index id из бд
    kill = await kill_session(url_kill, APP_TOKEN, token)
    await manager.next()


async def confirm_request_question(callback, button, manager):
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
    await manager.start(AccountMainPage.main, mode=StartMode.RESET_STACK)


async def insert_question(message: Message, dialog: DialogProtocol, manager: DialogManager):
    manager.dialog_data[
        'new_question'] = f"{manager.start_data['request']['question']}\n---------------------\n{message.text}"
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
                              Cancel(Const("Главное меню🏠"))), state=MyRequests.requests, getter=get_data)
                )
request_watch = Dialog(Window(Format('{start_data[text]}'),
                              Button(Const("Добавить комментарий"), id='add', on_click=start_adding),
                              Button(Const("Ответы"), id='answers', on_click=start_answers),
                              Button(Const("Комментарии к заявке"), id='lamba', on_click=start_comments),
                              Button(Const("Закрыть заявку"), id='close_ticket', on_click=close_request_start),
                              Button(Const("Удалить заявку"), id='delete', on_click=start_deleting),
                              Back(Const("Назад⬅️")),
                              Cancel(Const("Главное меню🏠")), state=OpenedRequest.request_menu
                              ))
closed_request_watch = Dialog(Window(Format('{start_data[text]}'),
                                     Button(Const("Ответы"), id='answers', on_click=start_answers),
                                     Button(Const("Комментарии к заявке"), id='lamba', on_click=start_comments),
                                     Button(Const("Переоткрыть заявку"), id='reopen_ticket', on_click=reopen_request),
                                     Button(Const("Удалить заявку"), id='delete', on_click=start_deleting),
                                     Back(Const("Назад⬅️")),
                                     Cancel(Const("Главное меню🏠")), state=ClosedRequest.request_menu
                                     ))
delete_dialog = Dialog(Window(Const('Вы уверены?'),
                              Button(Const('Удалить'), id='delete_article', on_click=delete_request),
                              Cancel(Const("Отменить")), state=RequestDelete.sure),
                       Window(Const("Успешно!"),
                              Button(Const('К моим заявкам'), id='my_requests', on_click=my_requests_start),
                              state=RequestDelete.result))
comments_dialog = Dialog(
    Window(Format('{start_data[text]}'), Cancel(Const('Назад')), state=Comments.comment_showing))
add_to_request_dialog = Dialog(
    Window(Const('Отправьте дополнительный вопрос'), Cancel(Const("Отменить")), MessageInput(insert_question),
           state=AddToRequest.insert_question),
    Window(Format('{dialog_data[new_question]}'),
           Button(Const('Подтвердить'), id='confirm', on_click=confirm_request_question),
           Cancel(Const("Отменить")), state=AddToRequest.confirm))
answers_dialog = Dialog(
    Window(Format('{start_data[updated_answers]}'), Cancel(Const('Назад')), state=Answers.answer_showing))
close_ticket_dialog = Dialog(Window(Const('Вы уверены?'),
                                    Button(Format('Закрыть заявку'), id='close_ticket', on_click=close_request),
                                    Cancel(Const("Отменить")), state=RequestClose.sure),
                             Window(Const("Успешно!"),
                                    Button(Const('К моим заявкам'), id='my_requests', on_click=my_requests_start),
                                    state=RequestClose.result))

dp.include_router(closed_request_watch)
dp.include_router(request_watch)
dp.include_router(close_ticket_dialog)
dp.include_router(comments_dialog)
dp.include_router(answers_dialog)
dp.include_router(add_to_request_dialog)
dp.include_router(delete_dialog)
dp.include_router(dialog)
