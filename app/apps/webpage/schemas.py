from typing import Literal

from apps.base.models import Language, TaskMixin
from apps.base.schemas import BaseEntitySchema
from pydantic import BaseModel


class ProductInfo(BaseModel):
    name: str
    description: str

    def __str__(self) -> str:
        return f"{self.name}: {self.description}"


class Brief(BaseModel):
    description: str | None = None
    attention: str | None = None
    interest: str | None = None
    desire: str | None = None
    action: str | None = None

    def __str__(self, lang: Language = Language.Persian):
        match lang:
            case Language.Persian:
                introduction = "معرفی"
                attention = "توجه"
                interest = "علاقه"
                desire = "خواست"
                action = "عمل"

            case _:
                introduction = "Introduction"
                attention = "Attention"
                interest = "Interest"
                desire = "Desire"
                action = "Action"

        return "\n\n".join(
            [
                f"{introduction}: {self.description}",
                f"{attention}: {self.attention}",
                f"{interest}: {self.interest}",
                f"{desire}: {self.desire}",
                f"{action}: {self.action}",
            ]
        ).strip()


class SourceAIData(BaseModel):
    brand_name: str | None = None
    brief: Brief | str | None = None
    favicon: str | None = None
    colors: list[str] | None = None
    fonts: list[str] | None = None
    audience: str | None = None
    tone: Literal["friendly", "professional", "informal", "enthusiastic"] | None = None
    products: list[ProductInfo] | None = None
    product_index: int | None = None

    def __str__(self, lang: Language = Language.Persian) -> str:
        match lang:
            case Language.Persian:
                brand = "برند"
                products = "محصولات"
                audience = "مخاطب"
                tone = "لحن"
            case _:
                brand = "brand"
                products = "products"
                audience = "audience"
                tone = "tone"

        return "\n\n".join(
            [
                f"{brand}: {self.brand_name}",
                str(self.brief),
                (
                    f"{products}:\n"
                    + "\n".join([str(product) for product in self.products])
                    if self.products
                    else ""
                ),
                f"{audience}: {self.audience}",
                f"{tone}: {self.tone}",
            ]
        )


class Webpage(TaskMixin, BaseEntitySchema):
    url: str
    page_source: str | None = None
    crawl_method: Literal["direct", "browser"] = "direct"
    screenshot: str | None = None
    ai_data: SourceAIData | None = None

    @staticmethod
    def create_url():
        return "https://api.pixiee.io/webpages/"
