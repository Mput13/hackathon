
import logging
import re
from typing import Literal

import argon2
from geopy.distance import distance


def hash_password(password: str) -> str:
    argon2_hasher = argon2.PasswordHasher()
    return argon2_hasher.hash(password)


def check_password(hashed_password: str, password: str) -> bool:
    argon2_hasher = argon2.PasswordHasher()
    return argon2_hasher.verify(hashed_password, password)


def setup_logging(level: Literal['DEBUG', 'INFO', 'ERROR', 'WARNING'] = 'DEBUG'):
    while len(logging.root.handlers) > 0:
        logging.root.removeHandler(logging.root.handlers[-1])

    logging.basicConfig(
        level=getattr(logging, level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        force=True
    )


async def calculate_distance(point, user_coordinates):
    return distance(user_coordinates, (point["coordinates"]["lat"], point["coordinates"]["lon"])).km


def to_camel(string: str) -> str:
    """
    Верблюдезирует строку, со строчным написанием первого слова

    to_camel_case -> toCamelCase

    :param string: строка в snake case'е
    :type string: str
    :return: строка в camel case'е
    :rtype: str
    """
    return ''.join(word if i == 0 else word.capitalize() for i, word in enumerate(string.split('_')))


def to_snake(string: str) -> str:
    """
    Из CamelCase в snake_case
    """
    return re.sub('(?!^)([A-Z]+)', r'_\1', string).lower()


def to_cebab(string: str) -> str:
    """
    Из CamelCase в cebab-case
    """
    return re.sub('(?!^)([A-Z]+)', r'-\1', string).lower()


async def create_url(resource, id=None):
    url = "https://5.141.28.151/apirest.php/"
    resources = \
        {
            "init_session": "initSession",
            "kill_session": "killSession",
            "ticket_create_update": "Ticket",
            "ticket_info": f"Ticket/{id}",
            "create_get_comment": f"Ticket/{id}/ITILFollowup/",
            "get_solution": f"Ticket/{id}/ITILSolution"
        }
    new_url = url + resources[resource]
    return new_url
