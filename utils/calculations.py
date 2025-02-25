import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger("fox_calculator.calculations")

def calculate_revenue_share(gross_revenue: Decimal, role_percentage: Decimal) -> Tuple[Decimal, Decimal, Decimal]:
    """
    Calculate employee's cut based on gross revenue and role percentage
    
    Args:
        gross_revenue: The gross revenue amount
        role_percentage: The role's percentage cut
        
    Returns:
        Tuple of (net_revenue, employee_cut, platform_fee)
    """
    # Platform takes 20% of gross
    platform_fee = (gross_revenue * Decimal('0.2')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    # Net revenue is 80% of gross
    net_revenue = (gross_revenue * Decimal('0.8')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    # Employee gets percentage of net revenue
    employee_cut = (net_revenue * (role_percentage / Decimal('100'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    return net_revenue, employee_cut, platform_fee

def find_applicable_bonus(gross_revenue: Decimal, bonus_rules: List[Dict]) -> Decimal:
    """
    Find the applicable bonus based on revenue and rules
    
    Args:
        gross_revenue: The gross revenue amount
        bonus_rules: List of bonus rule dictionaries
        
    Returns:
        The bonus amount (0 if no applicable rule)
    """
    if not bonus_rules:
        return Decimal('0.00')
    
    # Sort rules by revenue range (ascending)
    sorted_rules = sorted(bonus_rules, key=lambda x: x['from'])
    
    # Find applicable rule
    for rule in sorted_rules:
        if rule['from'] <= gross_revenue <= rule['to']:
            return rule['amount']
            
    return Decimal('0.00')

def calculate_earnings(
    gross_revenue: Decimal, 
    role_percentage: Decimal, 
    bonus_rules: List[Dict]
) -> Dict[str, Decimal]:
    """
    Calculate all earnings values
    
    Args:
        gross_revenue: The gross revenue amount
        role_percentage: The role's percentage cut
        bonus_rules: List of bonus rule dictionaries
        
    Returns:
        Dictionary with all calculated values
    """
    net_revenue, employee_cut, platform_fee = calculate_revenue_share(gross_revenue, role_percentage)
    bonus = find_applicable_bonus(gross_revenue, bonus_rules)
    total_cut = (employee_cut + bonus).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    return {
        "gross_revenue": gross_revenue,
        "net_revenue": net_revenue,
        "platform_fee": platform_fee,
        "employee_cut": employee_cut,
        "bonus": bonus,
        "total_cut": total_cut
    }