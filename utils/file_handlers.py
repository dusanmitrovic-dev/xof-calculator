import os
import json
import shutil
import logging
import asyncio
import aiofiles
import motor.motor_asyncio # Import motor
from bson import ObjectId # Needed for MongoDB _id if we want to handle it directly

from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from config import settings

logger = logging.getLogger("xof_calculator.file_handlers")

# Create data directory if it doesn't exist
os.makedirs("data", exist_ok=True)

# File locks to prevent concurrent file access
_file_locks: Dict[str, asyncio.Lock] = {}

# MongoDB Client (initialized once)
mongo_client = None
db = None

def get_mongo_client():
    """Initializes and returns the MongoDB client."""
    global mongo_client, db
    if mongo_client is None and settings.MONGODB_URI:
        try:
            mongo_client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGODB_URI)
            db = mongo_client[settings.DATABASE_NAME]
            logger.info(f"Successfully connected to MongoDB Atlas database: {settings.DATABASE_NAME}")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}. MongoDB features will be disabled.")
            mongo_client = None # Ensure it's None if connection fails
            db = None
    elif not settings.MONGODB_URI:
        logger.warning("MONGODB_URI not set in .env. MongoDB features will be disabled.")
    return mongo_client, db

async def get_file_lock(filename: str) -> asyncio.Lock:
    """Get or create a lock for a specific file"""
    if filename not in _file_locks:
        _file_locks[filename] = asyncio.Lock()
    return _file_locks[filename]

def _is_config_file(filename: str) -> bool:
    """Check if the filename corresponds to a guild configuration file."""
    return os.path.basename(filename) in settings.FILENAME_TO_MONGO_KEY

def _is_earnings_file(filename: str) -> bool:
    """Check if the filename is the primary earnings file."""
    return os.path.basename(filename) == settings.EARNINGS_FILE

def _extract_guild_id(filename: str) -> Optional[int]:
    """Extracts guild ID from the file path."""
    parts = filename.split(os.sep)
    # Assumes path like 'data/config/GUILD_ID/file.json' or 'data/earnings/GUILD_ID/file.json'
    if len(parts) >= 3 and parts[-3] in ["config", "earnings"] and parts[-2].isdigit():
        return int(parts[-2])
    logger.warning(f"Could not extract guild ID from path: {filename}")
    return None

def _serialize_mongo_doc(doc: Dict) -> Dict:
    """Convert MongoDB ObjectId to string for JSON serialization."""
    if doc and '_id' in doc:
        doc['_id'] = str(doc['_id'])
    return doc

# --- MongoDB Helper Functions ---

async def _load_guild_config_mongo(guild_id: int, config_key: str) -> Optional[Any]:
    """Loads a specific config key for a guild from MongoDB."""
    _, mdb = get_mongo_client()
    # --- FIX HERE ---
    # if not mdb: return None
    if mdb is None: return None
    # --- END FIX ---

    try:
        guild_doc = await mdb[settings.GUILD_CONFIG_COLLECTION].find_one({"guild_id": guild_id})
        if guild_doc and config_key in guild_doc:
            logger.debug(f"Loaded '{config_key}' for guild {guild_id} from MongoDB.")
            return guild_doc[config_key]
        logger.debug(f"No MongoDB data found for '{config_key}' for guild {guild_id}.")
        return None
    except Exception as e:
        logger.error(f"MongoDB Error loading '{config_key}' for guild {guild_id}: {e}")
        return None

async def _load_earnings_mongo(guild_id: int) -> Optional[Dict[str, List[Dict]]]:
    """Loads all earnings entries for a guild from MongoDB and formats them."""
    _, mdb = get_mongo_client()
    # --- FIX HERE ---
    # if not mdb: return None
    if mdb is None: return None
    # --- END FIX ---

    try:
        cursor = mdb[settings.EARNINGS_COLLECTION].find({"guild_id": guild_id})
        entries = await cursor.to_list(length=None) # Load all entries
        if not entries:
            logger.debug(f"No earnings data found in MongoDB for guild {guild_id}.")
            return None

        # Group entries by user_id (stored as string mentions like '<@USER_ID>')
        earnings_by_user = {}
        for entry in entries:
            user_key = entry.get("user_mention")
            if user_key:
                # Ensure _id is serialized if needed elsewhere, but usually removed for file format
                entry.pop('_id', None) # Remove mongo _id before saving to file
                if user_key not in earnings_by_user:
                    earnings_by_user[user_key] = []
                earnings_by_user[user_key].append(entry)

        logger.debug(f"Loaded {len(entries)} earnings entries for guild {guild_id} from MongoDB.")
        return earnings_by_user
    except Exception as e:
        logger.error(f"MongoDB Error loading earnings for guild {guild_id}: {e}")
        return None

