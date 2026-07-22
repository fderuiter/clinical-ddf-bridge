from typing import Optional

from pydantic import BaseModel


class StudyDefinition(BaseModel):
    id: str
    name: str
    version: str = "1.0.0"
    description: Optional[str] = None
