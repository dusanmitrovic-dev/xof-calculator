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
    Safely load a JSON file or data from MongoDB if applicable.
    """
    if default is None:
        default = {}

    # Extract the guild ID from the file path
    guild_id = os.path.basename(os.path.dirname(filename))

    # Determine the MongoDB collection or key
    collection_name = MONGO_COLLECTION_MAPPING.get(os.path.basename(filename))

    print("================================")
    print(f"Loading data from {filename} with collection name: {collection_name}")
    print(f"Extracted guild ID: {guild_id}")
    print("================================")

    if collection_name:
        try:
            client = get_current_mongo_client()
            db = client.get_database()

            # Handle earnings collection
            if collection_name == "earnings":
                # Load all earnings for the guild
                data = list(db[collection_name].find({"guild_id": guild_id}))
                # Remove MongoDB-specific fields like `_id`
                for entry in data:
                    entry.pop("_id", None)

                    # Normalize the date format
                    try:
                        entry["date"] = normalize_date_format(entry["date"])
                    except (ValueError, TypeError) as e:
                        logger.error(f"Skipping entry with invalid date: {entry}. Error: {e}")
                        continue

                # Transform the list into a dictionary grouped by `user_mention`
                earnings_dict = {}
                for entry in data:
                    sender = entry.get("user_mention", "unknown_sender")
                    if sender not in earnings_dict:
                        earnings_dict[sender] = []
                    earnings_dict[sender].append(entry)

                print("================================")
                print(f"Loaded {len(data)} earnings entries for guild {guild_id} from MongoDB.")
                print(f"Transformed Data: {earnings_dict}")
                print("================================")

                if earnings_dict:
                    logger.info(f"Data successfully loaded and transformed from MongoDB collection: {collection_name}")
                    return earnings_dict

            logger.info(f"No data found in MongoDB for collection: {collection_name}. Returning default.")
        except Exception as e:
            logger.error(f"Error loading data from MongoDB for {collection_name}: {e}")

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
    Save data to both a JSON file and MongoDB if applicable.
    """
    # Extract the guild ID from the file path
    guild_id = os.path.basename(os.path.dirname(filename))

    # Determine the MongoDB collection or key
    collection_name = MONGO_COLLECTION_MAPPING.get(os.path.basename(filename))

    print("================================")
    print(f"Saving data to {filename} with collection name: {collection_name}")
    print(f"Extracted guild ID: {guild_id}")
    print("================================")

    # Initialize success flags
    db_success = False
    file_success = False

    # Save to MongoDB if applicable
    if collection_name:
        try:
            client = get_current_mongo_client()
            db = client.get_database()

            # Handle earnings collection
            if collection_name == "earnings":
                # Ensure the entry has the guild_id
                if isinstance(data, dict):
                    # Validate required fields
                    required_fields = [
                        "id", "date", "total_cut", "gross_revenue", "period",
                        "shift", "role", "models", "hours_worked", "user_mention"
                    ]
                    missing_fields = [field for field in required_fields if not data.get(field)]
                    if missing_fields:
                        logger.error(f"Cannot save earnings entry. Missing or invalid fields: {missing_fields}")
                        return False

                    # Transform the data to match the schema
                    transformed_data = {
                        "id": data.get("id"),
                        "guild_id": guild_id,
                        "date": data.get("date"),
                        "total_cut": data.get("total_cut"),
                        "gross_revenue": data.get("gross_revenue"),
                        "period": data.get("period"),
                        "shift": data.get("shift"),
                        "role": data.get("role"),
                        "models": data.get("models") if isinstance(data.get("models"), list) else [data.get("models")],
                        "hours_worked": data.get("hours_worked"),
                        "user_mention": data.get("user_mention")
                    }

                    # Insert the transformed data into MongoDB
                    db[collection_name].insert_one(transformed_data)
                    logger.info(f"Single earning entry successfully added to MongoDB collection: {collection_name}")
                else:
                    logger.error("Invalid data type for earnings. Expected a single dictionary entry.")
                    return False

                db_success = True

        except Exception as e:
            logger.error(f"Error saving data to MongoDB for {collection_name}: {e}")

    # Save to file system
    try:
        file_success = await save_json_to_file(filename, data, pretty, make_backup)
        if file_success:
            logger.info(f"Data successfully saved to file: {filename}")
    except Exception as e:
        logger.error(f"Error saving data to file: {filename}: {e}")

    # Return True if either operation succeeded
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