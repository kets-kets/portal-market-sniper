"""
Infrastructure: Collection Loader
"""
import json
from pathlib import Path
from typing import List
import structlog

from src.domain import Collection, CollectionId

logger = structlog.get_logger()

def load_collections_from_file(file_path: str) -> List[Collection]:
    """Loads collections from legacy JSON format"""
    path = Path(file_path)
    if not path.exists():
        logger.error("collections_file_not_found", path=str(path))
        return []
        
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        collections = []
        
        for name, info in data.items():
            if not isinstance(info, dict): 
                continue
                
            col_id = info.get("collection_id")
            short_name = info.get("short_name")
            models = info.get("models", [])
            
            if col_id and short_name:
                collections.append(Collection(
                    id=CollectionId(col_id),
                    name=name,
                    short_name=short_name,
                    models=models
                ))
                
        return collections
    except Exception as e:
        logger.error("collections_load_error", error=str(e))
        return []
