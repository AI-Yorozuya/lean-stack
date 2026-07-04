"""商品的輸入/輸出形狀（ninja Schema）。

教學重點：sku 只在「建立」時給——業務識別碼建立後要穩定，改資料時不動它。
"""
from decimal import Decimal

from ninja import Field, Schema


class ProductIn(Schema):
    sku: str = Field(..., min_length=1, max_length=40)
    name: str = Field(..., min_length=1, max_length=100)
    # 錢一律 Decimal，不用 float（float 有二進位誤差）。
    unit_price: Decimal = Field(..., ge=0)


class ProductUpdateIn(Schema):
    # 刻意沒有 sku：品號是商品的識別，建立後不給改。
    name: str = Field(..., min_length=1, max_length=100)
    unit_price: Decimal = Field(..., ge=0)


class ProductSchema(Schema):
    id: int
    sku: str
    name: str
    unit_price: float
    listed_at: str           # 上架日期（= created_at 的日期，建檔即上架）
    is_active: bool

    @staticmethod
    def resolve_listed_at(obj):
        return str(obj.created_at.date())


class ProductListSchema(Schema):
    """列表回應：items + count。"""
    items: list[ProductSchema]
    count: int


class MessageSchema(Schema):
    message: str
