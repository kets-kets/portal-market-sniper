"""
Portal Market Analytics API Client
Uses real endpoints to get statistics
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional

import aiohttp
import structlog

logger = structlog.get_logger()


class PortalAnalyticsClient:
    """Client for getting analytics from Portal Market API"""

    BASE_URL = "https://portal-market.com/api"

    def __init__(self, auth_token: str, cache_ttl: int = 60) -> None:
        self.auth_token = auth_token
        self.session: Optional[aiohttp.ClientSession] = None
        self._cache: Dict[str, tuple[datetime, object]] = {}
        self._cache_ttl = cache_ttl

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            headers = {
                "Authorization": self.auth_token,
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                "Accept": "application/json, text/plain, */*",
                "Referer": "https://portal-market.com/collection-list"
            }
            self.session = aiohttp.ClientSession(headers=headers)
        return self.session

    async def close(self) -> None:
        if self.session and not self.session.closed:
            await self.session.close()

    async def get_collections_stats(self) -> Dict[str, Dict[str, float]]:
        """Get list of collections and metrics for 24h"""
        cache_key = "collections_stats"
        cached = self._cache.get(cache_key)
        if cached:
            cached_time, cached_value = cached
            if (datetime.now() - cached_time).seconds < self._cache_ttl:
                return cached_value  # type: ignore[return-value]

        session = await self._get_session()
        url = f"{self.BASE_URL}/collections"
        params = {"offset": 0, "limit": 150}

        try:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error("collections_failed", status=resp.status, response=text[:200])
                    return {}
                data = await resp.json()

            if isinstance(data, list):
                items = data
            else:
                items = data.get("results") or data.get("collections") or data.get("data") or []

            result: Dict[str, Dict[str, float]] = {}
            for item in items:
                short_name = str(item.get("short_name", "")).lower()
                if not short_name:
                    continue

                result[short_name] = {
                    "volume_24h": float(item.get("volume_24h", 0) or 0),
                    "sales_24h": float(item.get("sales_count_24h", 0) or 0),
                    "floor": float(item.get("floor_price", 0) or 0),
                    "items_count": float(item.get("items_count", 0) or 0),
                    "owners_count": float(item.get("owners_count", 0) or 0)
                }

            self._cache[cache_key] = (datetime.now(), result)
            return result
        except Exception as e:
            logger.error("failed_to_get_collections_stats", error=str(e))
            return {}

    async def get_collection_id(self, short_name: str) -> Optional[str]:
        """Get collection ID by short_name"""
        cache_key = f"collection_id_{short_name}"
        cached = self._cache.get(cache_key)
        if cached:
            cached_time, cached_value = cached
            if (datetime.now() - cached_time).seconds < 3600:
                return cached_value  # type: ignore[return-value]

        session = await self._get_session()
        url = f"{self.BASE_URL}/collections/filters"

        try:
            async with session.get(url, params={"short_names": short_name}) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    collections = data.get("collections", [])
                    if collections:
                        collection_id = collections[0].get("id")
                        if collection_id:
                            self._cache[cache_key] = (datetime.now(), collection_id)
                            return collection_id
        except Exception as e:
            logger.error("failed_to_get_collection_id", short_name=short_name, error=str(e))

        return None

    async def get_collection_metrics(self, collection_id: str, days: int = 2) -> Dict[str, float]:
        """Get collection metrics by days"""
        cache_key = f"metrics_{collection_id}_{days}"
        cached = self._cache.get(cache_key)
        if cached:
            cached_time, cached_value = cached
            if (datetime.now() - cached_time).seconds < self._cache_ttl:
                return cached_value  # type: ignore[return-value]

        session = await self._get_session()
        url = f"{self.BASE_URL}/collections/{collection_id}/metrics"
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)

        params = {
            "group_by": "day",
            "from": from_date.isoformat(),
            "to": to_date.isoformat()
        }

        try:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error("metrics_failed", status=resp.status, response=text[:200])
                    return {"sales_24h": 0.0, "sales_48h": 0.0, "trending_score": 1.0}
                data = await resp.json()

            metrics = data.get("metrics", []) if isinstance(data, dict) else []
            cutoff_24h = datetime.now() - timedelta(hours=24)
            cutoff_48h = datetime.now() - timedelta(hours=48)

            sales_24h = 0.0
            sales_48h = 0.0

            for metric in metrics:
                metric_date = datetime.fromisoformat(metric["date"].replace("Z", "+00:00"))
                sales = float(metric.get("sales_count", 0) or 0)
                if metric_date >= cutoff_24h:
                    sales_24h += sales
                if metric_date >= cutoff_48h:
                    sales_48h += sales

            trending_score = 1.0
            prev_24h = sales_48h - sales_24h
            if prev_24h > 0:
                trending_score = sales_24h / prev_24h

            result = {
                "sales_24h": sales_24h,
                "sales_48h": sales_48h,
                "trending_score": trending_score
            }
            self._cache[cache_key] = (datetime.now(), result)
            return result
        except Exception as e:
            logger.error("failed_to_get_metrics", error=str(e))
            return {"sales_24h": 0.0, "sales_48h": 0.0, "trending_score": 1.0}

    async def get_sales_history(self, collection_id: str, hours: int = 24, limit: int = 100) -> List[Dict]:
        """Get sales history for the last N hours"""
        cache_key = f"sales_{collection_id}_{hours}"
        cached = self._cache.get(cache_key)
        if cached:
            cached_time, cached_value = cached
            if (datetime.now() - cached_time).seconds < self._cache_ttl:
                return cached_value  # type: ignore[return-value]

        session = await self._get_session()
        url = f"{self.BASE_URL}/market/actions/"
        params: Dict[str, str | int] = {"collection_id": collection_id, "action_types": "buy", "offset": 0, "limit": limit}

        try:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error("market_actions_failed", status=resp.status, response=text[:200])
                    return []
                data = await resp.json()

            cutoff_time = datetime.now() - timedelta(hours=hours)
            sales = []
            for item in data.get("results", []):
                created_at = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
                if created_at >= cutoff_time:
                    sales.append(item)

            self._cache[cache_key] = (datetime.now(), sales)
            return sales
        except Exception as e:
            logger.error("failed_to_get_sales_history", error=str(e))
            return []

    async def get_model_velocity(self, collection_id: str, model: str, hours: int = 24) -> int:
        """Get sales count for a specific model for N hours"""
        sales = await self.get_sales_history(collection_id, hours=hours, limit=200)
        model_sales = [s for s in sales if s.get("nft", {}).get("model") == model]
        return len(model_sales)

    async def is_trending(self, collection_id: str, threshold: float = 1.5) -> bool:
        """Check if demand is growing"""
        metrics = await self.get_collection_metrics(collection_id, days=2)
        return metrics.get("trending_score", 1.0) >= threshold
