from pydantic import BaseModel
from typing import Optional

class StudyDefinition(BaseModel):
    id: str
    name: str
    version: str = "1.0.0"
    description: Optional[str] = None