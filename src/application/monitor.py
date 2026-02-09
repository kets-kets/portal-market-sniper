"""
Application Layer: Market Monitor Service
Orchestrates the monitoring and sniping process.
"""
import asyncio
from typing import List, Dict, Any
import structlog
from decimal import Decimal

from src.domain import (
    Collection, SnipeStrategy, Money, NFT, NFTId, CollectionId, NFTAttribute, 
    ProfitCalculator
)
from src.application.ports import IMarketClient, IAccountClient, INotificationService
from src.infrastructure.config import settings

logger = structlog.get_logger()

class MarketMonitor:
    """
    Main Application Service.
    Coordinates fetching data, applying strategy, and executing trades.
    """
    
    def __init__(
        self,
        collections: List[Collection],
        market_client: IMarketClient,
        account_client: IAccountClient,
        notifier: INotificationService,
        monitor_config: Any # MonitorConfig from settings
    ):
        self.collections = collections
        self.market_client = market_client
        self.account_client = account_client
        self.notifier = notifier
        self.config = monitor_config
        
        # Strategy
        self.strategy = SnipeStrategy(
            min_profit=Money(Decimal(str(self.config.min_profit)), "TON")
        )
        self.profit_calc = ProfitCalculator(market_fee=self.config.market_fee)
        self.last_floors: Dict[str, Dict[str, float]] = {} # State for UI

    async def run_cycle(self) -> None:
        """Single iteration of the monitoring loop"""
        try:
            # 1. Fetch data (PARALLEL OPTIMIZATION)
            # We fetch floors and new NFTs concurrently to save time
            
            # Create coroutines
            floors_task = self.market_client.fetch_floor_prices(self.collections)
            nfts_task = self.market_client.fetch_nfts(self.collections, limit=self.config.top_n)
            
            # Wait for both
            floors_data, raw_nfts = await asyncio.gather(floors_task, nfts_task)
            
            # Save for UI
            self.last_floors = floors_data
            
            # Map raw data to Domain Entities
            nfts = self._map_to_domain(raw_nfts)
            
            # 2. Analyze
            profitable_ops = []
            
            # We need the balance for the decision
            # Optimization: Fetch balance only if we find a potential match? 
            # Or assume we have enough and fail later? 
            # Better to fetch balance periodically or catch InsufficientFunds.
            # For speed, let's assume we maintain a local balance estimation or fetch it async.
            balance = await self.account_client.get_balance() 

            for nft in nfts:
                # Find floor for this model
                collection = next((c for c in self.collections if c.id == nft.collection_id), None)
                if not collection: 
                    continue
                    
                coll_floors = floors_data.get(collection.short_name, {})
                model_floor_val = coll_floors.get(nft.model)
                
                if model_floor_val is None:
                    continue
                    
                model_floor = Money(Decimal(str(model_floor_val)), "TON")
                
                # Check Strategy
                if self.strategy.should_buy(nft, model_floor, balance):
                    profit = self.profit_calc.calculate_net_profit(nft.price, model_floor)
                    profitable_ops.append((nft, profit))

            # 3. Execute
            # Sort by highest profit
            profitable_ops.sort(key=lambda x: x[1].amount, reverse=True)
            
            async with asyncio.TaskGroup() as tg:
                for nft, profit in profitable_ops:
                    tg.create_task(self._process_buy(nft, profit))
                    
        except Exception as e:
            await self.notifier.notify_error("Error in run_cycle", e)
            logger.error("cycle_failed", error=str(e))

    async def _process_buy(self, nft: NFT, projected_profit: Money) -> None:
        """Execute buy and notify"""
        logger.info("attempting_buy", nft_id=nft.id, price=nft.price.amount, profit=projected_profit.amount)
        
        success = await self.account_client.buy_nft(nft, nft.price)
        
        if success:
            logger.info("buy_success", nft_id=nft.id)
            await self.notifier.notify_buy(nft, nft.price, projected_profit)
        else:
            logger.warning("buy_failed", nft_id=nft.id)

    def _map_to_domain(self, raw_nfts: List[Dict[str, Any]]) -> List[NFT]:
        """Convert API response to Domain Entities"""
        domain_nfts = []
        for item in raw_nfts:
            try:
                # Basic mapping logic - depends on exact API structure
                price_val = Decimal(str(item.get('price', 0)))
                attributes = [
                    NFTAttribute(trait_type=a.get('trait_type'), value=a.get('value'))
                    for a in item.get('attributes', [])
                ]
                
                # Extract model
                model = "Unknown"
                for attr in attributes:
                    if attr.trait_type == "Model": # Adjust if needed
                        model = attr.value
                        break
                
                nft = NFT(
                    id=NFTId(str(item.get('id'))),
                    collection_id=CollectionId(str(item.get('collection_id', ''))),
                    name=item.get('name', 'Unknown'),
                    rank=item.get('rank'),
                    image_url=item.get('image', {}).get('url', ''),
                    price=Money(price_val, "TON"),
                    attributes=attributes,
                    model=model
                )
                domain_nfts.append(nft)
            except Exception as e:
                logger.warning("mapping_error", error=str(e), item_id=item.get('id'))
        return domain_nfts
