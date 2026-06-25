import asyncio
import re
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Query, BackgroundTasks
from app.core.database import get_database
from app.core.computrabajo_scraper import ComputrabajoScraper
from app.core.linkedin_scraper import LinkedInScraper
from app.core.analytics import update_market_skills, update_career_metrics
from app.core.market_demand import get_market_demand_aggregated
from app.core.matching import evaluate_student_compatibility
from app.models.schemas import (
    JobOffer,
    MarketSkill,
    MatchRequest,
    ScrapingAudit,
    ExplorationTelemetry,
    RecommendationFeedback,
    CareerMetrics,
)

router = APIRouter()

# --- Scraper & Data ---


async def run_scraper_task(query: str) -> None:
    """Tarea de fondo para ejecutar múltiples scrapers en paralelo sin bloquear la API."""
    ct_scraper = ComputrabajoScraper()
    li_scraper = LinkedInScraper()

    # Ejecutamos ambos scrapers de forma concurrente
    results = await asyncio.gather(
        ct_scraper.scrape(query), li_scraper.scrape(query), return_exceptions=True
    )

    ct_offers = results[0] if not isinstance(results[0], Exception) else []
    li_offers = results[1] if not isinstance(results[1], Exception) else []

    # Guardamos los resultados
    await ct_scraper.save_offers(ct_offers)
    await li_scraper.save_offers(li_offers)


@router.post("/scraper/run", tags=["Scraper (RNF-07)"])
async def run_scraper(
    background_tasks: BackgroundTasks,
    query: str = Query(..., description="Término de búsqueda (ej. Python, React)"),
) -> Dict[str, Any]:
    """
    Ejecuta el scraper en segundo plano (RNF-07) y guarda los resultados en MongoDB.
    """
    background_tasks.add_task(run_scraper_task, query)
    return {
        "status": "accepted",
        "message": f"Scraping para '{query}' iniciado en segundo plano.",
        "query": query,
    }


@router.get("/offers", response_model=List[JobOffer], tags=["Data"])
async def get_offers(
    limit: int = Query(10, ge=1, le=50),
    skip: int = Query(0, ge=0),
    q: str = Query(
        None, description="Búsqueda por texto libre (puesto, empresa, habilidades)"
    ),
    skill: str = Query(None, description="Filtrar por habilidad específica"),
    modality: str = Query(
        None, description="Filtrar por modalidad (remoto, presencial, híbrido)"
    ),
    salary_min: float = Query(None, description="Salario mínimo normalizado USD"),
    salary_max: float = Query(None, description="Salario máximo normalizado USD"),
) -> List[JobOffer]:
    """
    Obtiene las ofertas laborales con filtros opcionales.
    - q: búsqueda libre sobre puesto, empresa y habilidades
    - skill: filtra ofertas que requieran esa habilidad
    - modality: filtra por modalidad
    - salary_min/salary_max: rango de salario normalizado
    """
    database = get_database()
    query_filter: Dict[str, Any] = {}

    # Text search across multiple fields
    if q:
        regex = re.compile(re.escape(q), re.IGNORECASE)
        query_filter["$or"] = [
            {"puesto": {"$regex": regex}},
            {"empresa": {"$regex": regex}},
            {"habilidades_requeridas": {"$regex": regex}},
        ]

    # Skill filter: offer must contain this skill in its array
    if skill:
        query_filter["habilidades_requeridas"] = {
            "$regex": re.compile(re.escape(skill), re.IGNORECASE)
        }

    # Modality filter
    if modality:
        query_filter["modalidad"] = {
            "$regex": re.compile(re.escape(modality), re.IGNORECASE)
        }

    # Salary range filters
    if salary_min is not None or salary_max is not None:
        salary_filter: Dict[str, Any] = {}
        if salary_min is not None:
            salary_filter["$gte"] = salary_min
        if salary_max is not None:
            salary_filter["$lte"] = salary_max
        query_filter["salario_normalizado_usd"] = salary_filter

    cursor = database["ofertas_laborales"].find(query_filter).skip(skip).limit(limit)
    offers = await cursor.to_list(length=limit)
    return offers


# --- Intelligence & Analytics ---


@router.post("/match/evaluate", tags=["Intelligence (RF-10)"])
async def match_evaluate(request: MatchRequest) -> Dict[str, Any]:
    """
    Calcula el Match-Score entre un estudiante y las ofertas del mercado (RF-10).
    """
    result: Dict[str, Any] = await evaluate_student_compatibility(
        request.student_id, request.skills
    )
    return result


