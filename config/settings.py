import os
from typing import Dict, Any, List, Optional

BOT_PREFIX = "!"

VERSION = "1.0.0"

DATA_DIRECTORY = "data"
ROLE_DATA_FILE = "role_percentages.json"
SHIFT_DATA_FILE = "shift_config.json"
PERIOD_DATA_FILE = "period_config.json"
MODELS_DATA_FILE = "models_config.json"
BONUS_RULES_FILE = "bonus_rules.json"
DISPLAY_SETTINGS_FILE = "display_settings.json"
COMMISSION_SETTINGS_FILE = "commission_settings.json"

EARNINGS_FILE_NAME_WITHOUT_EXT = "earnings"
EARNINGS_FILE = EARNINGS_FILE_NAME_WITHOUT_EXT + ".json"

DEFAULT_ROLE_DATA: Dict[str, Dict[str, float]] = {}
DEFAULT_SHIFT_DATA: Dict[str, List[str]] = {}
DEFAULT_PERIOD_DATA: Dict[str, List[str]] = {}
DEFAULT_MODELS_DATA: Dict[str, List[str]] = {}
DEFAULT_BONUS_RULES: Dict[str, List[Dict[str, float]]] = {}
DEFAULT_EARNINGS: Dict[str, List[Dict[str, Any]]] = {}
DEFAULT_DISPLAY_SETTINGS: Dict[str, Dict[str, bool]] = {
    "defaults": {
        "ephemeral_responses": True,
        "show_average": True,
        "agency_name": "Agency",
        "show_ids": True,
        "bot_name": "Shift Calculator"
    }
}
DEFAULT_COMMISSION_SETTINGS: Dict[str, Dict[str, float]] = {}

# Formatting
DATE_FORMAT = "%d/%m/%Y"
DECIMAL_PLACES = 2

os.makedirs(DATA_DIRECTORY, exist_ok=True)

def get_earnings_file_name_without_ext():
    return EARNINGS_FILE_NAME_WITHOUT_EXT

def get_earnings_file_for_guild(guild_id):
    # return f"{EARNINGS_FILE_NAME_WITHOUT_EXT}_{guild_id}.json" # TODO: remove
    return f"{EARNINGS_FILE_NAME_WITHOUT_EXT}.json"