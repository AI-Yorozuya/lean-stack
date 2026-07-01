---
name: add-feature
description: INTENT-first 加一個功能到 lean-stack（INTENT → 後端 app/apis/schemas/models → Vue view + api 呼叫 → 在 core/api.py 註冊 router）。當使用者要在 lean-stack 新增一塊業務功能時用。
---

# add-feature（v0 stub）

> **v0 stub — 等第一次真正 dogfood 後再長出血肉。** 目前只描述流程骨架。

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
   - `uv run python manage.py makemigrations && uv run python manage.py migrate`。

3. **生前端頁**（`apps/lean-web` 或 `apps/lean-admin`）
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

## TODO（fleshing out from first dogfood）

- 補：實際生成器指令 / 範例 diff / 命名慣例細則 / 常見坑。
