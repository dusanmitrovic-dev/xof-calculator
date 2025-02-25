import logging
import re
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Union, Optional, Tuple, List, Dict

logger = logging.getLogger("xof_calculator.validators")

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

def validate_shift(shift: str, valid_shifts: List[str]) -> Optional[str]:
    """
    Validate and find a shift by name (case-insensitive)
    
    Args:
        shift: Shift name to validate
        valid_shifts: List of valid shift names
        
    Returns:
        The matched shift name or None if not found
    """
    if not shift or not valid_shifts:
        return None
        
    # Case-insensitive matching
    for valid_shift in valid_shifts:
        if valid_shift.lower() == shift.lower():
            return valid_shift
            
    return None

def validate_period(period: str, valid_periods: List[str]) -> Optional[str]:
    """
    Validate and find a period by name (case-insensitive)
    
    Args:
        period: Period name to validate
        valid_periods: List of valid period names
        
    Returns:
        The matched period name or None if not found
    """
    if not period or not valid_periods:
        return None
        
    # Case-insensitive matching
    for valid_period in valid_periods:
        if valid_period.lower() == period.lower():
            return valid_period
            
    return None

def validate_bonus_rules(rules: List[Dict]) -> Tuple[List[Dict], List[str]]:
    """
    Validate bonus rules for consistency and overlaps
    
    Args:
        rules: List of bonus rule dictionaries
        
    Returns:
        Tuple of (valid_rules, error_messages)
    """
    valid_rules = []
    errors = []
    
    # Check each rule has required fields
    for i, rule in enumerate(rules):
        if not all(key in rule for key in ['from', 'to', 'amount']):
            errors.append(f"Rule #{i+1} is missing required fields (from, to, amount)")
            continue
            
        # Validate monetary values
        from_val = parse_money(rule['from'])
        to_val = parse_money(rule['to']) 
        amount = parse_money(rule['amount'])
        
        if None in (from_val, to_val, amount):
            errors.append(f"Rule #{i+1} contains invalid monetary values")
            continue
            
        # Check range validity
        if from_val > to_val:
            errors.append(f"Rule #{i+1} has 'from' value ({from_val}) greater than 'to' value ({to_val})")
            continue
            
        valid_rules.append({
            "from": from_val,
            "to": to_val,
            "amount": amount
        })
    
    # Check for overlapping ranges
    valid_rules.sort(key=lambda x: x['from'])
    for i in range(1, len(valid_rules)):
        prev_rule = valid_rules[i-1]
        curr_rule = valid_rules[i]
        
        if prev_rule['to'] >= curr_rule['from']:
            errors.append(
                f"Overlapping bonus rules: " 
                f"${prev_rule['from']} - ${prev_rule['to']} overlaps with "
                f"${curr_rule['from']} - ${curr_rule['to']}"
            )
    
    return valid_rules, errors