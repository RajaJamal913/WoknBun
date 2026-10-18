"""
Phone numbers are how we recognise a returning customer, so "0311-3925176",
"+92 311 3925176" and "923113925176" must all be the SAME person.
"""
import re


def normalize_phone(raw):
    """Canonical form like '+923113925176', or None if it can't be a phone number."""
    if raw is None:
        return None
    text = str(raw).strip()
    digits = re.sub(r"\D", "", text)
    if not digits:
        return None
    if digits.startswith("0092"):                       # 0092 311 3925176
        digits = digits[2:]
    elif text.startswith("+"):                          # already international
        pass
    elif digits.startswith("92") and len(digits) == 12:  # 92 311 3925176
        pass
    elif digits.startswith("0") and 10 <= len(digits) <= 11:   # 0311 3925176 / 051 1234567
        digits = "92" + digits[1:]
    elif digits.startswith("3") and len(digits) == 10:  # 311 3925176
        digits = "92" + digits
    if not 10 <= len(digits) <= 15:
        return None
    return "+" + digits


def search_digits(query):
    """Digits to look for when someone types part of a number into a search box."""
    digits = re.sub(r"\D", "", str(query or ""))
    if digits.startswith("0092"):
        digits = digits[4:]
    elif digits.startswith("92") and len(digits) > 2:
        digits = digits[2:]
    elif digits.startswith("0"):
        digits = digits[1:]
    return digits