async def _save_guild_config_mongo(guild_id: int, config_key: str, data: Any) -> bool:
    """Saves a specific config key for a guild to MongoDB."""
    _, mdb = get_mongo_client()
    # --- FIX HERE ---
    # if not mdb: return False
    if mdb is None: return False
    # --- END FIX ---

    try:
        update_result = await mdb[settings.GUILD_CONFIG_COLLECTION].update_one(
            {"guild_id": guild_id},
            {"$set": {config_key: data}},
            upsert=True # Create guild document if it doesn't exist
        )
        success = update_result.acknowledged and (update_result.modified_count > 0 or update_result.upserted_id is not None)
        if success:
            logger.debug(f"Saved '{config_key}' for guild {guild_id} to MongoDB.")
        else:
            logger.warning(f"MongoDB update for '{config_key}' (guild {guild_id}) not acknowledged or no changes made.")
        return success
    except Exception as e:
        logger.error(f"MongoDB Error saving '{config_key}' for guild {guild_id}: {e}")
        return False

async def _save_earnings_mongo(guild_id: int, data: Dict[str, List[Dict]]) -> bool:
    """Saves earnings data to MongoDB (Replaces existing entries for the guild)."""
    _, mdb = get_mongo_client()
    # --- FIX HERE ---
    # if not mdb: return False
    if mdb is None: return False
    # --- END FIX ---

    # ... (rest of the function remains the same) ...
    try:
        # 1. Delete existing entries for the guild
        delete_result = await mdb[settings.EARNINGS_COLLECTION].delete_many({"guild_id": guild_id})
        logger.debug(f"Deleted {delete_result.deleted_count} existing MongoDB earnings entries for guild {guild_id}.")

        # 2. Insert new entries
        all_entries_to_insert = []
        for user_mention, user_entries in data.items():
            for entry in user_entries:
                # Ensure guild_id and user_mention are in the entry for MongoDB
                entry_to_insert = entry.copy()
                entry_to_insert["guild_id"] = guild_id
                entry_to_insert["user_mention"] = user_mention
                # Remove potential ObjectId if loaded from Mongo previously and saving back
                entry_to_insert.pop('_id', None)
                all_entries_to_insert.append(entry_to_insert)

        if not all_entries_to_insert:
            logger.debug(f"No earnings data to insert into MongoDB for guild {guild_id}.")
            return True # Technically successful as there's nothing to save

        insert_result = await mdb[settings.EARNINGS_COLLECTION].insert_many(all_entries_to_insert)
        success = insert_result.acknowledged and len(insert_result.inserted_ids) == len(all_entries_to_insert)
        if success:
            logger.debug(f"Saved {len(all_entries_to_insert)} earnings entries for guild {guild_id} to MongoDB.")
        else:
            logger.error(f"MongoDB insert failed for earnings (guild {guild_id}). Acknowledged: {insert_result.acknowledged}")
        return success

    except Exception as e:
        logger.error(f"MongoDB Error saving earnings for guild {guild_id}: {e}")
        return False

# --- Modified Load/Save Functions ---

async def load_json(filename: str, default: Optional[Union[Dict, List]] = None) -> Union[Dict, List]:
    """
    Safely load JSON data, prioritizing MongoDB Atlas then falling back to local file.

    Args:
        filename: Path to the JSON file (used to determine guild ID and config type).
        default: Default value if data cannot be loaded from either source.

    Returns:
        The loaded data or the default value.
    """
    if default is None:
        default = {} # Ensure default is always a mutable type if expected

    guild_id = _extract_guild_id(filename)
    mongo_data = None

    # 1. Try loading from MongoDB
    if guild_id is not None:
        if _is_config_file(filename):
            config_key = settings.FILENAME_TO_MONGO_KEY.get(os.path.basename(filename))
            if config_key:
                mongo_data = await _load_guild_config_mongo(guild_id, config_key)
        elif _is_earnings_file(filename):
            mongo_data = await _load_earnings_mongo(guild_id)

    if mongo_data is not None:
        logger.info(f"Data for {os.path.basename(filename)} (guild {guild_id}) loaded from MongoDB.")
        return mongo_data # Return MongoDB data if successfully loaded

    # 2. Fallback to loading from local file if MongoDB fails or data not found
    logger.info(f"Falling back to loading {os.path.basename(filename)} (guild {guild_id}) from local file.")
    file_path = filename
    lock = await get_file_lock(file_path)

    async with lock:
        try:
            if not os.path.exists(file_path):
                logger.info(f"File {file_path} not found, returning default value")
                return default

            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()

            if not content.strip():
                logger.warning(f"File {file_path} is empty, returning default value")
                return default

            data = json.loads(content)
            return data

        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON from file {file_path}: {e}")
            # Create backup of corrupted file
            backup_file = f"{file_path}.corrupted.{datetime.now().strftime('%Y%m%d%H%M%S')}"
            try:
                if os.path.exists(file_path):
                    shutil.copy2(file_path, backup_file)
                    logger.info(f"Created backup of corrupted file: {backup_file}")
            except Exception as backup_error:
                logger.error(f"Failed to create backup of corrupted file: {backup_error}")
            return default

        except Exception as e:
            logger.error(f"Unexpected error loading file {file_path}: {e}")
            return default

