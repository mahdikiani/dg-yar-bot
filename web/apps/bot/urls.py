from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from .views import WebhookView

urlpatterns = [
    path(
        f"webhook/<str:bot_route>",
        csrf_exempt(WebhookView.as_view()),
        name="bot_webhook",
    ),
]
