rom pydantic import BaseModel, Field
from typing import Optional, List
import uuid


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    messages: List[ChatMessage]
    mode: str = "general"
    max_tokens: int = Field(default=800, le=4000)
    temperature: float = Field(default=0.4, ge=0.0, le=2.0)


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    kb_entries_used: List[str]
    model: str
    usage: dict
    finish_reason: str


class CorrectionRequest(BaseModel):
    session_id: str
    original_question: str
    gpt_answer: str
    correct_answer: str
    topic: Optional[str] = None


class ConfirmRequest(BaseModel):
    session_id: str
    question: str
    answer: str
    topic: Optional[str] = None
