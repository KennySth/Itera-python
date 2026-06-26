import logging
import re
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


class ComputrabajoScraper(BaseScraper):
    def __init__(self) -> None:
        super().__init__(
            source_name="Computrabajo", base_url="https://pe.computrabajo.com"
        )

    def _clean_company_name(self, text: str) -> str:
        """Limpia el nombre de la empresa."""
        if not text:
            return "Confidencial"
        text = re.sub(r"^\d,\d\s*", "", text)
        text = text.replace("\r", " ").replace("\n", " ").replace("\t", " ")
        return " ".join(text.split()).strip()

    def _generate_mock_vector(self) -> List[float]:
        return [round(random.uniform(-1, 1), 4) for _ in range(5)]

    def _extract_salary(self, text: str) -> Optional[float]:
        """Extrae salario en USD desde texto en Soles (S/)."""
        if not text:
            return None
        match = re.search(r"S/\s*([\d\.,]+)", text)
        if match:
            raw_num = match.group(1).replace(".", "")
            if re.search(r",\d{2}$", raw_num):
                raw_num = raw_num.replace(",", ".")
            else:
                raw_num = raw_num.replace(",", "")
            try:
                soles = float(raw_num)
                return round(soles / 3.7, 2)
            except ValueError:
                return None
        return None

    async def scrape(self, query: str, use_ai: bool = False) -> List[JobOffer]:
        """
        Scrape Computrabajo for job offers.

        Args:
            query: Búsqueda (ej. "Python Developer")
            use_ai: Si True, usa IA para extracción de skills y clasificación de carrera.
                    Default False para evitar latencia en batch.
        """
        search_query = urllib.parse.quote(query)
        url = f"{self.base_url}/trabajo-de-{search_query}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        }

        html = await self._fetch_page(url, headers=headers)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        offers: List[JobOffer] = []
        expiration_date = datetime.utcnow() + timedelta(days=30)

        job_articles = soup.find_all("article", class_="box_offer")

        for article in job_articles:
            try:
                title_tag = article.find("a", class_="js-o-link")
                if not title_tag:
                    continue

                title = title_tag.get_text().strip()
                link = self.base_url + title_tag.get("href")

                company_tag = article.find("p", class_="fs16")
                raw_company = company_tag.get_text() if company_tag else "Confidencial"
                company = self._clean_company_name(raw_company)

                # Salary extraction
                salary_usd: Optional[float] = None
                for tag in article.find_all(["span", "p"]):
                    tag_text = tag.get_text()
                    if "S/" in tag_text:
                        salary_usd = self._extract_salary(tag_text)
                        if salary_usd:
                            break

                # Short description (card level)
                desc_tag = article.find("p", class_="sh_70")
                short_desc = desc_tag.get_text() if desc_tag else ""

                # ── Phase 4: Enriched extraction ─────────────────────────────
                # Skills via skill_extractor (regex-only if use_ai=False)
                skill_result = extract_skills(
                    title=title,
                    company=company,
                    short_description=short_desc,
                    use_ai=use_ai,
                )
                skills = skill_result.skills

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
                    salario_normalizado_usd=salary_usd,
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
                logger.error(f"Error parsing Computrabajo article: {e}")
                continue

        return offers
