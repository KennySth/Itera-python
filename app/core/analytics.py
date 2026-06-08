from typing import List, Dict, Any
import re
from app.core.database import get_database
from app.models.schemas import MarketSkill, CareerMetrics
from collections import Counter
from datetime import datetime

async def update_market_skills() -> List[MarketSkill]:
    """
    Analiza todas las ofertas laborales y actualiza la colección habilidades_mercado.
    Calcula la demanda actual basándose en la frecuencia de aparición.
    """
    db = get_database()
    offers_collection = db["ofertas_laborales"]
    skills_collection = db["habilidades_mercado"]

    # 1. Obtener todas las ofertas
    cursor = offers_collection.find({}, {"habilidades_requeridas": 1})
    all_offers = await cursor.to_list(length=1000)
    
    if not all_offers:
        return []

    # 2. Contar frecuencias de habilidades
    skill_counter = Counter()
    total_offers = len(all_offers)
    
    for offer in all_offers:
        skills = offer.get("habilidades_requeridas", [])
        for skill in skills:
            skill_counter[skill] += 1

    # 3. Transformar y Guardar/Actualizar en habilidades_mercado
    market_skills = []
    for skill_name, count in skill_counter.items():
        # Calcular demanda actual como porcentaje
        demanda = (count / total_offers) * 100
        
        market_skill = MarketSkill(
            habilidad=skill_name,
            sinonimos=[],
            tipo_habilidad="tecnica", # Por defecto para el MVP
            demanda_actual=round(demanda, 2),
            tendencia_mensual="estable" # Valor inicial
        )
        
        # Upsert en la base de datos
        await skills_collection.update_one(
            {"habilidad": skill_name},
            {"$set": market_skill.model_dump(by_alias=True, exclude_none=True)},
            upsert=True
        )
        market_skills.append(market_skill)

    # Ordenar por demanda para devolver el top
    market_skills.sort(key=lambda x: x.demanda_actual, reverse=True)
    return market_skills

def _categorize_job_title(title: str) -> str:
    """Categoriza un título de puesto en una carrera general."""
    title_lower = title.lower()
    if re.search(r'\b(data|datos|machine learning|ia|artificial)\b', title_lower):
        return "Ciencia de Datos e IA"
    elif "full" in title_lower or "stack" in title_lower:
        return "Desarrollo Fullstack"
    elif re.search(r'\b(front|react|angular|ui|ux)\b', title_lower):
        return "Desarrollo Frontend"
    elif re.search(r'\b(back|python|java|node|php|sql)\b', title_lower):
        return "Desarrollo Backend"
    elif re.search(r'\b(devops|cloud|aws|infra|sistemas)\b', title_lower):
        return "Infraestructura y Cloud"
    return "Desarrollo de Software General"

def _clean_legacy_company(company: str) -> str:
    """Limpia nombres de empresa sucios que ya estaban en MongoDB."""
    if not company: return "Confidencial"
    c = re.sub(r'^\d,\d\s*', '', company)
    c = c.replace('\r', ' ').replace('\n', ' ').replace('\t', ' ')
    return " ".join(c.split()).strip()

async def update_career_metrics() -> List[str]:
    """
    Agrupa ofertas por categoría de carrera y calcula métricas agregadas
    para poblar la colección metricas_carreras (alineado con a.sql).
    """
    db = get_database()
    offers_col = db["ofertas_laborales"]
    careers_col = db["metricas_carreras"]
    
    # 1. Extraer todas las ofertas para procesarlas en Python
    cursor = offers_col.find({})
    offers = await cursor.to_list(length=2000)
    
    if not offers:
        return []

    # 2. Agrupar por categoría
    categorized_data: Dict[str, Dict[str, Any]] = {}
    
    for offer in offers:
        category = _categorize_job_title(offer.get("puesto", ""))
        
        if category not in categorized_data:
            categorized_data[category] = {
                "salaries": [],
                "skills": Counter(),
                "companies": Counter(),
                "count": 0
            }
            
        cat_data = categorized_data[category]
        cat_data["count"] += 1
        
        # Salarios
        salary = offer.get("salario_normalizado_usd")
        if salary:
            cat_data["salaries"].append(salary * 12)
            
        # Habilidades
        for skill in offer.get("habilidades_requeridas", []):
            cat_data["skills"][skill] += 1
            
        # Empresas (Limpiamos al vuelo por si hay datos legacy sucios)
        company = offer.get("empresa")
        if company and company != "Confidencial":
            clean_company = _clean_legacy_company(company)
            if clean_company and clean_company != "Confidencial":
                cat_data["companies"][clean_company] += 1

    # 3. Construir los objetos CareerMetrics y hacer Upsert
    updated_careers = []
    for category, data in categorized_data.items():
        
        # Calcular estadísticas salariales
        salaries = data["salaries"]
        salario_obj = {"min": 0, "max": 0, "promedio": 0}
        if salaries:
            salario_obj["min"] = round(min(salaries), 2)
            salario_obj["max"] = round(max(salaries), 2)
            salario_obj["promedio"] = round(sum(salaries) / len(salaries), 2)
            
        # Obtener Top Skills y Top Companies
        top_skills = [s[0] for s in data["skills"].most_common(5)]
        top_companies = [c[0] for c in data["companies"].most_common(3)]
        
        metrics = CareerMetrics(
            titulo_carrera=category,
            nivel_referencia="General",
            region_mercado="Perú",
            salario_anual_usd=salario_obj,
            demanda_mercado={"volumen_total": data["count"], "tendencia": "creciente"},
            analisis_competitivo={"top_empresas": top_companies},
            aprendizaje={"habilidades_clave": top_skills},
            ultima_actualizacion=datetime.utcnow()
        )
        
        await careers_col.update_one(
            {"titulo_carrera": category},
            {"$set": metrics.model_dump(by_alias=True, exclude_none=True)},
            upsert=True
        )
        updated_careers.append(category)
        
    return updated_careers
