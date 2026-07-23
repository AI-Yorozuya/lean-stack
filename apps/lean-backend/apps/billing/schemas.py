"""帳款的輸出形狀（ninja Schema）。帳款頁是**唯讀投影**——分錄由訂單生命週期產生，
這裡只把 append-only 的分錄流「算成」給人看的餘額與明細（真相在 apps/billing/models 的分錄）。
"""
from ninja import Schema


class CustomerBriefSchema(Schema):
    """帳款列裡帶的客戶摘要。"""
    id: int
    name: str
    phone: str


# ── 客戶應收總覽（一列一客戶）───────────────────────────────
class ReceivableRowSchema(Schema):
    customer: CustomerBriefSchema
    charged: float     # 應收合計（Σ 應收）
    paid: float        # 已收合計（Σ 收款）
    balance: float     # 未收餘額 = 應收 − 收款 − 沖銷（推導）
    entry_count: int   # 分錄筆數


class ReceivableListSchema(Schema):
    items: list[ReceivableRowSchema]
    count: int              # 有帳的客戶數
    total_balance: float    # 全體未收餘額（總應收帳款）


# ── 單一客戶的分錄流（含跑動餘額）─────────────────────────
class LedgerEntrySchema(Schema):
    id: int
    date: str              # 分錄日期
    kind: str              # CHARGE / PAYMENT / REVERSAL
    kind_display: str      # 應收 / 收款 / 沖銷
    amount: float          # 金額大小（正數）
    signed_amount: float   # 對餘額的影響（應收 +、收款/沖銷 −）
    order_no: str | None   # 關聯訂單單號（沒有為 null）
    memo: str
    running_balance: float  # 到這筆為止的累計餘額（後端逐筆累加）


class CustomerLedgerSchema(Schema):
    customer: CustomerBriefSchema
    charged: float
    paid: float
    balance: float
    entries: list[LedgerEntrySchema]
