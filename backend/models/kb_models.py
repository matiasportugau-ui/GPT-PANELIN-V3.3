from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid


class KBEntry(BaseModel):
      id: str = Field(default_factory=lambda: str(uuid.uuid4()))
      topic: str
      content: str
      source: str = "human_correction"
      confidence: float = Field(default=1.0, ge=0.0, le=1.0)
      embedding: Optional[List[float]] = None
      original_question: Optional[str] = None
      gpt_was_wrong: Optional[str] = None
      created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
      updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class KBEntryResponse(BaseModel):
      id: str
      topic: str
      content: str
      source: str
      confidence: float
      original_question: Optional[str] = None
      created_at: str
      updated_at: str
