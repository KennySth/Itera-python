import logging
import re
import urllib.parse
import random
from datetime import datetime, timedelta
from typing import List, Optional, Union
from bs4 import BeautifulSoup
from app.core.scraper_base import BaseScraper
from app.models.schemas import JobOffer

logger = logging.getLogger(__name__)

class ComputrabajoScraper(BaseScraper):
    def __init__(self) -> None:
        super().__init__(
            source_name="Computrabajo",
            base_url="https://pe.computrabajo.com"
        )
        self.skill_keywords: List[str] = [
            "Python", "Java", "SQL", "React", "Node", "Excel", "AWS", "Azure", 
            "Docker", "Kubernetes", "C#", "PHP", "Angular", "Vue", "JavaScript",
            "TypeScript", "HTML", "CSS", "NoSQL", "MongoDB", "PostgreSQL",
            "Inteligencia Artificial", "Machine Learning", "Analista", "Scrum",
            "Git", "Linux", "Power BI", "Tableau", "Oracle", "Spring"
        ]

    def _clean_company_name(self, text: str) -> str:
        """Limpia profundamente el nombre de la empresa."""
        if not text: return "Confidencial"
        # Elimina cualquier cosa que parezca una calificación (ej: 4,3) o estrellas
        text = re.sub(r'^\d,\d\s*', '', text)
        # Reemplaza saltos de línea y tabulaciones por espacios
        text = text.replace('\r', ' ').replace('\n', ' ').replace('\t', ' ')
        # Elimina espacios múltiples
        return " ".join(text.split()).strip()

    def _generate_mock_vector(self) -> List[float]:
        """Genera un vector aleatorio para pruebas de RF-10 (MVP)."""
        return [round(random.uniform(-1, 1), 4) for _ in range(5)]

    def _extract_salary(self, text: str) -> Optional[float]:
        """Extrae el salario aproximado en USD de un texto en Soles (S/)."""
        if not text: return None
        # Busca patrones como "S/ 3.000", "S/ 5,000.00", "S/ 5,000"
        match = re.search(r'S/\s*([\d\.,]+)', text)
        if match:
            raw_num = match.group(1)
            # Removemos puntos (usados para miles en AL)
            clean_num = raw_num.replace('.', '')
            # Si hay coma seguida de dos números al final, es decimal. Sino, es de miles.
            if re.search(r',\d{2}$', clean_num):
                clean_num = clean_num.replace(',', '.')
            else:
                clean_num = clean_num.replace(',', '')
                
            try:
                soles = float(clean_num)
                # Tasa de conversión aproximada PEN a USD (ej. 3.7)
                usd = soles / 3.7
                return round(usd, 2)
            except ValueError:
                return None
        return None

    async def scrape(self, query: str) -> List[JobOffer]:
        search_query = urllib.parse.quote(query)
        url = f"{self.base_url}/trabajo-de-{search_query}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        }
        
        html = await self._fetch_page(url, headers=headers)
        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        offers: List[JobOffer] = []
        
        # Computrabajo usa 'article' para las ofertas
        job_articles = soup.find_all('article', class_='box_offer')
        
        # RNF-12: Las ofertas expiran en 30 días por defecto
        expiration_date = datetime.utcnow() + timedelta(days=30)
        
        for article in job_articles:
            try:
                title_tag = article.find('a', class_='js-o-link')
                if not title_tag: continue
                
                title = title_tag.get_text().strip()
                link = self.base_url + title_tag.get('href')
                
                # Limpieza de Empresa
                company_tag = article.find('p', class_='fs16')
                raw_company = company_tag.get_text() if company_tag else "Confidencial"
                company = self._clean_company_name(raw_company)
                
                # Extracción de salario de etiquetas span/p que contengan "S/"
                salary_usd: Optional[float] = None
                info_tags = article.find_all(['span', 'p'])
                for tag in info_tags:
                    tag_text = tag.get_text()
                    if 'S/' in tag_text:
                        salary_usd = self._extract_salary(tag_text)
                        if salary_usd: break

                # Extracción de habilidades de la descripción corta y el título
                desc_tag = article.find('p', class_='sh_70')
                description = desc_tag.get_text() if desc_tag else ""
                
                full_text = f"{title} {description}".lower()
                skills = [s for s in self.skill_keywords if s.lower() in full_text]

                offer = JobOffer(
                    puesto=title,
                    empresa=company,
                    fuente=self.source_name,
                    url_origen=link,
                    habilidades_requeridas=skills,
                    salario_normalizado_usd=salary_usd,
                    vector_semantico=self._generate_mock_vector(),
                    fecha_expiracion=expiration_date
                )
                offers.append(offer)
            except Exception as e:
                logger.error(f"Error parsing article: {e}")
                continue
                
        return offers
