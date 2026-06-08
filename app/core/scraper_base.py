import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
import httpx
from urllib.robotparser import RobotFileParser
from app.models.schemas import JobOffer, ScrapingAudit
from app.core.database import get_database

logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    def __init__(self, source_name: str, base_url: str):
        self.source_name = source_name
        self.base_url = base_url
        self.rp = RobotFileParser()
        self.rp.set_url(f"{base_url.rstrip('/')}/robots.txt")
        self._robots_loaded = False
        
        self.audit_data = {
            "fuente": source_name,
            "estado": "iniciado",
            "ofertas_extraidas": 0,
            "ofertas_descartadas": 0,
            "errores_detectados": [],
            "fecha_ejecucion": datetime.utcnow()
        }

    async def _load_robots(self):
        """Loads robots.txt asynchronously."""
        if not self._robots_loaded:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(self.rp.url, timeout=10.0)
                    if response.status_code == 200:
                        self.rp.parse(response.text.splitlines())
                    else:
                        # If no robots.txt, assume everything is allowed
                        self.rp.parse(["User-agent: *", "Allow: /"])
                self._robots_loaded = True
            except Exception as e:
                logger.error(f"Error loading robots.txt for {self.source_name}: {e}")
                self._robots_loaded = True # Don't block if robots.txt fails

    async def is_allowed(self, url: str) -> bool:
        """Checks if a URL is allowed to be scraped according to robots.txt."""
        await self._load_robots()
        return self.rp.can_fetch("*", url)

    @abstractmethod
    async def scrape(self, query: str) -> List[JobOffer]:
        pass

    async def save_offers(self, offers: List[JobOffer]):
        db = get_database()
        if not offers:
            return
        
        collection = db["ofertas_laborales"]
        audit_collection = db["auditoria_scraping"]
        
        # Save offers
        for offer in offers:
            try:
                await collection.update_one(
                    {"url_origen": offer.url_origen},
                    {"$set": offer.model_dump(by_alias=True, exclude_none=True)},
                    upsert=True
                )
                self.audit_data["ofertas_extraidas"] += 1
            except Exception as e:
                logger.error(f"Error saving offer: {e}")
                self.audit_data["ofertas_descartadas"] += 1
                self.audit_data["errores_detectados"].append({"error": str(e)})

        # Update audit
        self.audit_data["estado"] = "completado"
        await audit_collection.insert_one(self.audit_data)

    async def _fetch_page(self, url: str, headers: Optional[dict] = None):
        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                return response.text
            except Exception as e:
                logger.error(f"Error fetching page {url}: {e}")
                self.audit_data["errores_detectados"].append({"url": url, "error": str(e)})
                return None
