import os
import json
import shutil
import logging
import asyncio
import aiofiles
import inspect

from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from config import settings
from utils.db import get_current_mongo_client, MONGO_COLLECTION_MAPPING, load_from_mongodb, save_to_mongodb

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
    Safely load a JSON file or data from MongoDB if applicable.
    """
    if default is None:
        default = {}

    # Check if the filename maps to a MongoDB collection
    collection_name = MONGO_COLLECTION_MAPPING.get(os.path.basename(filename))
    if collection_name:
        try:
            client = get_current_mongo_client()
            data = load_from_mongodb(client, collection_name)
            if data:
                return data
            logger.info(f"No data found in MongoDB for collection: {collection_name}. Returning default.")
        except Exception as e:
            logger.error(f"Error loading data from MongoDB for {collection_name}: {e}")
        return default

    # Fallback to file system
    return await load_json_from_file(filename, default)

async def load_json_from_file(filename: str, default: Optional[Union[Dict, List]] = None) -> Union[Dict, List]:
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
    
    file_path = filename
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
        
async def save_json(filename: str, data: Union[Dict, List], pretty: bool = True, make_backup: bool = True) -> bool:
    """
    Safely save data to a JSON file or MongoDB if applicable.
    """
    # Check if the filename maps to a MongoDB collection
    collection_name = MONGO_COLLECTION_MAPPING.get(os.path.basename(filename))
    if collection_name:
        try:
            client = get_current_mongo_client()
            success = save_to_mongodb(client, collection_name, data)
            if success:
                logger.info(f"Data successfully saved to MongoDB collection: {collection_name}")
                return True
        except Exception as e:
            logger.error(f"Error saving data to MongoDB for {collection_name}: {e}")
        return False

    # Fallback to file system
    return await save_json_to_file(filename, data, pretty, make_backup)

async def save_json_to_file(filename: str, data: Union[Dict, List], pretty: bool = True, make_backup: bool = True) -> bool:
    """
    Safely save data to a JSON file with atomic write operations
    
    Args:
        filename: Path to the JSON file
        data: Data to save
        pretty: Whether to format the JSON with indentation
        
    Returns:
        True if successful, False otherwise
    """
    file_path = filename
    temp_path = f"{file_path}.tmp"
    backup_path = f"{file_path}.bak"
    lock = await get_file_lock(file_path)
    
    async with lock:
        try:
            # Create parent directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Create backup of existing file
            if os.path.exists(file_path) and make_backup:
                try:
                    shutil.copy2(file_path, backup_path)
                except Exception as backup_error:
                    logger.warning(f"Failed to create backup of {file_path}: {backup_error}")
            
            # Write to temporary file first
            json_str = json.dumps(data, indent=4 if pretty else None)
            async with aiofiles.open(temp_path, 'w') as f:
                await f.write(json_str)
            
            # Validate the written file
            try:
                async with aiofiles.open(temp_path, 'r') as f:
                    content = await f.read()
                # Make sure the JSON is valid
                json.loads(content)
            except Exception as validation_error:
                logger.error(f"Validation of written data failed: {validation_error}")
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return False
            
            # Replace the original file with the temporary one (atomic operation)
            os.replace(temp_path, file_path)
            return True
            
        except Exception as e:
            logger.error(f"Error saving data to {file_path}: {e}")
            # Clean up temporary file if it exists
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            return False