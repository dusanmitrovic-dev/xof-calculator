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