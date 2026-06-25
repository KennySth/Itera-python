import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from app.core.database import get_database

logger = logging.getLogger(__name__)

# Simple in-memory cache for market demand data (RNF-06)
# Reduces MongoDB queries and ensures < 500ms response times
_cache: Dict[str, Any] = {
    "data": None,
    "timestamp": 0,
}
_CACHE_TTL_SECONDS = 300  # 5 minutes

_cache_career: Dict[str, Any] = {
    "data": None,
    "timestamp": 0,
}
_CACHE_CAREER_TTL_SECONDS = 300


async def get_market_demand_aggregated() -> Dict[str, Any]:
    """
    Agrega datos de MongoDB para que Angular los grafique (RF-07).
    Devuelve tendencias de salarios y habilidades más demandadas.
    Uses in-memory cache for RNF-06 (< 500ms target).
    """
    now = time.time()
    if _cache["data"] and (now - _cache["timestamp"]) < _CACHE_TTL_SECONDS:
        return _cache["data"]

    db = get_database()
    if db is None:
        return {"error": "Database not connected"}

    offers_col = db["ofertas_laborales"]

    # 1. Habilidades más demandadas (para gráficos de barra/pie)
    pipeline_skills: List[Dict[str, Any]] = [
        {"$unwind": "$habilidades_requeridas"},
        {"$group": {"_id": "$habilidades_requeridas", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10},
    ]

    cursor_skills = offers_col.aggregate(pipeline_skills)
    top_skills: List[Dict[str, Union[str, int]]] = [
        {"skill": doc["_id"], "demand_count": doc["count"]}
        async for doc in cursor_skills
    ]

    # 2. Distribución de Salarios Promedio en USD
    pipeline_salary: List[Dict[str, Any]] = [
        {"$match": {"salario_normalizado_usd": {"$ne": None, "$gt": 0}}},
        {
            "$bucket": {
                "groupBy": "$salario_normalizado_usd",
                "boundaries": [0, 500, 1000, 1500, 2000, 3000, 5000, 10000],
                "default": "10000+",
                "output": {"count": {"$sum": 1}},
            }
        },
    ]
    cursor_salary = offers_col.aggregate(pipeline_salary)
    salary_distribution: List[Dict[str, Union[str, int]]] = []

    async for doc in cursor_salary:
        label: str = ""
        if isinstance(doc["_id"], (int, float)):
            label = f"{doc['_id']} - {doc['_id'] + 500}"
        else:
            label = str(doc["_id"])

        salary_distribution.append({"range_usd": label, "count": doc["count"]})

    # 3. Métricas Generales
    total_offers: int = await offers_col.count_documents({})
    offers_with_salary: int = await offers_col.count_documents(
        {"salario_normalizado_usd": {"$ne": None}}
    )

    result = {
        "metrics": {
            "total_offers_analyzed": total_offers,
            "offers_with_salary_data": offers_with_salary,
            "last_updated": datetime.utcnow().isoformat(),
        },
        "top_skills": top_skills,
        "salary_distribution": salary_distribution,
    }

    _cache["data"] = result
    _cache["timestamp"] = now

    return result


async def get_salary_by_career_cached() -> Dict[str, Any]:
    """
    Returns salary-by-career data with caching for RNF-06.
    """
    now = time.time()
    if (
        _cache_career["data"]
        and (now - _cache_career["timestamp"]) < _CACHE_CAREER_TTL_SECONDS
    ):
        return _cache_career["data"]

    db = get_database()
    if db is None:
        return {"error": "Database not connected"}

    careers_col = db["metricas_carreras"]

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

    total_volume = sum(c.get("volumen_total", 0) for c in careers)
    avg_salary_all = (
        sum(c.get("salario_promedio", 0) * c.get("volumen_total", 0) for c in careers)
        / total_volume
        if total_volume > 0
        else 0
    )

    result = {
        "careers": careers,
        "summary": {
            "total_offers": total_volume,
            "avg_salary_weighted": round(avg_salary_all, 2),
            "career_count": len(careers),
        },
    }

    _cache_career["data"] = result
    _cache_career["timestamp"] = now

    return result
