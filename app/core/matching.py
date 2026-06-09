import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
import numpy as np
from app.core.database import get_database
from app.models.schemas import MatchHistory, JobOffer

logger = logging.getLogger(__name__)

def calculate_cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """
    Calcula la similitud del coseno entre dos vectores numéricos.
    """
    if not vec_a or not vec_b:
        return 0.0
    if len(vec_a) != len(vec_b):
        logger.warning(f"Vectores con diferentes longitudes: {len(vec_a)} vs {len(vec_b)}")
        return 0.0
    
    a = np.array(vec_a)
    b = np.array(vec_b)
    
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
        
    return float(np.dot(a, b) / (norm_a * norm_b))

from collections import Counter

async def evaluate_student_compatibility(
    student_id: str, 
    student_skills: List[str]
) -> Dict[str, Any]:
    """
    Compara las habilidades de un estudiante contra las ofertas del mercado laboral
    y calcula el Match-Score y la brecha de habilidades.
    """
    db = get_database()
    if db is None:
        return {"error": "Database not connected"}
        
    offers_col = db["ofertas_laborales"]
    matches_col = db["historico_matches"]
    
    # 1. Obtener todas las ofertas para analizar el mercado (Top skills demandadas)
    cursor = offers_col.find({}, {"habilidades_requeridas": 1})
    all_offers = await cursor.to_list(length=500)
    
    if not all_offers:
        return {
            "score": 0,
            "habilidades_faltantes": [],
            "recomendaciones": ["No hay datos de mercado suficientes. Intenta ejecutar el scraper."]
        }

    # 2. Identificar las Top 15 habilidades más demandadas en el mercado actualmente
    market_skills_counter = Counter()
    for doc in all_offers:
        market_skills_counter.update(doc.get("habilidades_requeridas", []))
    
    top_market_skills = [skill for skill, count in market_skills_counter.most_common(15)]
    
    # 3. Calcular Match-Score basado en intersección de conjuntos
    student_skills_set = set(s.lower() for s in student_skills)
    market_skills_set = set(s.lower() for s in top_market_skills)
    
    intersection = student_skills_set.intersection(market_skills_set)
    
    # Score simple: porcentaje de habilidades del top mercado que posee el estudiante
    score = int((len(intersection) / len(market_skills_set)) * 100) if market_skills_set else 0
    
    # 4. Identificar habilidades faltantes (Gap Analysis)
    missing_skills = [s for s in top_market_skills if s.lower() not in student_skills_set]
    
    # 5. Generar recomendaciones
    recommendations = []
    if missing_skills:
        top_missing = missing_skills[:3]
        recommendations.append(f"Para mejorar tu perfil, considera aprender: {', '.join(top_missing)}.")
    
    if score < 50:
        recommendations.append("Tu nivel de coincidencia es bajo. Enfócate en las habilidades core del mercado.")
    else:
        recommendations.append("¡Buen trabajo! Estás alineado con las tendencias. Sigue profundizando en especialidades.")

    # 6. Persistir en MatchHistory (opcional para el MVP)
    # ...
    
    return {
        "score": score,
        "habilidades_faltantes": missing_skills[:5],
        "recomendaciones": recommendations
    }
