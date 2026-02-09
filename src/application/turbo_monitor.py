"""
Application: Turbo Monitor (Optimized Version)
- Parallel collection processing
- Caching with TTL
- Batch buying
- Aggressive timing
"""
import asyncio
from typing import List, Dict, Set
from decimal import Decimal
import structlog
from datetime import datetime, timedelta

from src.domain import Collection, NFT, Money, SnipeStrategy, ProfitCalculator
from src.domain.analytics_strategy import AnalyticsStrategy
from src.application.ports import IMarketClient, IAccountClient, INotificationService
from src.infrastructure.config import settings
from src.infrastructure.portal_analytics import PortalAnalyticsClient

logger = structlog.get_logger()


class TurboMarketMonitor:
    """
    Turbo version of monitoring with aggressive optimizations:
    1. Parallel check of all collections
    2. Floor cache with TTL 30s (instead of 60s)
    3. Batch buying (5 simultaneously)
    4. Pre-loading balance
    5. Skip already processed NFTs
    """
    
    def __init__(
        self,
        collections: List[Collection],
        market_client: IMarketClient,
        account_client: IAccountClient,
        notifier: INotificationService,
        monitor_config,
        analytics_client: PortalAnalyticsClient
    ):
        self.collections = collections
        self.market_client = market_client
        self.account_client = account_client
        self.notifier = notifier
        self.config = monitor_config
        self.analytics_client = analytics_client
        
        # Strategy with real analytics
        self.strategy = AnalyticsStrategy(
            analytics_client=analytics_client,
            min_profit=Money(Decimal(str(self.config.min_profit)), "TON")
        )
        self.profit_calc = ProfitCalculator(market_fee=self.config.market_fee)
        
        # Optimizations
        self.floor_cache: Dict[str, Dict[str, tuple]] = {}  # (price, timestamp)
        self.processed_nfts: Set[str] = set()  # Processed NFT IDs
        self.cached_balance: Money = Money(Decimal("0"), "TON")
        self.balance_last_fetch: datetime = datetime.min
        
        # State
        self.last_floors: Dict[str, Dict[str, float]] = {}
        self.total_snipes_attempted = 0
        self.successful_snipes = 0
        
        # Analytics cache for UI
        self.analytics_cache: Dict[str, Dict[str, float]] = {}
        self._cycle_counter = 0
    
    async def run_cycle(self) -> None:
        """One cycle - MAX SPEED"""
        try:
            # 1. Update balance (once every 10 seconds, not every cycle)
            if (datetime.now() - self.balance_last_fetch).seconds > 10:
                self.cached_balance = await self.account_client.get_balance()
                self.balance_last_fetch = datetime.now()
            
            # 2. Process ALL collections PARALLEL
            tasks = [
                self._process_collection(collection)
                for collection in self.collections
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 3. Collect opportunities from all collections
            all_opportunities = []
            for result in results:
                if isinstance(result, list):
                    all_opportunities.extend(result)
            
            # 4. Sort by profit
            all_opportunities.sort(key=lambda x: x[1].amount, reverse=True)
            
            # 5. BATCH BUY top-5 (parallel)
            if all_opportunities:
                batch = all_opportunities[:5]
                
                buy_tasks = [
                    self._process_buy(nft, profit, reason)
                    for nft, profit, reason in batch
                ]
                
                await asyncio.gather(*buy_tasks, return_exceptions=True)
            
            # 6. Clear old processed NFTs (don't keep forever)
            if len(self.processed_nfts) > 1000:
                self.processed_nfts.clear()

            # 7. Update analytics cache every 5 cycles
            self._cycle_counter += 1
            if self._cycle_counter % 5 == 0:
                await self._update_analytics_cache()
        
        except Exception as e:
            logger.error("cycle_failed", error=str(e))
    
    async def _process_collection(self, collection: Collection) -> List[tuple]:
        """Process one collection (fast)"""
        try:
            # 1. Get floors (with cache)
            floors = await self._get_floors_cached(collection)
            
            # 2. Get new NFTs
            raw_nfts = await self.market_client.fetch_nfts(
                [collection],
                limit=self.config.top_n
            )
            
            nfts = self._map_to_domain(raw_nfts)
            
            # 3. Filter profitable
            opportunities = []
            
            for nft in nfts:
                # Skip already processed
                if nft.id in self.processed_nfts:
                    continue
                
                # Check strategy
                model_floor_val = floors.get(nft.model)
                if not model_floor_val:
                    continue
                
                model_floor = Money(Decimal(str(model_floor_val)), "TON")
                
                # Analytics strategy (async)
                should_buy, reason = await self.strategy.should_buy(
                    nft, 
                    model_floor, 
                    self.cached_balance,
                    collection.short_name
                )
                
                if should_buy:
                    profit = self.profit_calc.calculate_net_profit(nft.price, model_floor)
                    opportunities.append((nft, profit, reason))
                    
                    logger.info(
                        "opportunity_found",
                        nft=nft.name,
                        model=nft.model,
                        reason=reason,
                        profit=float(profit.amount)
                    )

                    
                    # Mark as processed
                    self.processed_nfts.add(nft.id)
            
            return opportunities
        
        except Exception as e:
            logger.error("collection_processing_failed", collection=collection.name, error=str(e))
            return []
    
    async def _get_floors_cached(self, collection: Collection) -> Dict[str, float]:
        """Get floors with caching (TTL 30s)"""
        cache_key = collection.short_name
        now = datetime.now()
        
        # Check cache
        if cache_key in self.floor_cache:
            cached_data = self.floor_cache[cache_key]
            
            # Check if not stale (30s TTL)
            is_fresh = all(
                (now - timestamp).seconds < 30
                for _, timestamp in cached_data.values()
            )
            
            if is_fresh:
                return {
                    model: price
                    for model, (price, _) in cached_data.items()
                }
        
        # Cache miss - load
        floors_data = await self.market_client.fetch_floor_prices([collection])
        floors = floors_data.get(collection.short_name, {})
        
        # Save to cache with timestamp
        self.floor_cache[cache_key] = {
            model: (price, now)
            for model, price in floors.items()
        }
        
        # Update state for UI
        self.last_floors[collection.short_name] = floors
        
        return floors
    
    async def _process_buy(self, nft: NFT, profit: Money, reason: str) -> None:
        """Buy NFT (with error handling)"""
        try:
            self.total_snipes_attempted += 1
            
            result = await self.account_client.buy_nft(nft, nft.price)
            
            if result:
                self.successful_snipes += 1
                await self.notifier.notify_buy(nft, nft.price, profit)
                
                logger.info(
                    "snipe_success",
                    nft=nft.name,
                    model=nft.model,
                    price=float(nft.price.amount),
                    profit=float(profit.amount),
                    reason=reason,
                    success_rate=f"{self.successful_snipes}/{self.total_snipes_attempted}"
                )
            else:
                logger.warning("snipe_failed", nft=nft.name, result=result)
        
        except Exception as e:
            await self.notifier.notify_error(f"Buy failed: {nft.name}", e)
            logger.error("snipe_error", nft=nft.name, error=str(e))
    
    async def _update_analytics_cache(self) -> None:
        """Update analytics cache for UI"""
        try:
            # Get all collections in one request
            stats = await self.analytics_client.get_collections_stats()
            
            for collection in self.collections[:2]:
                short_name = collection.short_name.lower()
                data = stats.get(short_name)
                
                if data:
                    self.analytics_cache[collection.short_name] = {
                        'velocity': data['sales_24h'],
                        'trending_score': 1.0  # TODO: calculate from history
                    }
                    logger.info(
                        "analytics_updated",
                        collection=collection.short_name,
                        velocity=data['sales_24h'],
                        volume_24h=data['volume_24h']
                    )
        except Exception as e:
            logger.error("analytics_cache_failed", error=str(e))
    
    def _map_to_domain(self, raw_nfts: List[Dict]) -> List[NFT]:
        """Map API response to domain entities"""
        from src.domain import NFTId, CollectionId, NFTAttribute
        
        result = []
        for raw in raw_nfts:
            try:
                nft = NFT(
                    id=NFTId(raw.get("address", "")),
                    collection_id=CollectionId(raw.get("collection", "")),
                    name=raw.get("name", "Unknown"),
                    rank=raw.get("rank"),
                    image_url=raw.get("image", ""),
                    price=Money(Decimal(str(raw.get("price", 0))), "TON"),
                    attributes=[
                        NFTAttribute(
                            trait_type=attr.get("trait_type", ""),
                            value=str(attr.get("value", ""))
                        )
                        for attr in raw.get("attributes", [])
                    ],
                    model=raw.get("model", "Unknown")
                )
                result.append(nft)
            except Exception as e:
                logger.warning("nft_parsing_failed", raw=raw, error=str(e))
        
        return result
