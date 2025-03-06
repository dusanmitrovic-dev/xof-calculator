import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger("xof_calculator.calculations")

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

def calculate_hourly_earnings(gross_revenue: Decimal, hours: Decimal, hourly_rate: Decimal, bonus_rules: List[Dict[str, Decimal]]) -> Dict[str, Decimal]:
    commission_earnings = calculate_earnings(gross_revenue, 0, bonus_rules)
    gross_revenue = gross_revenue
    hourly_revenue = hours * hourly_rate
    net_revenue = 0
    platform_fee = 0
    employee_cut = hourly_revenue
    bonus = commission_earnings["bonus"]
    total_cut = employee_cut + bonus
    
    return {
        "gross_revenue": gross_revenue,
        "net_revenue": net_revenue,
        "platform_fee": platform_fee,
        "employee_cut": employee_cut,
        "bonus": bonus,
        "total_cut": total_cut
    }

def calculate_combined_earnings(gross_revenue: Decimal, percentage: Decimal, hours: Decimal, hourly_rate: Decimal, bonus_rules: List[Dict[str, Decimal]]) -> Dict[str, Decimal]:
    # Calculate commission-based earnings
    commission_earnings = calculate_earnings(gross_revenue, percentage, bonus_rules)
    
    # Calculate hourly earnings
    hourly_earnings = calculate_hourly_earnings(gross_revenue, hours, hourly_rate, [])
    
    # Combine results
    total_cut = commission_earnings["total_cut"] + hourly_earnings["total_cut"]
    
    return {
        "gross_revenue": gross_revenue,
        "net_revenue": commission_earnings["net_revenue"],
        "platform_fee": commission_earnings["platform_fee"],
        "employee_cut": commission_earnings["employee_cut"],
        "bonus": commission_earnings["bonus"],
        "total_cut": total_cut
    }

def get_total_earnings(earnings_data: List[Dict], period: str, from_date: Optional[str] = None, to_date: Optional[str] = None) -> Decimal:
    """
    Calculate total earnings from a list of earnings data
    
    Args:
        earnings_data: List of earnings dictionaries
        period: Period to filter by
        from_date: Optional start date (format: DD/MM/YYYY)
        to_date: Optional end date (format: DD/MM/YYYY)
        
    Returns:
        Total earnings amount
    """
    from datetime import datetime
    
    # Filter by period
    filtered_data = [entry for entry in earnings_data if entry.get("period", "").lower() == period.lower()]
    
    # Filter by date range if provided
    if from_date and to_date:
        try:
            from_date_obj = datetime.strptime(from_date, "%d/%m/%Y")
            to_date_obj = datetime.strptime(to_date, "%d/%m/%Y")
            
            filtered_data = [
                entry for entry in filtered_data 
                if from_date_obj <= datetime.strptime(entry.get("date", "01/01/1970"), "%d/%m/%Y") <= to_date_obj
            ]
        except ValueError as e:
            logger.error(f"Date parsing error: {e}")
    
    # Sum total cuts
    gross = sum(Decimal(str(entry.get("gross_revenue", 0))) for entry in filtered_data)
    total = sum(Decimal(str(entry.get("total_cut", 0))) for entry in filtered_data)
    return gross.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP), total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)