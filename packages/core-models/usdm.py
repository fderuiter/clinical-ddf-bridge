from pydantic import BaseModel, Field
from typing import Optional, List

class StudyDefinition(BaseModel):
    id: str
    name: str
    version: str = "1.0.0"
    description: Optional[str] = None