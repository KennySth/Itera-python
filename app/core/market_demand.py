import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from app.core.database import get_database

logger = logging.getLogger(__name__)

async def get_market_demand_aggregated() -> Dict[str, Any]:
    """
    Agrega datos de MongoDB para que Angular los grafique (RF-07).
    Devuelve tendencias de salarios y habilidades más demandadas.
    """
    db = get_database()
    if db is None:
        return {"error": "Database not connected"}
        
    offers_col = db["ofertas_laborales"]
    
    # 1. Habilidades más demandadas (para gráficos de barra/pie)
    pipeline_skills: List[Dict[str, Any]] = [
        {"$unwind": "$habilidades_requeridas"},
        {"$group": {"_id": "$habilidades_requeridas", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    
    cursor_skills = offers_col.aggregate(pipeline_skills)
    top_skills: List[Dict[str, Union[str, int]]] = [
        {"skill": doc["_id"], "demand_count": doc["count"]} async for doc in cursor_skills
    ]

    # 2. Distribución de Salarios Promedio en USD
    # Agrupamos en buckets de 500 USD
    pipeline_salary: List[Dict[str, Any]] = [
        {"$match": {"salario_normalizado_usd": {"$ne": None, "$gt": 0}}},
        {"$bucket": {
            "groupBy": "$salario_normalizado_usd",
            "boundaries": [0, 500, 1000, 1500, 2000, 3000, 5000, 10000],
            "default": "10000+",
            "output": {"count": {"$sum": 1}}
        }}
    ]
    cursor_salary = offers_col.aggregate(pipeline_salary)
    salary_distribution: List[Dict[str, Union[str, int]]] = []
    
    async for doc in cursor_salary:
        label: str = ""
        if isinstance(doc["_id"], (int, float)):
            label = f"{doc['_id']} - {doc['_id']+500}"
        else:
            label = str(doc["_id"])
            
        salary_distribution.append({
            "range_usd": label,
            "count": doc["count"]
        })

    # 3. Métricas Generales
    total_offers: int = await offers_col.count_documents({})
    offers_with_salary: int = await offers_col.count_documents({"salario_normalizado_usd": {"$ne": None}})

    return {
        "metrics": {
            "total_offers_analyzed": total_offers,
            "offers_with_salary_data": offers_with_salary,
            "last_updated": datetime.utcnow().isoformat()
        },
        "top_skills": top_skills,
        "salary_distribution": salary_distribution
    }
