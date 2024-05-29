import json
import operator
import os

from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram_dialog import Dialog, Window, DialogProtocol, DialogManager
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Cancel, Back, Column, Multiselect, Button
from aiogram_dialog.widgets.text import Const, Format

from app import dp
from commands.state_classes import AdminPointCreate
from core.text import dialogs
from utils.utils import get_city

intro_dialogs = dialogs['intro']
admin_point_create_router = Router(name='admin_point_create')
commands_dir = os.path.dirname(os.path.abspath(__file__))

waste_select = Multiselect(
    Format("✓ {item[0]}"),
    Format("{item[0]}"),
    id="m_waste_types",
    item_id_getter=operator.itemgetter(1),
    items="waste_types"
)

categories = ['Бумага📃',
              'Пластик🔫',
              'Стекло🍾',
              'Металл⚙️',
              'Одежда🎩',
              'Лампочки💡',
              'Крышечки🔴',
              'Техника📱',
              'Батареки🪫',
              'Шины🛞',
              'Опасное☢',
              'Другое']


async def get_data(**kwargs):
    waste_types = [(el, i) for i, el in enumerate(categories)]
    return {
        "waste_types": waste_types,
        "count": len(waste_types),
    }


async def insert_title(message: Message, dialog: DialogProtocol, manager: DialogManager):
    manager.dialog_data['title'] = message.text
    await manager.next()


async def insert_description(message: Message, dialog: DialogProtocol, manager: DialogManager):
    manager.dialog_data['description'] = message.text
    await manager.next()


async def insert_adress(message: Message, dialog: DialogProtocol, manager: DialogManager):
    manager.dialog_data['address'] = message.text
    await manager.next()


async def insert_phone(message: Message, dialog: DialogProtocol, manager: DialogManager):
    manager.dialog_data['phone_number'] = message.text
    await manager.next()


async def insert_cords(message: Message, dialog: DialogProtocol, manager: DialogManager):
    lst = message.text.replace(" ", "").split(',')
    manager.dialog_data["coordinates"] = {}
    manager.dialog_data["coordinates"]['lat'] = float(lst[0])
    manager.dialog_data["coordinates"]['lon'] = float(lst[1])
    await manager.next()


async def process_categories(callback: CallbackQuery, button: Button, manager: DialogManager):
    chosen = [categories[int(i)][:-1] for i in waste_select.get_checked(manager)]
    manager.dialog_data['types_of_garbage'] = chosen
    await manager.next()


async def save(callback: CallbackQuery, button: Button, manager: DialogManager):
    with open(os.path.join(commands_dir, 'points.json'), encoding='utf-8') as file:
        points = json.load(file)
    city = await get_city(manager.dialog_data["coordinates"]["lat"], manager.dialog_data["coordinates"]["lon"])
    if points.get(city):
        points[city].append(manager.dialog_data)
    else:
        points[city] = []
        points[city].append(manager.dialog_data)
    with open(os.path.join(commands_dir, 'points.json'), "w", encoding='utf-8') as file:
        json.dump(points, file, indent=4)
    await manager.next()


dialog = Dialog(Window(Const("Отправьте название точки"), Cancel(Const("Отмена")), MessageInput(insert_title),
                       state=AdminPointCreate.title),
                Window(Const("Отправьте описание точки"),
                       Back(Const("Назад")), Cancel(Const("Отмена")), MessageInput(insert_description),
                       state=AdminPointCreate.description),
                Window(Const("Отправьте адрес точки аналогично\nНижневартовск, Маршала Жукова, 6А"),
                       Back(Const("Назад")), Cancel(Const("Отмена")),
                       MessageInput(insert_adress), state=AdminPointCreate.address),
                Window(Const("Отправьте номер телефона  по которому можно связаться с работниками точки"),
                       Back(Const("Назад")), Cancel(Const("Отмена")),
                       MessageInput(insert_phone), state=AdminPointCreate.phone_number),
                Window(
                    Const("Выберите виды мусора для сортировки"),
                    Button(Const("Категории выбраны✔️"), id="all_done", on_click=process_categories),
                    Column(waste_select),
                    Back(Const("Назад")), Cancel(Const("Отмена")),
                    getter=get_data,
                    state=AdminPointCreate.types_of_garbage
                ),
                Window(Const(
                    "Отправьте координаты вида <b>55.756265512853076,37.542354827164544</b> (можете взять координаты с сайта https://snipp.ru/tools/address-coord"),
                    Back(Const("Назад")), Cancel(Const("Отмена")),
                    MessageInput(insert_cords), state=AdminPointCreate.cords),
                Window(Format("""{dialog_data[title]}

{dialog_data[description]}

{dialog_data[address]}

Принимается: {dialog_data[types_of_garbage]}

Номер телефона: {dialog_data[phone_number]}"""),
                       Cancel(Const("Отмена")), Back(Const("Назад")),
                       Button(Const("Подтвердить"), id="approve", on_click=save), state=AdminPointCreate.sure),
                Window(Const('Точка добавлена успешно!'), Cancel(Const("Меню администратора")),
                       state=AdminPointCreate.save)
                )

dp.include_router(dialog)