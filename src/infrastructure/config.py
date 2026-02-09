"""
Infrastructure Layer: Configuration Adapter
"""
from pathlib import Path
from typing import Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Global application settings loaded from .env file and environment variables.
    Follows 12-factor app methodology.
    """
    
    # Telegram Keys
    api_id: int = Field(..., alias="API_ID")
    api_hash: str = Field(..., alias="API_HASH")
    
    # Aportals
    aportals_auth: SecretStr = Field(..., alias="APORTALS_AUTH")
    aportals_analytics_auth: Optional[SecretStr] = Field(None, alias="APORTALS_ANALYTICS_AUTH")
    
    # Monitoring
    scan_delay: float = Field(0.4, alias="SCAN_DELAY")
    floor_cache_ttl: int = Field(60, alias="FLOOR_CACHE_TTL")
    top_n: int = Field(3, alias="TOP_N")
    
    # Trading
    min_profit: float = Field(0.3, alias="MIN_PROFIT")
    market_fee: float = Field(0.05, alias="MARKET_FEE")
    snipe_minutes: int = Field(30, alias="SNIPE_MINUTES")
    
    # System
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    dry_run: bool = Field(False, alias="DRY_RUN")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Singleton instance
try:
    settings = Settings() # type: ignore
except Exception as e:
    # We want to fail fast if config is invalid
    print(f"❌ Configuration Error: {e}")
    # Don't exit here, let the main app handle it or cras
    settings = None # type: ignore
