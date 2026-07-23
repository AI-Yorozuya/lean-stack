"""整個專案唯一的 NinjaAPI 物件，與「新功能 router 註冊處」。

教學重點（擴充模式）：
- 只建「一個」NinjaAPI（掛在 core/urls.py 的 /api/v1/）。
- 每個 feature app 在自己的 apis.py 裡建一個 ninja `Router`，
  然後在「下面這個區塊」用 api.add_router(...) 掛上來。
- 想加新功能 → 寫 apps/<feature>/apis.py 的 router → 來這裡加一行。
  這就是這個 sandbox 的標準擴充點。
"""
from ninja import NinjaAPI

from apps.health.apis import router as health_router
from apps.member.apis import router as member_router
from apps.order.apis import router as order_router
from apps.product.apis import router as product_router
from apps.quotation.apis import router as quotation_router
from apps.progress.apis import router as progress_router

# title / version 會顯示在自動產生的 API 文件（/api/v1/docs）。
api = NinjaAPI(title='lean-stack API', version='1.0.0')

# ──────────────────────────────────────────────────────────────
# 新功能 router 註冊在這
#   範例：api.add_router('/ledger/', ledger_router)
# ──────────────────────────────────────────────────────────────
api.add_router('/health', health_router)
api.add_router('/progress', progress_router)
api.add_router('/members', member_router)
api.add_router('/products', product_router)
api.add_router('/quotations', quotation_router)
api.add_router('/orders', order_router)

# auth 的接法（本 repo 現況）：
#   - 不在 NinjaAPI 設全域 auth——後台 CRUD 端點刻意公開（帳房是內部後台）。
#   - 要「登入才能用」的端點，在該 router / endpoint 上設 auth=member_auth
#     （見 apps/member 的 /me）。憑證怎麼發/驗見 apps/member/auth.py。
