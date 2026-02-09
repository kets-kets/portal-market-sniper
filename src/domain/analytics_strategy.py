"""
Smart Strategy with real analytics from Portal Market API
"""
from decimal import Decimal
from typing import Tuple, cast
import structlog

from src.domain.models import NFT, Money
from src.infrastructure.portal_analytics import PortalAnalyticsClient

logger = structlog.get_logger()


class AnalyticsStrategy:
    """
    Strategy using real analytics from Portal Market
    
    Buying criteria:
    1. Minimum liquidity: velocity >= 3 sales/24h
    2. Trending bonus: if demand grows (+50%) -> can pay more
    3. Basic profit: min_profit (e.g. 0.3 TON)
    """
    
    def __init__(
        self,
        analytics_client: PortalAnalyticsClient,
        min_profit: Money,
        min_velocity: int = 3,
        trending_threshold: float = 1.5
    ):
        self.analytics = analytics_client
        self.min_profit = min_profit
        self.min_velocity = min_velocity
        self.trending_threshold = trending_threshold
        
        # Cache for collection_id
        self._collection_ids: dict[str, str] = {}
    
    async def _get_collection_id(self, short_name: str) -> str | None:
        """Get collection ID with caching"""
        if short_name not in self._collection_ids:
            cid = await self.analytics.get_collection_id(short_name)
            if cid:
                self._collection_ids[short_name] = cid
            else:
                return None
        return self._collection_ids.get(short_name)
    
    async def should_buy(
        self,
        nft: NFT,
        floor: Money,
        balance: Money,
        collection_short_name: str
    ) -> Tuple[bool, str]:
        """
        Purchase decision based on real analytics
        
        Returns:
            (True/False, reason)
        """
        # 1. Basic balance check
        if nft.price >= balance:
            return False, "insufficient_balance"
        
        # 2. Basic profit
        profit = floor - nft.price
        if profit < self.min_profit:
            return False, f"low_profit_{profit.amount:.2f}"
        
        # 3. Get collection_id
        collection_id = await self._get_collection_id(collection_short_name)
        if not collection_id:
            # Fallback: if no analytics - use basic profit
            logger.warning("no_collection_id", collection=collection_short_name)
            return True, f"no_analytics_profit_{profit.amount:.2f}"
        
        # 4. Check velocity (liquidity)
        try:
            velocity = await self.analytics.get_model_velocity(
                collection_id,
                nft.model,
                hours=24
            )
            
            if velocity < self.min_velocity:
                return False, f"low_velocity_{velocity}_sales"
            
            # 5. Check trending
            is_trending = await self.analytics.is_trending(
                collection_id,
                threshold=self.trending_threshold
            )
            
            # 6. Adaptive profit
            # Using custom division operator on Money
            discount_pct = cast(float, profit / floor) * 100
            
            if is_trending:
                # Trending: can buy with smaller discount (>= 5%)
                if discount_pct >= 5:
                    return True, f"trending_good_discount_{discount_pct:.1f}%_vel_{velocity}"
                else:
                    return False, f"trending_but_small_discount_{discount_pct:.1f}%"
            
            elif velocity >= 10:
                # High liquidity: >= 8% discount
                if discount_pct >= 8:
                    return True, f"high_velocity_{velocity}_discount_{discount_pct:.1f}%"
                else:
                    return False, f"high_velocity_but_small_discount_{discount_pct:.1f}%"
            
            else:
                # Medium liquidity: >= 12% discount
                if discount_pct >= 12:
                    return True, f"moderate_velocity_{velocity}_discount_{discount_pct:.1f}%"
                else:
                    return False, f"moderate_velocity_small_discount_{discount_pct:.1f}%"
        
        except Exception as e:
            logger.error("analytics_failed", error=str(e))
            # Fallback: use basic profit
            return True, f"analytics_error_fallback_profit_{profit.amount:.2f}"
