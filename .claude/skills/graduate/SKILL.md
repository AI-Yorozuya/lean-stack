---
name: graduate
description: 把玩家的 lean-landing 一頁式官網「畢業」到 lean-stack 全端生意系統，續接不斷（招牌/氣質/INTENT/心智圖搬過去，官網留在 CF Pages 當門面）。當 lean-landing 玩家說要「收名單自己管/管客人/接單/讓客人預約/蓋真系統」時用。
---

# graduate：一頁式官網 → 全端生意系統（續接不斷）

玩家在 lean-landing 做出了一頁官網、上線了。現在他想要「自己管名單/管客人/接單」——那是全端、是**另一個交付物**。這支 skill 帶他畢業到 lean-stack，**不製造 repo-hop 斷崖**：官網留在網路上當門面，生意系統在 lean-stack 新長，他的招牌/氣質/意圖/心智圖全部搬過去、續接。

> 這是「升級一個使用者的專案、續接不斷」的通用原語＝正規化即服務／母機的一塊（設計正本＝ai-yorozuya `docs/5-課程/`）。lean-landing→lean-stack 是它第一個 instance；日後 lean-stack 內版本升級、跨棧搬遷同一支演進。

## 心智模型（先講清楚，別讓玩家以為要重來）

**一頁式官網與生意系統是兩個東西，不是同一物的兩階段。** 靜態官網永遠住 CF Pages（他的公開門面，不搬、不關）；生意系統是在 lean-stack 上**新起**的。所以沒有「遷移」——官網不動，系統是 additive。玩家搬的只有**招牌與氣質**（讓兩邊看起來是同一個品牌），內容重新長。

台詞：「你的官網繼續掛在網路上收客人，一個字都不會動。現在要蓋的是它背後的**生意系統**——我把你的招牌和氣質搬過去，內容在新的地方長。」

## 前置：確認畢業訊號（別提前拉人下水）

只在玩家**真的表達**要「收名單自己管／管客人／接單／讓客人預約／看誰欠多少」時才跑。純粹想改官網＝留 lean-landing。畢業＝跨進全端＝付費線（誠實講白：全端要養 server／月費，或走我們 managed）。

## 搬家五步（教練代跑，玩家點頭）

1. **取來 lean-stack**：在玩家機器旁邊 clone lean-stack（`git clone` 到 sibling 目錄）；確認 Docker（這一步才第一次需要 Docker，講一句權限安心話術）。
2. **搬招牌與氣質**（讓兩邊同一個品牌）：
   - 讀 lean-landing 的 `src/style.css` `:root` 主題 token → 貼進 lean-stack `apps/lean-web/src/style.css` `:root`。
   - 讀 lean-landing 的 Hero/招牌文案 → 帶進 lean-stack 官網頁。
3. **續接進度檔**（不重問、不失憶）：把 lean-landing 的 `INTENT.md`／`PROGRESS.md`／`心智圖.md` 複製進 lean-stack 工作目錄。他在 landing 答過的六問、那條鐵則、那張心智圖——全部沿用，不從零。
4. **接會員全端劇本**：`git pull` 私有能力包＋erp/booking 劇本（會員內容，見 ai-yorozuya），交給 `coach` 的全端劇本（erp.md／booking.md）——從「你的生意最需要盯的是哪種事」接著問，用他 INTENT 裡已寫的當預填。
5. **官網留守**：提醒玩家 lean-landing 那頁繼續在 CF Pages 上跑、也可繼續改；兩個東西並存，靠同一個招牌連著。

## 續接鐵律

- **零失憶**：INTENT/PROGRESS/心智圖 續用，不重問六問。心智圖從「一頁式頁面圖」升級成「生意系統包圖」時，是**在同一張圖上加**（抗腐三步：讀關聯→報炸半徑→回填），不是重畫。
- **官網不動**：畢業不碰 lean-landing 那頁——它是門面，永遠留著。
- **付費界線在這**：搬進 lean-stack ＋私有劇本＋（要人顧就）managed ＝付費/會員；code 全開源，gate 在方法與服務。

## 驗收

畢業成功＝玩家在 lean-stack 起了第一張能動的表（客戶表），且他認得那是「同一個品牌、接著上次」——不是「又要重來一次」。
