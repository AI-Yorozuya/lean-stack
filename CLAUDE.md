# lean-stack — AI agent 指引

全端教學 sandbox。給在這 repo 工作的 AI agent 的慣例與紀律。**規則優先於預設行為。**
細節盡量寫在「對應檔案的 in-code 註解」裡，這份只給地圖與鐵則。

## 三 app 佈局

| app | 是什麼 | 技術 |
|-----|--------|------|
| `apps/lean-backend` | 後端 API + DB（唯一真相） | Django 6 + django-ninja + Postgres（uv） |
| `apps/lean-admin` | 管理後台（auth 之後長在這） | Vue 3 + Vite（:5174） |
| `apps/lean-web` | 對外門市（登入→加購→真下單，無金流） | Vue 3 + Vite（:5175） |

> `lean-web` 極簡但**能真下單**：登入（示範登入——後端刻意還沒 auth，email 對到會員即可）→ 加購 → 結帳 `POST /order` → 後台訂單列表就看得到那張「待付款」單。示範完整 loop：「改後台→前台變」＋「前台下單→後台看到」。**訂單不再 seed**（`seed_demo` 只灌會員＋商品，訂單由門市產生；測試客 `hero@ai-yorozuya.com`）。仍不是可上線門市（金流／庫存／驗證留下游）。兩個前端都打 `/api/v1`。

`infra/` = 部署層（terraform 一台 EC2 + 整套 prod compose + nginx）。`intents/` = 規則先於 code。

## 後端慣例

- **每個 feature app 一個 ninja `Router`**（不是 NinjaAPI），寫在該 app 的 `apis.py`。參考 `apps/lean-backend/apps/health/apis.py`。
- **單一註冊點**：所有 router 在 `apps/lean-backend/core/api.py` 用 `api.add_router(...)` 掛上去（只有一個 NinjaAPI，掛在 `/api/v1/`）。新增端點不用改 `core/urls.py`。
- **`_common.TimeStampedModel`**：領域 model 一律繼承它（自動 created_at / updated_at）。見 `apps/_common/models.py`。
- schema 用 ninja `Schema`（pydantic）放各 app 的 `schemas.py`。
- **整套一律用 docker compose 起**（`infra/docker-compose.local.yml`，從 repo 根目錄跑；一次帶 postgres+redis+backend+worker+admin+web 前端；backend `uvicorn --reload`、前端 vite dev，改 code 都即時反映不用 rebuild）。**預設全走 docker、不跑本機 runserver**——Docker Desktop 是唯一狀態視窗（五綠燈=活著），log 用 `docker compose logs <service>` 直讀。（工程師例外：host 直接 `npm run dev` 可以，vite proxy 沒設 env 時 fallback `localhost:8000`——那是 dogfood 用的後門，新手流程一律 docker。）管理指令走 `docker compose -f infra/docker-compose.local.yml exec backend uv run python manage.py <cmd>`。`uv`/`npm` 都是容器內的事。撞 port 用 `LEAN_BACKEND_PORT`/`LEAN_ADMIN_PORT`/`LEAN_WEB_PORT` 覆寫。新手啟動劇本見 `START.md`（下半是給 AI 的 runbook，照做）。

## INTENT-first 加功能（本 repo 的核心做法）

先寫規則、再生 code。順序：

1. **寫 INTENT**：在 `intents/` 依 `_TEMPLATE.md` 描述狀態機 + 權限 + 鐵則（語法見 `intents/README.md`）。**「名詞」段附一張 Mermaid `erDiagram` 畫資料模型**（純文字、GitHub 直接渲染、學員可直接改）；model 設計原則（快照／衍生／業務識別碼／停用不刪）見 `intents/資料模型設計原則.md`。
2. **生後端**：依 INTENT 建 app（`apps.py`/`apis.py`/`schemas.py`/`models.py`，model 繼承 TimeStampedModel）→ 在 `core/api.py` 註冊 router → 容器內 `makemigrations && migrate`（`docker compose … exec backend uv run python manage.py …`）。
3. **生前端頁**：在 `lean-admin` 的 `src/views/` 加 view、`src/api/` 加呼叫、`src/router/index.js` 加一條路由（lazy load）。
4. **接線驗證**：頁面打得到端點即通。

對應 skill：`.claude/skills/add-feature`（v0 stub）。

## 前端設計系統（shadcn-vue + Tailwind）

- **UI 積木一律用 `@/components/ui/*`（shadcn-vue，Tailwind v4）**，別再手刻內聯樣式。已有：`button`、`input`、`label`、`card`、`table`、`dialog`、`badge`。缺的用 `npx shadcn-vue@latest add <name>` 補（元件是複製進 repo 的 .vue 檔，你擁有、可改）。
- **顏色只用語意 token**（`bg-background`/`text-muted-foreground`/`bg-primary`/`border`…），定義在 `src/assets/index.css` 的 `:root`（換主題只改這裡）。圖示用 `@lucide/vue`。
- **版面外殼在 `src/components/layout/AppShell.vue`**（常駐 sidebar + 頂部 bar + 內容區）。頁面只寫自己的內容，殼由 `App.vue` 套上。
- **清單頁的表格一律用 `@/components/DataTable.vue`**（自家 base table，不是 shadcn 的 TanStack 版）。它把「表頭/表身兩張表、共用 colgroup、捲軸只在表身且與表頭右緣對齊、底線畫滿、水平同步、空狀態」這套水電包好；頁面只要給 `columns`（`{ label, width?, align? }`）＋ `#row` slot（一列的儲存格）＋選配 `#actions` slot（釘右操作欄）。範例見 `OrderLifecycleView.vue`。**別再自己手刻 `<table>` + sticky 表頭**。

