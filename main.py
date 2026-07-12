import uvicorn
from contextlib import asynccontextmanager
from typing import Dict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection, db
from app.api import router as api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to MongoDB and create indexes
    await connect_to_mongo()
    yield
    # Shutdown: Close connection
    await close_mongo_connection()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Microservicio de Inteligencia de Mercado para la plataforma Itera.",
    version="1.1.0",
    lifespan=lifespan
)

# Configurar CORS para permitir comunicación con Angular
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://localhost",
        "https://itera-frontend.vercel.app",
        "https://itera-frontend-git-main.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montar el router principal sin prefijo interno (el Gateway maneja los prefijos)
app.include_router(api_router)

@app.get("/", tags=["Root"])
async def root() -> Dict[str, str]:
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "docs": "/docs",
        "contract": "/api/ia/"
    }

@app.get("/health", tags=["System"])
async def health_check() -> Dict[str, str]:
    try:
        await db.client.admin.command('ping')
        return {
            "status": "online",
            "database": "connected",
            "version": "1.1.0"
        }
    except Exception as e:
        return {
            "status": "degraded",
            "database": "disconnected",
            "error": str(e)
        }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
