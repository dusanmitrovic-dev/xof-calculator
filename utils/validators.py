import logging
import re
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Union, Optional, Tuple, List, Dict

logger = logging.getLogger("fox_calculator.validators")

def parse_money(value: Union[str, int, float, Decimal]) -> Optional[Decimal]:
    """
    Parse a monetary value to Decimal with proper validation
    
    Args:
        value: The value to parse (can be string with $ and commas)
        
    Returns:
        Decimal representation or None if invalid
    """
    if isinstance(value, Decimal):
        return value
        
    try:
        if isinstance(value, str):
            # Remove currency symbols, commas, and other non-numeric chars except decimal point
            value = re.sub(r'[^\d.-]', '', value)
        
        # Convert to Decimal with 2 decimal places
        amount = Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return amount
        
    except (InvalidOperation, ValueError, TypeError) as e:
        logger.error(f"Invalid monetary value '{value}': {e}")
        return None