import os
from typing import Dict, Any, List, Optional

# Bot configuration
BOT_PREFIX = "!"

VERSION = "1.0.0"

# File paths
DATA_DIRECTORY = "data"
ROLE_DATA_FILE = "role_percentages.json"
SHIFT_DATA_FILE = "shift_config.json"
PERIOD_DATA_FILE = "period_config.json"
MODELS_DATA_FILE = "models_config.json"
BONUS_RULES_FILE = "bonus_rules.json"
EARNINGS_FILE = "earnings.json"
DISPLAY_SETTINGS_FILE = "display_settings.json"

# Default settings
DEFAULT_ROLE_DATA: Dict[str, Dict[str, float]] = {}
DEFAULT_SHIFT_DATA: Dict[str, List[str]] = {}
DEFAULT_PERIOD_DATA: Dict[str, List[str]] = {}
DEFAULT_MODELS_DATA: Dict[str, List[str]] = {}
DEFAULT_BONUS_RULES: Dict[str, List[Dict[str, float]]] = {}
DEFAULT_EARNINGS: Dict[str, List[Dict[str, Any]]] = {}
DEFAULT_DISPLAY_SETTINGS: Dict[str, Dict[str, bool]] = {} 

# Date format
DATE_FORMAT = "%d/%m/%Y"

# Create data directory if it doesn't exist
os.makedirs(DATA_DIRECTORY, exist_ok=True)