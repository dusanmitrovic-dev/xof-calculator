# --- START OF FILE file_handlers.py ---

import os
import json
import shutil
import logging
import asyncio
import aiofiles
import motor.motor_asyncio
# Make sure 'ReplaceOne' or 'operations' is NOT imported from motor.motor_asyncio here
# Example: Remove or comment out -> # from motor.motor_asyncio import operations

from bson import ObjectId
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
    base_name = os.path.basename(filename)
    # Exclude backup files explicitly if they share base names
    if base_name.endswith(".bak") or base_name.endswith(".tmp") or ".corrupted." in base_name:
        return False
    return base_name in settings.FILENAME_TO_MONGO_KEY

def _is_earnings_file(filename: str) -> bool:
    """Check if the filename is the primary earnings file."""
    base_name = os.path.basename(filename)
     # Exclude backup files explicitly if they share base names
    if base_name.endswith(".bak") or base_name.endswith(".tmp") or ".corrupted." in base_name:
        return False
    return base_name == settings.EARNINGS_FILE

def _extract_guild_id(filename: str) -> Optional[int]:
    """Extracts guild ID from the file path."""
    # Clean the path to handle potential relative paths or odd separators
    norm_path = os.path.normpath(filename)
    parts = norm_path.split(os.sep)
    # Try finding 'config' or 'earnings' and expect guild ID after it
    try:
        if 'config' in parts:
            config_index = parts.index('config')
            if len(parts) > config_index + 1 and parts[config_index + 1].isdigit():
                return int(parts[config_index + 1])
        if 'earnings' in parts:
            earnings_index = parts.index('earnings')
            if len(parts) > earnings_index + 1 and parts[earnings_index + 1].isdigit():
                return int(parts[earnings_index + 1])
    except ValueError: # .index() fails if 'config'/'earnings' not found
        pass
    except IndexError: # parts aren't long enough after finding the directory
        pass

    logger.debug(f"Could not extract guild ID from path: {filename}")
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
    if mdb is None:
        logger.debug(f"MongoDB client not available, cannot load '{config_key}' for guild {guild_id}.")
        return None

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
    if mdb is None:
        logger.debug(f"MongoDB client not available, cannot load earnings for guild {guild_id}.")
        return None

    try:
        cursor = mdb[settings.EARNINGS_COLLECTION].find({"guild_id": guild_id})
        entries = await cursor.to_list(length=None) # Load all entries
        if not entries:
            logger.debug(f"No earnings data found in MongoDB for guild {guild_id}.")
            return {} # Return empty dict instead of None if no entries found

        # Group entries by user_id (stored as string mentions like '<@USER_ID>')
        earnings_by_user = {}
        for entry in entries:
            user_key = entry.get("user_mention")
            if user_key:
                # Ensure _id is serialized if needed elsewhere, but usually removed for file format
                entry.pop('_id', None) # Remove mongo _id before saving to file
                 # Add back the 'id' field if it was stored separately in Mongo
                if 'sale_id' in entry:
                    entry['id'] = entry.pop('sale_id')

                if user_key not in earnings_by_user:
                    earnings_by_user[user_key] = []
                earnings_by_user[user_key].append(entry)

        logger.debug(f"Loaded {len(entries)} earnings entries for guild {guild_id} from MongoDB.")
        return earnings_by_user
    except Exception as e:
        logger.error(f"MongoDB Error loading earnings for guild {guild_id}: {e}")
        return None # Return None on error

