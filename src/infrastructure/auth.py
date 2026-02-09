"""
Infrastructure Layer: Authentication Service
Handles automatic token refresh via aportalsmp.
"""
import asyncio
import os
from pathlib import Path
import structlog
from typing import Optional

from src.infrastructure.config import settings

logger = structlog.get_logger()

class TokenRefresher:
    """
    Refreshes the Aportals authentication token using Telegram credentials.
    Updates the .env file and returns the new token.
    """
    
    @staticmethod
    async def refresh_token() -> Optional[str]:
        """
        Executes the refresh logic.
        Returns the new token string if successful, None otherwise.
        """
        try:
            from aportalsmp.auth import update_auth
            
            logger.info("refreshing_token", api_id=settings.api_id)
            
            # Ensure sessions dir exists
            base_dir = Path(__file__).parent.parent.parent
            sessions_dir = base_dir / "data" / "sessions"
            sessions_dir.mkdir(parents=True, exist_ok=True)
            
            # Call external lib to do the heavy lifting (Telegram Auth)
            new_token = await update_auth(
                api_id=settings.api_id,
                api_hash=settings.api_hash,
                session_path=str(sessions_dir),
                session_name="account"
            )
            
            if new_token:
                logger.info("token_refreshed_successfully")
                TokenRefresher._update_env_file(new_token)
                return str(new_token)
            else:
                logger.error("token_refresh_returned_empty")
                return None
                
        except Exception as e:
            logger.error("token_refresh_failed", error=str(e))
            return None

    @staticmethod
    def _update_env_file(new_token: str) -> None:
        """Updates the .env file with the new token to persist it."""
        env_path = Path(".env")
        if not env_path.exists():
            logger.warning("env_file_not_found", path=str(env_path.absolute()))
            return

        try:
            lines = env_path.read_text(encoding="utf-8").splitlines()
            new_lines = []
            updated = False
            
            for line in lines:
                if line.startswith("APORTALS_AUTH="):
                    new_lines.append(f"APORTALS_AUTH={new_token}")
                    updated = True
                else:
                    new_lines.append(line)
            
            if not updated:
                # Append if not found
                new_lines.append(f"APORTALS_AUTH={new_token}")
            
            env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            logger.info("env_file_updated")
            
        except Exception as e:
            logger.error("env_file_update_failed", error=str(e))
