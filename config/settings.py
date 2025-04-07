import os
from typing import Dict, Any, List
from dotenv import load_dotenv
load_dotenv() # Load environment variables from .env file

BOT_PREFIX = "!"

VERSION = "1.1.0"

DATA_DIRECTORY = "data"
CONFIG_DIR = os.path.join(DATA_DIRECTORY, "config")
EARNINGS_DIR = os.path.join(DATA_DIRECTORY, "earnings")
os.makedirs(CONFIG_DIR, exist_ok=True)
os.makedirs(EARNINGS_DIR, exist_ok=True)


ROLE_DATA_FILE = "role_percentages.json"
SHIFT_DATA_FILE = "shift_config.json"
PERIOD_DATA_FILE = "period_config.json"
MODELS_DATA_FILE = "models_config.json"
BONUS_RULES_FILE = "bonus_rules.json"
DISPLAY_SETTINGS_FILE = "display_settings.json"
COMMISSION_SETTINGS_FILE = "commission_settings.json"

EARNINGS_FILE_NAME_WITHOUT_EXT = "earnings"
EARNINGS_FILE = EARNINGS_FILE_NAME_WITHOUT_EXT + ".json"

# --- MongoDB Settings ---
MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = MONGODB_URI.split('/')[-1].split('?')[0] if MONGODB_URI else "xof_calculator_db" # Extract from URI or default
GUILD_CONFIG_COLLECTION = "guild_configs"
EARNINGS_COLLECTION = "earnings"
# --- End MongoDB Settings ---

# DEFAULT_ROLE_DATA: Dict[str, Dict[str, float]] = {}# TODO: remove
DEFAULT_ROLE_DATA = {}
# DEFAULT_SHIFT_DATA: Dict[str, List[str]] = {} # TODO: remove
DEFAULT_SHIFT_DATA = []
# DEFAULT_PERIOD_DATA: Dict[str, List[str]] = {} # TODO: remove
DEFAULT_PERIOD_DATA = []
# DEFAULT_MODELS_DATA: Dict[str, List[str]] = {} # TODO: remove
DEFAULT_MODELS_DATA = []
DEFAULT_BONUS_RULES = []
DEFAULT_EARNINGS: List[Dict[str, Any]] = {}

DEFAULT_DISPLAY_SETTINGS = {
        "ephemeral_responses": True,
        "show_average": True,
        "agency_name": "Agency",
        "show_ids": True,
        "bot_name": "Shift Calculator"
}

DEFAULT_COMMISSION_SETTINGS = {
    "roles": {},
    "users": {}
}

# Formatting
DATE_FORMAT = "%d/%m/%Y"
DECIMAL_PLACES = 2

os.makedirs(DATA_DIRECTORY, exist_ok=True)

# def get_earnings_file_name_without_ext(): # TODO: remove
#     return EARNINGS_FILE_NAME_WITHOUT_EXT

# def get_earnings_file_for_guild(guild_id):
#     return f"{EARNINGS_FILE_NAME_WITHOUT_EXT}_{guild_id}.json"

def get_guild_path(guild_id: int) -> str:
    """Return path to guild's config directory"""
    path = os.path.join(CONFIG_DIR, str(guild_id))
    os.makedirs(path, exist_ok=True)
    return path

def get_guild_earnings_path_dir(guild_id: int) -> str:
    """Return path to guild's earnings directory"""
    path = os.path.join(EARNINGS_DIR, str(guild_id))
    os.makedirs(path, exist_ok=True)
    return path

def get_guild_file(guild_id: int, filename: str) -> str:
    """Get full path to a guild-specific config file"""
    return os.path.join(get_guild_path(guild_id), filename)

def get_guild_earnings_file(guild_id: int, filename: str) -> str:
    """Get full path to a guild-specific config file"""
    path = os.path.join(EARNINGS_DIR, str(guild_id))
    return os.path.join(path, filename)

# NOTE: MODELS

def get_guild_models_path(guild_id: int) -> str:
    """Get path to guild's models config file"""
    return get_guild_file(guild_id, MODELS_DATA_FILE)

# NOTE: ROLES

def get_guild_roles_path(guild_id: int) -> str:
    """Get path to guild's roles config file"""
    return get_guild_file(guild_id, ROLE_DATA_FILE)

# NOTE: SHIFTS

def get_guild_shifts_path(guild_id: int) -> str:
    """Get path to guild's shifts config file"""
    return get_guild_file(guild_id, SHIFT_DATA_FILE)

# NOTE: PERIODS

def get_guild_periods_path(guild_id: int) -> str:
    """Get path to guild's periods config file"""
    return get_guild_file(guild_id, PERIOD_DATA_FILE)

# NOTE: BONUS

def get_guild_bonus_rules_path(guild_id: int) -> str:
    """Get path to guild's bonus rules config file"""
    return get_guild_file(guild_id, BONUS_RULES_FILE)

# NOTE: COMMISSION

def get_guild_commission_path(guild_id: int) -> str:
    """Get path to guild's commission settings"""
    return get_guild_file(guild_id, COMMISSION_SETTINGS_FILE)

# NOTE: DISPLAY

def get_guild_display_path(guild_id: int) -> str:
    """Get path to guild's display settings"""
    return get_guild_file(guild_id, DISPLAY_SETTINGS_FILE)

# NOTE: EARNINGS

def get_guild_earnings_path(guild_id: int) -> str:
    """Get path to guild's earnings file"""
    return get_guild_earnings_file(guild_id, EARNINGS_FILE)

# This helps structure the MongoDB document
FILENAME_TO_MONGO_KEY = {
    ROLE_DATA_FILE: "roles",
    SHIFT_DATA_FILE: "shifts",
    PERIOD_DATA_FILE: "periods",
    MODELS_DATA_FILE: "models",
    BONUS_RULES_FILE: "bonus_rules",
    DISPLAY_SETTINGS_FILE: "display_settings",
    COMMISSION_SETTINGS_FILE: "commission_settings",
}