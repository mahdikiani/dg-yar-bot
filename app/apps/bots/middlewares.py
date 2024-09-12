import uuid

from telebot import async_telebot
from usso.core import UserData

from apps.accounts.schemas import Profile
from apps.bots import Bot, schemas


class UserMiddleware(async_telebot.BaseMiddleware):
    def __init__(self, bot: Bot.BaseBot, *args, **kwargs):
        self.update_sensitive = True
        self.update_types = [
            "message",
            #  "edited_message",
            "callback_query",
            # "inline_query"
        ]
        self.bot = bot
        self.bot_type = bot.bot_type
        super().__init__(*args, **kwargs)

    async def pre_process_message(self, message: async_telebot.types.Message, data):
        messenger = self.bot_type
        from_user = message.from_user if message.from_user else message.chat
        if from_user.id == (await self.bot.get_me()).id:
            from_user = message.chat

        credentials = {
            "auth_method": messenger,
            "representor": f"{from_user.id}",
        }
        user: UserData = UserData(user_id=str(uuid.uuid4()))
        profile: Profile = Profile()
        message_owned: schemas.MessageOwned = message
        message_owned.user = user
        message_owned.profile = profile
        return

    async def pre_process_callback_query(
        self, call: async_telebot.types.CallbackQuery, data
    ):
        await self.pre_process_message(call.message, data)

    async def post_process_message(
        self, message: async_telebot.types.Message, data, exception
    ):
        pass

    async def post_process_callback_query(
        self, call: async_telebot.types.CallbackQuery, data, exception
    ):
        pass
