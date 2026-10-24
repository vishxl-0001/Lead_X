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
                    "--disable-infobars",
                    "--window-size=1366,768",
                ],
            )
            context: BrowserContext = await browser.new_context(
                viewport={"width": 1366, "height": 768},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                locale="en-US",
            )
            page: Page = await context.new_page()

            try:
                try:
                    await stealth_async(page)
                except Exception:
                    pass

                if self.progress_callback:
                    self.progress_callback(0, 0, 0, f"Loading Google Maps around {self.location} ({self.radius_km} km radius)...")

                await page.goto(maps_url, timeout=35000, wait_until="domcontentloaded")
                await asyncio.sleep(2.0)

                # Dismiss consent dialogs if present
                for btn_text in ["Accept all", "I agree", "Agree", "Reject all"]:
                    try:
                        consent_btn = page.locator(f"button:has-text('{btn_text}')").first
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
                            if not title:
                                lines = card_text.split("\n")
                                title = lines[0].strip() if lines else "Business"

                            # 2. Extract Rating from card (e.g. '4.8 stars' or span '4.8')
                            rating = None
                            star_el = card.locator('[aria-label*="star" i]').first
                            if await star_el.count() > 0:
                                s_aria = await star_el.get_attribute("aria-label") or ""
                                m_star = re.search(r'([1-5]\.[0-9])', s_aria)
                                if m_star:
                                    rating = float(m_star.group(1))

                            if not rating:
                                for s_txt in await card.locator("span").all_inner_texts():
                                    if re.match(r'^[1-5]\.[0-9]$', s_txt.strip()):
                                        rating = float(s_txt.strip())
                                        break

                            # 3. Extract Reviews Count
                            reviews_count = None
                            m_rev = re.search(r'\(([0-9,KM\.]+)\)', card_text)
                            if m_rev:
                                raw_rev = m_rev.group(1).replace(",", "")
                                if "k" in raw_rev.lower():
                                    reviews_count = int(float(raw_rev.lower().replace("k", "")) * 1000)
                                else:
                                    reviews_count = int(float(raw_rev))

                            # 4. Check Website Presence & URL on Feed Card first
                            card_web_url = None
                            for w_sel in ["a[data-value='Website']", "a[aria-label*='website' i]", "a[data-tooltip*='website' i]"]:
                                w_el = card.locator(w_sel).first
                                if await w_el.count() > 0:
                                    h = await w_el.get_attribute("href")
                                    if h and h.startswith("http") and "google.com" not in h and "gstatic.com" not in h:
                                        card_web_url = h
                                        break

                            # 5. Extract Phone from Feed Card (DOM or Text)
                            card_phone = None
                            for tel_el in await card.locator("a[href^='tel:'], [data-item-id^='phone:tel:']").all():
                                h = await tel_el.get_attribute("href") or ""
                                did = await tel_el.get_attribute("data-item-id") or ""
                                val = h.replace("tel:", "").strip() or did.replace("phone:tel:", "").strip()
                                clean_test, _, _ = clean_phone_number(val, self.country_code)
                                if clean_test:
                                    card_phone = clean_test
                                    break

                            if not card_phone:
                                for cand in PHONE_PATTERN.findall(card_text):
                                    if sum(c.isdigit() for c in cand) >= 7 and not cand.startswith(("202", "199")) and ":" not in cand:
                                        clean_test, _, _ = clean_phone_number(cand, self.country_code)
                                        if clean_test:
                                            card_phone = clean_test
                                            break

                            # 6. Click card to open the detail panel for deep verification
                            await card.scroll_into_view_if_needed()
                            await link_el.click()
                            await asyncio.sleep(1.5)

                            detail_pane = page.locator('div[role="main"][aria-label]').first
                            has_detail = await detail_pane.count() > 0

                            detail_web_url = None
                            detail_phone = None
                            detail_address = None
                            detail_text = ""

                            if has_detail:
                                detail_text = await detail_pane.inner_text()

                                # Deep Website Verification in Detail Pane
                                for we in await detail_pane.locator("a[data-item-id='authority'], a[aria-label*='website' i], a[data-tooltip*='website' i], a[aria-label*='Website' i]").all():
                                    u = await we.get_attribute("href")
                                    if u and u.startswith("http") and "google.com" not in u and "gstatic.com" not in u:
                                        detail_web_url = u
                                        break

                                if not detail_web_url:
                                    # Check Io6YTe rows for domain names
                                    for row in await detail_pane.locator("div.Io6YTe, span.Io6YTe").all_inner_texts():
                                        dm = DOMAIN_PATTERN.search(row)
                                        if dm and not any(ign in row.lower() for ign in ["google", "facebook", "instagram", "twitter", "apple"]):
                                            detail_web_url = f"https://{dm.group(1)}"
                                            break

                                # Deep Phone Extraction in Detail Pane
                                for pel in await detail_pane.locator("a[href^='tel:'], [data-item-id^='phone:tel:'], [aria-label*='Phone:' i], button[data-tooltip*='phone' i]").all():
                                    href = await pel.get_attribute("href") or ""
                                    did = await pel.get_attribute("data-item-id") or ""
                                    aria = await pel.get_attribute("aria-label") or ""
                                    for s in [href.replace("tel:", ""), did.replace("phone:tel:", ""), aria.replace("Phone:", "")]:
                                        clean_test, _, _ = clean_phone_number(s, self.country_code)
                                        if clean_test:
                                            detail_phone = clean_test
                                            break
                                    if detail_phone:
                                        break

                                if not detail_phone:
                                    for row in await detail_pane.locator("div.Io6YTe, span.Io6YTe").all_inner_texts():
                                        for cand in PHONE_PATTERN.findall(row):
                                            if sum(c.isdigit() for c in cand) >= 7 and not cand.startswith(("202", "199")) and ":" not in cand:
                                                clean_test, _, _ = clean_phone_number(cand, self.country_code)
                                                if clean_test:
                                                    detail_phone = clean_test
                                                    break
                                        if detail_phone:
                                            break

                                if not detail_phone and detail_text:
                                    for cand in PHONE_PATTERN.findall(detail_text):
                                        if sum(c.isdigit() for c in cand) >= 7 and not cand.startswith(("202", "199")) and ":" not in cand:
                                            clean_test, _, _ = clean_phone_number(cand, self.country_code)
                                            if clean_test:
                                                detail_phone = clean_test
                                                break

                                # Detail Address
                                addr_el = detail_pane.locator("[data-item-id='address'], [aria-label*='Address:' i]").first
                                if await addr_el.count() > 0:
                                    detail_address = (await addr_el.inner_text()).strip()
                                if not detail_address:
                                    for row in (await detail_pane.locator("div.Io6YTe").all_inner_texts())[:2]:
                                        if any(term in row for term in ["St", "Rd", "Ave", "Blvd", "Way", "Drive", "Street", "Road", "Terrace", "Pl", "Place", "Hwy", "Lane", "No"]):
                                            detail_address = row.strip()
                                            break

                                # Detail Rating
                                if not rating:
                                    f7_el = detail_pane.locator("div.F7nice span[aria-hidden='true']").first
                                    if await f7_el.count() > 0:
                                        t = (await f7_el.inner_text()).strip()
                                        if re.match(r'^[1-5]\.[0-9]$', t):
                                            rating = float(t)

                                # Detail Reviews
                                if not reviews_count:
                                    for rev_el in await detail_pane.locator("button[aria-label*='review' i], span[aria-label*='review' i]").all():
                                        r_aria = await rev_el.get_attribute("aria-label") or ""
                                        m_rev_aria = re.search(r'([0-9,]+)\s+review', r_aria, re.IGNORECASE)
                                        if m_rev_aria:
                                            reviews_count = int(m_rev_aria.group(1).replace(",", ""))
                                            break
                                    if not reviews_count:
                                        m_rev2 = re.search(r'\b([0-9,]+)\s+reviews?\b', detail_text, re.IGNORECASE)
                                        if m_rev2:
                                            reviews_count = int(m_rev2.group(1).replace(",", ""))

                            # 7. Unified Merged Resolution
                            website_url = detail_web_url or card_web_url
                            has_website = bool(website_url)

                            # If user strictly wants Zero-Website leads and this business has one, skip
                            if self.no_website_only and has_website:
                                logger.info(f"Skipping {title} (Has Website: {website_url})")
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

                            # Phone resolution
                            phone_raw = detail_phone or card_phone
                            phone_clean, is_mob, info = clean_phone_number(phone_raw or "", self.country_code)

                            # Filter mobile if toggled
                            if self.mobile_only and not is_mob:
                                if self.progress_callback:
                                    self.progress_callback(
                                        self.total_scanned,
                                        self.no_website_count,
                                        self.mobile_count,
                                        f"Skipped {title} (Landline: {phone_raw})",
                                    )
                                continue

                            if phone_clean:
                                self.mobile_count += 1

                            # Address resolution & cleaning
                            raw_addr = detail_address
                            if not raw_addr:
                                for line in card_text.split("\n"):
                                    if any(term in line for term in ["St", "Rd", "Ave", "Blvd", "Way", "Drive", "Street", "Road", "Terrace", "Pl", "Place"]):
                                        if " · " in line:
                                            raw_addr = line.split(" · ")[-1].strip()
                                        else:
                                            raw_addr = line.strip().lstrip("·").strip()
                                        break
                            address = re.sub(r'[\ue000-\uf8ff]', '', raw_addr or '').strip() if raw_addr else self.location
                            address = re.sub(r'^Address:\s*', '', address, flags=re.IGNORECASE).strip()
                            address = " ".join(line.strip() for line in address.splitlines() if line.strip())

                            # Filter by rating if set
                            if self.min_rating > 0 and (rating or 0.0) < self.min_rating:
                                continue

                            owner_name = self._extract_owner_name(title)

                            # 10. Generate WhatsApp Link
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
                                phone_raw=phone_raw,
                                phone_clean=phone_clean or phone_raw,
                                is_mobile=is_mob,
                                has_website=has_website,
                                website_url=website_url,
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

                    # Scroll the feed down to load the next batch of cards!
                    if await feed_locator.count() > 0:
                        if self.progress_callback:
                            self.progress_callback(
                                self.total_scanned,
                                self.no_website_count,
                                self.mobile_count,
                                f"Scrolling for more leads ({len(self.leads_collected)}/{self.target_count} collected)...",
                            )
                        await feed_locator.evaluate("el => el.scrollBy(0, 2500)")
                        await asyncio.sleep(1.8)
                    else:
                        await page.mouse.wheel(0, 2500)
                        await asyncio.sleep(1.8)

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
            finally:
                await context.close()
                await browser.close()

        return self.leads_collected
