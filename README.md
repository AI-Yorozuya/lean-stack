# lean-stack

全端教學 sandbox。一條最小的端到端骨架：

```
Vue 3 (Vite)  →  /api/v1/health  →  django-ninja  →  Django 6  →  PostgreSQL
```

範例 app：`health`（router 範例）、`progress`（celery 非同步示範）。領域功能以 INTENT-first 方式加——`intents/` 已有**訂單管理、會員管理**兩份 INTENT（code 生成中）。
結構與慣例沿用 `top-erp` 的三 app 慣例（top-backend / top-admin / top-web）。

> **先看哪裡？**
> - 👶 **第一次用、不會寫程式** → 往下看「**給新手：零終端機上手**」。不用終端機、不用背指令，用講的就好。
> - 🛠 **工程師 / dogfood** → 看「**快速啟動**」與 `CLAUDE.md`。

## 👶 給新手：零終端機上手

**看 [START.md](./START.md) 就好**——這套適合誰、首次準備（裝 Claude App＋Docker Desktop）、每次開工、你會用到的話、東西去哪看，全在那一份。
你唯一要記的一句話：把 START.md 拉進 Claude Code，說「**照 START.md 把系統跑起來**」。

---

## 三個 app

| app | 是什麼 | 技術 | dev port |
|-----|--------|------|----------|
| **lean-backend** | 後端 API + DB | Django 6 + django-ninja + Postgres（uv） | 8000 |
| **lean-admin** | 管理後台 / 後台 console | Vue 3 + Vite | 5174 |
| **lean-web** | 對外前台 | Vue 3 + Vite | 5173 |

`lean-admin` 與 `lean-web` 結構完全相同（同樣的 `api/ + views/ + components/ + 一條路由的 router`），
「怎麼加一頁」的流程在兩個前端一致；差別只在用途：admin 是之後 **登入/權限** 真正重要的地方。
兩個前端都把 `/api` proxy 到同一個 `lean-backend`（:8000）。

```
lean-stack/
├── apps/
│   ├── lean-backend/   Django 6 + django-ninja + Postgres（uv 管理）
│   │   ├── core/        settings / urls / api（root NinjaAPI）/ asgi / wsgi
│   │   └── apps/
│   │       ├── _common/ 共用抽象 model（TimeStampedModel）
│   │       └── health/  health 端點（router 範例）
│   ├── lean-admin/     Vue 3 + Vite（管理後台，:5174）
│   │   └── src/         api/（client）router/（一條路由＋auth 接縫）views/ components/
│   └── lean-web/       Vue 3 + Vite（對外前台，:5173）
│       └── src/         api/（client）router/（一條路由）views/ components/
├── infra/              部署層：terraform（一台 EC2 + SG + media S3）、prod compose、nginx、deploy 腳本
│   ├── terraform/      flat 單環境 HCL（plan-first 紀律）
│   ├── docker-compose.prod.yml   整套 prod 編排（postgres + backend + nginx）
│   ├── nginx/nginx.conf          服務兩個前端 + 反代 /api
│   ├── scripts/deploy.sh
│   └── DEPLOY.md       部署 runbook（單一真相來源）
├── intents/            先寫規則再寫 code：INTENT 語法 + 範本
├── .claude/skills/     AI 工作流 skill（add-feature / deploy，v0 stub）
├── CLAUDE.md           AI agent 指引（慣例 + 鐵則）
├── README.md
└── DEPLOY.md           → 指向 infra/DEPLOY.md
```

## AI-native 層

- `CLAUDE.md` — 在這 repo 工作的 AI agent 慣例與鐵則（3-app 佈局、ninja router 單一註冊點、TimeStampedModel、INTENT-first 流程、media 切換、infra plan-first、絕不 commit 機密）。
- `intents/` — 業務規則「寫在 code 之前」。語法 `From --(Who: Action)--> To [Guard] {鐵則}` + 權限 5W；見 `intents/README.md`、`intents/_TEMPLATE.md`。已有 `訂單管理`（Stage A/B）與 `會員管理` 兩份。
- `.claude/skills/` — `add-feature`（INTENT→後端→前端→註冊 router）與 `deploy`（本機→plan/review/apply→部署）的 v0 stub。

## 快速啟動（工程師 / dogfood）

> 新手請走 [START.md](./START.md)；這段是手動版——也就是 Claude 在幕後跑的東西。

**一句話起整套**（postgres + redis + backend + celery worker + 兩個前端，全在 Docker 裡）：

```bash
docker compose -f docker-compose.local.yml up --build -d
```

驗證：

