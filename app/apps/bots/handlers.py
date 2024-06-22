import logging

import singleton
from apps.bots import Bot, middlewares
from apps.bots.bot_functions import callback, inline_query, inline_query_ai, message
from server.config import Settings
from telebot import async_telebot
from utils.basic import get_all_subclasses


def get_bot(bot_name: str) -> Bot.BaseBot:
    for bot_cls in get_all_subclasses(Bot.BaseBot):
        bot: Bot.BaseBot = bot_cls()
        if bot.me == bot_name:
            return bot
    else:
        raise ValueError("Bot not found")


class BotFunctions(metaclass=singleton.Singleton):
    is_setup = False

    # def __init__(self):
    #     asyncio.run(self.setup())

    async def setup(self):
        if self.is_setup:
            return

        for bot_cls in get_all_subclasses(Bot.BaseBot):
            bot: Bot.BaseBot = bot_cls()

            await self.setup_webhook(bot)
            await self.setup_bot(bot)

        self.is_setup = True

    async def setup_webhook(self, bot: Bot.BaseBot):
        # reverse_url = reverse("bot_webhook", kwargs={"bot_route": bot.webhook_route})
        reverse_url = f"bots/webhook/{bot.webhook_route}"
        webhook_url = f"https://{Settings().root_url}/{reverse_url}"
        if (await bot.get_webhook_info()).url != webhook_url:
            await bot.delete_webhook()
            res = await bot.set_webhook(url=webhook_url)
            logging.warning(f"set webhook for {bot} with result: {res}")

    async def setup_bot(self, bot: Bot.BaseBot):
        middleware = middlewares.UserMiddleware(bot)
        bot.setup_middleware(middleware)
        bot.register_callback_query_handler(
            callback, func=lambda _: True, pass_bot=True
        )
        bot.register_message_handler(
            message,
            func=lambda _: True,
            content_types=["text", "voice"],
            pass_bot=True,
        )
        if bot.bot_type == "telegram":
            bot.register_inline_handler(
                inline_query, func=lambda _: True, pass_bot=True
            )
            bot.register_chosen_inline_handler(
                inline_query_ai, func=lambda _: True, pass_bot=True
            )


async def update_bot(bot_route: str, update_dict: dict, *args, **kwargs):
    for bot_cls in get_all_subclasses(Bot.BaseBot):
        bot: Bot.BaseBot = bot_cls()
        if bot.webhook_route == bot_route:
            break
    else:
        logging.error(f"Bot not found for {bot_route}")
        raise ValueError(f"Bot not found for {bot_route}")

    update = async_telebot.types.Update.de_json(update_dict)

    if update:
        await bot.process_new_updates([update])


def main():
    import asyncio

    BotFunctions()
    bot = Bot.TGTelegramBot()
    asyncio.run(bot.delete_webhook())
    asyncio.run(bot.polling())


if __name__ == "__main__":
    main()
