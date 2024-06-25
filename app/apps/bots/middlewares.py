from telebot import async_telebot
from usso.core import UserData

from apps.accounts.handlers import get_user_profile, get_usso_user
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
        user: UserData = await get_usso_user(credentials)
        profile: Profile = await get_user_profile(user_id=user.uid)
        message_owned: schemas.MessageOwned = message
        message_owned.user = user
        message_owned.profile = profile
        return
        # TODO

        # user, _ = User.objects.get_or_create(username=u.uid)

        user.last_login = datetime.datetime.now(datetime.UTC)

        save_name = " ".join(
            [
                f"{self.bot.me}: "
                f'{from_user.first_name if from_user.first_name else ""}',
                f'{from_user.last_name if from_user.last_name else ""}',
            ]
        )
        if save_name != user.first_name:
            user.first_name = save_name
        if from_user.username and from_user.username != user.last_name:
            user.last_name = from_user.username
        user.save()

        message.user = user

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
