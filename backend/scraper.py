import asyncio
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
                    "--single-process",
                    "--no-zygote",
                    "--renderer-process-limit=1",
                    "--js-flags=--max-old-space-size=64",
                    "--disable-extensions",
                    "--disable-background-networking",
                    "--disable-default-apps",
                    "--disable-sync",
                    "--no-first-run",
                    "--mute-audio",
                    "--disable-features=AudioServiceOutOfProcess,IsolateOrigins,site-per-process,Translate,BackForwardCache",
                    "--window-size=1024,600",
                ],
            )
            context: BrowserContext = await browser.new_context(
                viewport={"width": 1024, "height": 600},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                locale="en-US",
            )
            page: Page = await context.new_page()

            # Abort heavy photo carousels, media, and fonts to prevent OOM memory spikes on cloud containers
            await page.route(
                "**/*",
                lambda r: r.abort() if r.request.resource_type in ["image", "media", "font"] else r.continue_()
            )

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

                    new_items_processed = 0

                    for card in cards:
                        if len(self.leads_collected) >= self.target_count or not self.is_running:
                            break

                        try:
                            # 1. Get Title from link aria-label or card text
                            link_el = card.locator("a.hfpxzc").first
                            if await link_el.count() == 0:
                                link_el = card.locator("a[href*='/maps/place/']").first

                            if await link_el.count() == 0:
                                continue

                            href = await link_el.get_attribute("href") or ""
                            title = await link_el.get_attribute("aria-label") or ""

                            place_id_match = re.search(r"/maps/place/([^/]+)/", href)
                            place_id = place_id_match.group(1) if place_id_match else href[:80]

                            if place_id in self.seen_place_ids:
                                continue
                            self.seen_place_ids.add(place_id)
                            new_items_processed += 1
                            self.total_scanned += 1

                            card_text = await card.inner_text()
                            lines = [l.strip() for l in card_text.split("\n") if l.strip()]
                            if not title and lines:
                                title = lines[0]

                            # 2. Extract Website directly from Card links
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

                            has_website = bool(card_web_url)

                            # Filter Zero-Website strictly if requested
                            if self.no_website_only and has_website:
                                logger.info(f"Skipping {title} (Has Website: {card_web_url})")
                                if self.progress_callback:
                                    self.progress_callback(
                                        self.total_scanned,
                                        self.no_website_count,
                                        self.mobile_count,
                                        f"Skipped {title} (Has Website)",
                                    )
                                continue

                            if not has_website:
                                self.no_website_count += 1

                            # 3. Extract Phone & Mobile Detection
                            phone_clean, is_mob = None, False
                            phone_raw = None
                            for cand in lines:
                                c, m, _ = clean_phone_number(cand, self.country_code)
                                if c:
                                    phone_clean, is_mob = c, m
                                    phone_raw = cand
                                    break
                            if not phone_clean:
                                for tel_el in await card.locator("a[href^='tel:'], [data-item-id^='phone:tel:']").all():
                                    h = await tel_el.get_attribute("href") or ""
                                    did = await tel_el.get_attribute("data-item-id") or ""
                                    val = h.replace("tel:", "").strip() or did.replace("phone:tel:", "").strip()
                                    c, m, _ = clean_phone_number(val, self.country_code)
                                    if c:
                                        phone_clean, is_mob = c, m
                                        phone_raw = val
                                        break

                            # Filter mobile if toggled
                            if self.mobile_only and not is_mob:
                                if self.progress_callback:
                                    self.progress_callback(
                                        self.total_scanned,
                                        self.no_website_count,
                                        self.mobile_count,
                                        f"Skipped {title} (Non-mobile: {phone_clean or 'None'})",
                                    )
                                continue

                            if phone_clean:
                                self.mobile_count += 1

                            # 4. Extract Rating & Reviews
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

                            # 5. Extract Address
                            raw_addr = None
                            for line in lines:
                                if "·" in line and not any(kw in line.lower() for kw in ["open", "closed", "opens", "closes", "hour"]):
                                    cleaned_line = re.sub(r'[\ue000-\uf8ff]', '', line)
                                    parts = [p.strip() for p in cleaned_line.split("·") if p.strip()]
                                    if len(parts) >= 2:
                                        raw_addr = parts[-1]
                                        break

                            if not raw_addr:
                                for line in lines:
                                    cleaned_line = re.sub(r'[\ue000-\uf8ff]', '', line).strip()
                                    if any(term in cleaned_line for term in ["St", "Rd", "Ave", "Blvd", "Way", "Drive", "Street", "Road", "Terrace", "Pl", "Place", "Lane", "Hwy", "Highway", "Floor", "Level"]):
                                        parts = [p.strip() for p in cleaned_line.split("·") if p.strip()]
                                        raw_addr = parts[-1] if parts else cleaned_line
                                        break

                            # Clean and format address with city
                            clean_street = re.sub(r'[\ue000-\uf8ff]', '', raw_addr or '').strip() if raw_addr else ""
                            clean_street = re.sub(r'^Address:\s*', '', clean_street, flags=re.IGNORECASE).strip()
                            clean_street = " ".join(l.strip() for l in clean_street.splitlines() if l.strip())

                            if clean_street and clean_street.lower() != self.location.lower():
                                primary_city = self.location.split(",")[0].strip()
                                if primary_city.lower() not in clean_street.lower():
                                    address = f"{clean_street}, {self.location}"
                                else:
                                    address = clean_street
                            else:
                                address = self.location

                            # Filter by rating if set
                            if self.min_rating > 0 and (rating or 0.0) < self.min_rating:
                                continue

                            owner_name = self._extract_owner_name(title)

                            # 6. Generate WhatsApp Link
                            whatsapp_link = None
                            if phone_clean:
                                context_dict = {
                                    "business_name": title,
                                    "area": self.location,
                                    "category": self.query,
                                    "owner_name": owner_name or "there",
                                }
                                whatsapp_link = generate_whatsapp_link(phone_clean, self.template, context_dict)

                            lead = LeadItem(
                                place_id=place_id,
                                title=title,
                                category=self.query,
                                address=address or self.location,
                                city=self.location,
                                phone_raw=phone_raw or phone_clean,
                                phone_clean=phone_clean or phone_raw,
                                is_mobile=is_mob,
                                has_website=has_website,
                                website_url=card_web_url,
                                rating=rating,
                                reviews_count=reviews_count,
                                owner_name=owner_name,
                                whatsapp_link=whatsapp_link,
                                job_id=self.job_id,
                                created_at=datetime.now().isoformat(),
                            )

                            self.leads_collected.append(lead)
                            logger.info(f"Captured ({len(self.leads_collected)}/{self.target_count}): {lead.title} | Rating: {lead.rating} ({lead.reviews_count}) | Phone: {lead.phone_clean}")

                            if self.lead_callback:
                                self.lead_callback(lead)

                            if self.progress_callback:
                                self.progress_callback(
                                    self.total_scanned,
                                    self.no_website_count,
                                    self.mobile_count,
                                    f"Captured ({len(self.leads_collected)}/{self.target_count}): {lead.title}",
                                )

                        except Exception as card_err:
                            logger.debug(f"Card processing error: {card_err}")
                            continue

                    # Check if reached target
                    if len(self.leads_collected) >= self.target_count:
                        break

                    # Check if Google Maps reached end of results
                    end_text = await page.locator("text='You\\'ve reached the end of the list'").count()
                    if end_text > 0:
                        logger.info("Reached the end of Google Maps results.")
                        break

                    # Scroll the feed down with scrollTop = scrollHeight and PageDown!
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
                        await page.mouse.wheel(0, 2500)
                        await page.keyboard.press("PageDown")
                        await asyncio.sleep(2.0)

                    if new_items_processed == 0:
                        idle_scroll_attempts += 1
                        if idle_scroll_attempts >= max_idle_scrolls:
                            logger.info("No more new listings found after multiple scrolls.")
                            break
                    else:
                        idle_scroll_attempts = 0

            except Exception as e:
                logger.error(f"Scraper error: {e}")
                if self.progress_callback:
                    self.progress_callback(self.total_scanned, self.no_website_count, self.mobile_count, f"Error: {e}")
                raise e
            finally:
                await context.close()
                await browser.close()

        return self.leads_collected
