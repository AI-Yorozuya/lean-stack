#!/bin/bash
# SessionStart hook：學員場開場注入——教練接手從「機率」變「必然」。
# stdout 會成為 session 的 additional context（人類不會直接看到）。
cd "$CLAUDE_PROJECT_DIR" 2>/dev/null
echo "=== lean-stack 開場指示（SessionStart 自動注入）==="
if [ -f PROGRESS.md ]; then
  echo "本 repo 是教學遊戲，已有進度檔 PROGRESS.md——使用者任何開場，直接用 coach skill 以「歡迎回來」續玩（先讀 PROGRESS.md 定位，從下一個未完成任務接）。"
else
  echo "本 repo 是教學遊戲（尚無進度檔）——使用者任何開場搭話都由 coach skill 接手："
  echo "・已講明想做什麼（例「我要學習製作一頁式官網」）→ Beat 0 意圖直達，跳過選單直進對應劇本。"
  echo "・沒講明 → 出四劇本可點選單。"
  echo "不要導覽 repo、不要摘要 README、不要旁白你在讀什麼——直接開演。"
fi
