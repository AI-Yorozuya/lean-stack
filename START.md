# START — 第一次把它跑起來

> 這份文件兩個人看:**上半給你**(人,照步驟做);**下半給 Claude**(AI 的啟動劇本)。
> 你只要把這份檔案拉進 Claude Code,說一句:**「照 START.md 把系統跑起來」**,剩下它來。

---

## 這套適合誰(先誠實說)

- **必須會(裝一次)**:照指示裝兩個桌面 App(Claude、Docker)、有 Claude 付費訂閱。
- **必須能(每次)**:打開 App、選資料夾、用講的下指令、把畫面上看到的問題描述回去。
- **不必懂**:git、docker、npm、終端機指令、任何程式語法——**那些是 Claude 的工作,不是你的**。

> 如果「照著指示裝一個桌面 App」對你有困難,建議先找人陪你做完首次準備——之後的日常使用就都是用講的了。

## 首次準備(只做一次,約 15 分鐘)

1. **裝 [Claude 桌面 App](https://claude.ai/download)** 並登入(需要付費方案,Code 功能才會動)。
2. **裝 [Docker Desktop](https://www.docker.com/products/docker-desktop/)**:下載、拖進應用程式、**打開它一次**、按同意。看到左下角出現**綠色**就是好了,之後讓它留在背景。
   - 它是什麼?你的系統(資料庫、後端、網頁)都住在它裡面。**它同時是你的儀表板:綠燈=活著,紅燈=有東西掛了。**
3. 打開 Claude 桌面 App → 上方 **Code** 分頁(⚠️ 不是 Chat)→ **Select folder** 選一個放專案的資料夾。
4. 跟 Claude 說:
   > 幫我把 https://github.com/AI-Yorozuya/lean-stack 抓下來,然後照裡面的 START.md 把系統跑起來。
5. **第一次會等 5–20 分鐘**(它在幫你下載和組裝環境),不是當掉。之後每次啟動都是幾十秒的事。
6. 完成時 Claude 會給你**後台網址**(給你管理的)。打開,動了,就是你的系統。

## 每次開工(日常)

打開 Docker Desktop(留背景)→ 打開 Claude Code、選同一個資料夾 → 說「**把系統跑起來**」→ 拿後台網址開工。

## 你會用到的話(講這些就夠)

| 你想做的 | 你就說 |
|---|---|
| 啟動 | 「把系統跑起來」 |
| 存個進度(怕等下改壞) | 「幫我**存個檔**」 |
| 備份到雲端 | 「幫我**備份**上去」 |
| 改壞了 | 「**退回**上一個會動的版本」 |
| 加功能 / 改東西 | 「我想要 ⬚⬚⬚,幫我做」 |
| 畫面怪怪的 | 「剛剛按 ⬚⬚ 的時候壞了,幫我看看」(不用貼 log,它自己會查) |
| 收工 | 「幫我把系統關掉」 |

## 東西去哪看

| 想看什麼 | 去哪 |
|---|---|
| 我的系統(成果) | **瀏覽器**——Claude 給你的後台網址 |
| 系統活著沒 | **Docker Desktop**——綠燈活著、紅燈掛了(跟 Claude 說一聲就好) |
| 錯誤訊息、log | **不用你看**——Claude 自己讀得到 |

## 護欄(你不用設定,講給你安心的)

這個專案內建了 Claude Code 的安全護欄(`.claude/settings.json` + `.claude/hooks/guard.sh`,clone 下來就生效):

- **日常操作零彈窗**——起系統、裝套件、存檔,Claude 直接做,不會一直跳視窗問你。
- **危險操作直接被擋**——會真的抹掉檔案/紀錄的操作(強制刪除、清空資料庫、覆蓋歷史…)Claude 做不了,會被擋下來改走安全做法。
- **就算真的壞了也救得回**——程式有存檔點可以退回,資料庫一句「幫我重灌示範資料」就重建。

所以放心大膽玩。**很少見的情況**下跳出權限視窗 = Claude 想做一件不可逆的事,看不懂就先問(在這裡或找我們都行)。

---
---

## 給 Claude 的啟動劇本(人類可以不用讀了)

> 你(Claude / AI agent)被要求「照 START.md 跑起來」時,照以下步驟。全程對使用者講**生活語言**(見 CLAUDE.md「版本控制」節的語言紀律),不要她碰任何指令。

### 1. 前置檢查

```bash
docker info >/dev/null 2>&1 || open -a Docker   # daemon 沒起就叫起 Docker Desktop
# 然後每 10 秒 poll docker info,最多等 5 分鐘
```
- 等超過 2 分鐘還沒 ready:請她看 Docker Desktop 視窗有沒有跳同意/權限視窗。
- 卡在半啟動(鯨魚圖示轉不停):請她 Quit Docker Desktop 再重開一次(已知問題,重開即解)。

### 2. 起整套

```bash
docker compose -f infra/docker-compose.local.yml up --build -d
```
- 首次 build 慢(拉 image + npm install),**先主動告訴她**「第一次要等幾分鐘,不是當掉」。
- **撞 port**(`port is already allocated`):用環境變數覆寫再起,並告訴她網址變了:
  `LEAN_BACKEND_PORT=8001 LEAN_ADMIN_PORT=5176 docker compose -f infra/docker-compose.local.yml up -d`(只覆寫撞到的那個即可)

### 3. 驗收(全過才算跑起來)

```bash
docker compose -f infra/docker-compose.local.yml ps          # 五個 service 全 Up(postgres/redis 要 healthy)
curl -s localhost:8000/api/v1/health                   # {"status": "ok"}(port 有覆寫就用覆寫的)
curl -s -o /dev/null -w '%{http_code}' localhost:5174  # 200
curl -s localhost:5174/api/v1/health                   # 前端 proxy 穿透也要通
```

### 4. 回報格式

給她一個可點的網址＋一句話:
> 跑起來了 ✓
> 後台(給你管理的):http://localhost:5174
> Docker Desktop 裡那五個綠燈就是你的系統,亮著=活著。

### 5. 之後的日常對應

| 她說 | 你做 |
|---|---|
| 「把系統跑起來」 | 步驟 1–4 |
| 「幫我把系統關掉」 | `docker compose -f infra/docker-compose.local.yml down` |
| 「壞了/怪怪的」 | `docker compose -f infra/docker-compose.local.yml logs <service> --tail 50` 自己讀,別叫她貼 log |
| 「存檔/備份/退回」 | 照 CLAUDE.md 版本控制節(commit/push/checkout,對她講生活語言) |
| 改了 celery task 的 code | `docker compose -f infra/docker-compose.local.yml restart celery-worker`(worker 無自動 reload) |

### 紀律(不可違反)

- 對她**永遠不出現** git/docker/npm 這些詞的教學——用做的,不用教的。
- 危險操作(會真的抹掉東西的)動手前先問,見 CLAUDE.md 護欄清單。
- 改 code 前先存進度點;做完一個會動的功能主動存檔並用生活語言回報。
