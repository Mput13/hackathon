from mistralai import Mistral
import csv
from asyncio import run, sleep
import aiofiles


async def get_categories() -> list:
    categories = []
    async with aiofiles.open('C:/Users/mputi/PycharmProjects/faq_hackathon/bot/utils/БЗ.csv', 'r', encoding='utf-8') as csvfile:
        # Читаем содержимое файла
        contents = await csvfile.read()
        # Используем csv.reader для обработки содержимого
        reader = csv.reader(contents.splitlines(), delimiter=';')
        for row in reader:
            categories.append(row[0])
    return categories


async def get_instruction(category) -> str:
    instruction = None
    async with aiofiles.open('C:/Users/mputi/PycharmProjects/faq_hackathon/bot/utils/БЗ.csv', 'r', encoding='utf-8') as csvfile:
        # Читаем содержимое файла
        contents = await csvfile.read()
        # Используем csv.reader для обработки содержимого
        reader = csv.reader(contents.splitlines(), delimiter=';')
        for row in reader:
            if row[0] == category:
                instruction = row[1]
                break
    return instruction


async def ask_ai(model, client, question) -> str:
    while True:
        try:
            chat_response = client.chat.complete(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": question,
                    },
                ]
            )
            return chat_response.choices[0].message.content
        # Если получаем ошибку с превышением лимита запросов к API ждём 1 с. и повторяем попытку
        except Exception as e:
            if hasattr(e, 'status_code') and e.status_code == 429:
                await sleep(1)
            else:
                # Если ошибка не связана с лимитом, выбрасываем её дальше
                raise e


async def get_ai_answer(question, category=None):
    api_key = "x5IIBLdAZHQ2e7DrpjyVzvQiL2tjk0jV"
    model = "mistral-large-latest"
    client = Mistral(api_key=api_key)

    question_about_category = (f'На основе категорий вопросов, скажи к какой категории относится вопрос {question}.'
                               f' Пиши в таком формате: name: название категории. Вот Категории вопросов:'
                               f' {", ".join(await get_categories())} Если ни одна категория не подходит пиши:'
                               f' name: ошибка')
    if not category:
        category = (await ask_ai(model, client, question_about_category)).split(': ')[1]

    if 'ошибка' in category:
        return 'Нейросеть не смогла ответить на ваш вопрос'
    else:
        instruction = await get_instruction(category)
        if instruction:
            question_about_instruction = (f'используя данную инструкцию, напиши ответ на вопрос {question}.'
                                          f' Вот инсрукция {instruction}')

            return await ask_ai(model, client, question_about_instruction)
        else:
            return 'Инструкция не найдена'

