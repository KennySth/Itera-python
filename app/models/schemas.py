from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from app.models.base import PyObjectId


class JobOffer(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    puesto: str
    empresa: str
    fuente: str
    url_origen: str
    nivel_experiencia: Optional[str] = None
    modalidad: Optional[str] = None
    ubicacion_geografica: Dict[str, Any] = Field(default_factory=dict)
    salario_original: Dict[str, Any] = Field(default_factory=dict)
    salario_normalizado_usd: Optional[float] = None
    habilidades_requeridas: List[str] = Field(default_factory=list)
    vector_semantico: List[float] = Field(default_factory=list)
    version_modelo_ia: Optional[str] = None
    fecha_expiracion: Optional[datetime] = None
    # ponytail: Enriched fields (Phase 4) - backward compatible, optional
    categoria_carrera: Optional[str] = Field(
        default=None, description="ID de categoría de carrera (ej. ciencia-datos-ia)"
    )
    categoria_carrera_nombre: Optional[str] = Field(
        default=None, description="Nombre de categoría (ej. Ciencia de Datos e IA)"
    )
    company_tier: Optional[int] = Field(
        default=None, description="Tier de empresa 1-4 (1=TOP)"
    )
    skill_extraction_method: Optional[str] = Field(
        default=None, description="Método: regex, ai, mixed"
    )
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "puesto": "Senior Python Developer",
                "empresa": "Tech Solutions",
                "fuente": "LinkedIn",
                "url_origen": "https://linkedin.com/jobs/...",
                "salario_normalizado_usd": 85000.0,
                "habilidades_requeridas": ["Python", "FastAPI", "MongoDB"],
                "categoria_carrera": "desarrollo-backend",
                "categoria_carrera_nombre": "Desarrollo Backend",
                "company_tier": 2,
                "skill_extraction_method": "regex",
            }
        },
    )


class CareerMetrics(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    titulo_carrera: str
    nivel_referencia: str
    region_mercado: str
    salario_anual_usd: Dict[str, Any]
    demanda_mercado: Dict[str, Any]
    analisis_competitivo: Dict[str, Any]
    aprendizaje: Dict[str, Any]
    ultima_actualizacion: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class SalarySnapshot(BaseModel):
    """
    Periodic snapshot of career salary metrics for historical comparison.
    Saved before each update_career_metrics() recalculation.
    """

    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    titulo_carrera: str = Field(..., description="Career category name")
    snapshot_year: int = Field(..., description="Year of the snapshot (e.g., 2025)")
    snapshot_month: int = Field(..., description="Month of the snapshot (1-12)")
    salario_min: float = Field(..., description="Minimum annual salary USD")
    salario_max: float = Field(..., description="Maximum annual salary USD")
    salario_promedio: float = Field(..., description="Average annual salary USD")
    volumen_total: int = Field(..., description="Number of offers analyzed")
    tendencia: str = Field(
        default="estable", description="Trend: creciente, estable, decreciente"
    )
    habilidades_clave: List[str] = Field(default_factory=list)
    snapshot_date: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class MarketSkill(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    habilidad: str
    sinonimos: List[str] = Field(default_factory=list)
    tipo_habilidad: str
    demanda_actual: float
    tendencia_mensual: str

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class ScrapingAudit(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    fuente: str
    estado: str
    ofertas_extraidas: int
    ofertas_descartadas: int
    errores_detectados: List[Dict[str, Any]] = Field(default_factory=list)
    fecha_ejecucion: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class MatchHistory(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    estudiante_id: str  # UUID
    objetivo_evaluado: str
    score_general: float
    version_modelo_ia: str
    fecha_evaluacion: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class RecommendationFeedback(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    estudiante_id: str
    entidad_evaluada: str
    calificacion_estrellas: int
    comentario: Optional[str] = None
    fecha: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class ExplorationTelemetry(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    estudiante_id: str
    accion: str
    datos_contexto: Dict[str, Any]
    tiempo_permanencia_segundos: int
    fecha: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class MatchRequest(BaseModel):
    student_id: str = Field(..., description="UUID del estudiante")
    skills: List[str] = Field(
        default_factory=list, description="Lista de habilidades del estudiante"
    )
    career_category: Optional[str] = Field(
        default=None,
        description="Filtrar por categoría de carrera (ej. desarrollo-frontend, devops-cloud)",
    )
