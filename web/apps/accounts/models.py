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
            AIEngines.gpt4o: "9abab26b-c45a-4d86-a5e6-8efbf03adb60",
            AIEngines.gpt4turbo: "9abab26b-c45a-4d86-a5e6-8efbf03adb60",
            AIEngines.gpt4: "9abab26b-c45a-4d86-a5e6-8efbf03adb60",
            AIEngines.gpt35turbo: "9abab26b-c45a-4d86-a5e6-8efbf03adb60",
            AIEngines.claud3opus: "9abab26b-c45a-4d86-a5e6-8efbf03adb60",
            AIEngines.claud3sonnet: "9abab26b-c45a-4d86-a5e6-8efbf03adb60",
            AIEngines.claud3haiku: "9abab26b-c45a-4d86-a5e6-8efbf03adb60",
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