async def _save_guild_config_mongo(guild_id: int, config_key: str, data: Any) -> bool:
    """Saves a specific config key for a guild to MongoDB."""
    _, mdb = get_mongo_client()
    if mdb is None:
        logger.warning(f"MongoDB client not available, cannot save '{config_key}' for guild {guild_id}.")
        return False

    try:
        update_result = await mdb[settings.GUILD_CONFIG_COLLECTION].update_one(
            {"guild_id": guild_id},
            {"$set": {config_key: data}},
            upsert=True # Create guild document if it doesn't exist
        )
        # Check acknowledged and if something was actually changed or inserted
        success = update_result.acknowledged and (update_result.modified_count > 0 or update_result.upserted_id is not None or update_result.matched_count > 0)
        if success:
            # Check if it was just a match with no modification (data was identical)
            if update_result.matched_count > 0 and update_result.modified_count == 0 and update_result.upserted_id is None:
                 logger.debug(f"Data for '{config_key}' (guild {guild_id}) in MongoDB is already up-to-date.")
                 # Consider this a success as the state is consistent
            else:
                logger.info(f"Saved '{config_key}' for guild {guild_id} to MongoDB.")
        else:
             # Log detailed update result if save wasn't clearly successful or data was identical
            logger.warning(f"MongoDB update for '{config_key}' (guild {guild_id}) potentially didn't save. Result: {update_result.raw_result}")
            # Return False if not acknowledged, otherwise consider it okay if matched/modified/upserted
            return update_result.acknowledged
        return True # Return True if acknowledged and matched/modified/upserted
    except Exception as e:
        logger.error(f"MongoDB Error saving '{config_key}' for guild {guild_id}: {e}", exc_info=True)
        return False

async def _save_earnings_mongo(guild_id: int, data: Dict[str, List[Dict]]) -> bool:
    """Saves earnings data to MongoDB (Replaces existing entries for the guild)."""
    _, mdb = get_mongo_client()
    if mdb is None:
        logger.warning(f"MongoDB client not available. Skipping MongoDB save for earnings (guild {guild_id}).")
        return False # Indicate Mongo save didn't happen

    try:
        collection = mdb[settings.EARNINGS_COLLECTION]

        # 1. Prepare the list of documents to insert
        all_entries_to_insert = []
        for user_mention, user_entries in data.items():
            # Basic validation of input structure
            if not isinstance(user_entries, list):
                logger.error(f"Invalid data format for user {user_mention} in guild {guild_id}. Expected list, got {type(user_entries)}. Skipping Mongo save.")
                return False # Stop if data structure is wrong

            for entry in user_entries:
                if not isinstance(entry, dict):
                    logger.error(f"Invalid entry format for user {user_mention} in guild {guild_id}. Expected dict, got {type(entry)}. Skipping Mongo save.")
                    return False # Stop if data structure is wrong

                # Create a copy to avoid modifying original data
                entry_to_insert = entry.copy()
                # Ensure guild_id and user_mention are added for MongoDB querying
                entry_to_insert["guild_id"] = guild_id
                entry_to_insert["user_mention"] = user_mention
                # Remove MongoDB's internal _id if it exists (e.g., from a previous load)
                entry_to_insert.pop('_id', None)
                all_entries_to_insert.append(entry_to_insert)

        # 2. Delete existing entries for the guild *before* inserting new ones
        # This ensures atomicity at the operation level (replace)
        delete_result = await collection.delete_many({"guild_id": guild_id})
        logger.debug(f"Deleted {delete_result.deleted_count} existing MongoDB earnings entries for guild {guild_id} before inserting new data.")

        # 3. Insert the new batch if there are any entries to insert
        if all_entries_to_insert:
            insert_result = await collection.insert_many(all_entries_to_insert, ordered=False) # ordered=False might be slightly faster
            success = insert_result.acknowledged and len(insert_result.inserted_ids) == len(all_entries_to_insert)
            if success:
                logger.debug(f"Successfully inserted {len(all_entries_to_insert)} earnings entries for guild {guild_id} into MongoDB.")
            else:
                logger.error(f"MongoDB insert failed or incomplete for earnings (guild {guild_id}). Acknowledged: {insert_result.acknowledged}, Inserted: {len(insert_result.inserted_ids)}/{len(all_entries_to_insert)}")
            return success
        else:
            # If there was nothing to insert, the operation is still considered successful
            # as the state matches the input (empty earnings for the guild).
            logger.debug(f"No new earnings entries to insert for guild {guild_id} after deletion.")
            return True

    except Exception as e:
        # Log the full traceback for better debugging
        logger.error(f"MongoDB Error saving/syncing earnings for guild {guild_id}: {e}", exc_info=True)
        return False

# --- Modified Load/Save Functions ---

