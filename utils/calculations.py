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