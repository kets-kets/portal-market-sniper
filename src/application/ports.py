"""
Application Layer: Ports (Interfaces)
Defines how the Application layer expects to interact with the Infrastructure.
"""
from typing import List, Protocol, Dict, Optional, Any
from src.domain import NFT, Collection, Money

class IMarketClient(Protocol):
    """Interface for fetching NFT data from external API"""
    
    async def fetch_nfts(self, collections: List[Collection], limit: int) -> List[Dict[str, Any]]:
        ...
    
    async def fetch_floor_prices(self, collections: List[Collection]) -> Dict[str, Dict[str, float]]:
        """Returns {collection_slug: {model_name: floor_price}}"""
        ...

class IAccountClient(Protocol):
    """Interface for account actions (balance, buy)"""
    
    async def get_balance(self) -> Money:
        ...
        
    async def buy_nft(self, nft: NFT, price: Money) -> bool:
        ...

class INotificationService(Protocol):
    """Interface for user notifications"""
    
    async def notify_buy(self, nft: NFT, price: Money, profit: Money) -> None:
        ...
        
    async def notify_error(self, message: str, error: Exception) -> None:
        ...
