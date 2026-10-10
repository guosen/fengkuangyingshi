# Tier1 部署清单（零 VPS）

## 1. 本仓库（源订阅）

1. Fork / 使用本仓库 `fengkuangyingshi`。
2. **Settings → Pages → Build and deployment → Source** 选择 **GitHub Actions**。
3. **Actions** → **Sync LibreTV sources** → **Run workflow**（或合并到 `main` 后自动跑）。
4. 打开 `https://<USER>.github.io/<REPO>/`，复制 **订阅地址**（即 `.../data/sources.json`）。

可选：编辑 `config/sources-policy.json` 调整 `maxSources`、`minRating`、`maxResponseTimeMs`。

> **说明**：ziyuanzu API 可能对 GitHub Actions IP 返回 403。此时 workflow 会使用仓库内 `docs/data/ziyuanzu-cache.json`（可本地运行 `sync_sources.py` 在能访问 API 的网络下更新后提交）。

## 2. LibreTV（播放端）

推荐 Fork [LibreSpark/LibreTV](https://github.com/LibreSpark/LibreTV) 并部署到 **Vercel** 或 **Cloudflare Pages**。

### Vercel 环境变量（最小集）

| Name | Value |
|------|--------|
| `PASSWORD` | 强密码 |
| `DEFAULT_SUBSCRIPTIONS` | `["https://<USER>.github.io/<REPO>/data/sources.json"]` |

完整可选变量见仓库 `config/libretv.env.example` 与 [LibreTV 配置文档](https://libretv.is-an.org/wiki/Deployment.html)。

### 验证

1. 打开 LibreTV URL，输入密码。
2. **设置 → 源管理 → 数据源订阅** 应已有预置订阅（或手动粘贴 `sources.json` URL）→ 同步。
3. 搜索测试；手机浏览器访问同一 URL → **添加到主屏幕**。

## 3. 费用与限制

- GitHub Pages + Vercel 免费档：适合 **个人、低流量**。
- 播放流量走 LibreTV 所在平台的 **出站代理**，免费档有超时/流量上限；不稳定时见 [DEPLOY-VPS.md](./DEPLOY-VPS.md)。

## 4. 迁移到 VPS 时

- **不要改** `sources.json` URL（可继续用 Pages），或把 `docs/data/` 拷到 VPS 静态目录后只改 `DEFAULT_SUBSCRIPTIONS` 一处。
- 播放端改用 `deploy/tier2-vps/docker-compose.yml`，环境变量键名与 Tier1 相同。
