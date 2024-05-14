from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from .views import WebhookView

urlpatterns = [
    path(
        f"webhook/telegram", csrf_exempt(WebhookView.as_view()), name="telegram_webhook"
    ),
    path(f"webhook/bale", csrf_exempt(WebhookView.as_view()), name="bale_webhook"),
]