async def load_json(
    filename: str,
    default: Optional[Union[Dict, List]] = None,
    force_file_load: bool = False # New flag
) -> Union[Dict, List]:
    """
    Safely load JSON data, prioritizing MongoDB Atlas then falling back to local file,
    unless force_file_load is True.

    Args:
        filename: Path to the JSON file (used to determine guild ID and config type).
        default: Default value if data cannot be loaded from either source.
        force_file_load: If True, skip MongoDB and load directly from the file.

    Returns:
        The loaded data or the default value.
    """
    if default is None:
        # Use list default for files expected to be lists, else dict
        base_name = os.path.basename(filename)
        if base_name in [settings.SHIFT_DATA_FILE, settings.PERIOD_DATA_FILE, settings.MODELS_DATA_FILE, settings.BONUS_RULES_FILE]:
             default = []
        else:
             default = {}


    guild_id = _extract_guild_id(filename)
    mongo_data = None

    # 1. Try loading from MongoDB (skip if force_file_load is True)
    if not force_file_load and guild_id is not None:
        if _is_config_file(filename):
            config_key = settings.FILENAME_TO_MONGO_KEY.get(os.path.basename(filename))
            if config_key:
                mongo_data = await _load_guild_config_mongo(guild_id, config_key)
        elif _is_earnings_file(filename):
            mongo_data = await _load_earnings_mongo(guild_id) # Returns {} if no entries, None on error

    if not force_file_load and mongo_data is not None: # mongo_data could be {} for empty earnings
        # Ensure structure matches default type if empty dict/list returned
        if isinstance(mongo_data, dict) and isinstance(default, list):
             logger.warning(f"MongoDB returned dict for {filename} but list default expected. Returning default.")
             mongo_data = default
        elif isinstance(mongo_data, list) and isinstance(default, dict):
             logger.warning(f"MongoDB returned list for {filename} but dict default expected. Returning default.")
             mongo_data = default

        logger.info(f"Data for {os.path.basename(filename)} (guild {guild_id}) loaded from MongoDB.")
        return mongo_data # Return MongoDB data if successfully loaded (or empty if applicable)
    elif not force_file_load and guild_id is not None:
         logger.info(f"No data found in MongoDB for {os.path.basename(filename)} (guild {guild_id}), or MongoDB disabled/error.")


    # 2. Fallback to loading from local file (or load directly if force_file_load is True)
    if force_file_load:
        logger.info(f"Forcing load of {os.path.basename(filename)} (guild {guild_id}) from local file.")
    else:
        logger.info(f"Falling back to loading {os.path.basename(filename)} (guild {guild_id}) from local file.")

    file_path = filename
    lock = await get_file_lock(file_path)

    async with lock:
        try:
            if not os.path.exists(file_path):
                logger.info(f"File {file_path} not found, returning default value: {default}")
                # Before returning default, try to save the default value to create the file
                # This helps initialize files if they are missing entirely
                # But only do this if we didn't intend to force file load (as file is missing)
                if not force_file_load:
                    logger.info(f"Attempting to create missing file {file_path} with default data.")
                    # Use save_json internally, but disable mongo sync for this initial creation
                    await save_json(file_path, default, make_backup=False, sync_to_mongo=False)
                return default

            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()

            if not content.strip():
                logger.warning(f"File {file_path} is empty, returning default value: {default}")
                return default

            data = json.loads(content)
             # Validate data type against default
            if type(data) != type(default):
                logger.warning(f"Loaded data type ({type(data)}) from {file_path} does not match default type ({type(default)}). Returning default.")
                return default
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
                logger.error(f"Failed to create backup of corrupted file {file_path}: {backup_error}")
            return default

        except Exception as e:
            logger.error(f"Unexpected error loading file {file_path}: {e}", exc_info=True)
            return default

