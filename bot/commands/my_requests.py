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
            requests.append((request.question[:15], i))
        return {
            "requests": requests,
            "count": len(requests),
        }


async def on_request_selected(callback: CallbackQuery, widget: Any,
                              manager: DialogManager, item_id: str):
    request = manager.dialog_data['transition'][int(item_id)]
    manager.dialog_data['request'] = vars(request)
    await manager.next()


async def start_adding(callback: CallbackQuery, button: Button,
                       manager: DialogManager):
    await manager.start(AddToRequest.insert_question, data=manager.dialog_data)


async def start_answers(callback: CallbackQuery, button: Button,
                        manager: DialogManager):
    # TODO: запрос в апи получает ответы и соединяет их
    answers = "FIMOZZZZZZZZZ"
    await manager.start(Answers.answer_showing, data={"updated_answers": answers})


async def start_deleting(callback: CallbackQuery, button: Button,
                         manager: DialogManager):
    await manager.start(RequestDelete.sure, data=manager.dialog_data)


async def delete_request(callback, button, manager):
    # TODO: тут можно заодно закрыть запрос
    async with db_async_session_manager() as session:
        await request_repository.delete_request_by_id(session, manager.start_data['request']['id'])
    await manager.next()


async def confirm_request_question(callback, button, manager):
    async with db_async_session_manager() as session:
        await request_repository.update_request_question_by_id(session, manager.start_data['request']['id'],
                                                               manager.dialog_data['new_question'])
    await manager.start(AccountMainPage.main, mode=StartMode.RESET_STACK)


async def insert_question(message: Message, dialog: DialogProtocol, manager: DialogManager):
    manager.dialog_data[
        'new_question'] = f"{manager.start_data['request']['question']}\n---------------------\n{message.text}"
    # TODO: тут я возможно тебя неправильно понял, но зто добавление нового текста к запросу, типа как дополнительный уточняющий вопрос тут тоже нужна апишка
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
                Window(Format('{dialog_data[request][question]}'),
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
