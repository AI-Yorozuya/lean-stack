"""訂單管理的輸入/輸出形狀（ninja Schema，底層 pydantic）。

教學重點：
- 「In」結尾＝進來的（建立/修改用），其他＝出去的（回給前端用）。
- 建單時明細只給 product_id + quantity——品名與單價**不由前端傳**，
  由後端從目錄抄快照（見 apps/order/models.py 的 OrderItem.snapshot_from）。
  這防止前端亂塞價格，也是「目錄=單一真相」的落點。
- 出去的 name / unit_price / subtotal / total 都是後端算/抄好的，前端只顯示。
"""
from ninja import Field, Schema


# ── 明細 ──────────────────────────────────────────────
class OrderItemIn(Schema):
    product_id: int                               # 從商品目錄挑
    quantity: int = Field(..., gt=0)              # 數量必須 > 0


class OrderItemSchema(Schema):
    id: int
    product_id: int
    name: str                                  # 下單當下的快照
    quantity: int
    unit_price: float                          # 下單當下的快照
    subtotal: float                            # 後端算的（鐵則），非手填


# ── 訂單 ──────────────────────────────────────────────
class OrderMemberSchema(Schema):
    """訂單裡帶的會員摘要（不必回整包會員，夠顯示即可）。"""
    id: int
    name: str
    phone: str


class OrderIn(Schema):
    member_id: int
    # 鐵則 {一張訂單至少一筆明細}：min_length=1 在門口就擋掉空單。
    items: list[OrderItemIn] = Field(..., min_length=1)


class OrderSchema(Schema):
    id: int
    order_no: str                              # 業務單號（≠ 主鍵）
    member: OrderMemberSchema
    order_date: str = Field(..., alias='order_date')  # 下訂日期
    updated_at: str                            # 修改日期（最後一次變動）
    note: str                                  # 備註（自由文字）
    total: float                               # 後端算的（鐵則），非手填
    items: list[OrderItemSchema]
    # Stage B：狀態機相關（Stage A 頁面收到但不理它）。
    status: str                                # 狀態 code（PENDING / AWAITING / SHIPPED / CANCELLED）
    status_display: str                        # 中文（待付款 / 待出貨 / 已出貨 / 已取消）
    paid_amount: float                         # 已收金額（收款後 = 總額）
    available_actions: list[str]               # 目前合法的動作（pay/ship/cancel）

    @staticmethod
    def resolve_order_date(obj):
        return str(obj.order_date)

    @staticmethod
    def resolve_updated_at(obj):
        return str(obj.updated_at.date())      # 只到日期（列表夠用）

    @staticmethod
    def resolve_status_display(obj):
        return obj.get_status_display()

    @staticmethod
    def resolve_available_actions(obj):
        return obj.available_actions()


class OrderListSchema(Schema):
    """列表回應：items + count，配合前端的 table + pagination。"""
    items: list[OrderSchema]
    count: int


class OrderNoteIn(Schema):
    """只改備註（自由文字，跟狀態機無關，隨時可改）。"""
    note: str = ''


class MessageSchema(Schema):
    message: str
