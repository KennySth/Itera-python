import logging
import urllib.parse
import random
import re
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from app.core.scraper_base import BaseScraper
from app.core.skill_extractor import extract as extract_skills
from app.core.career_classifier import classify as classify_career
from app.core.company_ranker import rank_company
from app.models.schemas import JobOffer

logger = logging.getLogger(__name__)

# ── Common selectors that appear across LinkedIn redesigns ──────────────
# LinkedIn changes CSS classes frequently; we try multiple strategies.
_JOB_CONTAINER_SELECTORS = [
    "ul.jobs-search__results-list",  # Classic layout
    "div.jobs-search-results-list",  # 2023+ layout
    "div.jobs-search-results",  # Alternative container
    "div.scaffold-layout__list-container",  # Newer layout
    "[data-job-search-results]",  # Data-attr based
]

_JOB_CARD_SELECTORS = [
    "li.jobs-search-results__list-item",  # Classic card item
    "li[data-occludable-job-id]",  # Data-attr card
    "div.job-card-container",  # Container-based card
    "article.job-card",  # Article-based
    "li.occludable-update",  # Older layout
    "[data-job-id]",  # Broad data attr
]

_TITLE_SELECTORS = [
    "a.job-card-list__title",  # Classic title link
    "a.job-card-container__link",  # Container title link
    "a[data-anonymize='job-title']",  # Anonymized title
    "span.job-card-container__primary-description",  # Alternative title
    "a.job-card-search__title",  # Search title
    "h3 a",  # Generic fallback
    "a.job-card-search__company-name",  # Sometimes title is here
]

_COMPANY_SELECTORS = [
    "span.job-card-container__primary-description",  # Classic company
    "a.job-card-container__company-name",  # Container company link
    "span[data-anonymize='company-name']",  # Anonymized company
    "a.job-card-search__company-name",  # Search company name
    "span.job-card-list__company-name",  # List company name
    '[data-anonymize="company-name"]',  # Broad data-attr
]

_LINK_SELECTORS = [
    "a.job-card-list__title",
    "a.job-card-container__link",
    "a.base-card__full-link",
    "a[data-anonymize='job-title']",
    "a.job-card-search__title",
]

_LOCATION_SELECTORS = [
    "span.job-card-container__metadata-item",
    "li.job-card-container__metadata-item",
    "span.job-card-list__location",
    '[data-anonymize="location"]',
]


