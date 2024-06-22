import logging
import os

from apps.accounts.schemas import Profile, ProfileCreate
from apps.ai.models import AIEngines
from server.config import Settings
from usso.async_api import AsyncUssoAPI
from usso.async_session import AsyncUssoSession
from usso.core import UserData


async def get_usso_user(credentials: dict) -> UserData:
    usso_api = AsyncUssoAPI(
        url="https://sso.pixiee.io", api_key=os.getenv("USSO_API_KEY")
    )
    try:
        u = await usso_api.get_user_by_credentials(credentials)
    except Exception as e:
        logging.warning(e)
        u = await usso_api.create_user_by_credentials(credentials=credentials)
    return u


async def get_user_profile(user_id: str):
    async with AsyncUssoSession(
        os.getenv("USSO_REFRESH_URL"), os.getenv("PIXIEE_REFRESH_TOKEN")
    ) as session:
        async with session.get(
            f"{Settings.profile_service_url}/profiles/{user_id}"
        ) as response:
            if response.status == 200:
                return Profile(**await response.json())
            elif response.status >= 400 and response.status != 404:
                raise Exception(await response.text())

        profile_request = ProfileCreate(
            user_id=user_id, data={"ai_engine": AIEngines.default()}
        )
        async with session.post(
            f"{Settings.profile_service_url}/profiles/",
            data=profile_request.model_dump_json(),
            headers={"Content-Type": "application/json"},
        ) as response:
            response.raise_for_status()
            return Profile(**await response.json())
