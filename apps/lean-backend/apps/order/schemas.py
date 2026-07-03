"""訂單管理的輸入/輸出形狀（ninja Schema，底層 pydantic）。

教學重點：
- 「In」結尾＝進來的（建立/修改用），其他＝出去的（回給前端用）。
- 進來的資料在這一層就先驗（數量 > 0、至少一筆明細）——擋在門口，
  不讓髒資料走到 model。
- 出去的 subtotal / total 是後端算好的，前端只負責顯示。
"""
from decimal import Decimal

from ninja import Field, Schema


# ── 客戶 ──────────────────────────────────────────────
class CustomerIn(Schema):
    name: str = Field(..., min_length=1, max_length=100)
    phone: str = ''


class CustomerSchema(Schema):
    id: int
    name: str
    phone: str


# ── 明細 ──────────────────────────────────────────────
class OrderItemIn(Schema):
    name: str = Field(..., min_length=1, max_length=100)
    quantity: int = Field(..., gt=0)              # 數量必須 > 0
    # 錢一律用 Decimal，不用 float——float 有二進位誤差（0.1+0.2≠0.3），
    # 算錢會慢慢飄掉。pydantic 會把 JSON 數字安全轉成 Decimal。
    unit_price: Decimal = Field(..., ge=0)        # 單價不可為負


class OrderItemSchema(Schema):
    id: int
    name: str
    quantity: int
    unit_price: float
    subtotal: float                            # 後端算的（鐵則），非手填


# ── 訂單 ──────────────────────────────────────────────
class OrderIn(Schema):
    customer_id: int
    # 鐵則 {一張訂單至少一筆明細}：min_length=1 在門口就擋掉空單。
    items: list[OrderItemIn] = Field(..., min_length=1)


class OrderSchema(Schema):
    id: int
    customer: CustomerSchema
    order_date: str = Field(..., alias='order_date')
    total: float                               # 後端算的（鐵則），非手填
    items: list[OrderItemSchema]

    @staticmethod
    def resolve_order_date(obj):
        return str(obj.order_date)


class OrderListSchema(Schema):
    """列表回應：items + count，配合前端的 table + pagination。"""
    items: list[OrderSchema]
    count: int


class MessageSchema(Schema):
    message: str
