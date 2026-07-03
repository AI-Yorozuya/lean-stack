# 部署

部署的單一真相來源已搬到 **[`infra/DEPLOY.md`](./infra/DEPLOY.md)** —— 那裡有完整三段式 runbook：

1. **本機 docker** 先跑通（後端+DB、admin 前端 dev server，或整套 prod compose 含 nginx）。
2. **Terraform** 開一台伺服器：`plan → REVIEW → apply`（plan-first 紀律）。
3. **deploy app**：`bash infra/scripts/deploy.sh`（build 前端 → compose up → migrate）。

相關檔：
- `infra/docker-compose.prod.yml` — 整套 prod 編排（postgres + backend + nginx）。
- `infra/nginx/nginx.conf` — 服務 lean-admin + 反代 `/api`。
- `infra/terraform/` — 一台 EC2 + security group + media S3 bucket（flat 單環境）。
- `infra/.env.prod.example` — 正式環境變數範本（含 `USE_S3=True` + S3 bucket）。

## 鐵則（速記）

- **AI 不自動對真雲 `apply`** —— plan 先、人 review 後人手 apply。
- **永不 commit** state（`*.tfstate*`）、`*.tfvars`、任何 `.env` / `.env.prod`。
- **憑證走環境變數**（`AWS_PROFILE`...），不進 repo。

## 快速本機驗證

```bash
docker compose -f infra/docker-compose.local.yml up --build
curl -s localhost:8000/api/v1/health    # {"status": "ok"}
```
