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
                "habilidades_requeridas": ["Python", "FastAPI", "MongoDB"]
            }
        }
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
    estudiante_id: str # UUID
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
