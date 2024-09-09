import aiohttp
from aiocache import cached
from utils.aionetwork import aio_request_session


@cached(ttl=3600)
async def aio_request(*, method: str = "get", url: str = None, **kwargs) -> dict:
    async with aiohttp.ClientSession() as session:
        return await aio_request_session(session, method=method, url=url, **kwargs)


async def get_sheet_url(*args, **kwargs):
    return "https://docs.google.com/spreadsheets/d/1WHDJsLY23fnQFoGp2H3UIvGsRMDQAfZB4U5XKvy0C_g/edit?gid=2089675657#gid=2089675657"
