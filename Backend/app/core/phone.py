import re
from typing import Tuple, Optional

# Regex for stripping non-digits except leading +
CLEAN_REGEX = re.compile(r"[^\d+]")

def normalize_phone_number(raw_phone: str, default_country_code: str = "91") -> Tuple[str, str]:
    """
    Normalizes a phone number to standard E.164 format and returns (normalized, display_format).
    Handles Indian mobile numbers:
      - 10 digits starting with 6, 7, 8, 9: '9876543210' -> ('+919876543210', '+91 98765 43210')
      - With leading 0: '09876543210' -> ('+919876543210', '+91 98765 43210')
      - With 91 prefix: '91-9876543210' -> ('+919876543210', '+91 98765 43210')
      - With +91 prefix: '+91 98765 43210' -> ('+919876543210', '+91 98765 43210')
    Also supports international numbers starting with '+' and 10 to 15 digits.
    Raises ValueError on invalid numbers.
    """
    if not raw_phone or not str(raw_phone).strip():
        raise ValueError("Mobile number cannot be empty.")

    cleaned = str(raw_phone).strip()
    # Strip spaces, dashes, parentheses, dots
    cleaned = re.sub(r"[\s\-\(\)\.]", "", cleaned)

    # Check for invalid characters
    if not re.match(r"^\+?\d+$", cleaned):
        raise ValueError("Mobile number contains invalid characters.")

    has_plus = cleaned.startswith("+")
    digits_only = cleaned.lstrip("+")

    if not digits_only.isdigit():
        raise ValueError("Mobile number must contain digits.")

    # Check Indian number formats
    # 1. Plain 10 digits
    if len(digits_only) == 10:
        if not has_plus:
            # Must start with 6, 7, 8, 9 for valid Indian mobile
            if digits_only[0] not in "6789":
                raise ValueError("Indian mobile numbers must begin with 6, 7, 8, or 9.")
            normalized = f"+91{digits_only}"
            display = f"+91 {digits_only[:5]} {digits_only[5:]}"
            return normalized, display
        else:
            # + followed by 10 digits (e.g. US +1XXXXXXXXX or international)
            normalized = f"+{digits_only}"
            display = f"+{digits_only}"
            return normalized, display

    # 2. 11 digits starting with 0 (Indian trunk prefix 0)
    if len(digits_only) == 11 and digits_only.startswith("0") and not has_plus:
        ten_digits = digits_only[1:]
        if ten_digits[0] not in "6789":
            raise ValueError("Indian mobile numbers must begin with 6, 7, 8, or 9.")
        normalized = f"+91{ten_digits}"
        display = f"+91 {ten_digits[:5]} {ten_digits[5:]}"
        return normalized, display

    # 3. 12 digits starting with 91 (Indian country code)
    if len(digits_only) == 12 and digits_only.startswith("91"):
        ten_digits = digits_only[2:]
        if ten_digits[0] not in "6789":
            raise ValueError("Indian mobile numbers must begin with 6, 7, 8, or 9.")
        normalized = f"+91{ten_digits}"
        display = f"+91 {ten_digits[:5]} {ten_digits[5:]}"
        return normalized, display

    # 4. General International number with leading '+' and 10-15 digits
    if has_plus and 10 <= len(digits_only) <= 15:
        normalized = f"+{digits_only}"
        display = f"+{digits_only}"
        return normalized, display

    raise ValueError("Invalid mobile number length or format. Please provide a valid 10-digit mobile number.")