@router.post("/analytics/refresh", tags=["Analytics"])
async def refresh_analytics() -> Dict[str, Any]:
    """
    Procesa las ofertas actuales para actualizar métricas de habilidades y carreras.
    """
    skills = await update_market_skills()
    careers_updated = await update_career_metrics()

    return {
        "status": "success",
        "skills_updated": len(skills),
        "careers_updated": len(careers_updated),
        "top_skills": skills[:5],
        "careers_processed": careers_updated,
    }


@router.get("/careers/metrics", response_model=List[CareerMetrics], tags=["Analytics"])
async def get_career_metrics() -> List[CareerMetrics]:
    """
    Obtiene los perfiles agregados por carrera (salarios, demanda, top skills).
    """
    database = get_database()
    cursor = database["metricas_carreras"].find()
    careers = await cursor.to_list(length=100)
    return careers


@router.get("/market/demand", tags=["Analytics (RF-07)"])
async def market_demand() -> Dict[str, Any]:
    """
    Expone rutas REST para que Angular pueda pintar los gráficos (RF-07).
    """
    data = await get_market_demand_aggregated()
    return data


@router.get("/market/salary-by-career", tags=["Analytics (RF-07)"])
async def salary_by_career() -> Dict[str, Any]:
    """
    Obtiene la distribución salarial por categoría de carrera para gráficos comparativos (RF-07).
    """
    database = get_database()
    careers_col = database["metricas_carreras"]

    pipeline: List[Dict[str, Any]] = [
        {
            "$project": {
                "titulo_carrera": 1,
                "salario_min": {"$ifNull": ["$salario_anual_usd.min", 0]},
                "salario_max": {"$ifNull": ["$salario_anual_usd.max", 0]},
                "salario_promedio": {"$ifNull": ["$salario_anual_usd.promedio", 0]},
                "volumen_total": {"$ifNull": ["$demanda_mercado.volumen_total", 0]},
                "tendencia": {"$ifNull": ["$demanda_mercado.tendencia", "estable"]},
                "habilidades_clave": {
                    "$ifNull": ["$aprendizaje.habilidades_clave", []]
                },
            }
        },
        {"$sort": {"salario_promedio": -1}},
    ]

    cursor = careers_col.aggregate(pipeline)
    careers = await cursor.to_list(length=20)

    # Summary stats
    total_volume = sum(c.get("volumen_total", 0) for c in careers)
    avg_salary_all = (
        sum(c.get("salario_promedio", 0) * c.get("volumen_total", 0) for c in careers)
        / total_volume
        if total_volume > 0
        else 0
    )

    return {
        "careers": careers,
        "summary": {
            "total_offers": total_volume,
            "avg_salary_weighted": round(avg_salary_all, 2),
            "career_count": len(careers),
        },
    }


@router.get("/analytics/skills", response_model=List[MarketSkill], tags=["Analytics"])
async def get_market_skills() -> List[MarketSkill]:
    """
    Obtiene las tendencias de habilidades del mercado guardadas.
    """
    database = get_database()
    cursor = database["habilidades_mercado"].find().sort("demanda_actual", -1)
    skills = await cursor.to_list(length=50)
    return skills


# --- Audit & Monitoring (RF-09) ---


@router.get(
    "/audit/scraping", response_model=List[ScrapingAudit], tags=["Audit (RF-09)"]
)
async def get_scraping_audit(limit: int = 20) -> List[ScrapingAudit]:
    """
    Obtiene los registros de ejecución del scraper para el panel administrativo (RF-09).
    """
    database = get_database()
    cursor = (
        database["auditoria_scraping"].find().sort("fecha_ejecucion", -1).limit(limit)
    )
    logs = await cursor.to_list(length=limit)
    return logs


# --- Telemetry & Feedback (RF-11) ---


@router.post("/telemetry/event", tags=["Intelligence (RF-11)"])
async def record_telemetry(event: ExplorationTelemetry) -> Dict[str, str]:
    """
    Registra eventos de exploración del usuario para mejorar la IA (RF-11).
    """
    database = get_database()
    await database["telemetria_exploracion"].insert_one(
        event.model_dump(by_alias=True, exclude_none=True)
    )
    return {"status": "recorded"}


@router.post("/feedback/recommendation", tags=["Intelligence (RF-11)"])
async def record_feedback(feedback: RecommendationFeedback) -> Dict[str, str]:
    """
    Registra el feedback (estrellas/comentarios) del usuario sobre las recomendaciones (RF-11).
    """
    database = get_database()
    await database["feedback_recomendaciones"].insert_one(
        feedback.model_dump(by_alias=True, exclude_none=True)
    )
    return {"status": "recorded"}
