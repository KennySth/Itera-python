"""
Analytics - Career & Market Metrics - Phase 5.

ponytail: Uses enriched fields from JobOffer when available
(categoria_carrera_nombre, company_tier). Falls back to
career_classifier for legacy offers without enrichment.
"""

from typing import List, Dict, Any
from collections import Counter
from datetime import datetime

from app.core.database import get_database
from app.core.career_classifier import classify as classify_career
from app.core.company_filter import normalize_company_name
from app.models.schemas import MarketSkill, CareerMetrics


# ─────────────────────────────────────────────────────────────────────────────
# Generic / non-technical skills that should NOT count as market demand.
# These are job roles, soft skills, or office tools — not technical skills.
# ─────────────────────────────────────────────────────────────────────────────
GENERIC_SKILLS = {
    # Job roles (not skills)
    "analista",
    "análisis",
    "desarrollador",
    "desarrolladora",
    "ingeniero",
    "ingeniera",
    "consultor",
    "consultora",
    "técnico",
    "técnica",
    "especialista",
    "devops",
    "devops engineer",
    # Office / generic tools
    "office",
    "microsoft office",
    "excel",
    "powerpoint",
    "word",
    "outlook",
    # Soft skills
    "comunicación",
    "liderazgo",
    "trabajo en equipo",
    "gestión",
    "planificación",
    "organización",
    "proactivo",
    "responsable",
    "proactiva",
    "responsable",
    # Vague / non-measurable
    "experiencia",
    "conocimiento",
    "habilidad",
    "capacidad",
    "disponibilidad",
    "compromiso",
    "dedicación",
}


def _is_generic_skill(skill_name: str) -> bool:
    """Check if a skill is too generic to count as technical market demand."""
    return skill_name.lower().strip() in GENERIC_SKILLS


def _normalize_skill_name(name: str) -> str:
    """
    Normalize a skill name to its canonical form.
    Fixes case inconsistencies like 'Aws' → 'AWS', 'Devops' → 'DevOps'.
    """
    from app.core.skill_taxonomy import ALIAS_TO_SKILL

    normalized = name.strip()
    # Check exact match first
    canonical = ALIAS_TO_SKILL.get(normalized.lower())
    if canonical:
        return canonical
    # Check with common fixes
    canonical = ALIAS_TO_SKILL.get(normalized.lower().replace(" ", " "))
    if canonical:
        return canonical
    return normalized


async def update_market_skills() -> List[MarketSkill]:
    """
    Analiza todas las ofertas laborales y actualiza la colección habilidades_mercado.
    Calcula la demanda actual basándose en la frecuencia de aparición.

    Filters out generic/non-technical skills (job roles, soft skills, office tools)
    so they don't pollute the market demand data.

    Also removes stale generic entries from the collection.
    """
    db = get_database()
    offers_collection = db["ofertas_laborales"]
    skills_collection = db["habilidades_mercado"]

    # Clear all existing skills before repopulating (prevents stale/duplicate entries)
    await skills_collection.delete_many({})

    cursor = offers_collection.find({}, {"habilidades_requeridas": 1})
    all_offers = await cursor.to_list(length=1000)

    if not all_offers:
        return []

    skill_counter = Counter()
    total_offers = len(all_offers)

    for offer in all_offers:
        skills = offer.get("habilidades_requeridas", [])
        for skill in skills:
            if not _is_generic_skill(skill):
                normalized = _normalize_skill_name(skill)
                skill_counter[normalized] += 1

    market_skills = []
    for skill_name, count in skill_counter.items():
        demanda = (count / total_offers) * 100

        market_skill = MarketSkill(
            habilidad=skill_name,
            sinonimos=[],
            tipo_habilidad="tecnica",
            demanda_actual=round(demanda, 2),
            tendencia_mensual="estable",
        )

        await skills_collection.update_one(
            {"habilidad": skill_name},
            {"$set": market_skill.model_dump(by_alias=True, exclude_none=True)},
            upsert=True,
        )
        market_skills.append(market_skill)

    market_skills.sort(key=lambda x: x.demanda_actual, reverse=True)
    return market_skills


