import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
import numpy as np
from app.core.database import get_database
from app.core.skill_taxonomy import ALIAS_TO_SKILL
from app.models.schemas import MatchHistory, JobOffer

logger = logging.getLogger(__name__)

# Generic skills that should not dominate the match score
GENERIC_SKILLS = {
    "analista",
    "análisis",
    "office",
    "microsoft office",
    "excel",
    "comunicación",
    "liderazgo",
    "trabajo en equipo",
    "gestión",
    "planificación",
    "organización",
    "proactivo",
    "responsable",
    "devops",
}

# ─────────────────────────────────────────────────────────────────────────────
# Career category → allowed skill keywords (from career_taxonomy.py)
# Used to filter top_market_skills so irrelevant skills don't appear
# ─────────────────────────────────────────────────────────────────────────────
CATEGORY_SKILL_KEYWORDS: Dict[str, List[str]] = {
    "desarrollo-backend": [
        "python",
        "java",
        "node",
        "node.js",
        "sql",
        "postgresql",
        "mysql",
        "mongodb",
        "redis",
        "docker",
        "django",
        "flask",
        "fastapi",
        "spring",
        "spring boot",
        "laravel",
        "php",
        "go",
        "c#",
        ".net",
        "git",
        "rest api",
        "kubernetes",
        "linux",
        "oracle",
        "sql server",
        "express",
        "nestjs",
        "ruby",
        "rails",
        "scala",
        "kotlin",
        "rust",
        "aws",
        "azure",
    ],
    "desarrollo-frontend": [
        "react",
        "angular",
        "vue",
        "vue.js",
        "javascript",
        "typescript",
        "html",
        "css",
        "html/css",
        "next.js",
        "tailwind css",
        "redux",
        "graphql",
        "rest api",
        "svelte",
        "node.js",
        "python",
        "git",
        "d3.js",
        "bootstrap",
        "jquery",
        "sql",
        "postgresql",
        "mongodb",
    ],
    "ciencia-datos-ia": [
        "python",
        "machine learning",
        "deep learning",
        "sql",
        "tensorflow",
        "pytorch",
        "spark",
        "airflow",
        "dbt",
        "pandas",
        "numpy",
        "scikit-learn",
        "nlp",
        "ai generativa",
        "snowflake",
        "bigquery",
        "databricks",
        "etl",
        "data warehouse",
        "power bi",
        "tableau",
        "r",
        "docker",
        "aws",
        "azure",
        "postgresql",
        "mongodb",
    ],
    "devops-cloud": [
        "aws",
        "azure",
        "google cloud",
        "docker",
        "kubernetes",
        "terraform",
        "ansible",
        "jenkins",
        "github actions",
        "gitlab ci",
        "linux",
        "nginx",
        "prometheus",
        "grafana",
        "helm",
        "ci/cd",
        "git",
        "python",
        "bash/shell",
        "cloudformation",
        "pulumi",
        "serverless",
        "vault",
    ],
    "desarrollo-fullstack": [
        "react",
        "angular",
        "vue",
        "vue.js",
        "javascript",
        "typescript",
        "node",
        "node.js",
        "python",
        "sql",
        "postgresql",
        "mongodb",
        "html",
        "css",
        "html/css",
        "git",
        "docker",
        "rest api",
        "graphql",
    ],
}


def _skill_belongs_to_category(skill_name: str, category_id: Optional[str]) -> bool:
    """Check if a skill is relevant for the given career category."""
    if not category_id:
        return True  # General mode: keep all skills

    allowed = CATEGORY_SKILL_KEYWORDS.get(category_id, [])
    if not allowed:
        return True  # Unknown category: keep all

    skill_lower = skill_name.lower().strip()
    # Direct match (case-insensitive)
    if skill_lower in allowed:
        return True
    # Check via taxonomy canonical name
    canonical = ALIAS_TO_SKILL.get(skill_lower, skill_lower)
    if canonical.lower() in allowed:
        return True
    return False


# Skill synonyms for fuzzy matching
SKILL_SYNONYMS = {
    "javascript": ["js", "ecmascript", "es6", "es2015"],
    "typescript": ["ts"],
    "python": ["py"],
    "react": ["reactjs", "react.js"],
    "angular": ["angularjs", "angular.js"],
    "vue": ["vuejs", "vue.js", "vue3"],
    "node": ["nodejs", "node.js"],
    "java": ["jdk", "jvm"],
    "c#": ["csharp", "c sharp", ".net"],
    "sql": ["mysql", "postgresql", "postgres", "sql server", "mariadb"],
    "nosql": ["mongodb", "redis", "cassandra", "dynamodb"],
    "html": ["html5"],
    "css": ["css3", "sass", "scss", "less", "tailwind"],
    "docker": ["containers", "containerization"],
    "kubernetes": ["k8s"],
    "aws": ["amazon web services"],
    "gcp": ["google cloud", "google cloud platform"],
    "azure": ["microsoft azure"],
    "git": ["github", "gitlab", "bitbucket"],
    "rest": ["restful", "rest api", "api rest"],
    "graphql": ["gql"],
    "machine learning": ["ml", "aprendizaje automático"],
    "deep learning": ["dl", "aprendizaje profundo"],
    "data science": ["ciencia de datos"],
    "power bi": ["powerbi"],
    "tableau": [],
    "spark": ["apache spark", "pyspark"],
}


