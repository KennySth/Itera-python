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

async def evaluate_student_compatibility(
    student_id: str, 
    student_vector: List[float], 
    target_role: str
) -> Dict[str, Any]:
    """
    Compara el perfil de un estudiante contra las ofertas del mercado laboral
    y guarda el resultado en el histórico de matches.
    """
    db = get_database()
    if db is None:
        return {"error": "Database not connected"}
        
    offers_col = db["ofertas_laborales"]
    matches_col = db["historico_matches"]
    
    # 1. Buscar ofertas relevantes para el objetivo
    # Usamos regex para una búsqueda flexible en el puesto
    query = {"puesto": {"$regex": target_role, "$options": "i"}}
    cursor = offers_col.find(query)
    offers_raw = await cursor.to_list(length=100)
    
    if not offers_raw:
        logger.info(f"No se encontraron ofertas para el rol: {target_role}")
        return {
            "score_general": 0.0,
            "total_evaluado": 0,
            "top_matches": [],
            "message": "No hay ofertas suficientes para este rol en la base de datos."
        }
        
    # 2. Calcular similitudes vectoriales
    scored_matches: List[Dict[str, Any]] = []
    for doc in offers_raw:
        # Validar si tiene vector semántico
        if "vector_semantico" in doc and doc["vector_semantico"]:
            score = calculate_cosine_similarity(student_vector, doc["vector_semantico"])
            scored_matches.append({
                "offer_id": str(doc["_id"]),
                "puesto": doc["puesto"],
                "empresa": doc.get("empresa", "Confidencial"),
                "score": round(score * 100, 2)
            })
            
    # 3. Calcular score general (promedio de los mejores 5 matches)
    scored_matches.sort(key=lambda x: x["score"], reverse=True)
    top_matches = scored_matches[:5]
    
    avg_score: float = 0.0
    if top_matches:
        avg_score = sum(m["score"] for m in top_matches) / len(top_matches)
        
    # 4. Persistir en MatchHistory (RF-10)
    match_entry = MatchHistory(
        estudiante_id=student_id,
        objetivo_evaluado=target_role,
        score_general=avg_score,
        version_modelo_ia="v1-cosine-similarity",
        fecha_evaluacion=datetime.utcnow()
    )
    
    await matches_col.insert_one(match_entry.model_dump(by_alias=True, exclude_none=True))
    
    return {
        "score_general": round(avg_score, 2),
        "total_evaluado": len(scored_matches),
        "top_matches": top_matches,
        "version_ia": "v1-cosine-similarity"
    }
