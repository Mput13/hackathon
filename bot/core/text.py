dialogs = {
    'intro': {
        'start': {
            'hello': """Войдите в систему""",

            'usage_statistic': 'Скибиди доб доб',
            # лучше стараться избегать формулировок, где нужно склонение с числительными

            'confirm_button': 'Поехали заполнять!',
            'sign_in': 'Зарегистрироваться',
            'log_in': 'Войти',
            'my_requests': 'Мои заявки',
            'create_request': 'Задать вопрос'
        },
        'about_info': 'Расскажи о себе:',
        'roles': '  Выберите роль',
        'target': 'Расскажите, какой проект вы хотите сделать',
        'complete': 'Спасибо, теперь вы можете подыскать себе команду или создать новую! Для этого нажмите на /teams',
        'profile_info': 'Вы ранее заполняли:\n\nО Себе: {about}, Роль: {role}\n\nЦель: {target}\n\n'
                        'Если хотите заново заполнить информацию о себе, можете нажать /start'
    },
    'entry': {
        'sign_in': 'Отправьте свой логин',
        'login_exists': 'Логин уже существует, отправьте другой',
        'password': 'Придумайте пароль',
        'password_check': 'Подтвердите свой пароль. Отправьте его снова',
        'insert_password': 'Отправьте свой пароль',
        'different_passwords': 'Пароли различаются, исправьте и отправьте снова',
        'log_in': 'Отправьте свой логин или нажмите "далее" если используете свой телеграм ник в качестве логина',
        'no_such_login': 'Такого логина не существует, попробуйте другой.',
        'wrong_password': 'Неверный пароль, попробуйте снова.'
    },
    'creating_request': {'request_start': 'Отправьте интересующий вас вопрос форматом: Категория, Вопрос'},
    'my_requests': {'main_page': 'Ваши заявки:'},
    'admin': {
        'manage_articles_button': 'Управлять статьями',
        'post_news_button': 'Выложить новость',
        'get_statistic_button': 'Статистика',
        'password': 'Введите пароль администратора'}
}


async def get_point_text(closest_point):
    return f"""{closest_point['title']}
        
{closest_point['description']}

{closest_point['address']}
Номер телефона: {closest_point['phone_number']}

{closest_point['schedule']}

Принимается:
{closest_point['types_of_garbage']}"""


async def get_point_request_text(point):
    return f"""{point.title}

{point.description}

{point.address}

Принимается: {point.types_of_garbage}

Номер телефона: {point.phone_number}

Автор запроса: {point.author}"""
