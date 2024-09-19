import random
from datetime import datetime, timedelta

import requests
from singleton import Singleton


class DGClient(metaclass=Singleton):

    def __init__(self):
        self.base_url = "https://digikala.bot.inbeet.tech/api/v3"
        self.urls = [
            "",
            "/auth/scopes",
            "/auth/scopes/{client_code}",
            "/auth/token",
            "/auth/refresh-token",
            "/auth/decrypt-code",
            "/product-creation/search/v2",
            "/product-creation/search/suggestion/v2",
            "/product-creation/be-seller/{product_id}",
            "/product-creation/search/category/v2/{keyword}",
            "/product-creation/category/{category_id}/validation",
            "/product-creation/product/detail/validation",
            "/product-creation/draft-product/count",
            "/product-creation/draft-product/{draft_product_id}",
            "/product-creation/{draft_product_id}/auto-title",
            "/product-creation/auto-title/save",
            "/product-creation/attributes/{category_id}",
            "/product-creation/attributes",
            "/product-creation/images/requests/brand-logo/upload",
            "/product-creation/images/requests/upload",
            "/product-creation/images/upload",
            "/product-creation/images/ai",
            "/product-creation/save",
            "/product-creation/assign",
            "/product-creation/brand/request",
            "/product-creation/brand",
            "/draft-products/seller",
            "/draft-products/{draft_product_id}",
            "/products/seller",
            "/products/{product_id}/score",
            "/product-edit/{product_id}/publish",
            "/product-edit/{product_id}",
            "/product-edit/{category_id}/auto-title",
            "/commission/commissions/{product_id}",
            "/commission/{category_id}/{brand_id}",
            "/variants",
            "/variants/{variant_id}",
            "/variants/b2b-activation",
            "/variants/export",
            "/variants/{variant_id}/gold",
            "/variants/{variant_id}/price-calculator",
            "/variants/{variant_id}/activation",
            "/variants/{variant_id}/b2b-prices",
            "/variants/{variant_id}/archive",
            "/variants/{variant_id}/seller-stock",
            "/orders",
            "/orders/statistics",
            "/orders/ongoing",
            "/orders/ongoing/statistics",
            "/orders/history",
            "/orders/excel/export",
            "/orders/{order_item_id}",
            "/variants/{variant_id}/order-items",
            "/variants/{variant_id}/order-items/statistics",
            "/inventories",
            "/inventories/{product_variant_id}",
            "/inventories/{product_variant_id}/export",
            "/inventories/export",
            "/packages",
            "/packages/warehouses",
            "/packages/warehouses/{warehouse_id}/capacities",
            "/packages/{package_id}",
            "/packages/{package_id}/excel/export",
            "/packages/consignment/variants",
            "/packages/order-fulfilment/variants",
            "/variants/packages/consignment",
            "/shipments/dk",
            "/shipments/dk/packages",
            "/shipments/dk/{shipment_id}",
            "/profile",
            "/profile/business",
            "/profile/store",
            "/profile/address",
            "/profile/warehouse",
            "/profile/document",
            "/profile/training",
            "/profile/performance",
            "/questions",
            "/questions/{question_id}",
            "/questions/answer",
            "/insight/overview",
            "/insight/top-deactivated",
            "/insight/trend-sales-reports",
            "/insight/sales-reports",
            "/insight/overview/export",
            "/lightening-deal/products",
            "/lightening-deal/products/{product_id}",
            "/lightening-deal/promotions",
            "/lightening-deal/promotions/{productId}",
            "/lightening-deal/bids",
            "/lightening-deal/bidsSummary",
            "/lightening-deal/check-duplicate-dkp-in-promotion/{promotionId}/{productId}",
            "/lightening-deal/bids/{bidId}/payment-method",
        ]

    def _request(self, method, url=None, status_code="200", **kwargs):
        if url is None:
            path = kwargs.pop("path")
            url = self.get_route(path)

        headers = kwargs.get("headers", {})
        headers["x-response-code"] = status_code
        headers["content-type"] = "application/json"

        response = requests.request(method=method, url=url, headers=headers, **kwargs)
        response.raise_for_status()
        return response.json()

    def get_auth(self, token):
        path = "auth/token"
        res = self._request("POST", path=path, json={"authorization_code": token})
        return res.get('data')

    def get_route(self, path):
        return f"{self.base_url}/{path}"

    def generate_random_order(self) -> dict:
        return {
            "product_variant_id": random.randint(1000, 9999),
            "product_image_url": "http://dkstatics-public.digikala.com/digikala-products/c72042c9bb6b8795f6094e07837edf9f00_1613546028.jpg?x-oss-process=image/resize,m_lfit,h_115,w_115/quality,q_60",
            "product_variant_title": "کتاب | گارانتی اصالت و سلامت فیزیکی کالا",
            "supplier_code": "sc01",
            "order_id": random.randint(10000, 99999),
            "order_created_at": (
                datetime.now() - timedelta(seconds=random.randint(0, 1000))
            ).isoformat(),
            "warehouse_status_at": (
                datetime.now() - timedelta(seconds=random.randint(0, 1000))
            ).isoformat(),
            "commitment_date": (
                datetime.now() - timedelta(seconds=random.randint(0, 1000))
            ).isoformat(),
            "quantity": random.randint(1, 10),
            "selling_price": 645800,
            "amazing_discount": 1200,
            "discount_manager": 123,
            "total_price": 645800,
        }

    def get_orders(self, from_date: datetime) -> list:
        path = "orders"
        r = self._request(method="get", path=path)
        orders = r.get("data", {}).get("items", [])
        orders = [
            self.generate_random_order()
            for _ in range(random.choices([1, 2, 3], [0.5, 0.3, 0.2])[0])
        ]
        return [
            order
            for order in orders
            if datetime.fromisoformat(order["order_created_at"]) > from_date
        ]

    def get_canceled_order_history(self):
        return [
            self.generate_random_order()
            for _ in range(random.choices([0, 1, 2], [0.95, 0.03, 0.02])[0])
        ]

    def get_product(self, product_variant_id):
        pass

    def get_category_details(self, category_id):
        path = f"product-creation/category/{category_id}/validation"
        r = self._request(method="get", path=path)
        return r

    def get_category_attribute(self, category_id):
        path = f"product-creation/attributes/{category_id}"
        r = self._request(method="get", path=path)
        attr_groups = r.get("data").get("category_group_attributes")

        attributes = []
        for attrs in attr_groups.values():
            attributes += list(attrs.get("attributes").values())

        return attributes

    def get_product_details(self, url):
        # url = 'https://www.digikala.com/product/dkp-10797167/sadlkjalkd-fasfn'
        pid = url.split("/")[4].split("-")[1]
        return requests.get(f"https://api.digikala.com/v2/product/{pid}/").json()
    
    def save_product(self, product_data):
        path = "/product-creation​/product​/detail​/validation"
        draft = self._request("post", path=path, json=product_data)

        path = 'product-creation​/auto-title​/save'
        draft = self._request("post", path=path, json={"draft_product_id": draft.get("data").get("draft_product_id"), **product_data})

        return draft