class LinkedInScraper(BaseScraper):
    def __init__(self) -> None:
        super().__init__(source_name="LinkedIn", base_url="https://www.linkedin.com")

    def _generate_mock_vector(self) -> List[float]:
        return [round(random.uniform(-1, 1), 4) for _ in range(5)]

    async def _maybe_accept_cookies(self, page) -> None:
        """Click cookie consent button if it appears."""
        cookie_selectors = [
            'button[action="accept"]',
            'button:has-text("Aceptar")',
            'button:has-text("Accept")',
            'button:has-text("Permitir")',
            ".cookies-consent button:first-child",
            "#cookieconsent button",
            '[data-tracking-control-name="cookies-accept"]',
        ]
        for sel in cookie_selectors:
            try:
                btn = await page.wait_for_selector(sel, timeout=3000)
                if btn:
                    await btn.click()
                    await page.wait_for_timeout(500)
                    logger.info("Cookie consent accepted")
                    return
            except (PlaywrightTimeout, Exception):
                continue

    def _extract_job_cards(
        self, soup: BeautifulSoup
    ) -> List[Tuple[str, str, str, str]]:
        """
        Extract (title, company, url, location) tuples from parsed page.
        Tries multiple selector strategies in order of specificity.
        """
        results: List[Tuple[str, str, str, str]] = []
        seen_urls: set = set()

        # Strategy 1: Find job cards using broad selectors
        cards = []
        for container_sel in _JOB_CONTAINER_SELECTORS:
            container = soup.select_one(container_sel)
            if container:
                for card_sel in _JOB_CARD_SELECTORS:
                    cards = container.select(card_sel)
                    if cards:
                        logger.info(
                            f"Found {len(cards)} cards via container"
                            f" '{container_sel}' + card '{card_sel}'"
                        )
                        break
                if cards:
                    break

        # Fallback: try card selectors directly on whole page
        if not cards:
            for card_sel in _JOB_CARD_SELECTORS:
                cards = soup.select(card_sel)
                if cards:
                    logger.info(
                        f"Found {len(cards)} cards via direct selector '{card_sel}'"
                    )
                    break

        # If still no cards, try broader listing approach
        if not cards:
            # Look for any <li> elements inside the main content area
            main_area = soup.select_one(
                "main, .jobs-search-results, .scaffold-layout__list"
            )
            if main_area:
                cards = main_area.find_all("li", recursive=False)
                logger.info(f"Fallback: found {len(cards)} li candidates in main area")

        for card in cards:
            try:
                title = ""
                company = ""
                link = ""
                location = ""

                # Title: try selectors
                for sel in _TITLE_SELECTORS:
                    tag = card.select_one(sel)
                    if tag:
                        title = tag.get_text().strip()
                        break
                # Fallback: any <a> with job-related text
                if not title:
                    for a_tag in card.find_all("a", href=True):
                        text = a_tag.get_text().strip()
                        if text and len(text) > 5:
                            title = text
                            link = a_tag["href"]
                            break

                # Company
                for sel in _COMPANY_SELECTORS:
                    tag = card.select_one(sel)
                    if tag:
                        company = tag.get_text().strip()
                        break
                if not company:
                    # Try any small text that isn't the title
                    small_tags = card.find_all(["span", "small", "p"])
                    for st in small_tags:
                        text = st.get_text().strip()
                        if text and text != title and len(text) > 2:
                            company = text
                            break
                company = company or "Confidencial"

                # Link
                for sel in _LINK_SELECTORS:
                    tag = card.select_one(sel)
                    if tag and tag.get("href"):
                        link = tag["href"]
                        break
                if not link:
                    a_tag = card.find("a", href=True)
                    if a_tag:
                        link = a_tag["href"]

                # Location
                for sel in _LOCATION_SELECTORS:
                    tag = card.select_one(sel)
                    if tag:
                        location = tag.get_text().strip()
                        break

                # Clean and deduplicate
                if title and link and link not in seen_urls:
                    # Clean link: remove query params except for tracking
                    clean_link = link.split("?")[0] if "?" in link else link
                    if not clean_link.startswith("http"):
                        clean_link = (
                            f"https://www.linkedin.com{clean_link}"
                            if clean_link.startswith("/")
                            else clean_link
                        )
                    seen_urls.add(link)
                    results.append((title, company, clean_link, location))

            except Exception as e:
                logger.warning(f"Error parsing individual card: {e}")
                continue

        return results

    async def scrape(self, query: str, use_ai: bool = False) -> List[JobOffer]:
        """
        Scrape LinkedIn for job offers using Playwright (headless Chromium).

        Args:
            query: Búsqueda (ej. "Python Developer")
            use_ai: Si True, usa IA para extracción de skills y clasificación.
        """
        search_query = urllib.parse.quote(query)
        url = (
            f"{self.base_url}/jobs/search"
            f"?keywords={search_query}&location=Per%C3%BA"
            f"&f_TPR=r604800"  # Past 7 days
        )

        offers: List[JobOffer] = []
        expiration_date = datetime.utcnow() + timedelta(days=30)

        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                    ],
                )
                context = await browser.new_context(
                    viewport={"width": 1366, "height": 768},
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    locale="es-ES",
                )
                page = await context.new_page()

                logger.info(f"Navigating to LinkedIn search: {url}")
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)

                # Short human-like delay
                await page.wait_for_timeout(2000)

                # Accept cookies if popup appears
                await self._maybe_accept_cookies(page)

                # Wait additional time for JS rendering
                await page.wait_for_timeout(3000)

                # Scroll down to trigger lazy loading
                await page.evaluate("window.scrollTo(0, 300)")
                await page.wait_for_timeout(1500)
                await page.evaluate("window.scrollTo(0, 600)")
                await page.wait_for_timeout(1000)

                # Check if we hit a sign-in wall (log-only, still try to parse)
                signin_indicators = [
                    "div.auth-wall",
                    "div.sign-in-modal",
                    'form[action*="login"]',
                    "h2:has-text('Inicia sesión')",
                    "h2:has-text('Sign in')",
                ]
                for sel in signin_indicators:
                    try:
                        el = await page.wait_for_selector(sel, timeout=2000)
                        if el and await el.is_visible():
                            logger.warning(
                                "LinkedIn sign-in wall detected, results may be limited"
                            )
                            break
                    except (PlaywrightTimeout, Exception):
                        continue

                # Get page HTML
                html = await page.content()
                await browser.close()

                if not html:
                    logger.warning("Empty page content from LinkedIn")
                    return []

                # Parse with BeautifulSoup
                soup = BeautifulSoup(html, "html.parser")

                # Extract job cards
                job_data = self._extract_job_cards(soup)
                logger.info(f"Extracted {len(job_data)} job entries from LinkedIn")

                for title, company, link, location in job_data:
                    try:
                        # Skip very short titles (likely not real jobs)
                        if len(title) < 5:
                            continue

                        # Clean title: remove common prefixes
                        title = re.sub(
                            r"^(¡|Únete a|Buscamos|Se busca|Vacante:?\s*)",
                            "",
                            title,
                            flags=re.IGNORECASE,
                        ).strip()

                        # ── Enrichment pipeline ──
                        skill_result = extract_skills(
                            title=title,
                            company=company,
                            short_description="",
                            use_ai=use_ai,
                        )
                        skills = skill_result.skills
                        if not skills and query:
                            skills = [query.capitalize()]

                        career_result = classify_career(title, company, use_ai=use_ai)
                        company_rank = rank_company(company)

                        offer = JobOffer(
                            puesto=title,
                            empresa=company,
                            fuente=self.source_name,
                            url_origen=link,
                            habilidades_requeridas=skills,
                            salario_normalizado_usd=None,
                            vector_semantico=self._generate_mock_vector(),
                            fecha_expiracion=expiration_date,
                            categoria_carrera=career_result.category_id,
                            categoria_carrera_nombre=(career_result.category_name),
                            company_tier=company_rank.tier,
                            skill_extraction_method=skill_result.method,
                        )
                        offers.append(offer)
                    except Exception as e:
                        logger.error(f"Error enriching LinkedIn entry '{title}': {e}")
                        continue

        except Exception as e:
            logger.error(f"LinkedIn scraper failed: {e}", exc_info=True)

        return offers