```bash
curl -s localhost:8000/api/v1/health        # {"status": "ok"}
open http://localhost:5173                  # 前台（看到「後端連線正常 ✓」= 整條通）
open http://localhost:5174                  # 管理後台
```

- 撞 port？用 env 覆寫：`LEAN_BACKEND_PORT=8001 LEAN_WEB_PORT=5175 LEAN_ADMIN_PORT=5176 docker compose ... up -d`
- backend 掛 source volume＋`uvicorn --reload`、前端跑 vite dev（HMR 事件穿透 bind mount 已驗證）——**改 code 即時反映，不用 rebuild**。
- 改 celery task 的 code：`docker compose -f docker-compose.local.yml restart celery-worker`（worker 無自動 reload）。
- 加/改後端依賴：改 `pyproject.toml` → `up --build`。前端依賴：改 `package.json` → 重啟該 service（容器內會重跑 npm install）。
- Django 管理指令進容器跑：

```bash
docker compose -f docker-compose.local.yml exec backend uv run python manage.py <cmd>
```

- 關閉：`docker compose -f docker-compose.local.yml down`

> 兩個前端也收進 compose 的理由：Docker Desktop 變成**整個 app 的單一狀態視窗**（六個綠燈=活著），
> AI 對所有 service 的 log 有直讀權（`docker compose logs <service>`）——新手不用開任何終端機、不用貼 log。
> `uv` 與 `npm` 都是**容器內**的事；你本機不必裝 Python/uv/Node 就能開發。

## 怎麼擴充

### 加一個後端 API

1. 建 app：`apps/lean-backend/apps/<feature>/`，裡面放 `apps.py`、`apis.py`、`schemas.py`、`models.py`。
2. 在 `apis.py` 建一個 ninja `Router`（參考 `apps/health/apis.py`），用 `@router.get/post` 定義端點。
3. 領域 model 繼承 `apps._common.models.TimeStampedModel`，自動有 created_at / updated_at。
4. 到 **`core/api.py`** 找「`# 新功能 router 註冊在這`」，加一行 `api.add_router('/<feature>/', <feature>_router)`。
5. 把新 app 加進 `core/settings.py` 的 `INSTALLED_APPS`，然後在容器內 makemigrations／migrate：
   `docker compose -f docker-compose.local.yml exec backend uv run python manage.py makemigrations`（再跑一次 `migrate`）。

> 整個專案只有 **一個** NinjaAPI（`core/api.py`），掛在 `/api/v1/`。
> `core/urls.py` 不用再改。

### 加一個前端頁面（lean-web 或 lean-admin，流程相同）

1. 在 `src/views/` 新增一個 `.vue`。
2. 在 `src/router/index.js` 的 `routes` 加一筆（建議用 `() => import(...)` lazy load）。
3. 共用 UI 放 `src/components/`；呼叫後端的函式集中放 `src/api/`。

### 上傳檔 / media（env 切換，零摩擦）

用 `USE_S3` 開關決定檔案存哪（見 `apps/lean-backend/core/settings.py` 的 `STORAGES`）：

- 本機開發 `USE_S3=False` → 檔案系統 `/media`，零設定。
- 正式環境 `USE_S3=True` → S3 私有 bucket（由 `infra/terraform` 建）。

model 寫 `models.ImageField(upload_to='...')` / `FileField` **兩種模式都直接可用**，切換只改 env、不改 code。（`ImageField` 需要 Pillow，用時再加進 pyproject。）

### 之後要加登入驗證（auth）

骨架階段刻意 **不含 auth**，但前後端都留好接縫：
- 後端：在 `apps/lean-backend/core/api.py` 建 `NinjaAPI` 時帶 `auth=...`，或在個別 router / endpoint 上指定（詳見該檔註解）。
- 後台前端：`apps/lean-admin/src/router/index.js` 已標好 `router.beforeEach` 登入守衛的位置（admin 是 auth 最重要的地方）。

> 非同步任務（celery）已內建：redis broker＋真 worker，示範見 `apps/progress`（Job 進度表＋輪詢頁）。

## 部署

見 **[`infra/DEPLOY.md`](./infra/DEPLOY.md)**（單一真相來源）：本機 docker 跑通 → terraform `plan→review→apply` 開一台伺服器 → `bash infra/scripts/deploy.sh` 部署。
鐵則：**AI 不自動對真雲 apply；state / 機密永不進版控；憑證走環境變數。**

## 之後的步驟

下一步（不在本骨架範圍）：以 INTENT-first 的方式設計第一批領域模型，
依「怎麼擴充」的流程加到 `apps/lean-backend/apps/<新 app>/`。
