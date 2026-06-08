import logging
import urllib.parse
import random
from datetime import datetime, timedelta
from typing import List, Optional
from bs4 import BeautifulSoup
from app.core.scraper_base import BaseScraper
from app.models.schemas import JobOffer

logger = logging.getLogger(__name__)

class LinkedInScraper(BaseScraper):
    def __init__(self) -> None:
        super().__init__(
            source_name="LinkedIn",
            base_url="https://www.linkedin.com"
        )
        self.skill_keywords: List[str] = [
            "Python", "Java", "SQL", "React", "Node", "Excel", "AWS", "Azure", 
            "Docker", "Kubernetes", "C#", "PHP", "Angular", "Vue", "JavaScript",
            "TypeScript", "HTML", "CSS", "NoSQL", "MongoDB", "PostgreSQL",
            "Inteligencia Artificial", "Machine Learning", "Analista", "Scrum",
            "Git", "Linux", "Power BI", "Tableau", "Oracle", "Spring"
        ]

    def _generate_mock_vector(self) -> List[float]:
        return [round(random.uniform(-1, 1), 4) for _ in range(5)]

    async def scrape(self, query: str) -> List[JobOffer]:
        # Usamos el endpoint para invitados (jobs/search)
        search_query = urllib.parse.quote(query)
        # Por defecto buscamos en Perú para el MVP
        url = f"{self.base_url}/jobs/search?keywords={search_query}&location=Per%C3%BA"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        }
        
        html = await self._fetch_page(url, headers=headers)
        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        offers: List[JobOffer] = []
        
        expiration_date = datetime.utcnow() + timedelta(days=30)
        
        # LinkedIn public search usa una lista de cards
        job_cards = soup.find_all('div', class_='base-card')
        
        for card in job_cards:
            try:
                # Título y Link
                title_tag = card.find('h3', class_='base-search-card__title')
                link_tag = card.find('a', class_='base-card__full-link')
                
                if not title_tag or not link_tag:
                    continue
                    
                title = title_tag.get_text().strip()
                # A veces LinkedIn añade parámetros de tracking largos, extraemos la URL base de la oferta
                link = link_tag.get('href', '').split('?')[0] 
                
                # Empresa
                company_tag = card.find('h4', class_='base-search-card__subtitle')
                company = company_tag.get_text().strip() if company_tag else "Confidencial"
                
                # Habilidades (Buscamos en el título y empresa, ya que la descripción completa no está en la tarjeta)
                full_text = f"{title} {company}".lower()
                skills = [s for s in self.skill_keywords if s.lower() in full_text]
                
                # Si el título no tenía skills, asignamos la búsqueda original como fallback lógico
                if not skills and query.lower() in [k.lower() for k in self.skill_keywords]:
                    skills.append(query.capitalize())

                offer = JobOffer(
                    puesto=title,
                    empresa=company,
                    fuente=self.source_name,
                    url_origen=link,
                    habilidades_requeridas=skills,
                    salario_normalizado_usd=None, # Rara vez LinkedIn expone salarios en la tarjeta pública
                    vector_semantico=self._generate_mock_vector(),
                    fecha_expiracion=expiration_date
                )
                offers.append(offer)
            except Exception as e:
                logger.error(f"Error parsing LinkedIn article: {e}")
                continue
                
        return offers
