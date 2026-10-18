from typing import List, Optional, Protocol
from pydantic import BaseModel, Field


class ExtractedEntityItem(BaseModel):
    name: str = Field(..., min_length=1, max_length=160)
    entity_type: str = Field(default="Concept", max_length=80)
    aliases: List[str] = Field(default_factory=list)


class ExtractedFactItem(BaseModel):
    subject_name: str = Field(..., min_length=1, max_length=160)
    subject_type: str = Field(default="Service", max_length=80)
    predicate: str = Field(..., min_length=1, max_length=120)
    object_value: str = Field(..., min_length=1, max_length=500)
    object_entity_name: Optional[str] = Field(default=None, max_length=160)
    confidence: float = Field(default=0.92, ge=0.0, le=1.0)


class ExtractedProcedureItem(BaseModel):
    name: str = Field(..., min_length=2, max_length=160)
    trigger_text: str = Field(..., min_length=3, max_length=500)
    steps: List[str] = Field(..., min_length=1, max_length=25)


class ExtractionPayload(BaseModel):
    entities: List[ExtractedEntityItem] = Field(default_factory=list)
    facts: List[ExtractedFactItem] = Field(default_factory=list)
    procedures: List[ExtractedProcedureItem] = Field(default_factory=list)


class ExtractorProvider(Protocol):
    provider_name: str

    def extract(self, content: str) -> ExtractionPayload:
        ...