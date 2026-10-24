import re
import urllib.parse
from typing import Optional, Tuple
from backend.country_detector import GLOBAL_COUNTRIES

try:
    import phonenumbers
    from phonenumbers import PhoneNumberType, geocoder, carrier
    HAS_PHONENUMBERS = True
except ImportError:
    HAS_PHONENUMBERS = False


def clean_phone_number(raw_phone: str, default_region: str = "IN") -> Tuple[Optional[str], bool, str]:
    """
    Cleans raw phone number and determines if it is a mobile number suitable for WhatsApp,
    adapting to any country (e.g. New Zealand +64, Australia +61, US/Canada +1, India +91, UK +44).
    
    Returns:
        (clean_e164, is_mobile, carrier_or_region_info)
    """
    if not raw_phone:
        return None, False, "No phone provided"

    cleaned = re.sub(r"[^\d+]", "", raw_phone)
    if not cleaned:
        return None, False, "Invalid number"

    region = default_region.upper()

    if HAS_PHONENUMBERS:
        try:
            parsed = phonenumbers.parse(raw_phone, region)
            if not phonenumbers.is_valid_number(parsed):
                parsed = phonenumbers.parse(cleaned, region)
            
            if phonenumbers.is_valid_number(parsed):
                e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
                num_type = phonenumbers.number_type(parsed)
                
                # Check mobile vs fixed line
                is_mob = num_type in (
                    PhoneNumberType.MOBILE,
                    PhoneNumberType.FIXED_LINE_OR_MOBILE,
                    PhoneNumberType.PERSONAL_NUMBER
                )
                
                info = carrier.name_for_number(parsed, "en") or geocoder.description_for_number(parsed, "en") or "Valid"
                return e164, is_mob, info
        except Exception:
            pass

    # Regex heuristic fallbacks when phonenumbers library is missing or fails
    digits = re.sub(r"\D", "", raw_phone)
    dial_prefix = GLOBAL_COUNTRIES.get(region, {}).get("dial_code", "+91")

    # If number already starts with full international prefix (+64, +61, +1, +44, +91)
    if raw_phone.startswith("+"):
        return f"+{digits}", True, f"{region} International"

    # New Zealand (+64)
    if region == "NZ":
        # NZ mobile typically starts with 02 (021, 022, 027, 020, 029), 9-11 digits
        if digits.startswith("64"):
            return f"+{digits}", True, "NZ Mobile"
        if digits.startswith("02") and 9 <= len(digits) <= 11:
            return f"+64{digits[1:]}", True, "NZ Mobile"
        if digits.startswith("2") and 8 <= len(digits) <= 10:
            return f"+64{digits}", True, "NZ Mobile"
        # Landline (03 for South Island / Queenstown, 09 for Auckland, 04 for Wellington)
        if digits.startswith("0") and len(digits) in (9, 10):
            return f"+64{digits[1:]}", False, "NZ Landline"
        if len(digits) >= 7:
            return f"+64{digits.lstrip('0')}", True, "NZ Phone"

    # Australia (+61)
    elif region == "AU":
        if digits.startswith("61"):
            return f"+{digits}", True, "AU Mobile"
        if digits.startswith("04") and len(digits) == 10:
            return f"+61{digits[1:]}", True, "AU Mobile"
        if digits.startswith("0") and len(digits) == 10:
            return f"+61{digits[1:]}", False, "AU Landline"
        if len(digits) >= 8:
            return f"+61{digits.lstrip('0')}", True, "AU Phone"

    # United Kingdom (+44)
    elif region == "GB":
        if digits.startswith("44"):
            return f"+{digits}", True, "UK Mobile"
        if digits.startswith("07") and len(digits) == 11:
            return f"+44{digits[1:]}", True, "UK Mobile"
        if digits.startswith("01") or digits.startswith("02"):
            return f"+44{digits[1:]}", False, "UK Landline"
        if len(digits) >= 9:
            return f"+44{digits.lstrip('0')}", True, "UK Phone"

    # United States / Canada (+1)
    elif region in ("US", "CA"):
        if len(digits) == 10:
            return f"+1{digits}", True, "US/CA Mobile"
        if len(digits) == 11 and digits.startswith("1"):
            return f"+{digits}", True, "US/CA Mobile"

    # India (+91)
    elif region == "IN":
        if len(digits) == 10 and digits[0] in "6789":
            return f"+91{digits}", True, "India Mobile"
        if len(digits) == 11 and digits.startswith("0") and digits[1] in "6789":
            return f"+91{digits[1:]}", True, "India Mobile"
        if len(digits) == 12 and digits.startswith("91") and digits[2] in "6789":
            return f"+{digits}", True, "India Mobile"
        if len(digits) in (10, 11) and digits[0] in "012345":
            return f"+91{digits.lstrip('0')}", False, "India Landline"

    # Generic global fallback
    if len(digits) >= 8:
        clean_prefix = dial_prefix.lstrip("+")
        if digits.startswith(clean_prefix):
            return f"+{digits}", True, "Mobile"
        return f"{dial_prefix}{digits.lstrip('0')}", True, "Mobile"

    return None, False, "Invalid number"


def generate_whatsapp_link(phone_e164: str, template: str, context: dict) -> str:
    """
    Constructs an instant https://wa.me/ link with pre-filled message text.
    """
    if not phone_e164:
        return ""
    
    number_digits = re.sub(r"\D", "", phone_e164)
    
    message = template
    for key, val in context.items():
        message = message.replace(f"{{{key}}}", str(val or ""))
    
    encoded_text = urllib.parse.quote(message)
    return f"https://wa.me/{number_digits}?text={encoded_text}"
