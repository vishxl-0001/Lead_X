import requests
import logging
from typing import List, Dict, Any

logger = logging.getLogger("lead_finder.geocoding")

# 100% Free global geocoding APIs with zero key requirements
OPEN_METEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
PHOTON_URL = "https://photon.komoot.io/api/"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}


def search_locations_global(query: str, limit: int = 8) -> List[Dict[str, Any]]:
    """
    Searches worldwide locations, cities, states, regions, and neighborhoods.
    Uses ultra-fast Open-Meteo as primary (unrestricted for cloud/Render instances),
    with Photon and Nominatim as fallback.
    Returns clean suggestions with display name, city, state, country, country_code, lat, lon.
    """
    if not query or len(query.strip()) < 2:
        return []

    q = query.strip()
    results = []

    # 1. Try Open-Meteo Global Geocoding (Ultra-fast ~50ms, 100% free, never blocks cloud/Render IPs)
    try:
        resp = requests.get(
            OPEN_METEO_URL,
            params={"name": q, "count": limit, "language": "en", "format": "json"},
            headers=BROWSER_HEADERS,
            timeout=4
        )
        if resp.status_code == 200:
            items = resp.json().get("results") or []
            if not items and "," in q:
                # If no direct match with comma, try first token (e.g. "Auckland" from "Auckland, New Zealand")
                first_token = q.split(",")[0].strip()
                resp2 = requests.get(
                    OPEN_METEO_URL,
                    params={"name": first_token, "count": limit, "language": "en", "format": "json"},
                    headers=BROWSER_HEADERS,
                    timeout=4
                )
                if resp2.status_code == 200:
                    items = resp2.json().get("results") or []

            for item in items:
                name = item.get("name") or ""
                admin1 = item.get("admin1") or ""
                country = item.get("country") or ""
                country_code = (item.get("country_code") or "").upper()
                parts = [p for p in [name, admin1, country] if p]
                display_label = ", ".join(dict.fromkeys(parts))

                results.append({
                    "display_name": display_label,
                    "name": name,
                    "city": name,
                    "state": admin1,
                    "country": country,
                    "country_code": country_code,
                    "lat": float(item.get("latitude", 0)),
                    "lon": float(item.get("longitude", 0)),
                    "type": "city"
                })

            if results:
                return results
    except Exception as e:
        logger.debug(f"Open-Meteo lookup warning: {e}")

    # 2. Try Photon fallback (OpenStreetMap data)
    try:
        resp = requests.get(
            PHOTON_URL,
            params={"q": q, "limit": limit, "lang": "en"},
            headers=BROWSER_HEADERS,
            timeout=4
        )
        if resp.status_code == 200:
            data = resp.json()
            features = data.get("features", [])
            for feat in features:
                props = feat.get("properties", {})
                coords = feat.get("geometry", {}).get("coordinates", [0, 0])
                lon, lat = coords[0], coords[1]

                name = props.get("name", "")
                city = props.get("city") or props.get("town") or props.get("district") or name
                state = props.get("state", "")
                country = props.get("country", "")
                country_code = (props.get("countrycode") or "").upper()

                parts = [p for p in [name, city if city != name else None, state, country] if p]
                display_label = ", ".join(dict.fromkeys(parts))

                results.append({
                    "display_name": display_label,
                    "name": name,
                    "city": city,
                    "state": state,
                    "country": country,
                    "country_code": country_code,
                    "lat": lat,
                    "lon": lon,
                    "type": props.get("type", "location")
                })

            if results:
                return results
    except Exception as e:
        logger.debug(f"Photon lookup error: {e}")

    # 3. Fallback to Nominatim
    try:
        resp = requests.get(
            NOMINATIM_URL,
            params={"q": q, "format": "json", "addressdetails": 1, "limit": limit, "accept-language": "en"},
            headers=BROWSER_HEADERS,
            timeout=4
        )
        if resp.status_code == 200:
            items = resp.json()
            for it in items:
                addr = it.get("address", {})
                city = addr.get("city") or addr.get("town") or addr.get("suburb") or addr.get("village") or it.get("name")
                state = addr.get("state") or addr.get("region", "")
                country = addr.get("country", "")
                country_code = (addr.get("country_code") or "").upper()

                results.append({
                    "display_name": it.get("display_name", ""),
                    "name": it.get("name", ""),
                    "city": city,
                    "state": state,
                    "country": country,
                    "country_code": country_code,
                    "lat": float(it.get("lat", 0)),
                    "lon": float(it.get("lon", 0)),
                    "type": it.get("type", "location")
                })
    except Exception as e:
        logger.debug(f"Nominatim lookup error: {e}")

    return results


def get_sub_areas_for_region(region_name: str, country_code: str = "") -> List[str]:
    """
    Returns prominent cities/neighborhoods for popular regions like Ontario, California, Texas, etc.
    """
    region_lower = region_name.lower().strip()
    
    # Common global regions pre-mapped with top business sub-areas
    PRESET_SUB_AREAS = {
        "ontario": [
            "Toronto, Ontario", "Ottawa, Ontario", "Mississauga, Ontario",
            "Brampton, Ontario", "Hamilton, Ontario", "London, Ontario",
            "Markham, Ontario", "Vaughan, Ontario", "Kitchener, Ontario",
            "Windsor, Ontario", "Richmond Hill, Ontario", "Oakville, Ontario",
            "Burlington, Ontario", "Barrie, Ontario", "Oshawa, Ontario"
        ],
        "california": [
            "Los Angeles, California", "San Francisco, California", "San Diego, California",
            "San Jose, California", "Sacramento, California", "Fresno, California",
            "Long Beach, California", "Oakland, California", "Anaheim, California"
        ],
        "texas": [
            "Houston, Texas", "Dallas, Texas", "Austin, Texas",
            "San Antonio, Texas", "Fort Worth, Texas", "El Paso, Texas",
            "Arlington, Texas", "Plano, Texas"
        ],
        "new south wales": [
            "Sydney, NSW", "Newcastle, NSW", "Wollongong, NSW", "Parramatta, NSW"
        ],
        "victoria": [
            "Melbourne, Victoria", "Geelong, Victoria", "Ballarat, Victoria"
        ],
        "england": [
            "London", "Manchester", "Birmingham", "Leeds", "Liverpool", "Bristol", "Sheffield"
        ],
        "auckland": [
            "Auckland Central", "North Shore", "Manukau", "Waitakere", "Ponsonby"
        ],
        "otago": [
            "Queenstown", "Wanaka", "Dunedin", "Arrowtown", "Cromwell"
        ]
    }

    for key, areas in PRESET_SUB_AREAS.items():
        if key in region_lower:
            return areas

    return []
