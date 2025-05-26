from typing import Union, Tuple

def parse_bet(amount_str: str, balance: int) -> Tuple[Union[int, None], str]:
    """
    Parse bet amount from various formats
    Returns (amount, error_message)
    Supports:
    - Regular numbers: 100, 400, 1000
    - Percentages: 50%, 100%, 5.5%
    - K/M notation: 1k, 1.5k, 100k, 1m, 2.5m
    - Scientific: 1e3, 1.5e3, 1e6
    """
    try:
        # Clean the input
        amount_str = amount_str.lower().strip()
        
        # Handle 'all' or 'max'
        if amount_str in ['all', 'max']:
            return balance, None
            
        # Handle percentage
        if amount_str.endswith('%'):
            try:
                percentage = float(amount_str[:-1])
                if not 0 < percentage <= 100:
                    return None, "Percentage must be between 0 and 100!"
                return round((percentage / 100) * balance), None
            except ValueError:
                return None, "Invalid percentage format!"
        
        # Handle k/m notation
        multiplier = 1
        if amount_str.endswith('k'):
            multiplier = 1000
            amount_str = amount_str[:-1]
        elif amount_str.endswith('m'):
            multiplier = 1000000
            amount_str = amount_str[:-1]
        
        # Convert scientific notation and decimals
        if 'e' in amount_str:
            amount = float(amount_str)
        else:
            amount = float(amount_str)
        
        # Apply multiplier and round
        final_amount = round(amount * multiplier)
        
        if final_amount <= 0:
            return None, "Bet must be positive!"
            
        return final_amount, None
        
    except ValueError:
        return None, "Invalid bet amount!"
