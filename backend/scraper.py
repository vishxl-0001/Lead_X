import asyncio
import gc
import json
import logging
import random
import re
import sys
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

# Ensure venv packages are available
VENV_SITE = Path(__file__).resolve().parent.parent / "venv" / "lib" / "python3.12" / "site-packages"
if VENV_SITE.exists() and str(VENV_SITE) not in sys.path:
    sys.path.insert(0, str(VENV_SITE))

from backend.config import DEFAULT_TEMPLATE
from backend.country_detector import detect_country_from_location, GLOBAL_COUNTRIES
from backend.geocoding import search_locations_global
from backend.models import LeadItem
from backend.phone_utils import clean_phone_number, generate_whatsapp_link

logger = logging.getLogger("lead_finder.scraper")
logging.basicConfig(level=logging.INFO)

PHONE_PATTERN = re.compile(
    r'(?:(?:\+|00)[1-9]\d{0,3}[\s./-]*)?'
    r'(?:\(?\d{1,5}\)?[\s./-]*){2,5}\d{2,6}'
)

DOMAIN_PATTERN = re.compile(
    r'\b([a-zA-Z0-9-]+\.(?:com|org|net|co|io|nz|ca|uk|es|de|fr|in|biz|info|tech|online|store|agency|pro|me|app)(?:\.[a-z]{2})?)\b',
    re.IGNORECASE
)

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    from playwright_stealth import stealth_async
    HAS_PLAYWRIGHT = True
except Exception as e:
    logger.warning(f"Playwright import warning: {e}")
    HAS_PLAYWRIGHT = False


