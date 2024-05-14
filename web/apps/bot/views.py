import json

from django.http import HttpRequest, JsonResponse
from django.views import View

import telebot
from . import Bot
from . import bot_functions


class WebhookView(View):
    def post(self, request: HttpRequest, *args, **kwargs):
        bot_functions.BotFunctions()

        request_url = request.build_absolute_uri()
        if request_url.split("/")[-1].startswith("telegram"):
            bot = Bot.TelegramBot()
        # elif request_url.split("/")[-1].startswith("bale"):
        #     bot = Bot.BaleBot()

        update = json.loads(request.body)
        update = telebot.types.Update.de_json(update)

        if update:
            bot.process_new_updates([update])

        return JsonResponse({"ok": "POST request processed"})