async def save_json(
    filename: str,
    data: Union[Dict, List],
    pretty: bool = True,
    make_backup: bool = True,
    sync_to_mongo: bool = True # New flag
) -> bool:
    """
    Safely save data to a local JSON file and optionally save to MongoDB Atlas.

    Args:
        filename: Path to the JSON file.
        data: Data to save.
        pretty: Whether to format the JSON with indentation for the file.
        make_backup: Whether to create a local file backup (.bak).
        sync_to_mongo: If True, attempt to save the data to MongoDB as well.

    Returns:
        True if the *file* save was successful, False otherwise.
        MongoDB sync status is logged but doesn't affect the return value directly,
        unless sync_to_mongo is True and the sync *fails*, in which case it might
        be useful to indicate a partial success (logged).
        **Correction**: Let's return True only if *both* file save and requested mongo sync succeed.
    """
    file_path = filename
    temp_path = f"{file_path}.tmp"
    backup_path = f"{file_path}.bak"
    lock = await get_file_lock(file_path)
    file_save_successful = False
    mongo_save_successful = True # Default to True if sync is not requested

    async with lock:
        try:
            # Ensure parent directory exists for the file
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # Create local backup of existing file
            if os.path.exists(file_path) and make_backup:
                try:
                    # Check if data is identical to current file content before backing up/writing
                    async with aiofiles.open(file_path, 'r', encoding='utf-8') as f_read:
                         current_content = await f_read.read()
                    # Compare normalized JSON strings to avoid whitespace/indentation issues
                    current_data = json.loads(current_content) if current_content.strip() else None
                    new_data_str = json.dumps(data, sort_keys=True)
                    current_data_str = json.dumps(current_data, sort_keys=True) if current_data else None

                    if new_data_str == current_data_str:
                         logger.debug(f"Data for {file_path} hasn't changed. Skipping file write and backup.")
                         file_save_successful = True # Consider it successful as state is consistent
                         # Skip MongoDB sync as well if data hasn't changed? Debatable. Let's still sync.
                         # mongo_save_successful = True
                         # return True # Exit early

                    else:
                        # Data has changed, proceed with backup
                        shutil.copy2(file_path, backup_path)
                        logger.debug(f"Created backup for {file_path} as data changed.")

                except json.JSONDecodeError:
                     logger.warning(f"Could not decode current JSON in {file_path} for comparison. Proceeding with backup.")
                     try: shutil.copy2(file_path, backup_path)
                     except Exception as backup_error_fallback: logger.error(f"Fallback backup failed: {backup_error_fallback}")
                except Exception as backup_error:
                    logger.warning(f"Failed to create local backup of {file_path}: {backup_error}")

            # Write to temporary file first if file doesn't exist OR data has changed
            if not file_save_successful: # If we didn't skip due to identical data
                try:
                    # Ensure data is serializable before writing
                    json_str = json.dumps(data, indent=4 if pretty else None, ensure_ascii=False, default=str) # Use default=str for robustness
                except TypeError as te:
                    logger.error(f"Data for {file_path} is not JSON serializable even with default=str: {te}. Data: {str(data)[:200]}...")
                    return False # Cannot proceed if data cannot be serialized

                async with aiofiles.open(temp_path, 'w', encoding='utf-8') as f:
                    await f.write(json_str)

                # Validate the written temporary file
                try:
                    async with aiofiles.open(temp_path, 'r', encoding='utf-8') as f_validate:
                        content = await f_validate.read()
                    json.loads(content) # Check if it's valid JSON
                except Exception as validation_error:
                    logger.error(f"Validation of written temp file {temp_path} failed: {validation_error}")
                    if os.path.exists(temp_path): os.remove(temp_path)
                    return False # File save failed validation

                # Replace the original file with the temporary one (atomic on most OS)
                os.replace(temp_path, file_path)
                file_save_successful = True
                logger.info(f"Successfully saved data to local file: {file_path}")

        except Exception as e:
            logger.error(f"Error saving data to file {file_path}: {e}", exc_info=True)
            # Clean up temporary file if it exists
            if os.path.exists(temp_path):
                try: os.remove(temp_path)
                except OSError: pass
            file_save_successful = False # Explicitly set file save as failed

    # --- MongoDB Save Logic (Conditional) ---
    if file_save_successful and sync_to_mongo:
        guild_id = _extract_guild_id(filename)
        if guild_id is not None:
            mongo_save_successful = False # Reset for this attempt
            if _is_config_file(filename):
                config_key = settings.FILENAME_TO_MONGO_KEY.get(os.path.basename(filename))
                if config_key:
                    mongo_save_successful = await _save_guild_config_mongo(guild_id, config_key, data)
                else:
                    logger.warning(f"No MongoDB config key found for filename: {os.path.basename(filename)}. Skipping MongoDB sync.")
                    mongo_save_successful = True # No sync needed, so not a failure
            elif _is_earnings_file(filename):
                # Ensure data is in the expected format for earnings (Dict[str, List[Dict]])
                if isinstance(data, dict):
                    mongo_save_successful = await _save_earnings_mongo(guild_id, data)
                else:
                    logger.error(f"Attempted to save earnings to MongoDB with incorrect data type for guild {guild_id}. Expected Dict, got {type(data)}.")
                    mongo_save_successful = False
            else:
                 logger.debug(f"File {filename} is not a designated config or earnings file. Skipping MongoDB sync.")
                 mongo_save_successful = True # No sync needed, so not a failure

            if not mongo_save_successful:
                 logger.error(f"Failed to save corresponding data for {os.path.basename(filename)} (guild {guild_id}) to MongoDB.")
        else:
            logger.warning(f"Could not extract Guild ID from {filename}. Skipping MongoDB sync.")
            mongo_save_successful = True # Cannot sync without ID, not a failure of the operation itself

    # Return True only if file save succeeded AND (mongo sync wasn't requested OR mongo sync succeeded)
    final_success = file_save_successful and mongo_save_successful
    if file_save_successful and sync_to_mongo and not mongo_save_successful:
         logger.warning(f"Operation for {filename} succeeded locally but failed MongoDB sync.")
         # Depending on strictness, you might return False here. Let's return False for stricter consistency.
         final_success = False

    return final_success


