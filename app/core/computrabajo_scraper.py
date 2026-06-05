import logging
from typing import List
from bs4 import BeautifulSoup
from app.core.scraper_base import BaseScraper
from app.models.schemas import JobOffer
import urllib.parse

logger = logging.getLogger(__name__)

class ComputrabajoScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            source_name="Computrabajo",
            base_url="https://pe.computrabajo.com"
        )

    async def scrape(self, query: str) -> List[JobOffer]:
        search_query = urllib.parse.quote(query)
        url = f"{self.base_url}/trabajo-de-{search_query}"
        
        # Note: Computrabajo often uses anti-bot, so we use common headers
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        }
        
        html = await self._fetch_page(url, headers=headers)
        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        offers = []
        
        # Find job articles
        job_articles = soup.find_all('article', class_='box_offer')
        
        for article in job_articles:
            try:
                title_tag = article.find('a', class_='js-o-link')
                if not title_tag:
                    continue
                
                title = title_tag.get_text().strip()
                link = self.base_url + title_tag.get('href')
                
                company_tag = article.find('p', class_='fs16')
                company = company_tag.get_text().strip() if company_tag else "Confidencial"
                
                # Mocking skills as they are usually on the detail page
                # In a real scenario, we'd visit each link, but for the MVP 
                # we'll extract keywords from the short description if available
                desc_tag = article.find('p', class_='sh_70')
                description = desc_tag.get_text().strip() if desc_tag else ""
                
                # Simple keyword extraction for MVP
                potential_skills = ["Python", "Java", "SQL", "React", "Node", "Excel", "AWS"]
                skills = [s for s in potential_skills if s.lower() in description.lower() or s.lower() in title.lower()]

                offer = JobOffer(
                    puesto=title,
                    empresa=company,
                    fuente=self.source_name,
                    url_origen=link,
                    habilidades_requeridas=skills,
                    # Salaries are often hidden or in specific tags
                    salario_normalizado_usd=None 
                )
                offers.append(offer)
            except Exception as e:
                logger.error(f"Error parsing article: {e}")
                continue
                
        return offers