## 前端加一頁

在 `lean-admin` 的 `src/views/` 加 `.vue`（用 `@/components/ui/*` 拼版面）→ `src/router/index.js` 的 `routes` 加一筆（`() => import(...)`）→ **要進 sidebar 就在 `AppShell.vue` 的 `nav` 陣列加一筆**：單一項 `{ to, label, icon }`；要分子選單就用群組 `{ label, icon, children: [{ to, label }, …] }`（含 active 子項會自動展開）→ API 呼叫放 `src/api/`。

## media 儲存（上傳檔）

- 用 `USE_S3` env 開關切換（見 `apps/lean-backend/core/settings.py` 的 `STORAGES`）：
  本機 `USE_S3=False` → 檔案系統 `/media`（零摩擦）；prod `USE_S3=True` → S3（私有 bucket）。
- model 寫 `FileField` / `ImageField(upload_to=...)` **兩種模式都直接可用**，切換只改 env、不改 code。
- prod 的 S3 bucket 由 `infra/terraform` 建（私有、擋 public access）；憑證走 instance role / 環境變數。

## 非同步任務

- **非同步＝celery（redis broker + worker）**，設定見 `core/celery.py` / `core/settings.py`（`CELERY_*`），範例見 `apps/progress`（DB 存 `Job` 進度 + `tasks.py` + 前端「背景任務」清單頁 `lean-admin/.../BackgroundTaskView.vue`，有 RUNNING 就輪詢）。
- **local 與 prod 同構（dev/prod parity）**：兩個 compose 都跑真 redis + 真 worker，**刻意不開 eager** —— eager 把任務當同步函式跑，會藏掉序列化/連線/worker 沒起來這類 async bug，正是「demo 會動、上 prod 垮」的牆。
- 加任務：在某 app 寫 `tasks.py` 的 `@shared_task`（autodiscover 自動撿），API 端用 `.delay(...)` 派工，要追進度就照 `apps/progress` 用 `Job` 表。

## infra / 部署紀律（鐵則）

- **AI 不自動對真雲 `apply`。** plan 先、人 review 後人手 apply。把它當「新時代的金鑰外洩 / 上線垮」風險源。
- **永不 commit**：`*.tfstate*`、`.terraform/`、`*.tfvars`、任何 `.env` / `.env.prod`。
- **憑證走環境變數**（`AWS_PROFILE` / `AWS_ACCESS_KEY_ID`...），不進 repo、不寫進 `.tf` / `.tfvars`。
- 本機先用 docker 跑通，再上雲。runbook：`infra/DEPLOY.md`。對應 skill：`.claude/skills/deploy`（v0 stub）。

## 進階層（未內建，未來在此接入）

- **auth/登入**：未內建。後端接縫在 `core/api.py`（`NinjaAPI(auth=...)`）；後台前端守衛接縫在 `apps/lean-admin/src/router/index.js`。

## 版本控制（對新手：用生活語言演出來，別教 git 詞）

在這 sandbox 工作的使用者多半是**不懂 git 的新手**。git 是通用知識、機制交給你——但**別教她背 `commit`/`push`/`checkout`**（那是把「記語法」的負擔換句話裝回去）。你的工作是**用生活語言把版本控制演出來**，她看著看著自己就內化了。

**生活語言映射（她講左邊，你翻成右邊）：**

| 她心裡的需求 | 她會講的話（生活語） | 你翻成 |
|-----|-----|-----|
| 存個進度、怕等下改壞 | 「幫我**存個檔**」/「先存起來」 | commit（照下方 commit 慣例寫 message） |
| 這版穩了、想備份 / 上線 | 「**備份**一份」/「上傳到雲端」 | push |
| 剛改壞了 | 「**退回**上一個會動的版本」 | checkout / reset 到某個 commit |

心智模型就是**遊戲存檔**：commit＝存進度點（隨時回得來），push＝同步一份到雲端（換台電腦也在）。

**主動旁白（不等她想起，你在對的時機用生活語言做 + 講）：**

- **一個功能做到會跑了** → 主動存檔並報告：「這版會動了，我幫你**存了個進度點**『訂單功能 v1』，想退回這裡隨時說。」
- **她要做大改 / 危險操作前** → 先存檔當還原點：「動這個之前，先幫你**存個檔**喔。」
- **一個段落穩了 / 收工** → 提議備份：「要不要**備份**上 GitHub？換台電腦也在。」

**危險操作護欄（單向門，動手前一定先問人）：** `push -f`、`reset --hard`、`rebase` 已推出去的分支、`branch -D`、`clean -fd`、任何會**真的抹掉 commit / 檔案**的操作。這些「通用但難回頭」——放手但底下要有網。

## commit 慣例

`type(scope): subject` — type: feat/fix/refactor/docs/chore/test；scope: lean-backend / lean-admin / infra / docs。

> 新手講「存個檔」時你仍照此格式寫 message（她無感，但歷史保持乾淨、可讀）。

> **絕不 commit 機密 / state / .env。** 不確定的設計選擇先問人。
