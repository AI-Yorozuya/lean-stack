---
name: add-feature
description: INTENT-first 加一個功能到 lean-stack（INTENT → 後端 app/apis/schemas/models → Vue view + api 呼叫 → 在 core/api.py 註冊 router）。當使用者要在 lean-stack 新增一塊業務功能時用。
---

# add-feature（v1 — 已用「訂單 Stage A」dogfood 過）

照 lean-stack 的「先規則、後 code」做法加功能。完整慣例見 repo 根目錄 `CLAUDE.md`。

## 流程

1. **寫 INTENT**
   - 複製 `intents/_TEMPLATE.md` → `intents/<功能>.md`。
   - 填狀態機 `From --(Who: Action)--> To [Guard] {鐵則}`、權限 5W、鐵則。語法見 `intents/README.md`。
   - 規則沒寫清楚就先別寫 code。

2. **生後端**（`apps/lean-backend/apps/<功能>/`）
   - `apps.py`（AppConfig）、`models.py`（領域 model 繼承 `apps._common.models.TimeStampedModel`）。
   - `schemas.py`（ninja `Schema`）、`apis.py`（建一個 ninja `Router`，`@router.get/post...`）。參考 `apps/health/`。
   - 把 app 加進 `core/settings.py` 的 `INSTALLED_APPS`。
   - **在 `core/api.py` 用 `api.add_router('/<功能>/', <功能>_router)` 註冊**（唯一註冊點）。
   - migration 在容器內跑：`docker compose -f infra/docker-compose.local.yml exec backend uv run python manage.py makemigrations <app> && … migrate`。

3. **生前端頁**（`apps/lean-admin`）
   - `src/api/` 加呼叫後端的函式。
   - `src/views/` 加 view、`src/components/` 放共用 UI。
   - `src/router/index.js` 的 `routes` 加一筆（`() => import(...)` lazy load）。

4. **接線驗證**
   - 後端 `manage.py check` 通過；前端頁面打得到端點、拿到資料即通。

## 鐵則

- model 一律繼承 `TimeStampedModel`；router 一律在 `core/api.py` 註冊。
- 規則變更先改 `intents/`，再改 code。
- 不 commit 機密 / `.env`。
- 非同步任務（celery）目前未內建 —— 別在這裡硬接，那是進階層的另一輪。

## 範例（第一次 dogfood 的成品，照抄結構就對）

- INTENT：`intents/訂單管理.md`（Stage A/B、鐵則、5W）
- 後端：`apps/lean-backend/apps/order/`（models/schemas/apis 都有教學註解）
- 前端：`apps/lean-admin/src/views/OrderListView.vue` ＋ `src/api/order.js`

## 常見坑（dogfood 踩過的，動手前先讀）

1. **錢一律 Decimal，不准 float。** schema 用 `Decimal = Field(..., ge=0)`；model 計算再包一層 `Decimal(str(...))` 防禦（float×Decimal 會 TypeError；float 算錢會飄）。
2. **鐵則兩層守**：schema 在門口擋（如 `min_length=1`）、model `save()`/helper 守真相（如小計自動算、`recalc_total()`）。前端的即時計算只是顯示用——真相永遠是後端回傳。
3. **新建 app 目錄後 reload 可能漏**：compose 已設 `WATCHFILES_FORCE_POLLING`；若疑似跑舊 code，`docker compose -f infra/docker-compose.local.yml up -d backend` 重建一次再測。
4. **父子一起建要 `transaction.atomic`**（訂單＋明細要嘛全存要嘛全不存）。
5. **子路由命名**：靜態路徑（`/customers`）與 `/{id:int}` 可共存（int converter 不吃字串），但靜態的先註冊、少賭。
6. **驗證順序**：先 curl 打 API（含**故意違反鐵則**看 422）→ 再開瀏覽器走 UI 流程（建→列→刪）＋看 console 零錯誤。中文 query 用 `curl -G --data-urlencode`，不然是 client 端壞不是 API 壞。
7. **前端錯誤給白話**：422 時顯示「資料不合規則：…」而不是丟 raw error。