async def force_sync_to_mongo(filename: str) -> bool:
    """
    Loads data from the local file and forces a save to MongoDB.
    Useful after a local file restore.

    Args:
        filename: The path to the local file to sync.

    Returns:
        True if the MongoDB sync was successful, False otherwise.
    """
    logger.info(f"Attempting to force sync local file {filename} to MongoDB...")
    # Load directly from the file, skipping MongoDB check
    local_data = await load_json(filename, force_file_load=True)

    # Check if loaded data is the default value, potentially indicating an issue
    # (e.g., file was corrupted or empty and load_json returned default)
    # Need to compare against the correct default type
    default_val = [] if os.path.basename(filename) in [settings.SHIFT_DATA_FILE, settings.PERIOD_DATA_FILE, settings.MODELS_DATA_FILE, settings.BONUS_RULES_FILE] else {}
    if local_data == default_val:
         # Check if the file actually exists and is empty/corrupt or just missing
         if not os.path.exists(filename):
              logger.warning(f"Cannot force sync {filename}: File does not exist.")
              return False
         else:
              # File exists but loaded as default, likely empty or corrupt.
              # Decide whether to sync the default value or abort. Let's abort.
              logger.warning(f"Cannot force sync {filename}: Loaded data matches default, possibly empty/corrupt file. Aborting sync.")
              # You could choose to sync the default value here if desired:
              # pass

    # Proceed with sync if data seems valid
    guild_id = _extract_guild_id(filename)
    if guild_id is None:
        logger.error(f"Cannot force sync {filename}: Could not extract Guild ID.")
        return False

    mongo_sync_successful = False
    if _is_config_file(filename):
        config_key = settings.FILENAME_TO_MONGO_KEY.get(os.path.basename(filename))
        if config_key:
            mongo_sync_successful = await _save_guild_config_mongo(guild_id, config_key, local_data)
        else:
            logger.error(f"Cannot force sync {filename}: No MongoDB config key found.")
    elif _is_earnings_file(filename):
        if isinstance(local_data, dict):
            mongo_sync_successful = await _save_earnings_mongo(guild_id, local_data)
        else:
            logger.error(f"Cannot force sync {filename}: Loaded earnings data is not a dict ({type(local_data)}).")
    else:
        logger.warning(f"Cannot force sync {filename}: Not a recognized config or earnings file.")
        return False # Or True if "not needing sync" is success? Let's say False.

    if mongo_sync_successful:
        logger.info(f"Successfully force-synced {filename} to MongoDB.")
    else:
        logger.error(f"Failed to force-sync {filename} to MongoDB.")

    return mongo_sync_successful


# Ensure MongoDB client is initialized when the module loads
get_mongo_client()

# --- END OF FILE file_handlers.py ---