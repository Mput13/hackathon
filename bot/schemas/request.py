from models.request import RequestStatus
from schemas.core import Model


class RequestScheme(Model):
    system_id: int | None
    question: str
    answer: str
    # name: str
    user_id: int
    status: RequestStatus
