# 疯狂影视（fengkuangyingshi）

**Tier1 零 VPS 方案**：本仓库用 GitHub Pages 发布 **LibreTV 源订阅**；播放端单独部署 [LibreTV](https://github.com/LibreSpark/LibreTV)（Vercel / Cloudflare）。架构与迁移说明见 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)。

## 你能得到什么

| 组件 | 托管 | 作用 |
|------|------|------|
| 本仓库 Pages | GitHub 免费 | `data/sources.json` 订阅 + 说明页 |
| LibreTV | Vercel/CF 免费 | 搜索、聚合、播放、手机浏览器/PWA |
| VPS（可选） | 后期 | 同环境变量、同订阅 URL，见 [`docs/DEPLOY-VPS.md`](docs/DEPLOY-VPS.md) |

## 快速开始

1. 部署源订阅：[`docs/DEPLOY-TIER1.md`](docs/DEPLOY-TIER1.md)
2. 调整选源策略：[`config/sources-policy.json`](config/sources-policy.json)
3. LibreTV 环境变量模板：[`config/libretv.env.example`](config/libretv.env.example)

本地生成订阅（需网络访问 ziyuanzu API，失败则用缓存）：

```bash
pip install -r requirements.txt
python scripts/sync_sources.py
```

## 目录结构

```text
config/           # 选源策略 + LibreTV 环境变量契约（Tier1/2 共用）
scripts/          # sync_sources.py
docs/             # GitHub Pages 根目录（index + data/*.json）
deploy/tier2-vps/ # Docker Compose + .env.example（预留）
.github/workflows/# 定时同步 + Pages 部署
```

## 合规

第三方采集站内容版权归权利人所有；请 **密码保护** 播放端，仅供私人使用，勿作公开商业传播。