def _get_category_for_offer(offer: dict) -> str:
    """
    Get career category name from an offer.

    Priority:
    1. Enriched field (Phase 4): categoria_carrera_nombre
    2. Fallback: career_classifier on legacy offer
    """
    # Phase 4 enriched offer
    if offer.get("categoria_carrera_nombre"):
        return offer["categoria_carrera_nombre"]

    # Legacy offer - use classifier
    title = offer.get("puesto", "")
    company = offer.get("empresa", "")
    result = classify_career(title, company, use_ai=False)
    return result.category_name


# ─────────────────────────────────────────────────────────────────────────────
# Fallback salaries by category (Perú 2026, monthly USD)
# Covers all 17 categories from career_taxonomy.py
# ─────────────────────────────────────────────────────────────────────────────
SALARY_BASELINES_MONTHLY: dict[str, float] = {
    # Tier 1 - High demand/specialized
    "Ciencia de Datos e IA": 4000.0,
    "Desarrollo Backend": 3200.0,
    "Desarrollo Fullstack": 3000.0,
    "DevOps y Cloud": 3500.0,
    # Tier 2 - Mid-high demand
    "Desarrollo Frontend": 2500.0,
    "Ingeniería de Datos": 3500.0,
    "Seguridad Informática": 3200.0,
    "Desarrollo Mobile": 2800.0,
    # Tier 3 - Standard demand
    "QA y Testing": 2000.0,
    "Gestión de Bases de Datos": 2700.0,
    "Infraestructura y Sistemas": 2400.0,
    "Datos y Business Intelligence": 2300.0,
    "Analista de Negocios TI": 2200.0,
    "Gestión de Proyectos TI": 2500.0,
    "Product Manager": 2800.0,
    "Diseño UX/UI": 2300.0,
    # Tier 4 - Catch-all
    "Desarrollo de Software General": 2200.0,
    "Desarrollo de Videojuegos": 2000.0,
}


def _get_fallback_salary(category_name: str) -> float:
    """Provee salario base mensual USD según categoría (Perú 2026)."""
    return SALARY_BASELINES_MONTHLY.get(category_name, 2000.0)


def _clean_company_name(text: str) -> str:
    """Limpia nombres de empresa sucios."""
    if not text:
        return "Confidencial"
    text = text.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    text = " ".join(text.split()).strip()
    # Remove ratings like "4.3" or "4,3"
    import re

    text = re.sub(r"^\d[.,]\d\s*", "", text)
    return text or "Confidencial"


