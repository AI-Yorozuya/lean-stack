---
name: deploy
description: 部署 lean-fullstack —— 先本機 docker 跑通，再 terraform plan→review→apply 開一台伺服器，最後 deploy app。內建 plan-first / 不碰機密的雲端紀律。當使用者要部署、上雲、或動 infra 時用。
---

# deploy（v0 stub）

> **v0 stub — 等第一次真正 dogfood 後再長出血肉。** 目前只描述流程與紀律。

完整 runbook 見 `infra/DEPLOY.md`；terraform 細節見 `infra/terraform/README.md`。

## 鐵則（最重要，先讀）

- **AI 不自動對真雲 `apply`。** 永遠 `terraform plan` 先 → 人 review → 人手 `apply`。
  把未 review 的 apply 當「新時代的金鑰外洩 / 上線垮」風險：可能砍 DB、改防火牆、噴帳單。
- **永不 commit**：`*.tfstate*`、`.terraform/`、`*.tfvars`、`infra/.env.prod`、任何 `.env`。
- **憑證走環境變數**（`AWS_PROFILE` / `AWS_ACCESS_KEY_ID`...），不寫進 `.tf` / `.tfvars` / repo。

## 流程

1. **本機 docker 先跑通**
   - 後端+DB：`docker compose -f apps/lean-backend/docker-compose.local.yml up --build` → `curl localhost:8000/api/v1/health`。
   - 要試整套：build 兩個前端 → `docker compose -f infra/docker-compose.prod.yml --env-file infra/.env.prod up -d --build`。

2. **Terraform 開伺服器（plan → REVIEW → apply）**
   - `cd infra/terraform && cp terraform.tfvars.example terraform.tfvars`（填 `key_name` / `ssh_cidr`）。
   - `terraform init` → `terraform plan` → **停下來給人 review** → 人確認才 `terraform apply`。
   - `terraform output public_ip` / `media_bucket_name`。

3. **deploy app 到伺服器**
   - 把 repo 弄上去 → `cp infra/.env.prod.example infra/.env.prod`（填正式值，含 `USE_S3=True` + bucket）。
   - `bash infra/scripts/deploy.sh`（build 前端 → compose up → migrate）。
   - 驗證 `curl localhost/api/v1/health`；DNS 指到 public_ip；TLS 依 nginx.conf 末段開 443。

## TODO（fleshing out from first dogfood）

- 補：遠端 docker context 操作、回滾步驟、零停機更新、憑證/TLS 自動化、實際 plan 輸出範例。
