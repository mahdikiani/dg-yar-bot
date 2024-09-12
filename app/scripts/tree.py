import json
import time

import requests
from pydantic import BaseModel, model_validator

errors = []

tree_url = "https://seller.digikala.com/api/v2/categories/tree"

headers = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en,en-US;q=0.9,fa-IR;q=0.8,fa;q=0.7",
    "captcha-token": "",
    "priority": "u=1, i",
    "referer": "https://seller.digikala.com/pwa/product/create/1",
    "sec-ch-ua": '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "x-web-optimize-response": "1",
}

cookies = {
    "_gid": "GA1.2.134967806.1726044231",
    "_gcl_au": "1.1.1807809215.1726044232",
    "_hjSessionUser_2597519": "eyJpZCI6IjU5MmI3ZWY0LTgyMjktNTMwNC04NDFiLTI2MjkwNzczMTAxZCIsImNyZWF0ZWQiOjE3MjYwNDQyMzE4MTMsImV4aXN0aW5nIjpmYWxzZX0=",
    "_ga_LR50FG4ELJ": "GS1.1.1726044232.1.1.1726044365.23.0.0",
    "_ga": "GA1.1.1503749781.1726044231",
    "_hp2_id.1611673244": "%7B%22userId%22%3A%221191325817333604%22%2C%22pageviewId%22%3A%221749771587511869%22%2C%22sessionId%22%3A%224134296449081797%22%2C%22identity%22%3Anull%2C%22trackerVersion%22%3A%224.0%22%7D",
    "PHPSESSID": "oohqnt6mlclmumlsjcauhbm8co",
    "tracker_glob_new": "dm2zkq7",
    "seller_api_access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzM4NCJ9.eyJ0b2tlbl9pZCI6MTg5MjEyMDIsInNlbGxlcl9pZCI6MTUyMTYzNSwicGF5bG9hZCI6eyJ1c2VybmFtZSI6Ijk4OTEyMjM0MTc2OSIsInJlZ2lzdGVyX3Bob25lIjoiOTg5MTIyMzQxNzY5IiwiZW1haWwiOiJtYWhkaWtpYW55QGdtYWlsLmNvbSIsImJ1c2luZXNzX25hbWUiOiJcdTA2MjdcdTA2Y2NcdTA2NDZcdTA2MjhcdTA2Y2NcdTA2MmEiLCJmaXJzdF9uYW1lIjoiXHUwNjQ1XHUwNjJkXHUwNjQ1XHUwNjJmIFx1MDY0NVx1MDY0N1x1MDYyZlx1MDZjYyIsImxhc3RfbmFtZSI6Ilx1MDZhOVx1MDZjY1x1MDYyN1x1MDY0Nlx1MDZjYyIsImNvbXBhbnlfbmFtZSI6bnVsbCwidmVyaWZpZWRfYnlfb3RwIjpbIjk4OTEyMjM0MTc2OSJdfSwiZXhwIjoxNzI2OTE2MTU5fQ.bHgynD2_qU_C1db3CjSOoKEuW_3i6XkVc5bNxrRIvHpT4erdtEMYIWvXP3GXUxJ3",
    "_sp_ses.13cb": "*",
    "ab_test_experiments": "%5B%22229ea1a233356b114984cf9fa2ecd3ff%22%2C%22f0fd80107233fa604679779d7e121710%22%2C%2237136fdc21e0b782211ccac8c2d7be63%22%5D",
    "TS01b6ea4d": "010231059105e29c6268e181fc918a23340968e2be8852fab0755373cdbe30364cf87defcd37db8fdf19d899a785226e4bff5cb2fc4d241d9d9cb357d7ba3f094b81be61b48f82fedb87649f1087da3f0c3f5f0611a844ab7f11525b3ddcab5344133baf7e30d6ff398eac4bd92374ecf06997891cca933681a3b42369060bd14bea75027d258bca0141cc7ee1518a91a25e3f97252aa84ead4169c0c4c0b6f38df995cce0a2b7c4f7c5dad5ef71aeed3beda9d73c8a668f671768e90bddef822b62dc019086e74145792b5503e0ef30e0146bb3bd2f3e4e9727f95e9697c35bc4222ef851",
    "tracker_session": "3pwLKbR",
    "_ga_QQKVTD5TG8": "GS1.1.1726061735.2.0.1726061735.0.0.0",
    "TS018d011a": "0102310591dbb0d010ad5ab761564d79835ab1316e1caecb467c59004a62cf08f1ba324ef06c624fa5f70742e7fd424935f956c08e",
    "_ga_VELJGC0JY7": "GS1.1.1726062717.4.1.1726062769.0.0.0",
    "_sp_id.13cb": "164c003d-8069-4a0d-a73b-b2f042246754.1726052078.2.1726062773.1726054563.0e436a5e-8906-4419-be10-7b0e905b6a6c.a402eeca-a87b-470d-9bb5-a45aef363b98.21610314-dd55-43ad-9c6a-a62037d30f40.1726057593207.34",
}


class Node(BaseModel):
    id: int
    title: str
    leaf: bool
    category: str | None

    @model_validator(mode="before")
    def check_category(cls, values):
        if values.get("category") is None:
            values["category"] = values.get("title").split(" > ")[-1]
        return values


def get_cats(parent_id: int = None) -> list[Node]:
    params = {}
    if parent_id:
        params["search[parent_id]"] = f"{parent_id}"

    for i in range(3):
        try:
            r = requests.get(tree_url, headers=headers, cookies=cookies, params=params)
            time.sleep(1)
            data = r.json()
            items = data.get("data", {}).get("items", {})
            return [Node(**item) for item in items]
        except Exception as e:
            print("Error", e, params)

    errors.append(parent_id)
    return []


def get_cats_rec(parent_id: int = None, parent_name=""):
    print(parent_id, parent_name)
    res = []
    items = get_cats(parent_id)
    for item in items:
        if item.leaf:
            item.title = parent_name + " > " + item.title
            res.append(item)
        else:
            res += get_cats_rec(str(item.id), parent_name + " > " + item.title)
    return res


def crawl():
    all_cats = get_cats_rec()

    # with open("cats.txt", "w") as f:
    #     f.write(all_cats)

    with open("cats.json", "w") as f:
        json.dump(
            [node.model_dump() for node in all_cats], f, indent=4, ensure_ascii=False
        )


def load():
    with open("cats.json") as f:
        data = json.load(f)

    all_cats = [Node(**cat) for cat in data]
    with open("cats2.json", "w") as f:
        json.dump(
            [node.model_dump() for node in all_cats], f, indent=4, ensure_ascii=False
        )

    with open("cat_name.json", "w") as f:
        json.dump([node.category for node in all_cats], f, indent=4, ensure_ascii=False)


load()
