from pydantic import BaseModel
from typing import Any, List, Optional

class DatasetRow(BaseModel):
    id: str
    data: Any
    metadata: Optional[dict[str, Any]] = {}

class DatasetSchema(BaseModel):
    rows: List[DatasetRow]