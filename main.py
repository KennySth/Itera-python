from fastapi import FastAPI, Query
from contextlib import asynccontextmanager
from typing import List
from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection, db, get_database
from app.core.computrabajo_scraper import ComputrabajoScraper
from app.models.schemas import JobOffer

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to MongoDB
    await connect_to_mongo()
    yield
    # Shutdown: Close connection
    await close_mongo_connection()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Microservicio de Inteligencia de Mercado para la plataforma Itera.",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/", tags=["Root"])
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "docs": "/docs",
        "health": "/health"
    }

@app.post("/api/v1/scraper/run", tags=["Scraper"])
async def run_scraper(query: str = Query(..., description="Término de búsqueda (ej. Python, React)")):
    """
    Ejecuta el scraper para una búsqueda específica y guarda los resultados en MongoDB.
    """
    scraper = ComputrabajoScraper()
    offers = await scraper.scrape(query)
    await scraper.save_offers(offers)
    return {
        "status": "success",
        "query": query,
        "offers_extracted": len(offers),
        "source": scraper.source_name
    }

@app.get("/api/v1/offers", response_model=List[JobOffer], tags=["Data"])
async def get_offers(limit: int = 10, skip: int = 0):
    """
    Obtiene las ofertas laborales guardadas en la base de datos.
    """
    database = get_database()
    cursor = database["ofertas_laborales"].find().skip(skip).limit(limit)
    offers = await cursor.to_list(length=limit)
    return offers

@app.get("/health", tags=["System"])
async def health_check():
    try:
        # Check database connectivity
        await db.client.admin.command('ping')
        return {
            "status": "online",
            "database": "connected",
            "version": "1.0.0"
        }
    except Exception as e:
        return {
            "status": "degraded",
            "database": "disconnected",
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
