import logging
import re
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Union, Optional, Tuple, List, Dict

logger = logging.getLogger("fox_calculator.validators")