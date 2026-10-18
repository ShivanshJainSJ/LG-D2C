from decimal import Decimal
from typing import Union

ONES = [
    "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
    "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
    "Seventeen", "Eighteen", "Nineteen"
]

TENS = [
    "", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"
]

def _two_digits_to_words(n: int) -> str:
    if n == 0:
        return ""
    if n < 20:
        return ONES[n]
    tens_digit = n // 10
    ones_digit = n % 10
    if ones_digit:
        return f"{TENS[tens_digit]}-{ONES[ones_digit]}"
    return TENS[tens_digit]

def _three_digits_to_words(n: int) -> str:
    if n == 0:
        return ""
    hundreds = n // 100
    rem = n % 100
    parts = []
    if hundreds:
        parts.append(f"{ONES[hundreds]} Hundred")
    if rem:
        parts.append(_two_digits_to_words(rem))
    return " ".join(parts)

def _integer_to_words_inr(n: int) -> str:
    if n == 0:
        return "Zero"
    
    parts = []
    
    crore = n // 10000000
    n %= 10000000
    if crore > 0:
        parts.append(f"{_integer_to_words_inr(crore)} Crore")
        
    lakh = n // 100000
    n %= 100000
    if lakh > 0:
        parts.append(f"{_two_digits_to_words(lakh)} Lakh")
        
    thousand = n // 1000
    n %= 1000
    if thousand > 0:
        parts.append(f"{_two_digits_to_words(thousand)} Thousand")
        
    hundred_part = _three_digits_to_words(n)
    if hundred_part:
        parts.append(hundred_part)
        
    return " ".join(parts)

def amount_to_words_inr(amount: Union[float, Decimal, int]) -> str:
    """
    Converts a numerical amount in INR to Indian currency words format.
    Example: 60180.00 -> 'Rupees Sixty Thousand One Hundred Eighty Only.'
    Example: 60180.50 -> 'Rupees Sixty Thousand One Hundred Eighty and Fifty Paise Only.'
    """
    try:
        amount_dec = Decimal(str(amount)).quantize(Decimal("0.01"))
    except Exception:
        amount_dec = Decimal("0.00")
        
    if amount_dec < 0:
        sign = "Negative "
        amount_dec = abs(amount_dec)
    else:
        sign = ""
        
    rupees = int(amount_dec)
    paise = int(round((amount_dec - Decimal(rupees)) * 100))
    
    parts = []
    if rupees > 0 or paise == 0:
        rupees_words = _integer_to_words_inr(rupees)
        parts.append(f"Rupees {rupees_words}")
        
    if paise > 0:
        paise_words = _two_digits_to_words(paise)
        if parts:
            parts.append(f"and {paise_words} Paise")
        else:
            parts.append(f"{paise_words} Paise")
            
    return f"{sign}{' '.join(parts)} Only."
