import requests
import logging
from typing import List, Dict, Any

logger = logging.getLogger("lead_finder.geocoding")

# Using OpenStreetMap Nominatim / Photon global geocoder (100% Free, worldwide down to neighborhood level, no API key needed)
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
PHOTON_URL = "https://photon.komoot.io/api/"

HEADERS = {
    "User-Agent": "LeadFinderGlobalB2B/1.0 (contact@leadfinder.local)"
}


def search_locations_global(query: str, limit: int = 8) -> List[Dict[str, Any]]:
    """
    Searches worldwide locations, cities, states, regions, and neighborhoods.
    Returns clean suggestions with display name, city, state, country, country_code, lat, lon.
    """
    if not query or len(query.strip()) < 2:
        return []

    q = query.strip()
    results = []

    # Try Photon first (super fast global search built on OpenStreetMap)
    try:
        resp = requests.get(
            PHOTON_URL,
            params={"q": q, "limit": limit, "lang": "en"},
            headers=HEADERS,
            timeout=5
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

                # Build clean display label
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

    # Fallback to Nominatim
    try:
        resp = requests.get(
            NOMINATIM_URL,
            params={"q": q, "format": "json", "addressdetails": 1, "limit": limit, "accept-language": "en"},
            headers=HEADERS,
            timeout=5
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
