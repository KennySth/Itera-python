import logging
import urllib.parse
import random
from datetime import datetime, timedelta
from typing import List, Optional
from bs4 import BeautifulSoup
from app.core.scraper_base import BaseScraper
from app.core.skill_extractor import extract as extract_skills
from app.core.career_classifier import classify as classify_career
from app.core.company_ranker import rank_company
from app.models.schemas import JobOffer

logger = logging.getLogger(__name__)


class LinkedInScraper(BaseScraper):
    def __init__(self) -> None:
        super().__init__(source_name="LinkedIn", base_url="https://www.linkedin.com")

    def _generate_mock_vector(self) -> List[float]:
        return [round(random.uniform(-1, 1), 4) for _ in range(5)]

    async def scrape(self, query: str, use_ai: bool = False) -> List[JobOffer]:
        """
        Scrape LinkedIn for job offers.

        Args:
            query: Búsqueda (ej. "Python Developer")
            use_ai: Si True, usa IA para extracción de skills y clasificación de carrera.
                    Default False para evitar latencia en batch.
        """
        search_query = urllib.parse.quote(query)
        url = f"{self.base_url}/jobs/search?keywords={search_query}&location=Per%C3%BA"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        }

        html = await self._fetch_page(url, headers=headers)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        offers: List[JobOffer] = []
        expiration_date = datetime.utcnow() + timedelta(days=30)

        job_cards = soup.find_all("div", class_="base-card")

        for card in job_cards:
            try:
                title_tag = card.find("h3", class_="base-search-card__title")
                link_tag = card.find("a", class_="base-card__full-link")

                if not title_tag or not link_tag:
                    continue

                title = title_tag.get_text().strip()
                link = link_tag.get("href", "").split("?")[0]

                company_tag = card.find("h4", class_="base-search-card__subtitle")
                company = (
                    company_tag.get_text().strip() if company_tag else "Confidencial"
                )

                # ── Phase 4: Enriched extraction ─────────────────────────────
                # LinkedIn cards don't have description text - only title + company
                skill_result = extract_skills(
                    title=title,
                    company=company,
                    short_description="",  # Not available on LinkedIn cards
                    use_ai=use_ai,
                )
                skills = skill_result.skills

                # Fallback: if no skills extracted, use query as skill
                if not skills and query:
                    skills = [query.capitalize()]

                # Career classification
                career_result = classify_career(title, company, use_ai=use_ai)

                # Company tier
                company_rank = rank_company(company)
                # ───────────────────────────────────────────────────────────

                offer = JobOffer(
                    puesto=title,
                    empresa=company,
                    fuente=self.source_name,
                    url_origen=link,
                    habilidades_requeridas=skills,
                    salario_normalizado_usd=None,  # LinkedIn rarely exposes salary on public cards
                    vector_semantico=self._generate_mock_vector(),
                    fecha_expiracion=expiration_date,
                    # Enriched fields (Phase 4)
                    categoria_carrera=career_result.category_id,
                    categoria_carrera_nombre=career_result.category_name,
                    company_tier=company_rank.tier,
                    skill_extraction_method=skill_result.method,
                )
                offers.append(offer)
            except Exception as e:
                logger.error(f"Error parsing LinkedIn card: {e}")
                continue

        return offers
