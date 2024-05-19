from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class AIEngines(models.TextChoices):
    gpt4o = "gpt4o", "gpt4o"
    gpt4turbo = "gpt-4-turbo", "gpt-4-turbo"
    gpt4 = "gpt-4", "gpt-4"
    gpt35turbo = "gpt-3.5-turbo", "gpt-3.5-turbo"
    claud3opus = "claud-3-opus", "claud-3-opus"
    claud3sonnet = "claud-3-sonnet", "claud-3-sonnet"
    claud3haiku = "claud-3-haiku", "claud-3-haiku"

    @property
    def tapsage_bot_id(self):
        return {
            AIEngines.gpt4o: "55d1e911-67f1-493c-b4ff-bbafcca0e26b",
            AIEngines.gpt4turbo: "3e0640f3-286e-4c4d-abea-0993d522771f",
            AIEngines.gpt4: "288f04e2-728d-4be4-af0b-83ae1b97b87a",
            AIEngines.gpt35turbo: "03d99ad7-e344-4b0c-bbf5-46609f47d937",
            AIEngines.claud3opus: "0f87bb21-2357-49a4-a80d-d2f944b89671",
            AIEngines.claud3sonnet: "f9402e09-18b7-49e9-b08b-ad8bd8836511",
            AIEngines.claud3haiku: "2db268fe-914c-469e-b597-9ed46dc0f0f3",
        }[self]

    @property
    def price(self):
        return {
            AIEngines.gpt4o: 0.007,
            AIEngines.gpt4turbo: 0.007,
            AIEngines.gpt4: 0.007,
            AIEngines.gpt35turbo: 0.007,
            AIEngines.claud3opus: 0.007,
            AIEngines.claud3sonnet: 0.007,
            AIEngines.claud3haiku: 0.007,
        }[self]


class BotUser(AbstractUser):
    username = models.CharField(max_length=50, unique=True)
    # usso_id = models.UUIDField(unique=True, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict)
    bot_type = models.CharField(
        max_length=30,
        choices=[("telegram", "telegram"), ("bale", "bale")],
        default="telegram",
    )
    first_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(default=timezone.now)

    ai_engine = models.CharField(
        max_length=30,
        choices=AIEngines.choices,
        default=AIEngines.gpt4o,
    )

    # objects = CustomUserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.username