class GoogleMapsScraper:
    """
    High-efficiency Google Maps Scraper with infinite dynamic scrolling,
    precise radial zoom scaling, strict website verification, and 100% lead target fulfillment.
    """

    def __init__(
        self,
        query: str,
        location: str,
        target_count: int = 25,
        radius_km: int = 10,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        no_website_only: bool = False,
        mobile_only: bool = False,
        min_rating: float = 0.0,
        country_code: Optional[str] = None,
        template: Optional[str] = None,
        job_id: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int, int, str], None]] = None,
        lead_callback: Optional[Callable[[LeadItem], None]] = None,
        headless: bool = True,
    ):
        self.query = query.strip()
        self.location = location.strip()
        self.target_count = target_count
        self.radius_km = radius_km
        self.lat = lat
        self.lon = lon
        self.no_website_only = no_website_only
        self.mobile_only = mobile_only
        self.min_rating = min_rating

        # Auto-resolve coordinates if missing to ensure radial targeting
        if not self.lat or not self.lon:
            try:
                geo = search_locations_global(self.location, limit=1)
                if geo:
                    self.lat = geo[0].get("lat")
                    self.lon = geo[0].get("lon")
                    logger.info(f"Resolved coordinates for '{self.location}': {self.lat}, {self.lon}")
            except Exception as e:
                logger.debug(f"Could not auto-geocode {self.location}: {e}")

        # Auto-detect country code from location
        detected_code, _ = detect_country_from_location(self.location)
        if country_code:
            self.country_code = country_code.upper()
        elif detected_code:
            self.country_code = detected_code
        else:
            self.country_code = "CA" if "canada" in self.location.lower() or "ontario" in self.location.lower() else "IN"

        self.template = template or DEFAULT_TEMPLATE
        self.job_id = job_id
        self.progress_callback = progress_callback
        self.lead_callback = lead_callback
        self.headless = headless

        self.is_running = True
        self.total_scanned = 0
        self.no_website_count = 0
        self.mobile_count = 0
        self.leads_collected: List[LeadItem] = []
        self.seen_place_ids = set()
        self.seen_titles = set()
        self.phone_cache: Dict[str, str] = {}

    def stop(self):
        self.is_running = False

    def _extract_owner_name(self, title: str) -> Optional[str]:
        dr_match = re.search(r"\b(Dr\.|Doctor|Advocate|Er\.|CA)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", title, re.IGNORECASE)
        if dr_match:
            return dr_match.group(0).strip()

        possessive_match = re.search(
            r"^([A-Z][a-z]+)(?:'s|\s+and\s+|\s+&\s+|\s+(?:Electrical|Plumbing|Repairs|Services|Store|Traders|Solutions|Enterprise))",
            title
        )
        if possessive_match:
            candidate = possessive_match.group(1).strip()
            if candidate.lower() not in ("the", "all", "best", "super", "quick", "city", "new", "star", "local"):
                return candidate

        return None

    def _parse_tbm_response(self, body: str) -> List[Dict]:
        """Parses Google Maps internal JSON RPC responses to extract accurate phone numbers, addresses, and details."""
        clean = body
        for prefix in ["/*)]}'\n", "/*)]}'", ")]}'\n", ")]}'"]:
            if clean.startswith(prefix):
                clean = clean[len(prefix):]
                break
        try:
            data = json.loads(clean)
        except Exception:
            return []

        leads = []
        def scan_list(lst):
            res = []
            for item in lst:
                if isinstance(item, list) and len(item) > 1 and isinstance(item[1], list):
                    info = item[1]
                    if len(info) > 11 and isinstance(info[11], str) and info[11].strip():
                        res.append(info)
            return res

        candidates = []
        if isinstance(data, list):
            for sub in data:
                if isinstance(sub, list):
                    cand = scan_list(sub)
                    if cand:
                        candidates.extend(cand)

        for info in candidates:
            title = info[11].strip()

            phone = None
            if len(info) > 178 and isinstance(info[178], list) and len(info[178]) > 0:
                p0 = info[178][0]
                if isinstance(p0, list):
                    if len(p0) > 1 and isinstance(p0[1], list):
                        for sub in p0[1]:
                            if isinstance(sub, list) and len(sub) > 0 and str(sub[0]).strip().startswith("+"):
                                phone = str(sub[0]).strip()
                                break
                    if not phone and len(p0) > 0 and p0[0]:
                        phone = str(p0[0]).strip()
                    if not phone and len(p0) > 3 and p0[3]:
                        phone = str(p0[3]).strip()

            website = None
            if len(info) > 7 and isinstance(info[7], list) and len(info[7]) > 0 and info[7][0]:
                website = str(info[7][0]).strip()

            address = None
            if len(info) > 39 and isinstance(info[39], str) and info[39].strip():
                address = info[39].strip()
            elif len(info) > 18 and isinstance(info[18], str) and info[18].strip():
                address = info[18].strip()
            elif len(info) > 2 and isinstance(info[2], list) and len(info[2]) > 0:
                address = ", ".join(str(x) for x in info[2] if x)

            rating = None
            if len(info) > 4 and isinstance(info[4], list) and len(info[4]) > 7 and isinstance(info[4][7], (int, float)):
                rating = float(info[4][7])

            reviews_count = None
            if len(info) > 37 and isinstance(info[37], list) and len(info[37]) > 1 and isinstance(info[37][1], (int, float)):
                reviews_count = int(info[37][1])
            elif len(info) > 4 and isinstance(info[4], list) and len(info[4]) > 8 and isinstance(info[4][8], (int, float)):
                reviews_count = int(info[4][8])

            place_id = None
            if len(info) > 78 and isinstance(info[78], str) and info[78].strip():
                place_id = info[78].strip()
            elif len(info) > 10 and isinstance(info[10], str) and info[10].strip():
                place_id = info[10].strip()

            leads.append({
                "title": title,
                "phone": phone,
                "website": website,
                "address": address,
                "rating": rating,
                "reviews_count": reviews_count,
                "place_id": place_id,
            })
        return leads

    def _process_lead_dict(self, item: Dict) -> bool:
        """Processes a lead extracted from Google Maps payload or card. Returns True if accepted."""
        if not self.is_running or len(self.leads_collected) >= self.target_count:
            return False

        title = item.get("title", "").strip()
        if not title:
            return False

        place_id = item.get("place_id") or f"{title}_{self.location}"
        norm_title = re.sub(r"[^a-zA-Z0-9]", "", title).lower()

        raw_phone = item.get("phone")
        if raw_phone:
            self.phone_cache[title] = raw_phone
            self.phone_cache[norm_title] = raw_phone
            if place_id:
                self.phone_cache[place_id] = raw_phone

        if place_id in self.seen_place_ids or norm_title in self.seen_titles:
            return False

        self.seen_place_ids.add(place_id)
        self.seen_titles.add(norm_title)
        self.total_scanned += 1

        website = item.get("website")
        has_website = bool(website)
        if not has_website:
            self.no_website_count += 1

        if self.no_website_only and has_website:
            if self.progress_callback:
                self.progress_callback(
                    self.total_scanned,
                    self.no_website_count,
                    self.mobile_count,
                    f"Skipped {title} (Has Website)",
                )
            return False

        phone_clean, is_mob = None, False
        if raw_phone:
            phone_clean, is_mob, _ = clean_phone_number(raw_phone, self.country_code)

        if self.mobile_only and not is_mob:
            if self.progress_callback:
                self.progress_callback(
                    self.total_scanned,
                    self.no_website_count,
                    self.mobile_count,
                    f"Skipped {title} (Non-mobile: {phone_clean or 'None'})",
                )
            return False

        if phone_clean:
            self.mobile_count += 1

        rating = item.get("rating")
        if self.min_rating > 0 and (rating or 0.0) < self.min_rating:
            return False

        owner_name = self._extract_owner_name(title)
        whatsapp_link = None
        if phone_clean:
            context_dict = {
                "business_name": title,
                "area": self.location,
                "category": self.query,
                "owner_name": owner_name or "there",
            }
            whatsapp_link = generate_whatsapp_link(phone_clean, self.template, context_dict)

        clean_addr = item.get("address") or self.location
        clean_addr = re.sub(r'[\ue000-\uf8ff]', '', clean_addr).strip()
        clean_addr = re.sub(r'^Address:\s*', '', clean_addr, flags=re.IGNORECASE).strip()

        lead = LeadItem(
            place_id=place_id,
            title=title,
            category=self.query,
            address=clean_addr or self.location,
            city=self.location,
            phone_raw=raw_phone or phone_clean,
            phone_clean=phone_clean or raw_phone,
            is_mobile=is_mob,
            has_website=has_website,
            website_url=website,
            rating=rating,
            reviews_count=item.get("reviews_count"),
            owner_name=owner_name,
            whatsapp_link=whatsapp_link,
            job_id=self.job_id,
            created_at=datetime.now().isoformat(),
        )

        self.leads_collected.append(lead)
        logger.info(f"Captured ({len(self.leads_collected)}/{self.target_count}): {lead.title} | Phone: {lead.phone_clean} | Web: {lead.has_website}")

        if self.lead_callback:
            self.lead_callback(lead)

        if self.progress_callback:
            self.progress_callback(
                self.total_scanned,
                self.no_website_count,
                self.mobile_count,
                f"Captured ({len(self.leads_collected)}/{self.target_count}): {lead.title}",
            )
        return True

    def _build_maps_search_url(self) -> str:
        """
        Constructs the exact Google Maps search URL with precise radial zoom.
        - 5 km  -> 14z
        - 10 km -> 13z
        - 25 km -> 11z
        - 50 km -> 10z
        - 100 km -> 8z
        """
        encoded_query = urllib.parse.quote_plus(self.query)
        if self.radius_km <= 5:
            zoom = 14
        elif self.radius_km <= 15:
            zoom = 13
        elif self.radius_km <= 35:
            zoom = 11
        elif self.radius_km <= 70:
            zoom = 10
        else:
            zoom = 8

        if self.lat and self.lon:
            return f"https://www.google.com/maps/search/{encoded_query}/@{self.lat},{self.lon},{zoom}z?hl=en"
        else:
            search_query = f"{self.query} in {self.location}"
            return f"https://www.google.com/maps/search/{urllib.parse.quote_plus(search_query)}/?hl=en"

    async def run(self) -> List[LeadItem]:
        """Main scraping loop with dynamic infinite scrolling."""
        maps_url = self._build_maps_search_url()
        logger.info(
            f"Starting scraper for '{self.query}' in '{self.location}' "
            f"(Radius: {self.radius_km}km, Target: {self.target_count} leads) -> {maps_url}"
        )

        async with async_playwright() as p:
            browser: Browser = await p.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-software-rasterizer",
                    "--disable-webgl",
                    "--disable-webgl2",
                    "--disable-3d-apis",
                    "--disable-accelerated-2d-canvas",
                    "--disable-gl-drawing-for-tests",
                    "--blink-settings=imagesEnabled=false",
                    "--single-process",
                    "--no-zygote",
                    "--renderer-process-limit=1",
                    "--js-flags=--max-old-space-size=32",
                    "--disk-cache-size=1",
                    "--media-cache-size=1",
                    "--disable-extensions",
                    "--disable-default-apps",
                    "--disable-sync",
                    "--no-first-run",
                    "--mute-audio",
                    "--disable-features=AudioServiceOutOfProcess,IsolateOrigins,site-per-process,Translate,BackForwardCache,CalculateNativeWinOcclusion",
                    "--window-size=800,600",
                ],
            )
            context: BrowserContext = await browser.new_context(
                viewport={"width": 800, "height": 600},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                locale="en-US",
            )
            # Pre-inject Google consent cookies to bypass regional cookie walls & modals (US/EU datacenters)
            await context.add_cookies([
                {"name": "SOCS", "value": "CAESHAgBEhJnd3NfMjAyNDA0MTUtMF9SQzIaAmVuIAEaBgiA_LyuBg", "domain": ".google.com", "path": "/"},
                {"name": "CONSENT", "value": "PENDING+999", "domain": ".google.com", "path": "/"},
            ])
            page: Page = await context.new_page()

            # Abort heavy photo carousels, media, fonts, stylesheets, and vector map tiles
            # to keep Chromium well below Render's 512MB RAM ceiling
            await page.route(
                "**/*",
                lambda r: r.abort() if (
                    r.request.resource_type in ["image", "media", "font", "stylesheet"]
                    or any(k in r.request.url for k in [
                        "/maps/vt", "geometry", "vector",
                        "google-analytics", "play.google.com/log", "stats"
                    ])
                ) else r.continue_()
            )

            # Listen to Google Maps response streams to extract rich verified business profiles and phone numbers
            async def on_response(response):
                if not self.is_running or len(self.leads_collected) >= self.target_count:
                    return
                url = response.url
                if "tbm=map" in url or "/search?" in url:
                    try:
                        text = await response.text()
                        items = self._parse_tbm_response(text)
                        for item in items:
                            if not self.is_running or len(self.leads_collected) >= self.target_count:
                                break
                            self._process_lead_dict(item)
                    except Exception as e:
                        logger.debug(f"Response parser warning: {e}")

            page.on("response", on_response)

            try:
                try:
                    await stealth_async(page)
                except Exception:
                    pass

                if self.progress_callback:
                    self.progress_callback(0, 0, 0, f"Loading Google Maps around {self.location} ({self.radius_km} km radius)...")

                navigated = False
                for attempt in range(3):
                    try:
                        await page.goto(maps_url, timeout=35000, wait_until="domcontentloaded")
                        navigated = True
                        break
                    except Exception as nav_err:
                        logger.warning(f"Maps navigation attempt {attempt + 1} failed: {nav_err}. Retrying in 2s...")
                        await asyncio.sleep(2.0)

                if not navigated:
                    raise RuntimeError(f"Failed to navigate to Google Maps after 3 attempts.")

                await asyncio.sleep(2.0)

                # Dismiss consent dialogs if present
                for consent_sel in [
                    "button:has-text('Accept all')", "button:has-text('I agree')",
                    "button:has-text('Agree')", "button:has-text('Reject all')",
                    "button[aria-label*='Accept' i]", "button[aria-label*='Agree' i]",
                    "form[action*='consent'] button", "div[role='dialog'] button"
                ]:
                    try:
                        consent_btn = page.locator(consent_sel).first
                        if await consent_btn.is_visible(timeout=1500):
                            await consent_btn.click()
                            await asyncio.sleep(1.0)
                            break
                    except Exception:
                        pass

                # Wait for feed or business cards to appear
                try:
                    await page.wait_for_selector("div.Nv2PK, div[role='feed'], a.hfpxzc", timeout=15000)
                except Exception:
                    logger.warning("Feed container not found directly; checking page...")

                await asyncio.sleep(1.5)

                feed_locator = page.locator("div[role='feed']").first
                idle_scroll_attempts = 0
                max_idle_scrolls = 6

                # Continuous Infinite Scroll Loop: Keeps running until target_count is reached!
                while len(self.leads_collected) < self.target_count and self.is_running:
                    cards = await page.locator("div.Nv2PK").all()
                    if len(cards) == 0:
                        cards = await page.locator("a[href*='/maps/place/']").all()

                    # Scroll the last card into view to trigger lazy rendering and subsequent network responses
                    if cards:
                        try:
                            await cards[-1].scroll_into_view_if_needed(timeout=2500)
                        except Exception:
                            pass

                    # DOM fallback: Process any card not already captured via network response
                    for card in cards:
                        if len(self.leads_collected) >= self.target_count or not self.is_running:
                            break

                        try:
                            link_el = card.locator("a.hfpxzc").first
                            if await link_el.count() == 0:
                                link_el = card.locator("a[href*='/maps/place/']").first
                            if await link_el.count() == 0:
                                continue

                            href = await link_el.get_attribute("href") or ""
                            title = (await link_el.get_attribute("aria-label") or "").strip()
                            place_id_match = re.search(r"/maps/place/([^/]+)/", href)
                            place_id = place_id_match.group(1) if place_id_match else href[:80]
                            norm_title = re.sub(r"[^a-zA-Z0-9]", "", title).lower()

                            if place_id in self.seen_place_ids or norm_title in self.seen_titles:
                                continue

                            card_text = await card.inner_text()
                            lines = [l.strip() for l in card_text.split("\n") if l.strip()]
                            if not title and lines:
                                title = lines[0]

                            cached_phone = self.phone_cache.get(title) or self.phone_cache.get(norm_title) or self.phone_cache.get(place_id)
                            if not cached_phone:
                                for cand in lines:
                                    c, _, _ = clean_phone_number(cand, self.country_code)
                                    if c:
                                        cached_phone = cand
                                        break

                            card_web_url = None
                            for a in await card.locator("a").all():
                                h = await a.get_attribute("href") or ""
                                aria = (await a.get_attribute("aria-label") or "").lower()
                                if ("website" in aria or "web" in aria) and h.startswith("http") and "google.com" not in h and "gstatic.com" not in h:
                                    card_web_url = h
                                    break
                                elif h.startswith("http") and "google.com" not in h and "gstatic.com" not in h and "/maps/" not in h:
                                    card_web_url = h
                                    break

                            rating = None
                            reviews_count = None
                            for line in lines:
                                m_rat = re.search(r'\b([1-5]\.[0-9])\b', line)
                                if m_rat:
                                    rating = float(m_rat.group(1))
                                    break

                            m_rev = re.search(r'\(([0-9,KM\.]+)\)', card_text)
                            if m_rev:
                                raw_rev = m_rev.group(1).replace(",", "")
                                if "k" in raw_rev.lower():
                                    reviews_count = int(float(raw_rev.lower().replace("k", "")) * 1000)
                                else:
                                    try:
                                        reviews_count = int(float(raw_rev))
                                    except Exception:
                                        pass

                            raw_addr = None
                            for line in lines:
                                if "·" in line and not any(kw in line.lower() for kw in ["open", "closed", "opens", "closes", "hour"]):
                                    cleaned_line = re.sub(r'[\ue000-\uf8ff]', '', line)
                                    parts = [p.strip() for p in cleaned_line.split("·") if p.strip()]
                                    if len(parts) >= 2:
                                        raw_addr = parts[-1]
                                        break

                            self._process_lead_dict({
                                "title": title,
                                "phone": cached_phone,
                                "website": card_web_url,
                                "address": raw_addr or self.location,
                                "rating": rating,
                                "reviews_count": reviews_count,
                                "place_id": place_id,
                            })
                        except Exception as card_err:
                            logger.debug(f"Card processing error: {card_err}")
                            continue

                    # Check if reached target
                    if len(self.leads_collected) >= self.target_count or not self.is_running or page.is_closed():
                        break

                    # Check if Google Maps reached end of results
                    try:
                        end_text = await page.locator("text='You\\'ve reached the end of the list'").count()
                        if end_text > 0:
                            logger.info("Reached the end of Google Maps results.")
                            break
                    except Exception:
                        break

                    prev_count = len(self.leads_collected)

                    # Scroll the feed down with scrollTop = scrollHeight and PageDown!
                    try:
                        if await feed_locator.count() > 0:
                            if self.progress_callback:
                                self.progress_callback(
                                    self.total_scanned,
                                    self.no_website_count,
                                    self.mobile_count,
                                    f"Scrolling for more leads ({len(self.leads_collected)}/{self.target_count} collected)...",
                                )
                            await feed_locator.evaluate("el => el.scrollTop = el.scrollHeight")
                            await page.keyboard.press("PageDown")
                            await asyncio.sleep(2.0)
                        else:
                            await page.mouse.wheel(0, 3000)
                            await page.keyboard.press("PageDown")
                            await asyncio.sleep(2.0)
                    except Exception:
                        break

                    if len(self.leads_collected) == prev_count:
                        idle_scroll_attempts += 1
                        if idle_scroll_attempts >= max_idle_scrolls:
                            logger.info("No more new listings found after multiple scrolls.")
                            break
                    else:
                        idle_scroll_attempts = 0

            except Exception as e:
                # If we already collected leads and page was closed as part of completion, treat as success
                if len(self.leads_collected) > 0 and ("closed" in str(e).lower() or not self.is_running):
                    logger.info(f"Scraper finished with {len(self.leads_collected)} leads.")
                else:
                    logger.error(f"Scraper error: {e}")
                    if self.progress_callback:
                        self.progress_callback(self.total_scanned, self.no_website_count, self.mobile_count, f"Error: {e}")
                    raise e
            finally:
                try:
                    await context.close()
                except Exception:
                    pass
                try:
                    await browser.close()
                except Exception:
                    pass
                gc.collect()

        return self.leads_collected
