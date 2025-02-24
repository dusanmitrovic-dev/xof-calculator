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

def validate_percentage(value: Union[str, int, float, Decimal]) -> Optional[Decimal]:
    """
    Validate a percentage value is between 0-100
    
    Args:
        value: The percentage value to validate
        
    Returns:
        Decimal representation if valid, None otherwise
    """
    try:
        if isinstance(value, str):
            # Remove percentage symbol and whitespace
            value = value.replace('%', '').strip()
            
        percentage = Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        if percentage < 0 or percentage > 100:
            logger.error(f"Percentage value {percentage} out of range (0-100)")
            return None
            
        return percentage
        
    except (InvalidOperation, ValueError, TypeError) as e:
        logger.error(f"Invalid percentage value '{value}': {e}")
        return None

def validate_date_format(date_str: str, format_str: str = "%d/%m/%Y") -> bool:
    """
    Validate if a string matches the expected date format
    
    Args:
        date_str: Date string to validate
        format_str: Expected date format
        
    Returns:
        True if valid, False otherwise
    """
    import datetime
    try:
        datetime.datetime.strptime(date_str, format_str)
        return True
    except ValueError:
        return False