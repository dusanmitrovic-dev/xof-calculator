import logging
import inspect

from pymongo import MongoClient
from contextvars import ContextVar
from typing import Dict, List, Optional, Union

logger = logging.getLogger("xof_calculator.db")

# Context variable to store the current MongoDB client
current_mongo_client: ContextVar[MongoClient] = ContextVar("current_mongo_client", default=None)

def set_current_mongo_client(client: MongoClient):
    """
    Set the current MongoDB client in the context.
    """
    current_mongo_client.set(client)

def get_current_mongo_client() -> MongoClient:
    """
    Get the current MongoDB client from the context.
    """
    client = current_mongo_client.get()
    if not client:
        raise RuntimeError("No MongoDB client is set for the current context.")
    return client

MONGO_COLLECTION_MAPPING = {
    "role_percentages.json": "roles",
    "shift_config.json": "shifts",
    "period_config.json": "periods",
    "models_config.json": "models",
    "bonus_rules.json": "bonus_rules",
    "display_settings.json": "display_settings",
    "commission_settings.json": "commission_settings",
    "earnings.json": "earnings",
}

def connect_to_mongodb(connection_string: str) -> Optional[MongoClient]:
    """
    Connect to MongoDB using the provided connection string.

    Args:
        connection_string (str): The MongoDB connection string.

    Returns:
        MongoClient: A MongoClient instance connected to the database, or None if connection fails.
    """
    try:
        client = MongoClient(connection_string)
        # Test the connection
        client.admin.command('ping')
        logger.info("Connected to MongoDB successfully.")
        return client
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        return None

def save_to_mongodb(client: MongoClient, collection_name: str, data: Union[Dict, List]) -> bool:
    """
    Save data to a MongoDB collection.

    Args:
        client: MongoClient instance.
        collection_name: Name of the MongoDB collection.
        data: Data to save (must be a dictionary or list of dictionaries).

    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        db = client.get_database()
        collection = db[collection_name]
        if isinstance(data, list):
            collection.insert_many(data, ordered=False)
        else:
            collection.replace_one({"_id": data.get("_id", collection_name)}, data, upsert=True)
        logger.info(f"Data saved to MongoDB collection: {collection_name}")
        return True
    except Exception as e:
        logger.error(f"Error saving to MongoDB: {e}")
        return False

def load_from_mongodb(client: MongoClient, collection_name: str, query: Optional[Dict] = None) -> Union[Dict, List, None]:
    """
    Load data from a MongoDB collection.

    Args:
        client: MongoClient instance.
        collection_name: Name of the MongoDB collection.
        query: Query to filter data (default is None, which loads all data).

    Returns:
        Union[Dict, List, None]: The loaded data, or None if an error occurs.
    """
    try:
        db = client.get_database()
        collection = db[collection_name]
        if query:
            return list(collection.find(query))
        else:
            data = collection.find_one({"_id": collection_name})
            return data.get("data") if data else None
    except Exception as e:
        logger.error(f"Error loading from MongoDB: {e}")
        return None

def determine_data_type(data: Union[Dict, List], fallback: Optional[str] = None) -> Optional[str]:
    """
    Determine the type of data based on its structure, content, or calling function.

    Args:
        data: The data to analyze.
        fallback: Optional fallback data type if no match is found.

    Returns:
        str: The determined data type (e.g., 'roles', 'models'), or None if unknown.
    """
    # Check data structure
    if isinstance(data, dict):
        if "user_id" in data:
            return "users"
        elif "role_id" in data:
            return "roles"
        elif "shift_id" in data:
            return "shifts"
        elif "period_id" in data:
            return "periods"
        elif "model_id" in data:
            return "models"
        elif "bonus_rule_id" in data:
            return "bonus_rules"
        elif "display_settings" in data:
            return "display_settings"
        elif "commission_settings" in data:
            return "commission_settings"
        elif "earnings" in data:
            return "earnings"

    # Check for array-like data
    if isinstance(data, list):
        # Use parent function name to infer type
        stack = inspect.stack()
        for frame in stack:
            function_name = frame.function.lower()
            for keyword, collection in MONGO_COLLECTION_MAPPING.items():
                if keyword in function_name:
                    return keyword

        # Fallback to provided type
        if fallback:
            return fallback

    return None

async def save_json(client: MongoClient, filename: str, data: Union[Dict, List], pretty: bool = True, make_backup: bool = True) -> bool:
    """
    Save data to MongoDB if applicable, otherwise fallback to JSON file.

    Args:
        client: MongoClient instance.
        filename: Path to the JSON file.
        data: Data to save.
        pretty: Whether to format the JSON with indentation.
        make_backup: Whether to create a backup of the file.

    Returns:
        bool: True if successful, False otherwise.
    """
    data_type = determine_data_type(data)
    if data_type:
        collection_name = MONGO_COLLECTION_MAPPING.get(data_type)
        if collection_name and save_to_mongodb(client, collection_name, data):
            return True

    # Fallback to saving as JSON file
    from utils.file_handlers import save_json as save_json_to_file
    return await save_json_to_file(filename, data, pretty, make_backup)

async def load_json(client: MongoClient, filename: str, default: Optional[Union[Dict, List]] = None) -> Union[Dict, List]:
    """
    Load data from MongoDB if applicable, otherwise fallback to JSON file.

    Args:
        client: MongoClient instance.
        filename: Path to the JSON file.
        default: Default value if file doesn't exist or is invalid.

    Returns:
        Union[Dict, List]: The loaded data.
    """
    data_type = determine_data_type(default)
    if data_type:
        collection_name = MONGO_COLLECTION_MAPPING.get(data_type)
        if collection_name:
            data = load_from_mongodb(client, collection_name)
            if data:
                return data

    # Fallback to loading from JSON file
    from utils.file_handlers import load_json as load_json_from_file
    return await load_json_from_file(filename, default)