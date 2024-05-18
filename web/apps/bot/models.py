from django.contrib.auth import get_user_model

from django.db import models


User = get_user_model()
class Message(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
