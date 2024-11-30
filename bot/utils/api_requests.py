import aiohttp
import asyncio
import base64
import json


# Начало работы с API. Получаем токен сессии, он нужен во всех других запросах
async def init_session(url, app_token, login, password):
    string = login + ":" + password
    string_b64 = base64.b64encode(string.encode()).decode()
    token = f"basic {string_b64}"
    headers = {"Authorization": token}
    params = {"app_token": app_token}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, ssl=False, headers=headers, params=params) as response:
            return await response.json()


# Конец работы с API
async def kill_session(url, app_token, session_token):
    params = {"app_token": app_token, "session_token": session_token}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, ssl=False, params=params) as response:
            return await response.json()


# Создаём заявку. Сюда кидаем заголовок и сам текст.
# Возвращает json там id заявки
async def create_ticket(url, app_token, session_token, name_ticket, text_ticket):
    params = {"app_token": app_token, "session_token": session_token}
    headers = {'Content-Type': 'application/json'}
    data = json.dumps({
        "input":
            {
                "content": text_ticket,
                "name": name_ticket
            }
    })
    async with aiohttp.ClientSession() as session:
        async with session.post(url, ssl=False, params=params, data=data, headers=headers) as response:
            return await response.json()


# Обновление информации по заявке. Сюда кидаем новый заголовок и текст, а также id заявки
# возвращает json там новый id заявки
# Очень странная штука создаёт новую заявку на сайте и не закрывает старую можно конечно закрыть самим её, но странно
async def update_ticket(url, app_token, session_token, name_ticket, text_ticket, id):
    params = {"app_token": app_token, "session_token": session_token}
    headers = {'Content-Type': 'application/json'}
    data = json.dumps({
        "input":
            {
                "id": id,
                "content": text_ticket,
                "name": name_ticket
            }
    })
    async with aiohttp.ClientSession() as session:
        async with session.post(url, ssl=False, params=params, data=data, headers=headers) as response:
            return await response.json()


# Получаем информацию по заявке: текст, название, статус и так далее. id заявки в ссылке
# для получения статуса смотри ["status"]
# название: ["name"]
# текст: ["content"]
async def get_info_ticket(url, app_token, session_token):
    params = {"app_token": app_token, "session_token": session_token, "expand_dropdowns": "true"}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, ssl=False, params=params) as response:
            return await response.json()


# Создаёт комментарий к уже существующей заявке. id заявки в ссылке и в аргументах одинаковый
# возвращает json с id комментария, нам не надо
async def create_comment(url, app_token, session_token, text_comment, id):
    params = {"app_token": app_token, "session_token": session_token}
    headers = {'Content-Type': 'application/json'}
    data = json.dumps({
        "input":
            {
                "items_id": id,
                "itemtype": "Ticket",
                "requesttypes_id": 4,
                "content": text_comment
            }
    })
    async with aiohttp.ClientSession() as session:
        async with session.post(url, ssl=False, params=params, data=data, headers=headers) as response:
            return await response.json()


# Посмотреть комментарии по заявке id заявки в ссылке
# возвращает список словарей с информацией по комментариям
# посмотреть текст комментария: ["content"]
async def get_comments_for_ticket(url, app_token, session_token):
    params = {"app_token": app_token, "session_token": session_token}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, ssl=False, params=params) as response:
            return await response.json()


# Закрывает заявку (оставляет комментарий, что решение одобрено), id заявки в ссылке и в аргументах одинаковый
# Возвращает json с id, он нам не нужен
async def close_ticket(url, app_token, session_token, id):
    params = {"app_token": app_token, "session_token": session_token}
    headers = {'Content-Type': 'application/json'}
    data = json.dumps({
        "input":
            {
                "items_id": id,
                "itemtype": "Ticket",
                "requesttypes_id": 4,
                "add_reopen": "Утвердить решение",
                "content": "Решение одобрено",
                "_status": 6
            }
    })
    async with aiohttp.ClientSession() as session:
        async with session.post(url, ssl=False, params=params, data=data, headers=headers) as response:
            return await response.json()


# Переотркывает заявку типа ответ надо другой, id заявки в ссылке и в аргументах одинаковый
async def recreate_ticket(url, app_token, session_token, id):
    params = {"app_token": app_token, "session_token": session_token}
    headers = {'Content-Type': 'application/json'}
    data = json.dumps({
        "input":
            {
                "items_id": id,
                "itemtype": "Ticket",
                "requesttypes_id": 4,
                "add_reopen": "Отклонить решение",
                "content": "Переоткрыть"
            }
    })
    async with aiohttp.ClientSession() as session:
        async with session.post(url, ssl=False, params=params, data=data, headers=headers) as response:
            return await response.json()


# Посмотреть ответы по заявке id заявки в ссылке
# возвращает список словарей с информацией по ответам
# посмотреть текст ответа: ["content"]
async def get_answers_for_ticket(url, app_token, session_token):
    params = {"app_token": app_token, "session_token": session_token}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, ssl=False, params=params) as response:
            return await response.json()


# Возвращает базу данных с вопросами и ответами
# смотреть вопрос: ["name"]
# смотреть ответ: ["answer"]
# Нужно поразбивать на несколько запросов пагинацией,
# чтобы запрашивать просто вопросы для ии и потом ответ по найденному вопросу
async def get_data(url, app_token, session_token):
    params = {"app_token": app_token, "session_token": session_token}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, ssl=False, params=params) as response:
            return await response.json()
