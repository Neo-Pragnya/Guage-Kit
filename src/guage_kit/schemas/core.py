from pydantic import BaseModel
from typing import Any, List, Optional

class Query(BaseModel):
    id: str
    prompt: str
    references: Optional[List[str]] = None
    metadata: dict[str, Any] = {}

class ContextChunk(BaseModel):
    id: str
    text: str
    source: Optional[str] = None

class RetrievalResult(BaseModel):
    query_id: str
    chunks: List[ContextChunk]

class Generation(BaseModel):
    query_id: str
    text: str
    model: Optional[str] = None

class EvalSample(BaseModel):
    query: Query
    retrieval: Optional[RetrievalResult] = None
    generation: Generation