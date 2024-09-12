from apps.base.models import BaseEntity
from apps.digikala.digikala import DGClient


class Profile(BaseEntity):
    token: str = ""

    def access_token(self):
        data = DGClient().get_auth(self.token)
        access_token = data.get("data", {}).get("access_token")
        return access_token
