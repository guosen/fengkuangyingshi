# 架构设计（Tier1 落地 + VPS 预留）

## 目标

- **Tier1（零 VPS）**：本仓库负责 **源发现与订阅 JSON**；**LibreTV** 负责搜索、聚合、代理播放。
- **Tier2（VPS）**：播放端从 Vercel 迁到 Docker；**订阅 URL 与 policy 不变**，降低迁移成本。

## 分层

```text
┌─────────────────────────────────────────────────────────────┐
│ 客户端：手机/PC 浏览器（LibreTV PWA / 添加到主屏幕）          │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTPS
┌────────────────────────────▼────────────────────────────────┐
│ 播放层（Tier1: Vercel/CF Pages  │  Tier2: VPS docker-compose）│
│  LibreTV — PASSWORD, DEFAULT_SUBSCRIPTIONS, HLS 代理          │
└────────────┬───────────────────────────────┬──────────────────┘
             │ 拉取订阅 JSON                  │ 搜索/详情 Apple CMS API
             ▼                                ▼
┌────────────────────────────┐    ┌─────────────────────────────┐
│ 本仓库 GitHub Pages         │    │ 第三方采集站 api.php/...     │
│  /data/sources.json        │    │  (ziyuanzu 目录中的站点)     │
└────────────┬───────────────┘    └─────────────────────────────┘
             ▲
             │ 每 6h GitHub Actions
┌────────────┴───────────────┐
│ scripts/sync_sources.py     │
│ config/sources-policy.json  │
│ ziyuanzu API → 筛选 → JSON  │
└─────────────────────────────┘
```

## 仓库职责边界

| 路径 | 职责 | Tier1 | Tier2 |
|------|------|-------|-------|
| `scripts/sync_sources.py` | 生成 LibreTV SourceList | Actions | 可改 cron 在 VPS |
| `config/sources-policy.json` | 源数量、评分、响应时间阈值 | ✓ | ✓ 不变 |
| `docs/data/sources.json` | 对外订阅 | Pages | 可迁到 VPS `/static` |
| `deploy/tier2-vps/` | LibreTV + 预留 Caddy/API | 文档 | 启用 compose |
| `config/libretv.env.example` | 环境变量契约 | Vercel | `.env` 同键名 |

## 环境变量契约（Tier1 ↔ Tier2 不变）

| 变量 | 说明 |
|------|------|
| `PASSWORD` | 站点访问密码 |
| `DEFAULT_SUBSCRIPTIONS` | JSON 数组，指向 `sources.json` 的 HTTPS URL |
| `PROXY_SECRET` | 多实例/生产建议设置 |
| `COOKIE_SECURE` | VPS + HTTPS 反代时建议 `true` |

Tier2 仅增加：`LIBRETV_HOST_PORT`、Caddy 域名（见 `deploy/tier2-vps/`）。

## 预留扩展点（未实现，目录/注释已留）

1. **`services/api/`**（注释于 docker-compose）：自研聚合 API，与 LibreTV 并行；订阅仍可用同一 `sources.json`。
2. **`healthCheck.requireAliveForPublish`**：设为 `true` 时只发布探活通过的源（Tier2 带宽更稳时可开）。
3. **Redis 缓存**：Tier2+ 在 API 层加搜索结果 TTL，policy 文件不改。

## 手机端

- Tier1：LibreTV 响应式 UI + 用户 **添加到主屏幕**；源通过 `DEFAULT_SUBSCRIPTIONS` 下发，换机无需手填 API。
- Tier2：同一 URL；可选 PWA 仍指向 LibreTV 域名。

## 与 guosen/ziyuanzhan 的关系

- [ziyuanzhan](https://github.com/guosen/ziyuanzhan) 是 **监测面板 + online.json**；本仓库 **内嵌同步逻辑**，输出 **LibreTV 可直接订阅** 的 `sources.json`，不强制再 fork 监测站。
- 若需要可视化监测，可另 fork ziyuanzhan；本仓库 `manifest.json` 含源健康摘要。

## 合规

仅供私人学习与技术验证；请使用密码保护播放端，避免将代理暴露为公共服务。
