"""門市前台（lean-web）的 API —— 這個 app 是門市的 **BFF**（Backend For Frontend）。

為什麼要獨立一個 app、而不是把端點塞進 order？因為**同一個「下單」動作，兩種角色**：
- 後台店員替客人建單 → `POST /order`（收 `member_id`，指定是替誰下）。
- 門市客人自己下單   → `POST /web/order`（**不收 member_id**，下單的人 = 憑證裡的本人）。

把「登入才能用、以本人身分操作」的端點集中在 `web`，跟後台/共用的 CRUD 分開，
邊界清楚：**這裡的每一支都要帶憑證**（`auth=member_auth`），拿 `request.auth` 當本人。

建單的鐵則（快照 / 小計 / 總額）不在這裡重寫——共用 order 的 `place_order`，一處真相。
規則見 intents/會員登入.md（park 的「下單強制登入」在此落地）。
"""
from ninja import Field, Router, Schema

from apps.member.auth import member_auth
from apps.order.apis import place_order
from apps.order.schemas import OrderItemIn, OrderSchema

# 整個 router 都要登入：預設掛上 member_auth，底下每一支都受保護。
router = Router(tags=['web'], auth=member_auth)


class CheckoutIn(Schema):
    """門市下單輸入：**只給明細**，沒有 member_id——下單的人由憑證認定。"""
    # 鐵則 {一張訂單至少一筆明細}：min_length=1 在門口就擋掉空車結帳。
    items: list[OrderItemIn] = Field(..., min_length=1)


@router.post('/order', response=OrderSchema)
def checkout(request, payload: CheckoutIn):
    """門市下單：下單的人 = `request.auth`（守衛驗過的本人），前端說了不算。

    這就是把 auth 用起來的地方——沒帶有效憑證，連進都進不來（守衛擋在門口回 401）；
    member 由後端從憑證認定，杜絕「冒名替別人下單」。
    """
    return place_order(request.auth, payload.items)
