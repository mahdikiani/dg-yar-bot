from telebot import async_telebot
from usso import UserData
from pydantic import BaseModel

from apps.accounts.schemas import Profile


class MessageOwned(async_telebot.types.Message):
    user: UserData | None = None
    profile: Profile | None = None


class MSGButton(BaseModel):
    name: str
    text: str


class MessageStruct(BaseModel):
    desc: str | None = None
    msg: str
    btn: list[MSGButton] = []
    fields: str | None = None


class DGWebhook(BaseModel):
    dkp: str
