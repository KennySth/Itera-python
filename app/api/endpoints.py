import asyncio
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import quote
from fastapi import APIRouter, Query, BackgroundTasks
from fastapi.responses import RedirectResponse, HTMLResponse
from app.core.database import get_database
from app.core.computrabajo_scraper import ComputrabajoScraper
from app.core.linkedin_scraper import LinkedInScraper
from app.core.analytics import update_market_skills, update_career_metrics
from app.core.market_demand import get_market_demand_aggregated
from app.core.matching import evaluate_student_compatibility
from app.core.career_taxonomy import CAREER_CATEGORIES
from app.core.company_ranker import TIER_DEFINITIONS, rank_company
from app.core.skill_extractor import extract_from_offer
from app.models.schemas import (
    JobOffer,
    MarketSkill,
    MatchRequest,
    ScrapingAudit,
    ExplorationTelemetry,
    RecommendationFeedback,
    CareerMetrics,
    ToggleNodeRequest,
)

router = APIRouter()

# --- Scraper & Data ---

# --- Proxy / Redirect (external job sites) ---


@router.get("/offers/redirect", tags=["Offers"], include_in_schema=False)
async def redirect_to_external(url: str = Query(..., description="External job URL")):
    """
    Redirects to the external job URL with a clean browser context.
    Uses a meta-refresh HTML page instead of a 302 to avoid Referer
    header being sent to the external site.
    """
    safe_url = quote(url, safe=":/?#=&")
    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="0; url={safe_url}">
  <title>Redirigiendo...</title>
</head>
<body>
  <p>Redirigiendo a la oferta externa...</p>
  <a href="{safe_url}">Click aquí si no redirige automáticamente</a>
