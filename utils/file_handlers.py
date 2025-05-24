from calendar import c
import os
import json
import shutil
import logging
import asyncio
import aiofiles
import inspect

from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from utils.db import get_current_mongo_client, MONGO_COLLECTION_MAPPING

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

def normalize_date_format(date_str: str) -> str:
    """
    Normalize the date format to dd/mm/yyyy.

    Args:
        date_str: The date string to normalize.

    Returns:
        The normalized date string in dd/mm/yyyy format.

    Raises:
        ValueError: If the date format is invalid.
    """
    try:
        # Try parsing the date in various common formats
        parsed_date = datetime.strptime(date_str, "%d/%m/%Y")
        return parsed_date.strftime("%d/%m/%Y")
    except ValueError:
        try:
            parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
            return parsed_date.strftime("%d/%m/%Y")
        except ValueError:
            raise ValueError(f"Invalid date format: {date_str}. Use dd/mm/yyyy.")

async def load_json(filename: str, default: Optional[Union[Dict, List]] = None) -> Union[Dict, List]:
    """
    Load data from a JSON file or MongoDB if applicable.
    """
    print(f"=================================================================")
    print(f"Starting load_json for file: {filename}")
    if default is None:
        default = {}
    print(f"Default value: {default}")

    guild_id = os.path.basename(os.path.dirname(filename))
    collection_name = MONGO_COLLECTION_MAPPING.get(os.path.basename(filename))
    print(f"Determined guild_id: {guild_id}, collection_name: {collection_name}")

    if collection_name:
        try:
            client = get_current_mongo_client()
            db = client.get_database()
            print(f"Connected to MongoDB for collection: {collection_name}")

            if collection_name == "earnings":
                data = list(db[collection_name].find({"guild_id": guild_id}))
                print(f"Fetched data from MongoDB: {data}")
                for entry in data:
                    entry.pop("_id", None)
                    entry["models"] = entry["models"] if isinstance(entry["models"], list) else [entry["models"]]
                    try:
                        entry["date"] = normalize_date_format(entry["date"])
                    except ValueError as e:
                        logger.error(f"Skipping entry with invalid date: {entry}. Error: {e}")
                        continue

                earnings_dict = {}
                for entry in data:
                    user_mention = entry.get("user_mention", "unknown_sender")
                    if user_mention not in earnings_dict:
                        earnings_dict[user_mention] = []
                    earnings_dict[user_mention].append(entry)

                if earnings_dict:
                    logger.info(f"Data successfully loaded from MongoDB collection: {collection_name}")
                    return earnings_dict

            elif collection_name != "earnings":
                # Fetch the guild configuration document
                guild_config = db["guild_configs"].find_one({"guild_id": guild_id})
                if guild_config:
                    logger.debug(f"Fetched guild configuration: {guild_config}")
                    if collection_name in guild_config:
                        logger.info(f"Data successfully loaded for field: {collection_name}")
                        return guild_config[collection_name]
                    else:
                        logger.warning(f"Field '{collection_name}' not found in guild configuration for guild_id: {guild_id}")
                        return default
                else:
                    logger.warning(f"No guild configuration found for guild_id: {guild_id}")
                    return default

            else:
                print(f"Collection {collection_name} is not handled explicitly.")
        except Exception as e:
            logger.error(f"Error loading data from MongoDB for {collection_name}: {e}")

    print(f"Falling back to loading data from file: {filename}")
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
    Save data to both a JSON file and MongoDB if applicable.
    """
    print(f"=================================================================")
    print(f"Starting save_json for file: {filename}")
    print(f"Data to save: {data}")
    print(f"Pretty: {pretty}, Make Backup: {make_backup}")

    guild_id = os.path.basename(os.path.dirname(filename))
    collection_name = MONGO_COLLECTION_MAPPING.get(os.path.basename(filename))
    print(f"Determined guild_id: {guild_id}, collection_name: {collection_name}")

    db_success = False
    file_success = False

    if collection_name:
        try:
            client = get_current_mongo_client()
            db = client.get_database()
            print(f"Connected to MongoDB for collection: {collection_name}")

            if collection_name == "earnings":
                if isinstance(data, dict):
                    for user_mention, entries in data.items():
                        print(f"Processing user_mention: {user_mention}, entries: {entries}")
                        for entry in entries:
                            # Add the user_mention field to the entry
                            entry["user_mention"] = user_mention  # Ensure this field is present

                            # Validate and transform data
                            entry["guild_id"] = guild_id
                            entry["models"] = entry["models"] if isinstance(entry["models"], list) else [entry["models"]]
                            required_fields = ["id", "date", "total_cut", "gross_revenue", "period", "shift", "role", "models", "hours_worked", "user_mention"]
                            missing_fields = [field for field in required_fields if field not in entry]
                            if missing_fields:
                                logger.error(f"Cannot save earnings entry. Missing fields: {missing_fields}")
                                continue

                            print(f"Upserting entry into MongoDB: {entry}")
                            # Upsert into MongoDB
                            db[collection_name].update_one(
                                {"id": entry["id"], "guild_id": guild_id},
                                {"$set": entry},
                                upsert=True
                            )
                    db_success = True
                else:
                    logger.error("Invalid data type for earnings. Expected a dictionary grouped by user_mention.")
            else:
                print(f"Collection {collection_name} is not handled explicitly.")
        except Exception as e:
            logger.error(f"Error saving data to MongoDB for {collection_name}: {e}")

    try:
        print(f"Saving data to file: {filename}")
        file_success = await save_json_to_file(filename, data, pretty, make_backup)
        if file_success:
            logger.info(f"Data successfully saved to file: {filename}")
    except Exception as e:
        logger.error(f"Error saving data to file: {filename}: {e}")

    print(f"Save result - DB Success: {db_success}, File Success: {file_success}")
    return db_success or file_success

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