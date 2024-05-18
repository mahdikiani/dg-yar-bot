import json

from django.http import HttpRequest, JsonResponse
from django.views import View

from . import bot_functions


class WebhookView(View):
    def post(self, request: HttpRequest, *args, **kwargs):
        update = json.loads(request.body)
        bot_functions.update_bot.delay(update, request.build_absolute_uri())
        # bot_functions.update_bot(update, request.build_absolute_uri())

        return JsonResponse({"ok": "POST request processed"})
