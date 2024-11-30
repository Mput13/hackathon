from aiogram.fsm.state import StatesGroup, State


class MainMenu(StatesGroup):
    main = State()


class AdminMenu(StatesGroup):
    admin_password = State()
    days = State()
    admin_menu = State()
    requests_choose = State()
    request = State()


class Answers(StatesGroup):
    answer_showing = State()


class Comments(StatesGroup):
    comment_showing = State()


class CreateRequest(StatesGroup):
    category = State()
    question = State()
    answer = State()
    escalation = State()


class LogIn(StatesGroup):
    login = State()
    password = State()


class Entry(StatesGroup):
    entry = State()


class AccountMainPage(StatesGroup):
    main = State()


class MyRequests(StatesGroup):
    requests = State()
    request_menu = State()


class RequestView(StatesGroup):
    request = State()


class SignIn(StatesGroup):
    login = State()
    password = State()
    password_confirm = State()


class RequestDelete(StatesGroup):
    sure = State()
    result = State()


class EcoPiggyBank(StatesGroup):
    show = State()


class AddArticle(StatesGroup):
    insert_name = State()
    insert_text = State()
    sure = State()
    result = State()


class AddToRequest(StatesGroup):
    insert_question = State()
    confirm = State()


class CreatingNewsletter(StatesGroup):
    text_insert = State()
    media_insert = State()
    sure = State()
    result = State()


class AdminPointRequestsManaging(StatesGroup):
    cords = State()
    sure = State()
    save = State()


class GetStats(StatesGroup):
    days = State()
    stats = State()


class Links(StatesGroup):
    links = State()


class Nothing(StatesGroup):
    nothing = State()
