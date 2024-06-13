from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from . import views

urlpatterns = [
    path(
        f"webhook/<str:bot_route>",
        csrf_exempt(views.WebhookView.as_view()),
        name="bot_webhook",
    ),
    path(
        "webpage-webhook/",
        csrf_exempt(views.WebpageWebhookView.as_view()),
        name="webpage_webhook",
    ),
    path(
        "project-webhook/",
        csrf_exempt(views.ProjectWebhookView.as_view()),
        name="project_webhook",
    ),
]
