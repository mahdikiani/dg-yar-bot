import json
import httpx
import asyncio
import aiohttp
from aiocache import cached
from apify_client import ApifyClient
import openai

from utils.aionetwork import aio_request_session
from server.config import Settings
from utils.texttools import backtick_formatter, get_dict_data
from apps.digikala.digikala import DGClient


@cached(ttl=3600)
async def aio_request(*, method: str = "get", url: str = None, **kwargs) -> dict:
    async with aiohttp.ClientSession() as session:
        return await aio_request_session(session, method=method, url=url, **kwargs)


async def get_sheet_url(*args, **kwargs):
    return "https://docs.google.com/spreadsheets/d/1WHDJsLY23fnQFoGp2H3UIvGsRMDQAfZB4U5XKvy0C_g/edit?gid=2089675657#gid=2089675657"


async def guess_ai(product_data, prompt_key, **kwargs):
    client = openai.Client(api_key=Settings.OPENAI_API_KEY)
    system_prompt = Settings().prompts(f"{prompt_key}_system")
    user_prompt = Settings().prompts(f"{prompt_key}_user")

    messages = [
        {
            "role": "system",
            "content": system_prompt.format(**kwargs),
        },
        {
            "role": "user",
            "content": user_prompt.format(product=str(product_data), **kwargs),
        },
    ]

    response = client.chat.completions.create(model="gpt-4o", messages=messages)
    resp_text = backtick_formatter(response.choices[0].message.content)
    return json.loads(resp_text)


async def amazon(url):
    client = ApifyClient(Settings.APIFY_API_KEY)

    run_input = {
        "categoryOrProductUrls": [{"url": url}],
        "maxItemsPerStartUrl": 100,
        "proxyCountry": "AUTO_SELECT_PROXY_COUNTRY",
        "maxOffers": 0,
        "scrapeSellers": False,
        "useCaptchaSolver": False,
        "scrapeProductVariantPrices": False,
    }

    # Run the Actor and wait for it to finish
    run: dict = client.actor("BG3WDrGdteHgZgbPK").call(run_input=run_input)
    run_res = client.run(run.get("id")).get()

    while run_res.get("status") == "RUNNING":
        await asyncio.sleep(5)
        run_res = client.run(run.get("id")).get()

    dataset = client.dataset(run.get("defaultDatasetId")).list_items().items
    return dataset[0]


async def get_sheet(url):
    # data
    product_data = await amazon(url)

    # category
    category = await guess_ai(
        product_data,
        "get_category",
        categories=json.dumps(Settings().categories, ensure_ascii=False),
    )
    category = Settings().get_category_data(category)
    category_id = category.get("id")

    # brand
    r = DGClient().get_category_details(category.get("id"))
    brands = r.get("data").get("bind").get("brands")
    brand = await guess_ai(
        product_data,
        "get_category_brand",
        brands=json.dumps(brands, ensure_ascii=False),
    )
    brand_row = get_dict_data(brands, "title_fa", brand.get("brand"))
    if not brand_row:
        brand_row = get_dict_data(brands, "title_en", brand.get("brand"))
    brand_id = brand_row.get('id')

    


def get_product_fields(category_id, data):
    {
        "category_id": 1234,
        "division_id": 1234,
        "model": "S22 fan edition",
        "brand_id": "Samsung",
        "product_type_ids": [1234],
        "color_id": 1234,
        "is_iranian": True,
        "product_classes": [123],
        "fake": True,
        "fake_reasons": [1234],
        "general_mefa_id": "2132114141312321",
        "exclusive_mefa_id": "2132114141312321",
        "package_width": 12,
        "package_height": 12,
        "package_length": 12,
        "package_weight": 12,
        "description": "این محصول از توانایی های عجیبی برخوردار است ",
        "disadvantages": ["محصول بد، محصول ضعیف، باطری ضعیف "],
        "advantages": ["محصول خوب، محصول عالی، باطری قوی "],
        "draft_product_id": 1234,
    }
