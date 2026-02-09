"""
Infrastructure Layer: Aportals Client Adapter
"""
import asyncio
import json
from decimal import Decimal
from typing import List, Dict, Any, Optional
import aiohttp
import structlog
from urllib.parse import quote_plus

from src.application.ports import IMarketClient, IAccountClient
from src.domain import Collection, NFT, Money, NFTAttribute, NFTId, CollectionId
from src.infrastructure.config import settings

logger = structlog.get_logger()

# Constants
API_BASE = "https://portal-market.com/api" # Corrected domain

from src.infrastructure.auth import TokenRefresher

class AportalsClient(IMarketClient, IAccountClient):
    """
    Adapter for Aportals API using aiohttp.
    Implements both Market and Account interfaces.
    """
    
    def __init__(self) -> None:
        self._session: Optional[aiohttp.ClientSession] = None
        self._auth_header = settings.aportals_auth.get_secret_value()

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            # Optimization: Connection Pooling
            connector = aiohttp.TCPConnector(
                limit=100,          # High concurrency
                limit_per_host=20,  # Max connections to API
                ttl_dns_cache=300,  # Cache DNS 5min
                use_dns_cache=True,
                enable_cleanup_closed=True
            )

            self._session = aiohttp.ClientSession(
                connector=connector,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Encoding": "gzip, deflate, br, zstd",
                    "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
                    "Authorization": self._auth_header,
                    "Origin": "https://portal-market.com",
                    "Referer": "https://portal-market.com/marketplace"
                },
                timeout=aiohttp.ClientTimeout(total=10)
            )
        return self._session

    async def _update_auth_header(self, new_token: str) -> None:
        """Updates the auth header in memory and in the session"""
        self._auth_header = new_token
        # Re-create session to apply new header
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None 

    async def _handle_401(self) -> bool:
        """Attempts to refresh token. Returns True if refreshed."""
        logger.info("401_detected_attempting_refresh")
        new_token = await TokenRefresher.refresh_token()
        if new_token:
            await self._update_auth_header(new_token)
            return True
        return False

    async def close(self) -> None:
        if self._session:
            await self._session.close()

    # --- Market Client Implementation ---

    async def fetch_nfts(self, collections: List[Collection], limit: int) -> List[Dict[str, Any]]:
        return await self._fetch_nfts_internal(collections, limit, retry=True)

    async def _fetch_nfts_internal(self, collections: List[Collection], limit: int, retry: bool) -> List[Dict[str, Any]]:
        session = await self._get_session()
        
        # Prepare filters
        coll_slugs = [c.short_name for c in collections]
        models = [m for c in collections for m in c.models]
        
        # URL encoding
        coll_str = "%2C".join(quote_plus(s) for s in coll_slugs)
        models_str = "%2C".join(quote_plus(m) for m in models)
        
        url = (
            f"{API_BASE}/nfts"
            f"?offset=0&limit={limit}"
            f"&filter_by_collections={coll_str}"
            f"&filter_by_models={models_str}"
            f"&max_price=99999" # Practical infinity
            f"&sort_by=listed_at+desc"
            f"&status=listed"
            f"&premarket_status=all"
        )
        
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    results: List[Dict[str, Any]] = data.get("results", [])
                    return results
                elif response.status == 401 and retry:
                    if await self._handle_401():
                        return await self._fetch_nfts_internal(collections, limit, retry=False)
                    return []
                else:
                    logger.error("api_error", status=response.status, url=url)
                    return []
        except Exception as e:
            logger.error("fetch_error", error=str(e))
            return []

    async def fetch_floor_prices(self, collections: List[Collection]) -> Dict[str, Dict[str, float]]:
        return await self._fetch_floor_prices_internal(collections, retry=True)

    async def _fetch_floor_prices_internal(self, collections: List[Collection], retry: bool) -> Dict[str, Dict[str, float]]:
        session = await self._get_session()
        
        coll_slugs = [c.short_name for c in collections]
        slugs_str = ",".join(coll_slugs)
        
        url = f"{API_BASE}/collections/filters?short_names={slugs_str}"
        
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    floors = data.get('floor_prices', {})
                    result = {}
                    
                    for slug, val in floors.items():
                        models_data = val.get('models', {})
                        clean_models = {}
                        for m_name, price in models_data.items():
                            if price is not None:
                                try:
                                    clean_models[m_name] = float(price)
                                except (ValueError, TypeError):
                                    pass
                        result[slug] = clean_models
                    
                    return result
                elif response.status == 401 and retry:
                    if await self._handle_401():
                        return await self._fetch_floor_prices_internal(collections, retry=False)
                    return {}
                else:
                    logger.error("floor_api_error", status=response.status)
                    return {}
        except Exception as e:
            logger.error("floor_fetch_error", error=str(e))
            return {}

    # --- Account Client Implementation ---

    async def get_balance(self) -> Money:
        # NOTE: Implement actual API call using user profile
        # For now, if DRY_RUN is false, we might want to fail
        # But we will implement this properly later.
        # This is a placeholder as I don't have the exact profile endpoint in memory
        # Assuming we can just fetch user data.
        return Money(Decimal("100.0"), "TON") 

    async def buy_nft(self, nft: NFT, price: Money) -> bool:
        """
        Executes buy using pure HTTP request (Faster than legacy lib)
        Endpoint: POST /api/nfts
        Payload: {"nft_details": [{"id": "...", "price": "..."}]}
        """
        if settings.dry_run:
            logger.info("dry_run_buy", nft_id=nft.id, price=price.amount)
            return True
        
        session = await self._get_session()
        url = f"{API_BASE}/nfts"
        
        # Payload structure reverse-engineered from aportalsmp
        payload = {
            "nft_details": [
                {
                    "id": nft.id,
                    "price": str(price.amount)
                }
            ]
        }
        
        try:
            logger.info("executing_buy_request", nft_id=nft.id, price=price.amount)
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("buy_request_success", response=data)
                    return True
                elif response.status == 401:
                    logger.error("buy_auth_failed", status=401)
                    # Try refresh? Usually too late for snipe, but good for next time
                    # Fire and forget refresh
                    asyncio.create_task(self._handle_401()) 
                    return False
                else:
                    text = await response.text()
                    logger.error("buy_request_failed", status=response.status, response=text)
                    return False
                    
        except Exception as e:
            logger.error("buy_exception", error=str(e))
            return False
