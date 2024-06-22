from apps.base.models import OwnedEntity


class Message(OwnedEntity):
    content: str = ""
