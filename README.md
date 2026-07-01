# lean-stack

全端教學 sandbox。一條最小的端到端骨架：

```
Vue 3 (Vite)  →  /api/v1/health  →  django-ninja  →  Django 6  →  PostgreSQL
```

目前只有一個 health 端點，**還沒有任何領域模型**（帳本/訂單/交易等之後再以 INTENT-first 方式加）。
結構與慣例沿用 `top-erp` 的三 app 慣例（top-backend / top-admin / top-web）。

> **先看哪裡？**
> - 👶 **第一次用、不會寫程式** → 往下看「**給新手：零終端機上手**」。不用終端機、不用背指令，用講的就好。
> - 🛠 **工程師 / dogfood** → 看「**快速啟動**」與 `CLAUDE.md`。

## 👶 給新手：零終端機上手

沒寫過程式、沒碰過終端機也能把它跑起來。你只要**用講的**，指令的部分交給 AI。

**你唯一要裝的：** [Claude 桌面 App](https://claude.ai/download)。就這樣——不用先裝 Python、Node、Docker、git，這些等下 AI 會幫你處理。

**四步跑起來：**

1. 打開 Claude 桌面 App，點上方 **Code** 分頁。
   > ⚠️ 是 **Code**，不是 Chat。只有 Code 分頁能碰你電腦的檔案、幫你執行東西。
2. 點 **Select folder**，選一個要放專案的資料夾（例如桌面上新開一個「我的專案」）。
3. 直接打中文跟 Claude 說：
   > 幫我把 `https://github.com/AI-Yorozuya/lean-stack` 這個專案抓下來，然後跑起來給我看。
4. Claude 會自己抓專案、把環境裝好、開起來，最後給你一個網址。打開就看到畫面 ✓
   > 第一次會等幾分鐘（在幫你裝環境），正常。之後就快了。

**跑起來之後，你要做的都用「講的」——不用背任何指令：**

| 你想做的 | 你就這樣說 |
|---|---|
| 存一下進度（怕等下改壞） | 「幫我**存個檔**」 |
| 備份到雲端（換台電腦也在） | 「幫我**備份**上去」 |
| 改壞了想回到上一個好版本 | 「**退回**上一個會動的版本」 |
| 加一個新功能 | 「我想加一個 ⬚⬚⬚，幫我做」 |

`git`、`docker`、`npm` 這些字你都不用懂——**那是 Claude 的工作，不是你的**。你負責「想做什麼」，它負責「怎麼做出來」。

> 想懂剛剛每一步在幹嘛（白話版）？那是「第 0 課」教材的內容，跟這份 README 分開放。

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
- `intents/` — 業務規則「寫在 code 之前」。語法 `From --(Who: Action)--> To [Guard] {鐵則}` + 權限 5W；見 `intents/README.md`、`intents/_TEMPLATE.md`。（記帳 INTENT 由人下一步寫。）
- `.claude/skills/` — `add-feature`（INTENT→後端→前端→註冊 router）與 `deploy`（本機→plan/review/apply→部署）的 v0 stub。

## 快速啟動

> 這一段是**手動起法**——也正是上面「給新手」流程裡，Claude 在幕後幫你跑的那些指令。
> 想自己動手、或在做 dogfood 的工程師看這裡；純新手可以略過，交給 AI。

### 1. 後端 + 資料庫（Docker，一個指令）

從 repo 根目錄執行：

```bash
docker compose -f apps/lean-backend/docker-compose.local.yml up --build
```

這會起一個 `postgres:16` 和後端服務。後端會自動等 DB → 跑 migrate → 在
http://localhost:8000 起 server。驗證：

```bash
curl -s localhost:8000/api/v1/health
# {"status": "ok"}
```

關閉：

```bash
docker compose -f apps/lean-backend/docker-compose.local.yml down
```

### 2. 前台 lean-web（Vite dev server，:5173）

另開一個終端機：

```bash
cd apps/lean-web
npm install
npm run dev
```

打開 http://localhost:5173 ，看到「後端連線正常 ✓」就代表整條路通了。
（Vite 已設好 proxy，把 `/api` 轉到後端 :8000，所以不用煩惱 CORS。）

### 3. 管理後台 lean-admin（Vite dev server，:5174）

再開一個終端機：

```bash
cd apps/lean-admin
npm install
npm run dev
```

打開 http://localhost:5174 ，看到「lean-stack 管理後台」加上「後端連線正常 ✓」，
就代表後台也接到同一個後端了。（同樣已設好 `/api` → :8000 的 proxy。）

## 後端一律用 Docker 起

後端（含 postgres / redis / celery worker）**只透過 docker compose 啟動**——一種起法、跟 prod 同構（dev/prod parity），不留「本機直接 runserver」的分岔路。

```bash
# 從 repo 根：一條指令帶起 postgres + redis + backend + celery-worker
docker compose -f apps/lean-backend/docker-compose.local.yml up --build
```

- backend 掛了 source volume ＋ `uvicorn --reload`（DEBUG=True）：**改 code 自動重載，不用 rebuild**。
- 改 worker（celery task）的 code：`docker compose -f apps/lean-backend/docker-compose.local.yml restart celery-worker`（celery 無自動 reload）。
- 加/改依賴：改 `pyproject.toml` → 重新 `up --build`（uv 依 uv.lock 重裝）。

跑 Django 管理指令（migrate / makemigrations / createsuperuser…）進 backend 容器：

```bash
docker compose -f apps/lean-backend/docker-compose.local.yml exec backend \
  uv run python manage.py <cmd>
```

> `uv` 是**容器內**的套件管理器（依 `uv.lock`）；你本機不必裝 Python/uv 就能開發後端。

## 怎麼擴充

### 加一個後端 API

1. 建 app：`apps/lean-backend/apps/<feature>/`，裡面放 `apps.py`、`apis.py`、`schemas.py`、`models.py`。
2. 在 `apis.py` 建一個 ninja `Router`（參考 `apps/health/apis.py`），用 `@router.get/post` 定義端點。
3. 領域 model 繼承 `apps._common.models.TimeStampedModel`，自動有 created_at / updated_at。
4. 到 **`core/api.py`** 找「`# 新功能 router 註冊在這`」，加一行 `api.add_router('/<feature>/', <feature>_router)`。
5. 把新 app 加進 `core/settings.py` 的 `INSTALLED_APPS`，然後在容器內 makemigrations／migrate：
   `docker compose -f apps/lean-backend/docker-compose.local.yml exec backend uv run python manage.py makemigrations`（再跑一次 `migrate`）。

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

> 非同步任務（celery）＝進階層，未內建，未來再接入。

## 部署

見 **[`infra/DEPLOY.md`](./infra/DEPLOY.md)**（單一真相來源）：本機 docker 跑通 → terraform `plan→review→apply` 開一台伺服器 → `bash infra/scripts/deploy.sh` 部署。
鐵則：**AI 不自動對真雲 apply；state / 機密永不進版控；憑證走環境變數。**

## 之後的步驟

下一步（不在本骨架範圍）：以 INTENT-first 的方式設計第一批領域模型，
依「怎麼擴充」的流程加到 `apps/lean-backend/apps/<新 app>/`。