</body>
</html>"""
    return HTMLResponse(content=html)


# --- Scraper & Data


async def run_scraper_task(query: str, use_ai: bool = False) -> None:
    """Tarea de fondo para ejecutar múltiples scrapers en paralelo sin bloquear la API."""
    ct_scraper = ComputrabajoScraper()
    li_scraper = LinkedInScraper()

    # Ejecutamos ambos scrapers de forma concurrente
    results = await asyncio.gather(
        ct_scraper.scrape(query, use_ai=use_ai),
        li_scraper.scrape(query, use_ai=use_ai),
        return_exceptions=True,
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
    use_ai: bool = Query(
        False, description="Usar IA para extracción de skills y clasificación"
    ),
) -> Dict[str, Any]:
    """
    Ejecuta el scraper en segundo plano (RNF-07) y guarda los resultados en MongoDB.

    Params:
    - query: Término de búsqueda
    - use_ai: Si True, usa IA para extraer skills y clasificar carreras (más lento pero más preciso).
              Recomendado usar False para batch, True para scraping ocasional con preview.
    """
    background_tasks.add_task(run_scraper_task, query, use_ai)
    return {
        "status": "accepted",
        "message": f"Scraping para '{query}' iniciado en segundo plano (AI={use_ai}).",
        "query": query,
        "use_ai": use_ai,
    }


@router.post("/scraper/preview", tags=["Scraper (RNF-07)"])
async def preview_scraper(
    query: str = Query(..., description="Término de búsqueda (ej. Python, React)"),
    use_ai: bool = Query(
        True, description="Usar IA para clasificación y extracción de skills"
    ),
    limit: int = Query(10, ge=1, le=50, description="Máximo de ofertas a procesar"),
) -> Dict[str, Any]:
    """
    Ejecuta el scraper y retorna las ofertas ENRIQUECIDAS para revisión ANTES de guardar en MongoDB.

    Útil para verificar qué categoría, skills y tier de empresa se asigna a cada oferta
    antes de persistir los datos.

    Retorna:
    - Lista de ofertas con todos los campos enriquecidos
    - Método usado (regex/ai/keyword) por campo
    - Nivel de confianza
    - Estadísticas de resumen

    Una vez verificado, usar POST /scraper/run para guardar.
    """
    ct_scraper = ComputrabajoScraper()
    li_scraper = LinkedInScraper()

    # Scrap both sources in parallel (with AI enrichment if requested)
    results = await asyncio.gather(
        ct_scraper.scrape(query, use_ai=use_ai),
        li_scraper.scrape(query, use_ai=use_ai),
        return_exceptions=True,
    )

    ct_offers = results[0] if not isinstance(results[0], Exception) else []
    li_offers = results[1] if not isinstance(results[1], Exception) else []

    all_offers = ct_offers + li_offers
    all_offers = all_offers[:limit]  # Cap at limit

    # Build preview directly from already-enriched JobOffers
    preview_offers_list = []
    for offer in all_offers:
        preview_offers_list.append(
            {
                "source": offer.fuente,
                "url": offer.url_origen,
                "raw_title": offer.puesto,
                "raw_company": offer.empresa,
                "normalized_company": offer.empresa,
                "company_tier": offer.company_tier,
                "company_rank_confidence": 0.9 if offer.company_tier else 0.3,
                "career_category_id": offer.categoria_carrera or "",
                "career_category_name": offer.categoria_carrera_nombre or "",
                "career_classification_method": "regex",  # Default for now
                "career_confidence": 0.85,
                "raw_skills": offer.habilidades_requeridas,
                "skills_extracted": offer.habilidades_requeridas,
                "skills_extraction_method": offer.skill_extraction_method or "regex",
                "skills_ai_used": (offer.skill_extraction_method == "ai"),
                "raw_salary_usd": offer.salario_normalizado_usd,
            }
        )

    ai_used_count = sum(1 for o in preview_offers_list if o["skills_ai_used"])

    return {
        "query": query,
        "use_ai": use_ai,
        "total_scraped": len(all_offers),
        "preview": {
            "total_raw": len(all_offers),
            "total_enriched": len(all_offers),
            "ai_used_count": ai_used_count,
            "offers": preview_offers_list,
            "errors": [],
        },
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
        request.student_id, request.skills, request.career_category
    )
    return result


@router.post("/analytics/refresh", tags=["Analytics"])
async def refresh_analytics() -> Dict[str, Any]:
    """
    Procesa las ofertas actuales para actualizar métricas de habilidades y carreras.
    Limpia skills genéricos de ofertas legacy antes de recalcular.
    """
    from app.core.analytics import clean_legacy_generic_skills

    # Step 1: Clean generic skills from legacy offers
    cleanup = await clean_legacy_generic_skills()

    # Step 2: Refresh market skills and career metrics (with generic filter)
    skills = await update_market_skills()
    careers_updated = await update_career_metrics()

    return {
        "status": "success",
        "cleanup": cleanup,
        "skills_updated": len(skills),
        "careers_updated": len(careers_updated),
        "top_skills": skills[:5],
        "careers_processed": careers_updated,
    }


@router.post("/analytics/backfill", tags=["Analytics (Phase 8)"])
async def backfill_enriched_fields(
    dry_run: bool = Query(
        True, description="Si True, solo retorna qué se haría sin modificar la DB"
    ),
    use_ai: bool = Query(
        False, description="Usar IA para clasificación de carreras (más lento)"
    ),
    limit: int = Query(200, ge=1, le=1000, description="Máximo de ofertas a procesar"),
) -> Dict[str, Any]:
    """
    Re-enriquece ofertas legacy (sin categoria_carrera_nombre, company_tier, skill_extraction_method).

    Para cada oferta legacy:
    1. Clasifica carrera con career_classifier
    2. Clasifica tier de empresa con company_ranker
    3. Extrae skills con skill_extractor (solo si no tiene habilidades)

    Si dry_run=True, solo retorna el resumen sin persistir cambios.
    Útil para verificar qué se haría antes de aplicar.

    Luego de ejecutar con dry_run=False, ejecutar POST /analytics/refresh
    para recalcular métricas con los nuevos datos enriquecidos.
    """
    from app.core.career_classifier import classify as classify_career

    database = get_database()
    offers_col = database["ofertas_laborales"]

    # Find legacy offers (missing enriched fields)
    legacy_filter = {
        "$or": [
            {"categoria_carrera_nombre": {"$exists": False}},
            {"categoria_carrera_nombre": None},
            {"company_tier": {"$exists": False}},
            {"company_tier": None},
        ]
    }

    cursor = offers_col.find(legacy_filter).limit(limit)
    legacy_offers = await cursor.to_list(length=limit)

    if not legacy_offers:
        return {
            "status": "no_legacy_offers",
            "message": "No hay ofertas legacy por enriquecer",
            "dry_run": dry_run,
            "processed": 0,
            "changes": [],
        }

    # Process each legacy offer
    processed = 0
    career_counts: Dict[str, int] = {}
    tier_counts: Dict[int, int] = {}
    errors: List[Dict[str, Any]] = []
    changes: List[Dict[str, Any]] = []

    for offer in legacy_offers:
        try:
            offer_id = offer.get("_id")
            title = offer.get("puesto", "")
            company = offer.get("empresa", "")

            # 1. Classify career category
            career_result = classify_career(title, company, use_ai=use_ai)
            category_id = career_result.category_id
            category_name = career_result.category_name
            career_method = career_result.method

            # 2. Rank company tier
            rank_result = rank_company(company)
            company_tier = rank_result.tier
            normalized_company = rank_result.cleaned_name

            # 3. Extract skills (only if empty)
            existing_skills = offer.get("habilidades_requeridas", [])
            if existing_skills:
                skill_method = "existing"
                final_skills = existing_skills[:50]
            else:
                skill_result = extract_from_offer(offer, use_ai=use_ai)
                skill_method = skill_result.method
                final_skills = skill_result.skills[:50]

            # Build update payload
            update_payload = {
                "categoria_carrera": category_id,
                "categoria_carrera_nombre": category_name,
                "company_tier": company_tier,
                "skill_extraction_method": skill_method,
            }

            if final_skills and not existing_skills:
                update_payload["habilidades_requeridas"] = final_skills

            # Track stats
            career_counts[category_name] = career_counts.get(category_name, 0) + 1
            tier_counts[company_tier] = tier_counts.get(company_tier, 0) + 1

            change_record = {
                "offer_id": str(offer_id),
                "title": title,
                "company": company,
                "normalized_company": normalized_company,
                "category_id": category_id,
                "category_name": category_name,
                "career_method": career_method,
                "company_tier": company_tier,
                "skill_method": skill_method,
                "skill_count": len(final_skills),
            }
            changes.append(change_record)

            # Persist if not dry run
            if not dry_run:
                await offers_col.update_one(
                    {"_id": offer_id},
                    {"$set": update_payload},
                )

            processed += 1

        except Exception as e:
            errors.append(
                {
                    "offer_id": str(offer.get("_id", "unknown")),
                    "title": offer.get("puesto", ""),
                    "error": str(e),
                }
            )

    # Summary
    tier_labels = {
        1: "TOP - Big Tech",
        2: "Regional Conocida",
        3: "Mediana en Crecimiento",
        4: "Pequeña/Desconocida",
    }

    summary = {
        "total_legacy": len(legacy_offers),
        "processed": processed,
        "errors": len(errors),
        "career_distribution": career_counts,
        "tier_distribution": {
            tier_labels.get(t, f"Tier {t}"): count
            for t, count in sorted(tier_counts.items())
        },
        "skill_methods": {},
    }

    # Count skill methods
    for c in changes:
        m = c["skill_method"]
        summary["skill_methods"][m] = summary["skill_methods"].get(m, 0) + 1

    return {
        "status": "success",
        "dry_run": dry_run,
        "message": "Preview de cambios"
        if dry_run
        else "Ofertas enriquecidas correctamente",
        "summary": summary,
        "changes": changes[:50],  # Cap preview to 50
        "errors": errors,
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


@router.get("/careers/categories", tags=["Analytics (Phase 6)"])
async def get_careers_categories() -> Dict[str, Any]:
    """
    Lista todas las categorías de carrera disponibles con su información.

    Retorna todas las 17 categorías del taxonomy con:
    - id: identificador URL-safe
    - name: nombre para mostrar
    - description: descripción breve
    """
    categories = []
    for cat in CAREER_CATEGORIES:
        categories.append(
            {
                "id": cat.id,
                "name": cat.name,
                "description": f"Carreras relacionadas con {cat.name.lower()}",
            }
        )

    return {
        "total": len(categories),
        "categories": categories,
    }


@router.get("/companies/top", tags=["Analytics (Phase 6)"])
async def get_top_companies(
    min_tier: int = Query(
        1, ge=1, le=4, description="Filtrar por tier máximo (1=Tier 1, 2=Tier 1-2)"
    ),
    limit: int = Query(20, ge=1, le=100, description="Máximo de empresas a retornar"),
) -> Dict[str, Any]:
    """
    Lista las empresas TOP del mercado por tier.

    Tier 1: Big Tech y multinacionales (Google, Amazon, Mercado Libre, etc.)
    Tier 2: Empresas regionales conocidas (BBVA, Globant, Interbank, etc.)
    Tier 3: Empresas medianas en crecimiento (Belvo, Deel, etc.)

    Combina:
    1. Empresas que aparecen en las ofertas guardadas (con conteo real)
    2. Empresas conocidas del taxonomy que no tienen ofertas (con offer_count=0)

    Esto asegura que BBVA, BCP, Globant, etc. aparezcan aunque no tengan
    ofertas activas en la base de datos.
    """
    from app.core.company_ranker import (
        rank_company,
        TIER_1_TOP,
        TIER_2_KNOWN,
        TIER_3_MIDSIZE,
    )

    database = get_database()
    offers_col = database["ofertas_laborales"]

    # 1. Group companies from offers
    pipeline: List[Dict[str, Any]] = [
        {
            "$match": {
                "empresa": {"$ne": None, "$ne": "Confidencial"},
            }
        },
        {
            "$group": {
                "_id": "$empresa",
                "count": {"$sum": 1},
                "avg_tier": {"$avg": "$company_tier"},
                "avg_salary": {"$avg": "$salario_normalizado_usd"},
            }
        },
        {"$sort": {"count": -1}},
    ]

    cursor = offers_col.aggregate(pipeline)
    db_companies = await cursor.to_list(length=200)

    # Build dict of companies in DB: normalized_name -> {count, avg_salary, tier}
    db_companies_map: Dict[str, Dict[str, Any]] = {}
    for c in db_companies:
        raw_name = c["_id"]
        rank = rank_company(raw_name)
        stored_tier = c.get("avg_tier")
        tier = round(stored_tier) if stored_tier is not None else rank.tier
        db_companies_map[rank.cleaned_name.lower()] = {
            "count": c["count"],
            "avg_salary": c.get("avg_salary") or 0,
            "tier": tier,
            "clean_name": rank.cleaned_name,
        }

    tier_labels = {
        1: "TOP - Big Tech",
        2: "Regional Conocida",
        3: "Mediana en Crecimiento",
        4: "Pequeña/Desconocida",
    }

    # 2. Collect known companies from taxonomy (Tier 1-3)
    seen_names: set[str] = set()
    result_companies: List[Dict[str, Any]] = []

    # ponytail: include known companies from taxonomy tiers 1-3
    for tier_def in [TIER_1_TOP, TIER_2_KNOWN, TIER_3_MIDSIZE]:
        if tier_def.tier > min_tier:
            continue
        for alias in tier_def.aliases:
            key = alias.lower()
            if key in seen_names:
                continue
            seen_names.add(key)
            if key in db_companies_map:
                # Company exists in DB - use DB data
                data = db_companies_map[key]
                result_companies.append(
                    {
                        "name": data["clean_name"],
                        "offer_count": data["count"],
                        "tier": data["tier"],
                        "tier_name": tier_labels.get(data["tier"], "Desconocida"),
                        "avg_salary_usd": round(data["avg_salary"], 2),
                        "from_taxonomy": False,
                    }
                )
            else:
                # Known company not in DB yet - show with 0 offers
                result_companies.append(
                    {
                        "name": alias,
                        "offer_count": 0,
                        "tier": tier_def.tier,
                        "tier_name": tier_labels.get(tier_def.tier, "Desconocida"),
                        "avg_salary_usd": 0,
                        "from_taxonomy": True,
                    }
                )

    # 3. Add companies from DB that are not in taxonomy (Tier 4 or unknown)
    for c in db_companies:
        raw_name = c["_id"]
        rank = rank_company(raw_name)
        key = rank.cleaned_name.lower()
        if key in seen_names:
            continue
        seen_names.add(key)
        stored_tier = c.get("avg_tier")
        tier = round(stored_tier) if stored_tier is not None else rank.tier
        if tier > min_tier:
            continue
        result_companies.append(
            {
                "name": rank.cleaned_name,
                "offer_count": c["count"],
                "tier": tier,
                "tier_name": tier_labels.get(tier, "Desconocida"),
                "avg_salary_usd": round(c.get("avg_salary") or 0, 2),
                "from_taxonomy": False,
            }
        )

    # Sort: Tier 1 first, then companies WITH offers before those without,
    # then by offer_count descending
    result_companies.sort(
        key=lambda x: (-x["tier"], -(x["offer_count"] > 0), -x["offer_count"])
    )

    return {
        "min_tier": min_tier,
        "total": len(result_companies),
        "companies": result_companies[:limit],
    }


@router.post("/companies/cleanup", tags=["Analytics (Phase 8)"])
async def cleanup_dirty_company_names(
    dry_run: bool = Query(
        True, description="Si True, solo retorna qué se haría sin modificar la DB"
    ),
    limit: int = Query(500, ge=1, le=2000, description="Máximo de ofertas a limpiar"),
) -> Dict[str, Any]:
    """
    Limpia los nombres de empresa sucios en MongoDB.

    Algunos scrapers guardan nombres como:
    - "4,3\\r\\n\\t\\t\\t\\n...Overall Strategy"
    - "4.0\\\\nEmpresa SAC"
    - "3,8 DepilZONE"

    Este endpoint:
    1. Busca ofertas con nombres sucios (contienen \\r, \\n, o rating prefixes)
    2. Limpia usando rank_company().cleaned_name
    3. Actualiza el campo 'empresa' en MongoDB si dry_run=False

    Recomendación: ejecutar primero con dry_run=True para ver el preview.
    """
    import re

    from app.core.company_ranker import rank_company

    database = get_database()
    offers_col = database["ofertas_laborales"]

    # Find all offers
    cursor = offers_col.find({}).limit(limit)
    all_offers = await cursor.to_list(length=limit)

    # Detect dirty company names
    dirty_pattern = re.compile(r"[\r\n]|^[\d.,]+\s", re.IGNORECASE)

    dirty_offers = []
    clean_changes = []

    for offer in all_offers:
        raw_company = offer.get("empresa", "") or ""
        if dirty_pattern.search(raw_company) or re.match(
            r"^\d[.,]\d", raw_company.strip()
        ):
            rank = rank_company(raw_company)
            dirty_offers.append(offer.get("url_origen"))
            clean_changes.append(
                {
                    "url_origen": offer.get("url_origen"),
                    "raw": raw_company,
                    "cleaned": rank.cleaned_name,
                    "matched": rank.matched_pattern,
                }
            )

    if dry_run:
        return {
            "status": "preview",
            "dry_run": True,
            "total_checked": len(all_offers),
            "dirty_count": len(dirty_offers),
            "changes": clean_changes[:50],
            "message": f"Preview: {len(dirty_offers)} ofertas con nombres sucios (de {len(all_offers)} revisadas)",
        }

    # Apply changes using url_origen as unique identifier
    updated = 0
    errors = []
    for change in clean_changes:
        try:
            result = await offers_col.update_one(
                {"url_origen": change["url_origen"]},
                {"$set": {"empresa": change["cleaned"]}},
            )
            if result.modified_count > 0:
                updated += 1
        except Exception as e:
            errors.append({"url_origen": change["url_origen"], "error": str(e)})

    return {
        "status": "success",
        "dry_run": False,
        "total_checked": len(all_offers),
        "dirty_count": len(dirty_offers),
        "updated": updated,
        "errors": len(errors),
        "message": f"Se limpiaron {updated} nombres de empresa",
    }


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
                "_id": 0,
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


@router.get("/market/salary-snapshots", tags=["Analytics (RF-07)"])
async def salary_snapshots(
    career: Optional[str] = None, years: int = 2
) -> Dict[str, Any]:
    """
    Obtiene historial salarial por carrera para comparaciones año contra año.
    Returns snapshots grouped by career and year for the specified time range.
    """
    database = get_database()
    snapshots_col = database["salary_snapshots"]

    now = datetime.utcnow()
    min_year = now.year - years

    # Build match filter
    match_filter: Dict[str, Any] = {"snapshot_year": {"$gte": min_year}}
    if career:
        match_filter["titulo_carrera"] = career

    pipeline: List[Dict[str, Any]] = [
        {"$match": match_filter},
        {
            "$group": {
                "_id": {
                    "career": "$titulo_carrera",
                    "year": "$snapshot_year",
                },
                "salario_promedio": {"$avg": "$salario_promedio"},
                "salario_min": {"$first": "$salario_min"},
                "salario_max": {"$last": "$salario_max"},
                "volumen_total": {"$sum": "$volumen_total"},
                "snapshots_count": {"$sum": 1},
                "latest_month": {"$max": "$snapshot_month"},
            }
        },
        {
            "$project": {
                "_id": 0,
                "career": "$_id.career",
                "year": "$_id.year",
                "salario_promedio": {"$round": ["$salario_promedio", 0]},
                "salario_min": 1,
                "salario_max": 1,
                "volumen_total": 1,
                "snapshots_count": 1,
                "latest_month": 1,
            }
        },
        {"$sort": {"career": 1, "year": 1}},
    ]

    cursor = snapshots_col.aggregate(pipeline)
    raw_snapshots = await cursor.to_list(length=500)

    # Group by career
    by_career: Dict[str, List[Dict[str, Any]]] = {}
    for s in raw_snapshots:
        career_name = s["career"]
        if career_name not in by_career:
            by_career[career_name] = []
        by_career[career_name].append(
            {
                "year": s["year"],
                "salario_promedio": s["salario_promedio"],
                "salario_min": s["salario_min"],
                "salario_max": s["salario_max"],
                "volumen_total": s["volumen_total"],
            }
        )

    # Get available years for filter UI
    available_years = sorted(set(s["year"] for s in raw_snapshots), reverse=True)

    return {
        "snapshots": by_career,
        "available_years": available_years,
        "total_careers": len(by_career),
        "year_range": {"from": min_year, "to": now.year},
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


# --- Learning Paths (Roadmap) ---


@router.get("/learning/paths", tags=["Learning"])
async def get_all_learning_paths() -> Dict[str, Any]:
    """Retorna todas las rutas de aprendizaje disponibles."""
    db = get_database()
    cursor = db["learning_paths"].find({}, {"_id": 0}).sort("goal_id", 1)
    paths = await cursor.to_list(length=20)
    return {"paths": paths, "total": len(paths)}


@router.get("/learning/paths/{goal_id}", tags=["Learning"])
async def get_learning_path(goal_id: str) -> Dict[str, Any]:
    """Retorna una ruta específica por goal_id."""
    db = get_database()
    path = await db["learning_paths"].find_one({"goal_id": goal_id}, {"_id": 0})
    if not path:
        return {"error": "Path not found", "goal_id": goal_id}
    return path


@router.put("/learning/progress", tags=["Learning"])
async def toggle_node_progress(body: ToggleNodeRequest) -> Dict[str, Any]:
    """Marca o desmarca un nodo como completado para un usuario."""
    db = get_database()
    progress_col = db["user_learning_progress"]
    now = datetime.utcnow()

    # Find or create progress record
    progress = await progress_col.find_one(
        {
            "user_id": body.user_id,
            "goal_id": body.goal_id,
        }
    )

    if not progress:
        progress = {
            "user_id": body.user_id,
            "goal_id": body.goal_id,
            "completed_nodes": [],
            "current_node": None,
            "started_at": now,
            "last_activity": now,
        }

    completed = progress.get("completed_nodes", [])

    if body.completed and body.node_id not in completed:
        completed.append(body.node_id)
    elif not body.completed and body.node_id in completed:
        completed.remove(body.node_id)

    # Determine current_node (first non-completed node)
    path = await db["learning_paths"].find_one(
        {"goal_id": body.goal_id}, {"_id": 0, "nodes.id": 1}
    )
    current_node = None
    if path:
        for node in path.get("nodes", []):
            if node["id"] not in completed:
                current_node = node["id"]
                break

    await progress_col.update_one(
        {"user_id": body.user_id, "goal_id": body.goal_id},
        {
            "$set": {
                "completed_nodes": completed,
                "current_node": current_node,
                "last_activity": now,
            },
            "$setOnInsert": {
                "started_at": now,
            },
        },
        upsert=True,
    )

    total_nodes = len(path.get("nodes", [])) if path else 0
    progress_pct = (
        round((len(completed) / total_nodes * 100), 1) if total_nodes > 0 else 0
    )

    return {
        "status": "updated",
        "completed_nodes": completed,
        "current_node": current_node,
        "total_nodes": total_nodes,
        "progress_percent": progress_pct,
    }


@router.get("/learning/progress/{user_id}", tags=["Learning"])
async def get_user_progress(user_id: str) -> Dict[str, Any]:
    """Retorna el progreso del usuario en todas las rutas de aprendizaje."""
    db = get_database()
    cursor = db["user_learning_progress"].find({"user_id": user_id}, {"_id": 0})
    records = await cursor.to_list(length=20)

    enriched = []
    for rec in records:
        path = await db["learning_paths"].find_one(
            {"goal_id": rec["goal_id"]}, {"_id": 0, "nodes": 1}
        )
        total = len(path.get("nodes", [])) if path else 0
        completed_count = len(rec.get("completed_nodes", []))
        enriched.append(
            {
                **rec,
                "total_nodes": total,
                "progress_percent": round((completed_count / total * 100), 1)
                if total > 0
                else 0,
            }
        )

    return {"user_id": user_id, "progress": enriched}
