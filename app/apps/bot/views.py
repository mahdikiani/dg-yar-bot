import json

from django.http import HttpRequest, JsonResponse
from django.views import View
from utils.basic import get_all_subclasses

from . import Bot, bot_functions, dto, keyboards


class WebhookView(View):
    def post(self, request: HttpRequest, bot_route: str, *args, **kwargs):
        update = json.loads(request.body)
        bot_functions.update_bot.delay(
            update, request.build_absolute_uri(), bot_route, *args, **kwargs
        )
        # bot_functions.update_bot(update, request.build_absolute_uri())

        return JsonResponse({"ok": "POST request processed"})


class WebpageWebhookView(View):
    def post(self, request: HttpRequest, *args, **kwargs):
        webpage = dto.WebpageDTO(**json.loads(request.body))
        for bot_cls in get_all_subclasses(Bot.BaseBot):
            bot: Bot.BaseBot = bot_cls()
            if webpage.metadata and bot.me == webpage.metadata.get("bot_name"):
                break
        else:
            raise ValueError("Bot not found")

        if webpage.ai_data and webpage.ai_data.brief:
            text = str(webpage.ai_data)
            markup = keyboards.brief_keyboard(webpage.uid)
        else:
            text = f"{webpage.task_report} ..."
            markup = None

        if webpage.metadata.get("chat_id") and webpage.metadata.get("message_id"):
            bot.delete_message(
                chat_id=webpage.metadata.get("chat_id"),
                message_id=webpage.metadata.get("message_id"),
            )
            bot.send_message(
                text=text,
                chat_id=webpage.metadata.get("chat_id"),
                parse_mode="markdown",
                reply_markup=markup,
            )

        return JsonResponse(
            {"ok": f"Webpage webhook request processed for {webpage.uid}"}
        )


class ProjectWebhookView(View):
    def post(self, request: HttpRequest, *args, **kwargs):
        webpage = dto.WebpageDTO(**json.loads(request.body))
        for bot_cls in get_all_subclasses(Bot.BaseBot):
            bot: Bot.BaseBot = bot_cls()
            if webpage.metadata and bot.me == webpage.metadata.get("bot_name"):
                break
        else:
            raise ValueError("Bot not found")

        if webpage.ai_data and webpage.ai_data.brief:
            text = str(webpage.ai_data)
            markup = keyboards.brief_keyboard(webpage.uid)
        else:
            text = webpage.task_report
            markup = None

        if webpage.metadata.get("chat_id") and webpage.metadata.get("message_id"):
            bot.edit_message_text(
                text=text,
                chat_id=webpage.metadata.get("chat_id"),
                message_id=webpage.metadata.get("message_id"),
                parse_mode="markdown",
                reply_markup=markup,
            )

        return JsonResponse(
            {"ok": f"Webpage webhook request processed for {webpage.uid}"}
        )