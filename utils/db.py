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

def load_from_mongodb(client: MongoClient, collection_name: str, query: Dict) -> Optional[Union[Dict, List]]:
    """
    Load data from a MongoDB collection based on a query.

    Args:
        client: The MongoDB client.
        collection_name: The name of the collection to query.
        query: The query to filter the data.

    Returns:
        The data retrieved from the collection, or None if no data is found.
    """
    try:
        db = client.get_database()
        collection = db[collection_name]
        if "_id" in query or "id" in query:
            # Return a single document if querying by ID
            return collection.find_one(query)
        else:
            # Return a list of documents for general queries
            return list(collection.find(query))
    except Exception as e:
        logger.error(f"Error loading data from MongoDB collection '{collection_name}': {e}")
        return None


def save_to_mongodb(client: MongoClient, collection_name: str, data: Union[Dict, List], query: Optional[Dict] = None) -> bool:
    """
    Save data to a MongoDB collection.

    Args:
        client: The MongoDB client.
        collection_name: The name of the collection to save data to.
        data: The data to save (can be a single document or a list of documents).
        query: Optional query to update an existing document.

    Returns:
        True if the operation was successful, False otherwise.
    """
    try:
        db = client.get_database()
        collection = db[collection_name]

        if isinstance(data, list):
            # Insert multiple documents
            collection.insert_many(data)
        elif query:
            # Update or insert a single document
            collection.replace_one(query, data, upsert=True)
        else:
            # Insert a single document
            collection.insert_one(data)

        return True
    except Exception as e:
        logger.error(f"Error saving data to MongoDB collection '{collection_name}': {e}")
        return False