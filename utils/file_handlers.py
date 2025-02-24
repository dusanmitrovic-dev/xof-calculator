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