def _normalize_skill(skill: str) -> str:
    """Normalize a skill name for comparison."""
    from app.core.skill_taxonomy import ALIAS_TO_SKILL

    normalized = skill.lower().strip()
    return ALIAS_TO_SKILL.get(normalized, normalized)


def _find_synonym_match(student_skill: str, market_skill: str) -> bool:
    """Check if two skills match via synonyms."""
    s_norm = _normalize_skill(student_skill)
    m_norm = _normalize_skill(market_skill)

    # Direct match
    if s_norm == m_norm:
        return True

    # Check if market skill is a synonym of student skill
    for base, synonyms in SKILL_SYNONYMS.items():
        if s_norm == base and m_norm in synonyms:
            return True
        if m_norm == base and s_norm in synonyms:
            return True
        if s_norm in synonyms and m_norm in synonyms:
            return True
        if s_norm == base and m_norm == base:
            return True

    return False


def calculate_cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """
    Calcula la similitud del coseno entre dos vectores numéricos.
    """
    if not vec_a or not vec_b:
        return 0.0
    if len(vec_a) != len(vec_b):
        logger.warning(
            f"Vectores con diferentes longitudes: {len(vec_a)} vs {len(vec_b)}"
        )
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
    student_skills: List[str],
    career_category: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Compara las habilidades de un estudiante contra las ofertas del mercado laboral
    y calcula el Match-Score y la brecha de habilidades.

    Uses career taxonomy keywords as the canonical skill list per category,
    supplemented by actual market demand from offers.
    """
    db = get_database()
    if db is None:
        return {"error": "Database not connected"}

    offers_col = db["ofertas_laborales"]

    # Build query filter (optionally by career category)
    query_filter: Dict[str, Any] = {}
    if career_category:
        query_filter["categoria_carrera"] = career_category

    # Get offer count for context
    offer_count = await offers_col.count_documents(query_filter)
    has_offers = offer_count > 0

    # Get offer-based skill demand (only if we have offers)
    market_skills_counter: Counter = Counter()
    if has_offers:
        cursor = offers_col.find(query_filter, {"habilidades_requeridas": 1})
        all_offers = await cursor.to_list(length=500)
        for doc in all_offers:
            raw_skills = doc.get("habilidades_requeridas", [])
            for skill in raw_skills:
                norm = _normalize_skill(skill)
                if norm not in GENERIC_SKILLS:
                    market_skills_counter[norm] += 1

    # Build top skills: taxonomy keywords (authoritative) + market data (informational)
    top_skills: List[str] = []
    if career_category and career_category in CATEGORY_SKILL_KEYWORDS:
        # Use taxonomy keywords as canonical list, weighted by market demand
        taxonomy_skills = CATEGORY_SKILL_KEYWORDS[career_category]
        skill_scores: Dict[str, float] = {}
        for s in taxonomy_skills:
            # Score = market demand count (if available) + small base weight to ensure all appear
            market_count = market_skills_counter.get(s, 0)
            skill_scores[s] = market_count + 0.1

        # Sort by score descending
        sorted_skills = sorted(skill_scores.items(), key=lambda x: x[1], reverse=True)
        top_skills = [s for s, _ in sorted_skills[:10]]
    elif market_skills_counter:
        top_skills = [s for s, _ in market_skills_counter.most_common(10)]
    else:
        top_skills = []

    if not top_skills:
        return {
            "score": 0,
            "habilidades_faltantes": [],
            "recomendaciones": [
                "No se encontraron habilidades técnicas relevantes en el mercado."
            ],
        }

    # 3. Match student skills against market skills (with synonyms)
    student_skills_normalized = [_normalize_skill(s) for s in student_skills]
    matched_market_skills: List[str] = []
    missing_market_skills: List[str] = []

    for market_skill in top_skills:
        skill_matched = False
        for student_skill in student_skills_normalized:
            if _find_synonym_match(student_skill, market_skill):
                skill_matched = True
                break
        if skill_matched:
            matched_market_skills.append(market_skill)
        else:
            missing_market_skills.append(market_skill)

    # 4. Calculate score as % of skills matched (all skills equally weighted)
    total_skills = len(top_skills)
    matched_count = len(matched_market_skills)
    score = int((matched_count / total_skills) * 100) if total_skills > 0 else 0

    # 5. Generate actionable recommendations
    recommendations: List[str] = []
    if missing_market_skills:
        top_missing = missing_market_skills[:3]
        recommendations.append(
            f"Para mejorar tu perfil, considera aprender: {', '.join(top_missing)}."
        )

    if score >= 70:
        recommendations.append(
            "¡Buen trabajo! Estás bien alineado con las tendencias del mercado."
        )
    elif score >= 40:
        recommendations.append(
            "Tu nivel es intermedio. Profundiza en las habilidades faltantes para alcanzar un mejor puntaje."
        )
    else:
        recommendations.append(
            "Tu nivel de coincidencia es bajo. Enfócate en las habilidades core del mercado."
        )

    # 6. Also check student skills that are NOT in top market (their unique strengths)
    student_only_skills = []
    for s in student_skills_normalized:
        is_market = any(_find_synonym_match(s, m) for m in top_skills)
        if not is_market and s not in GENERIC_SKILLS:
            student_only_skills.append(s)

    if student_only_skills:
        recommendations.append(
            f"Tus habilidades únicas ({', '.join(student_only_skills[:3])}) te diferencian. "
            "Considera roles que las aprovechen."
        )

    return {
        "score": score,
        "habilidades_faltantes": missing_market_skills[:5],
        "recomendaciones": recommendations,
    }
