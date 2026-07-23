"""報價單的輸入/輸出形狀（ninja Schema，底層 pydantic）。刻意跟 order/schemas.py 同形。

教學重點：
- 「In」結尾＝進來的（建立/修改用），其他＝出去的（回給前端用）。
- 建報價時明細只給 product_id + quantity——品名與單價**不由前端傳**，
  由後端從目錄抄快照（見 models.py 的 QuotationItem.snapshot_from）。
- 出去的 name / unit_price / subtotal / total 都是後端算/抄好的，前端只顯示。
"""
from ninja import Field, Schema


# ── 明細 ──────────────────────────────────────────────
class QuotationItemIn(Schema):
    product_id: int                               # 從商品目錄挑
    quantity: int = Field(..., gt=0)              # 數量必須 > 0


class QuotationItemSchema(Schema):
    id: int
    product_id: int
    name: str                                  # 報價當下的快照
    quantity: int
    unit_price: float                          # 報價當下的快照
    subtotal: float                            # 後端算的（鐵則），非手填


# ── 報價單 ────────────────────────────────────────────
class QuotationCustomerSchema(Schema):
    """報價裡帶的客戶摘要（不必回整包會員，夠顯示即可）。"""
    id: int
    name: str
    phone: str


class QuotationIn(Schema):
    customer_id: int
    # 鐵則 {一張報價至少一筆明細}：min_length=1 在門口就擋掉空報價。
    items: list[QuotationItemIn] = Field(..., min_length=1)
    note: str = ''


class QuotationSchema(Schema):
    id: int
    quote_no: str                              # 業務單號（≠ 主鍵）
    customer: QuotationCustomerSchema
    created_at: str                            # 報價建立日期
    updated_at: str                            # 最後一次變動
    note: str
    total: float                               # 後端算的（鐵則），非手填
    items: list[QuotationItemSchema]
    # 狀態機相關。
    status: str                                # 狀態 code（DRAFT / SENT / WON / VOID）
    status_display: str                        # 中文（草稿 / 已送出 / 已成交 / 已作廢）
    available_actions: list[str]               # 目前合法的動作（send/win/void）
    order_id: int | None                       # 成交生的訂單 id（未成交為 null）

    @staticmethod
    def resolve_created_at(obj):
        return str(obj.created_at.date())

    @staticmethod
    def resolve_updated_at(obj):
        return str(obj.updated_at.date())

    @staticmethod
    def resolve_status_display(obj):
        return obj.get_status_display()

    @staticmethod
    def resolve_available_actions(obj):
        return obj.available_actions()

    @staticmethod
    def resolve_order_id(obj):
        return obj.order_id


class QuotationListSchema(Schema):
    """列表回應：items + count（＋ status_counts 給狀態頁籤計數），配合前端 table + pagination。"""
    items: list[QuotationSchema]
    count: int
    status_counts: dict[str, int] = {}


class QuotationNoteIn(Schema):
    """只改備註（自由文字，跟狀態機無關，隨時可改）。"""
    note: str = ''


class MessageSchema(Schema):
    message: str
