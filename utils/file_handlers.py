import os
import json
import shutil
import logging
import asyncio
import aiofiles

from datetime import datetime
from typing import Dict, List, Any, Optional, Union

logger = logging.getLogger("xof_calculator.file_handlers")

# Create data directory if it doesn't exist
os.makedirs("data", exist_ok=True)

# File locks to prevent concurrent access
_file_locks: Dict[str, asyncio.Lock] = {}

async def get_file_lock(filename: str) -> asyncio.Lock:
    """Get or create a lock for a specific file"""
    if filename not in _file_locks:
        _file_locks[filename] = asyncio.Lock()
    return _file_locks[filename]

async def load_json(filename: str, default: Optional[Union[Dict, List]] = None) -> Union[Dict, List]:
    """
    Safely load a JSON file
    
    Args:
        filename: Path to the JSON file
        default: Default value if file doesn't exist or is invalid
        
    Returns:
        The loaded JSON data or the default value
    """
    if default is None:
        default = {}
        
    file_path = f"data/{filename}"
    lock = await get_file_lock(file_path)
    
    async with lock:
        try:
            if not os.path.exists(file_path):
                logger.info(f"File {file_path} not found, returning default value")
                return default
                
            async with aiofiles.open(file_path, 'r') as f:
                content = await f.read()
                
            if not content.strip():
                logger.warning(f"File {file_path} is empty, returning default value")
                return default
                
            data = json.loads(content)
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON from {file_path}: {e}")
            
            # Create backup of corrupted file
            backup_file = f"{file_path}.corrupted.{datetime.now().strftime('%Y%m%d%H%M%S')}"
            try:
                shutil.copy2(file_path, backup_file)
                logger.info(f"Created backup of corrupted file: {backup_file}")
            except Exception as backup_error:
                logger.error(f"Failed to create backup of corrupted file: {backup_error}")
                
            return default
            
        except Exception as e:
            logger.error(f"Unexpected error loading {file_path}: {e}")
            return default