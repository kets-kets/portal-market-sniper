"""
Main Entry Point (Composition Root)
"""
import asyncio
import signal
import structlog
from typing import List

from src.infrastructure.config import settings
from src.infrastructure.api_client import AportalsClient
from src.infrastructure.portal_analytics import PortalAnalyticsClient
from src.application.monitor import MarketMonitor
from src.application.turbo_monitor import TurboMarketMonitor
from src.application.ports import INotificationService
from src.domain import Collection, CollectionId, Money, NFT

# Setup Logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
from src.application.ui import DashboardService

logger = structlog.get_logger()

class ConsoleNotifier(INotificationService):
    def __init__(self, dashboard: DashboardService):
        self.dashboard = dashboard

    async def notify_buy(self, nft: NFT, price: Money, profit: Money) -> None:
        msg = f"🚀 BOUGHT! {nft.model} | Price: {price.amount} | Profit: {profit.amount}"
        self.dashboard.add_log(msg, "INFO")

    async def notify_error(self, message: str, error: Exception) -> None:
        msg = f"❌ {message}: {error}"
        self.dashboard.add_log(msg, "ERROR")

from src.infrastructure.repo import load_collections_from_file

# ...

async def main() -> None:
    logger.info("startup", **settings.model_dump(exclude={'aportals_auth', 'aportals_analytics_auth'}))
    
    # 1. Load Collections
    collections: List[Collection] = load_collections_from_file("config/sniper_collections.json")
    print(f"DEBUG: Loaded {len(collections)} collections")
    
    # Fallback to rest file if main missing (as user had it open)
    if not collections:
         collections = load_collections_from_file("config/sniper_collections_rest.json")

    # Log loaded count
    if collections:
        logger.info("collections_loaded", count=len(collections), names=[c.name for c in collections])
    else:
        logger.warning("no_collections_loaded", message="Check config/sniper_collections.json")

    # 2. Composition
    client = AportalsClient()
    
    # Portal Analytics - token from browser session (if set)
    analytics_token = settings.aportals_analytics_auth or settings.aportals_auth
    analytics = PortalAnalyticsClient(auth_token=analytics_token.get_secret_value())
    
    dashboard = DashboardService(collections)
    notifier = ConsoleNotifier(dashboard)
    
    # TURBO MODE with analytics
    monitor = TurboMarketMonitor(
        collections=collections,
        market_client=client,
        account_client=client,
        notifier=notifier,
        monitor_config=settings,
        analytics_client=analytics
    )
    
    # 3. Shutdown handling
    stop_event = asyncio.Event()
    
    def signal_handler() -> None:
        dashboard.stop()
        logger.info("shutdown_signal_received")
        stop_event.set()

    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGINT, signal_handler)
    loop.add_signal_handler(signal.SIGTERM, signal_handler)

    # 4. Main Loop
    logger.info("starting_loop")
    dashboard.start()
    
    cycle_count = 0
    try:
        while not stop_event.is_set():
            await monitor.run_cycle()
            cycle_count += 1
            
            # Update UI with analytics
            dashboard.update_state(
                monitor.last_floors, 
                cycle_count,
                analytics_cache=monitor.analytics_cache
            )
            
            await asyncio.sleep(settings.scan_delay)
    except Exception as e:
        dashboard.stop()
        logger.critical("fatal_error", error=str(e))
        print(f"FATAL: {e}")
    finally:
        dashboard.stop()
        await client.close()
        await analytics.close()
        logger.info("shutdown_complete")

if __name__ == "__main__":
    asyncio.run(main())