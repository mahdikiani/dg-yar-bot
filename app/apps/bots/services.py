import logging
import asyncio
import json

import aiohttp
import openai
from aiocache import cached
from apify_client import ApifyClient

from apps.digikala import sheet
from apps.digikala.digikala import DGClient
from server.config import Settings
from utils.aionetwork import aio_request_session
from utils.texttools import backtick_formatter, get_dict_data


@cached(ttl=3600)
async def aio_request(*, method: str = "get", url: str = None, **kwargs) -> dict:
    async with aiohttp.ClientSession() as session:
        return await aio_request_session(session, method=method, url=url, **kwargs)


async def get_sheet_url(*args, **kwargs):
    return "https://docs.google.com/spreadsheets/d/1WHDJsLY23fnQFoGp2H3UIvGsRMDQAfZB4U5XKvy0C_g/edit?gid=2089675657#gid=2089675657"


def guess_ai(product_data, prompt_key, **kwargs):
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


async def get_sheet(url, provider):
    # return "https://docs.google.com/spreadsheets/d/1GdiHsAzDR6r7nPE17f-vTXu3DUQlphXvuU2mXFXwah4/edit?gid=0#gid=0"
    # data
    if provider == "Amazon":
        product_data = await amazon(url)
    elif provider == "Digikala":
        product_data = DGClient().get_product_details(url).get("data")
    elif provider == "Sazito":
        product_data = (
            await aio_request(method="get", url=url)
            .get("result", {})
            .get("product", {})
        )
    else:
        return "فروشنده پشتیبانی نمیشود"

    try:
        category = guess_ai(
            product_data,
            "get_category",
            categories=json.dumps(Settings().categories, ensure_ascii=False),
        )
        category = Settings().get_category_data(category)
        logging.info(category)
        category_id = category.get("id")

        # brand
        r = DGClient().get_category_details(category.get("id"))
        brands = r.get("data").get("bind").get("brands")
        logging.info(brands)

        brand = guess_ai(
            product_data,
            "get_category_brand",
            brands=json.dumps(brands, ensure_ascii=False),
        )
        brand_row = get_dict_data(brands, "title_fa", brand.get("brand"))
        if not brand_row:
            brand_row = get_dict_data(brands, "title_en", brand.get("brand"))
        brand_id = brand_row.get("id")

        logging.info(brand_id)

        data = get_product_fields(product_data, category_id, brand_id, provider)
        logging.info(data)
        # data = {
        #     "category_id": 1234,
        #     "division_id": None,
        #     "brand_id": 1234,
        # }
        gsheet = sheet.create_sheet_df([data])
        return sheet.get_sheet_url(gsheet)
    except Exception as e:
        import traceback

        traceback_str = "".join(traceback.format_tb(e.__traceback__))
        logging.error(f"sheet error {traceback_str} {e}")
        return "خطا در ایجاد شیت"


def get_product_types(product_data, types):
    return json.dumps([1234])


def get_product_model(product_data):
    return {
        "model": "",
        "description": "",
        "disadvantages": json.dumps([]),
        "advantages": json.dumps([]),
    } | guess_ai(product_data, "product_title")
    return {
        "model": "S22 fan edition",
        "description": "این محصول از توانایی های عجیبی برخوردار است",
        "disadvantages": json.dumps([]),
        "advantages": json.dumps([]),
    }


def mefa_id(product_data):
    return {
        "general_mefa_id": "2132114141312321",
        # "exclusive_mefa_id": "2132114141312321",
    }


def package_size(product_data):
    return {
        "package_width": 12,
        "package_height": 12,
        "package_length": 12,
        "package_weight": 12,
    }


def get_attribute_value(product_data, attribute):
    if attribute.get("type") in ["input", "text"]:
        return guess_ai(
            product_data,
            "attribute_match_text",
            field_name=attribute.get("title"),
            hint=attribute.get("hint"),
            field_values=attribute.get("values"),
        )
        return f'{attribute.get("type")} value'
    if attribute.get("type") == "checkbox":
        return guess_ai(
            product_data,
            "attribute_match_checkbox",
            field_name=attribute.get("title"),
            hint=attribute.get("hint"),
            field_values=attribute.get("values"),
        )
        return list(attribute.get("values").keys())[0]
    if attribute.get("type") == "select":
        return guess_ai(
            product_data,
            "attribute_match_select",
            field_name=attribute.get("title"),
            hint=attribute.get("hint"),
            field_values=attribute.get("values"),
        )
        return json.dumps(
            [list(attribute.get("values").values())[0].get("text")], ensure_ascii=False
        )


def get_attributes(product_data, category_id):
    attributes = DGClient().get_category_attribute(category_id)
    result = {}
    for attribute in attributes:
        result[attribute.get("title")] = json.dumps(
            get_attribute_value(product_data, attribute), ensure_ascii=False
        )

    return result


def get_images(product_data, origin):
    if origin == "Amazon":
        return product_data.get("highResolutionImages", [])
    if origin == "Digikala":
        return (
            product_data.get("data")
            .get("intrack")
            .get("eventData")
            .get("productImageUrl")
        )
    if origin == "Sazito":
        images = product_data.get("images", [])
        return [image.get("url") for image in images]

    return []


def get_product_fields(product_data, category_id, brand_id, origin):
    result = {}
    result.update(
        {
            "category_id": category_id,
            "division_id": None,
            "brand_id": brand_id,
            "product_type_ids": get_product_types(product_data, ["type1", "type2"]),
            "color_id": 1234,
            "is_iranian": origin in ["Sazito"],
            "product_classes": json.dumps([123]),
        }
    )
    result.update(get_product_model(product_data))
    result.update(mefa_id(product_data))
    result.update(package_size(product_data))

    result.update(get_attributes(product_data, category_id))

    images = get_images(product_data, origin)
    for i in range(5):
        result[f"image_{i+1}"] = images[i] if i < len(images) else None

    return result


async def main():
    url = "https://www.amazon.com/Redragon-S101-Keyboard-Ergonomic-Programmable/dp/B00NLZUM36"
    sheet_url = await get_sheet(url, "Amazon")
    print(sheet_url)


if __name__ == "__main__":
    asyncio.run(main())