async def update_career_metrics() -> List[str]:
    """
    Agrupa ofertas por categoría de carrera y calcula métricas agregadas.

    Usa el campo enriquecido `categoria_carrera_nombre` de las ofertas Phase 4.
    Para ofertas legacy (sin enrichment), usa career_classifier como fallback.

    La agrupación se hace por nombre de categoría para mantener
    compatibilidad hacia atrás con datos existentes.
    """
    db = get_database()
    offers_col = db["ofertas_laborales"]
    careers_col = db["metricas_carreras"]

    cursor = offers_col.find({})
    offers = await cursor.to_list(length=2000)

    if not offers:
        return []

    # ── Group by category ────────────────────────────────────────────────
    categorized_data: Dict[str, Dict[str, Any]] = {}

    for offer in offers:
        # Get category (enriched or classified)
        category = _get_category_for_offer(offer)

        if category not in categorized_data:
            categorized_data[category] = {
                "salaries": [],
                "skills": Counter(),
                "companies": Counter(),
                "count": 0,
                "tiers": Counter(),
            }

        cat_data = categorized_data[category]
        cat_data["count"] += 1

        # Salary (monthly normalized to annual)
        salary = offer.get("salario_normalizado_usd")
        if salary:
            cat_data["salaries"].append(salary * 12)

        # Skills (filter out generic/non-technical skills and normalize names)
        for skill in offer.get("habilidades_requeridas", []):
            if not _is_generic_skill(skill):
                normalized = _normalize_skill_name(skill)
                cat_data["skills"][normalized] += 1

        # Companies
        company = offer.get("empresa")
        if company and company != "Confidencial":
            clean_company = _clean_company_name(company)
            normalized = normalize_company_name(clean_company)
            if normalized and normalized != "Confidencial":
                cat_data["companies"][normalized] += 1

        # Company tier (from enriched field)
        tier = offer.get("company_tier")
        if tier:
            cat_data["tiers"][tier] += 1

    # ── Build CareerMetrics ───────────────────────────────────────────────
    updated_careers = []

    for category, data in categorized_data.items():
        salaries = data["salaries"]
        salario_obj = {"min": 0, "max": 0, "promedio": 0}

        if salaries:
            salario_obj["min"] = round(min(salaries), 2)
            salario_obj["max"] = round(max(salaries), 2)
            salario_obj["promedio"] = round(sum(salaries) / len(salaries), 2)
        else:
            # Fallback: estimate from market baselines
            base_monthly = _get_fallback_salary(category)
            salario_obj["promedio"] = round(base_monthly * 12, 2)
            salario_obj["min"] = round(salario_obj["promedio"] * 0.7, 2)
            salario_obj["max"] = round(salario_obj["promedio"] * 1.5, 2)

        # Top skills and companies
        top_skills = [s[0] for s in data["skills"].most_common(5)]
        top_companies = [c[0] for c in data["companies"].most_common(3)]

        # Dominant tier
        dominant_tier = data["tiers"].most_common(1)
        top_tier = dominant_tier[0][0] if dominant_tier else 4

        # Trend: growing if > 10 offers, stable otherwise
        tendencia = "creciente" if data["count"] > 10 else "estable"

        # Tier label
        tier_labels = {
            1: "TOP - Big Tech",
            2: "Regional Conocida",
            3: "Mediana en Crecimiento",
            4: "Pequeña/Desconocida",
        }

        metrics = CareerMetrics(
            titulo_carrera=category,
            nivel_referencia="General",
            region_mercado="Perú",
            salario_anual_usd=salario_obj,
            demanda_mercado={
                "volumen_total": data["count"],
                "tendencia": tendencia,
                "top_tier": top_tier,
                "top_tier_label": tier_labels.get(top_tier, "Desconocido"),
            },
            analisis_competitivo={"top_empresas": top_companies},
            aprendizaje={"habilidades_clave": top_skills},
            ultima_actualizacion=datetime.utcnow(),
        )

        await careers_col.update_one(
            {"titulo_carrera": category},
            {"$set": metrics.model_dump(by_alias=True, exclude_none=True)},
            upsert=True,
        )
        updated_careers.append(category)

    return updated_careers


async def clean_legacy_generic_skills() -> Dict[str, int]:
    """
    Remove generic/non-technical skills from legacy offers in ofertas_laborales.

    Returns dict with counts of skills removed per offer.
    """
    import re

    db = get_database()
    offers_col = db["ofertas_laborales"]

    # Find offers that contain generic skills (case-insensitive match)
    generic_pattern = "|".join(re.escape(s) for s in GENERIC_SKILLS)
    cursor = offers_col.find(
        {"habilidades_requeridas": {"$regex": f"^{generic_pattern}$", "$options": "i"}},
        {"habilidades_requeridas": 1},
    )
    offers = await cursor.to_list(length=2000)

    cleaned = 0
    total_removed = 0

    for offer in offers:
        skills = offer.get("habilidades_requeridas", [])
        filtered = [s for s in skills if not _is_generic_skill(s)]
        removed_count = len(skills) - len(filtered)

        if removed_count > 0 or any(_normalize_skill_name(s) != s for s in filtered):
            # Also normalize remaining skills
            normalized_skills = [_normalize_skill_name(s) for s in filtered]
            await offers_col.update_one(
                {"_id": offer["_id"]},
                {"$set": {"habilidades_requeridas": normalized_skills}},
            )
            cleaned += 1
            total_removed += removed_count

    return {"offers_cleaned": cleaned, "skills_removed": total_removed}


__all__ = [
    "update_market_skills",
    "update_career_metrics",
    "clean_legacy_generic_skills",
    "_get_category_for_offer",
    "_get_fallback_salary",
    "_is_generic_skill",
    "GENERIC_SKILLS",
    "SALARY_BASELINES_MONTHLY",
]
