from contextvars import ContextVar
from uuid import uuid4

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def new_request_id() -> str:
    return uuid4().hex


def get_request_id() -> str | None:
    return request_id_var.get()


def set_request_id(rid: str | None) -> None:
    request_id_var.set(rid)
