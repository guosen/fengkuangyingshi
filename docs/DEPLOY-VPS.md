# Tier2：迁移到 VPS

Tier1 与 Tier2 的 **唯一必需变更** 是 LibreTV 的托管位置；源策略与 `sources.json` 可继续使用 GitHub Pages。

## 步骤

1. 准备 VPS（1 核 1G+），安装 Docker 与 Docker Compose。
2. 复制 `deploy/tier2-vps/.env.example` → `deploy/tier2-vps/.env`，填写：
   - `PASSWORD`
   - `DEFAULT_SUBSCRIPTIONS`（仍指向 Pages 或自建静态 URL）
   - `COOKIE_SECURE=true`（若已配 HTTPS）
   - `PROXY_SECRET=$(openssl rand -hex 32)`
3. 在 `deploy/tier2-vps/` 执行：

```bash
docker compose up -d
```

4. 浏览器访问 `http://<VPS_IP>:8080`（或启用 `Caddyfile.example` 绑定域名）。

## 可选：源同步也迁到 VPS

```bash
cd /path/to/fengkuangyingshi
pip install -r requirements.txt
python scripts/sync_sources.py
# 用 nginx/caddy 托管 docs/data/sources.json，更新 DEFAULT_SUBSCRIPTIONS
```

cron 示例（每 6 小时）：

```cron
0 */6 * * * cd /path/to/fengkuangyingshi && /usr/bin/python3 scripts/sync_sources.py
```

## 可选：关闭 GitHub Actions

迁移自托管后，可在仓库 Actions 中禁用 **Sync LibreTV sources**，避免重复提交。

## Tier2+ 预留

`docker-compose.yml` 中已注释 `api`、`caddy` 服务；启用自研 API 时保持 `config/sources-policy.json` 为单一策略源。
