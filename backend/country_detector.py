import re
from typing import Tuple, Dict

# Comprehensive global country registry with dialing codes and common city/location keywords
GLOBAL_COUNTRIES: Dict[str, Dict] = {
    "NZ": {
        "name": "New Zealand",
        "code": "NZ",
        "dial_code": "+64",
        "flag": "🇳🇿",
        "keywords": [
            "new zealand", "newzealand", "queenstown", "auckland", "wellington",
            "christchurch", "hamilton", "tauranga", "napier", "dunedin",
            "palmerston", "nelson", "rotorua", "wanaka", "nz"
        ]
    },
    "AU": {
        "name": "Australia",
        "code": "AU",
        "dial_code": "+61",
        "flag": "🇦🇺",
        "keywords": [
            "australia", "sydney", "melbourne", "brisbane", "perth", "adelaide",
            "gold coast", "newcastle", "canberra", "sunshine coast", "wollongong",
            "hobart", "geelong", "townsville", "cairns", "darwin", "au"
        ]
    },
    "US": {
        "name": "United States",
        "code": "US",
        "dial_code": "+1",
        "flag": "🇺🇸",
        "keywords": [
            "united states", "usa", "america", "new york", "los angeles", "chicago",
            "houston", "phoenix", "philadelphia", "san antonio", "san diego", "dallas",
            "san jose", "austin", "jacksonville", "fort worth", "columbus", "charlotte",
            "san francisco", "indianapolis", "seattle", "denver", "washington", "boston",
            "el paso", "nashville", "detroit", "las vegas", "portland", "memphis",
            "louisville", "baltimore", "milwaukee", "albuquerque", "tucson", "fresno",
            "sacramento", "kansas city", "mesa", "atlanta", "omaha", "colorado springs",
            "raleigh", "virginia beach", "miami", "oakland", "minneapolis", "tulsa",
            "bakersfield", "wichita", "arlington", "california", "texas", "florida", "us"
        ]
    },
    "GB": {
        "name": "United Kingdom",
        "code": "GB",
        "dial_code": "+44",
        "flag": "🇬🇧",
        "keywords": [
            "united kingdom", "uk", "great britain", "england", "scotland", "wales",
            "london", "birmingham", "manchester", "leeds", "glasgow", "sheffield",
            "bradford", "liverpool", "edinburgh", "bristol", "cardiff", "belfast",
            "leicester", "wakefield", "coventry", "nottingham", "newcastle"
        ]
    },
    "CA": {
        "name": "Canada",
        "code": "CA",
        "dial_code": "+1",
        "flag": "🇨🇦",
        "keywords": [
            "canada", "toronto", "montreal", "vancouver", "calgary", "edmonton",
            "ottawa", "winnipeg", "quebec city", "hamilton", "kitchener", "victoria", "ca"
        ]
    },
    "IN": {
        "name": "India",
        "code": "IN",
        "dial_code": "+91",
        "flag": "🇮🇳",
        "keywords": [
            "india", "delhi", "mumbai", "bangalore", "bengaluru", "hyderabad",
            "ahmedabad", "chennai", "kolkata", "surat", "pune", "jaipur", "lucknow",
            "kanpur", "nagpur", "indore", "thane", "bhopal", "visakhapatnam", "pimpri",
            "patna", "vadodara", "ghaziabad", "ludhiana", "agra", "nashik", "faridabad",
            "meerut", "rajkot", "kalyan", "vasai", "varanasi", "srinagar", "aurangabad",
            "dhanbad", "amritsar", "navi mumbai", "allahabad", "ranchi", "howrah",
            "coimbatore", "jabalpur", "gwalior", "vijayawada", "jodhpur", "madurai",
            "raipur", "kota", "guwahati", "chandigarh", "noida", "gurgaon", "indiranagar",
            "andheri", "connaught place", "rohini", "koramangala", "whitefield"
        ]
    },
    "AE": {
        "name": "United Arab Emirates",
        "code": "AE",
        "dial_code": "+971",
        "flag": "🇦🇪",
        "keywords": ["uae", "united arab emirates", "dubai", "abu dhabi", "sharjah", "ajman", "ras al khaimah", "fujairah"]
    },
    "SG": {
        "name": "Singapore",
        "code": "SG",
        "dial_code": "+65",
        "flag": "🇸🇬",
        "keywords": ["singapore", "sg"]
    },
    "IE": {
        "name": "Ireland",
        "code": "IE",
        "dial_code": "+353",
        "flag": "🇮🇪",
        "keywords": ["ireland", "dublin", "cork", "galway", "limerick", "waterford"]
    },
    "ZA": {
        "name": "South Africa",
        "code": "ZA",
        "dial_code": "+27",
        "flag": "🇿🇦",
        "keywords": ["south africa", "johannesburg", "cape town", "durban", "pretoria", "port elizabeth"]
    },
    "DE": {
        "name": "Germany",
        "code": "DE",
        "dial_code": "+49",
        "flag": "🇩🇪",
        "keywords": ["germany", "deutschland", "berlin", "hamburg", "munich", "cologne", "frankfurt", "stuttgart", "dusseldorf"]
    },
    "FR": {
        "name": "France",
        "code": "FR",
        "dial_code": "+33",
        "flag": "🇫🇷",
        "keywords": ["france", "paris", "marseille", "lyon", "toulouse", "nice", "nantes", "strasbourg", "montpellier", "bordeaux"]
    }
}


def detect_country_from_location(location: str) -> Tuple[str, str]:
    """
    Analyzes location string and returns (country_code, dial_prefix).
    Defaults to ('NZ', '+64') if New Zealand is mentioned, etc.
    """
    if not location:
        return "IN", "+91"

    loc_lower = location.lower().strip()

    # Explicit country code checks
    for code, info in GLOBAL_COUNTRIES.items():
        for kw in info["keywords"]:
            # Check whole word match or substring
            pattern = rf"\b{re.escape(kw)}\b"
            if re.search(pattern, loc_lower):
                return code, info["dial_code"]

    # Fallback to India if nothing matched
    return "IN", "+91"
