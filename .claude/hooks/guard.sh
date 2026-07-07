#!/bin/bash
# lean-stack 新手護欄 hook（PreToolUse · Bash）
#
# settings.json 的 deny 是「字串前綴比對」，指令被包進 bash -c、管線、
# 或換個寫法就可能溜過。這支腳本對「整條指令字串」做 pattern 檢查，
# 攔下危險或不可復原的操作——exit 2 = 擋下並把原因回給 Claude（它會改走安全做法）。
#
# 零依賴：只用 grep（不需要 jq / python），新手電腦一定跑得動。
# 誤攔的代價是 Claude 換個方式或問人，很便宜；漏攔的代價是使用者的檔案，很貴。
# 所以規則寧可寬鬆匹配（對整段 stdin JSON 掃，不精確解析 command 欄位）。

INPUT=$(cat)

block() {
  echo "[lean-stack 護欄] 擋下危險操作：$1" >&2
  echo "這類操作不可復原（或會動到專案外的東西）。請改用安全做法；真的需要時，請使用者自己在終端機執行。" >&2
  exit 2
}

# ── 刪除／覆寫類（recursive+force 刪除、dd 寫裝置、格式化、清磁碟）──
echo "$INPUT" | grep -qE 'rm[[:space:]]+-[a-zA-Z]*[rR][a-zA-Z]*f|rm[[:space:]]+-[a-zA-Z]*f[a-zA-Z]*[rR]' && block "rm 遞迴強制刪除"
echo "$INPUT" | grep -qE 'dd[[:space:]]+[^;|&]*of=/dev/' && block "dd 直接寫入裝置"
echo "$INPUT" | grep -qE 'mkfs|diskutil[[:space:]]+(erase|partition)' && block "格式化／清除磁碟"

# ── 提權／改系統 ──
echo "$INPUT" | grep -qE '\bsudo\b|\bdoas\b' && block "sudo 提權"
echo "$INPUT" | grep -qE 'chmod[[:space:]]+(-[a-zA-Z]+[[:space:]]+)?777' && block "chmod 777"
echo "$INPUT" | grep -qE '>[[:space:]]*/etc/|>[[:space:]]*/System/|>[[:space:]]*~/Library/' && block "寫入系統目錄"

# ── 遠端腳本直接執行（供應鏈風險）──
echo "$INPUT" | grep -qE '(curl|wget)[^;|&]*\|[[:space:]]*(ba|z|da)?sh' && block "下載腳本直接執行（curl|sh）"

# ── git 單向門（會真的抹掉 commit / 檔案的操作，CLAUDE.md 護欄的硬體化）──
echo "$INPUT" | grep -qE 'git[[:space:]]+push[^;|&]*(--force|[[:space:]]-f\b)' && block "git 強制推送"
echo "$INPUT" | grep -qE 'git[[:space:]]+reset[[:space:]]+[^;|&]*--hard' && block "git reset --hard"
echo "$INPUT" | grep -qE 'git[[:space:]]+clean\b' && block "git clean"
echo "$INPUT" | grep -qE 'git[[:space:]]+branch[[:space:]]+[^;|&]*-D\b' && block "git 強制刪分支"
echo "$INPUT" | grep -qE 'git[[:space:]]+checkout[[:space:]]+--[[:space:]]' && block "git checkout --（丟棄未存檔的修改）"

# ── 資料庫破壞（容器裡的 DB 也一樣：seed 重灌很快，但別讓它悄悄發生）──
echo "$INPUT" | grep -qiE 'drop[[:space:]]+(table|database|schema)|truncate[[:space:]]+table' && block "DROP／TRUNCATE 資料表"
echo "$INPUT" | grep -qE 'manage\.py[[:space:]]+flush' && block "manage.py flush（清空整個資料庫）"
echo "$INPUT" | grep -qE 'docker[[:space:]]+(compose[[:space:]]+down[^;|&]*(-v|--volumes)|volume[[:space:]]+rm|system[[:space:]]+prune)' && block "刪除 docker volume（資料庫資料在裡面）"

exit 0
