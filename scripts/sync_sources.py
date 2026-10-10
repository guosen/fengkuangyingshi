#!/usr/bin/env python3
"""
从 ziyuanzu 数据生成 LibreTV-SourceList (version 2) 订阅 JSON。
Tier1: GitHub Actions 定时运行 → docs/data/sources.json → GitHub Pages。
Tier2: 同一脚本可在 VPS cron 运行，仅改 output 路径或 policy。
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "config" / "sources-policy.json"
ZIYUANZU_API = "https://www.ziyuanzu.com/api/v1/sources"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; fengkuangyingshi-sync/1.0; +https://github.com)"
    ),
    "Accept": "application/json",
}


def load_policy() -> dict[str, Any]:
    with POLICY_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def resolve_path(rel: str) -> Path:
    return ROOT / rel


def fetch_ziyuanzu(limit: int = 200) -> list[dict[str, Any]]:
    resp = requests.get(
        ZIYUANZU_API, params={"limit": limit}, headers=HEADERS, timeout=20
    )
    resp.raise_for_status()
    body = resp.json()
    if not body.get("success"):
        raise RuntimeError(f"ziyuanzu API error: {body}")
    data = body.get("data") or []
    if not isinstance(data, list):
        raise RuntimeError("unexpected ziyuanzu payload")
    return data


def load_cache(cache_path: Path) -> list[dict[str, Any]] | None:
    if not cache_path.is_file():
        return None
    with cache_path.open(encoding="utf-8") as f:
        raw = json.load(f)
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict) and isinstance(raw.get("data"), list):
        return raw["data"]
    return None


def normalize_api_url(api: str | None) -> str | None:
    if not api or not isinstance(api, str):
        return None
    api = api.strip()
    if not re.match(r"^https?://", api, re.I):
        return None
    return api.rstrip("/")


def site_link(item: dict[str, Any]) -> str | None:
    for key in ("url", "link"):
        val = item.get(key)
        if isinstance(val, str) and val.startswith("http"):
            return val.rstrip("/")
    return None


def score_item(item: dict[str, Any], prefer_tags: list[str]) -> float:
    rating = float(item.get("rating") or 0)
    rt = item.get("responseTime")
    try:
        response_ms = float(rt) if rt is not None else 9999.0
    except (TypeError, ValueError):
        response_ms = 9999.0
    tag_bonus = 0.0
    tags = item.get("tags") or []
    if isinstance(tags, list):
        for t in prefer_tags:
            if t in tags:
                tag_bonus += 0.05
    updates = item.get("todayUpdates") or 0
    try:
        update_bonus = min(float(updates) * 0.01, 0.2)
    except (TypeError, ValueError):
        update_bonus = 0.0
    # 分数越高越好；响应时间折算为减分
    return rating + tag_bonus + update_bonus - (response_ms / 10000.0)


def passes_filters(item: dict[str, Any], policy: dict[str, Any]) -> bool:
    if policy.get("requireStatusOk") and item.get("status") not in ("ok", "online"):
        return False
    rating = float(item.get("rating") or 0)
    if rating < float(policy.get("minRating", 0)):
        return False
    rt = item.get("responseTime")
    max_rt = policy.get("maxResponseTimeMs")
    if max_rt is not None and rt is not None:
        try:
            if float(rt) > float(max_rt):
                return False
        except (TypeError, ValueError):
            pass
    name = str(item.get("name") or "")
    for pat in policy.get("excludeNamePatterns") or []:
        if re.search(pat, name):
            return False
    if not normalize_api_url(item.get("api")):
        return False
    return True


def health_check(url: str, timeout: float) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        r = requests.get(
            url,
            headers=HEADERS,
            timeout=timeout,
            allow_redirects=True,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        alive = r.status_code < 500
        return {
            "is_alive": alive,
            "status_code": r.status_code,
            "response_time_ms": round(elapsed_ms, 2),
            "error": None if alive else f"HTTP {r.status_code}",
        }
    except requests.RequestException as exc:
        elapsed_ms = (time.perf_counter() - started) * 1000
        return {
            "is_alive": False,
            "status_code": None,
            "response_time_ms": round(elapsed_ms, 2),
            "error": str(exc),
        }


def to_libretv_source(item: dict[str, Any], health: dict[str, Any] | None) -> dict[str, Any]:
    api = normalize_api_url(item.get("api"))
    detail = site_link(item)
    entry: dict[str, Any] = {
        "name": str(item.get("name") or urlparse(api or "").netloc),
        "url": api,
        "isAdult": False,
    }
    if detail:
        entry["detail"] = detail
    if health:
        entry["_meta"] = {
            "rating": item.get("rating"),
            "responseTime": item.get("responseTime"),
            "health": health,
        }
    return entry


def strip_meta_for_publish(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """LibreTV 订阅只需 name/url/detail/isAdult；_meta 仅写在 manifest。"""
    out = []
    for s in sources:
        out.append({k: v for k, v in s.items() if not k.startswith("_")})
    return out


def main() -> int:
    policy = load_policy()
    out_cfg = policy.get("output") or {}
    sources_path = resolve_path(out_cfg.get("sourcesFile", "docs/data/sources.json"))
    manifest_path = resolve_path(out_cfg.get("manifestFile", "docs/data/manifest.json"))
    cache_path = resolve_path(out_cfg.get("cacheFile", "docs/data/ziyuanzu-cache.json"))

    raw: list[dict[str, Any]] | None = None
    fetch_error: str | None = None
    try:
        raw = fetch_ziyuanzu()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with cache_path.open("w", encoding="utf-8") as f:
            json.dump(
                {"fetchedAt": datetime.now(timezone.utc).isoformat(), "data": raw},
                f,
                ensure_ascii=False,
                indent=2,
            )
        print(f"[OK] ziyuanzu API: {len(raw)} items, cache updated")
    except Exception as exc:  # noqa: BLE001
        fetch_error = str(exc)
        raw = load_cache(cache_path)
        if raw:
            print(f"[WARN] API failed ({exc}), using cache ({len(raw)} items)")
        else:
            print(f"[ERROR] API failed and no cache: {exc}", file=sys.stderr)
            return 1

    prefer_tags = policy.get("preferTags") or []
    candidates = [i for i in raw if passes_filters(i, policy)]
    candidates.sort(
        key=lambda x: score_item(x, prefer_tags),
        reverse=True,
    )
    max_n = int(policy.get("maxSources", 12))
    selected = candidates[:max_n]

    hc_cfg = policy.get("healthCheck") or {}
    hc_enabled = bool(hc_cfg.get("enabled", True))
    hc_timeout = float(hc_cfg.get("timeoutSeconds", 8))
    require_alive = bool(hc_cfg.get("requireAliveForPublish", False))

    libretv_with_meta: list[dict[str, Any]] = []
    for item in selected:
        api = normalize_api_url(item.get("api"))
        if not api:
            continue
        health = None
        if hc_enabled:
            health = health_check(api, hc_timeout)
            if require_alive and not health.get("is_alive"):
                continue
        libretv_with_meta.append(to_libretv_source(item, health))

    publish_sources = strip_meta_for_publish(libretv_with_meta)
    subscription = {
        "name": policy.get("listName") or "fengkuangyingshi sources",
        "version": int(policy.get("version", 2)),
        "sources": publish_sources,
        "liveSources": [],
    }

    sources_path.parent.mkdir(parents=True, exist_ok=True)
    with sources_path.open("w", encoding="utf-8") as f:
        json.dump(subscription, f, ensure_ascii=False, indent=2)
        f.write("\n")

    manifest = {
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "tier": "1-github-pages",
        "fetchError": fetch_error,
        "policy": {
            "maxSources": max_n,
            "minRating": policy.get("minRating"),
            "maxResponseTimeMs": policy.get("maxResponseTimeMs"),
        },
        "stats": {
            "rawTotal": len(raw),
            "candidates": len(candidates),
            "published": len(publish_sources),
        },
        "sourcesDetail": libretv_with_meta,
        "subscriptionPath": "/data/sources.json",
        "libretv": {
            "defaultSubscriptionsEnv": 'DEFAULT_SUBSCRIPTIONS=["https://YOUR_USER.github.io/fengkuangyingshi/data/sources.json"]',
        },
    }
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"[OK] wrote {sources_path} ({len(publish_sources)} sources)")
    print(f"[OK] wrote {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
