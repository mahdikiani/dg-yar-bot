from apps.accounts.schemas import Profile
from telebot import async_telebot
from usso import UserData


class MessageOwned(async_telebot.types.Message):
    user: UserData | None = None
    profile: Profile | None = None
