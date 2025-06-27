# models/data_models.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# --- Modelos para 'categorias.json' ---

class CodeAssignment(BaseModel):
    """Representa la asignación de un código a una categoría."""
    code_id: str

class Category(BaseModel):
    """Representa una categoría conceptual con sus códigos asociados."""
    category_id: str
    category_name: str
    description: Optional[str] = None
    code_assignments: List[CodeAssignment] = []

# --- Modelos para 'codebook.json' ---

class Code(BaseModel):
    """Representa un código único en el libro de códigos."""
    id: str
    label: str
    description: Optional[str] = None
    embedding: Optional[List[float]] = None
    count: Optional[int] = 1

class Codebook(BaseModel):
    """Representa el libro de códigos completo."""
    codes: List[Code]
    metadata: Dict[str, Any] = Field(default_factory=dict)

# --- Modelo para 'analysis_results.jsonl' ---

class Insight(BaseModel):
    """Representa un fragmento de texto (evidencia) con sus códigos unificados."""
    id_fragmento: str
    fragmento_original: str
    unified_code_ids: List[str] = []
    context: Optional[str] = None
    intervening_conditions: Optional[str] = None
    consequences: Optional[str] = None

# --- Modelo para la salida del LLM en CategorizerAgent ---

class CategorizationResult(BaseModel):
    """
    Representa una única categoría tal como la devuelve el LLM en el proceso de categorización.
    Valida la estructura de cada elemento en la lista de respuesta.
    """
    category_name: str
    is_new: bool
    description: str
    code_assignments: List[CodeAssignment] = []

# --- Modelo para la salida del LLM en CoderAgent ---

class CodingResult(BaseModel):
    """
    Representa el resultado de la codificación para un único fragmento.
    Valida la estructura devuelta por el LLM en el CoderAgent.
    """
    id_fragmento: str
    fragmento_original: str
    codigos_abiertos: List[str]
    error: Optional[str] = None # Para mantener la compatibilidad con el manejo de errores

# --- Modelo para la salida del LLM en AxialAnalystAgent ---

class ParadigmItem(BaseModel):
    """Representa un único elemento dentro del modelo paradigmático (ej. una condición causal)."""
    description: str
    evidence_insight_ids: List[str] = Field(default_factory=list)

class ParadigmModel(BaseModel):
    """Representa el modelo paradigmático completo para una categoría."""
    causal_conditions: List[ParadigmItem] = Field(default_factory=list)
    context: List[ParadigmItem] = Field(default_factory=list)
    intervening_conditions: List[ParadigmItem] = Field(default_factory=list)
    action_strategies: List[ParadigmItem] = Field(default_factory=list)
    consequences: List[ParadigmItem] = Field(default_factory=list)

class PropertyAndDimension(BaseModel):
    """Representa una propiedad de la categoría y su rango dimensional."""
    property_name: str
    property_description: str
    dimensional_range: str
    evidence_insight_ids: List[str] = Field(default_factory=list)

class AxialAnalysisOutput(BaseModel):
    """
    Representa la salida completa y estructurada del análisis axial del LLM.
    Este es el modelo de validación principal para la respuesta de la API.
    """
    paradigm_model: ParadigmModel
    properties_and_dimensions: List[PropertyAndDimension] = Field(default_factory=list)

# --- Modelos para Metadatos de Trazabilidad ---

class InsightMetadata(BaseModel):
    """Almacena metadatos para un único insight, como su origen."""
    method: str
    source: str

class InsightsMetadataRegistry(BaseModel):
    """Registro completo de metadatos para todos los insights."""
    insights: Dict[str, InsightMetadata] = Field(default_factory=dict) 