async def save_json(filename: str, data: Union[Dict, List], pretty: bool = True, make_backup: bool = True) -> bool:
    """
    Safely save data to a local JSON file and attempt to save to MongoDB Atlas.

    Args:
        filename: Path to the JSON file.
        data: Data to save.
        pretty: Whether to format the JSON with indentation for the file.
        make_backup: Whether to create a local file backup (.bak).

    Returns:
        True if the *file* save was successful, False otherwise. MongoDB save errors are logged.
    """
    file_path = filename
    temp_path = f"{file_path}.tmp"
    backup_path = f"{file_path}.bak"
    lock = await get_file_lock(file_path)
    file_save_successful = False

    # --- File Save Logic ---
    async with lock:
        try:
            # Ensure parent directory exists for the file
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # Create local backup of existing file
            if os.path.exists(file_path) and make_backup:
                try:
                    shutil.copy2(file_path, backup_path)
                except Exception as backup_error:
                    logger.warning(f"Failed to create local backup of {file_path}: {backup_error}")

            # Write to temporary file first
            # Ensure data is serializable before writing
            try:
                json_str = json.dumps(data, indent=4 if pretty else None, ensure_ascii=False)
            except TypeError as te:
                logger.error(f"Data for {file_path} is not JSON serializable: {te}. Data: {str(data)[:200]}...")
                # Attempt to clean problematic types (like ObjectId if accidentally included)
                # This is a basic attempt; more robust serialization might be needed
                cleaned_data = json.loads(json.dumps(data, default=str))
                json_str = json.dumps(cleaned_data, indent=4 if pretty else None, ensure_ascii=False)
                logger.warning("Attempted to clean data for JSON serialization.")

            async with aiofiles.open(temp_path, 'w', encoding='utf-8') as f:
                await f.write(json_str)

            # Validate the written temporary file
            try:
                async with aiofiles.open(temp_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                json.loads(content) # Check if it's valid JSON
            except Exception as validation_error:
                logger.error(f"Validation of written temp file {temp_path} failed: {validation_error}")
                if os.path.exists(temp_path): 
                    os.remove(temp_path)
                return False # File save failed validation

            # Replace the original file with the temporary one (atomic on most OS)
            os.replace(temp_path, file_path)
            file_save_successful = True
            logger.info(f"Successfully saved data to local file: {file_path}")

        except Exception as e:
            logger.error(f"Error saving data to file {file_path}: {e}")
            # Clean up temporary file if it exists
            if os.path.exists(temp_path):
                try: 
                    os.remove(temp_path)
                except OSError: 
                    pass
            file_save_successful = False # Explicitly set file save as failed

    # --- MongoDB Save Logic (Attempt even if file save failed? No, only if file save succeeded) ---
    if file_save_successful:
        guild_id = _extract_guild_id(filename)
        mongo_save_successful = False
        if guild_id is not None:
            if _is_config_file(filename):
                config_key = settings.FILENAME_TO_MONGO_KEY.get(os.path.basename(filename))
                if config_key:
                    mongo_save_successful = await _save_guild_config_mongo(guild_id, config_key, data)
            elif _is_earnings_file(filename):
                # Ensure data is in the expected format for earnings (Dict[str, List[Dict]])
                if isinstance(data, dict):
                    mongo_save_successful = await _save_earnings_mongo(guild_id, data)
                else:
                    logger.error(f"Attempted to save earnings to MongoDB with incorrect data type for guild {guild_id}. Expected Dict, got {type(data)}.")
                    mongo_save_successful = False

            if not mongo_save_successful:
                 logger.error(f"Failed to save corresponding data for {os.path.basename(filename)} (guild {guild_id}) to MongoDB.")
            # else: # No need to log success here, it's logged in the helper

    return file_save_successful # Return status of the file save operation

# Ensure MongoDB client is initialized when the module loads
get_mongo_client()