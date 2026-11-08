from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Emotion(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    intensity: float


class DirectorPlan(BaseModel):
    model_config = ConfigDict(extra="allow")
    speaker_id: str
    addressee_ids: list[str]
    speech_act: str
    intent: str
    subtext: str
    emotion: Emotion
    delivery: dict[str, Any]
    action_hint: str
    information_to_convey: list[str]
    information_to_avoid_repeating: list[str]


class WriterCandidate(BaseModel):
    text: str
    tone: str = ""
    fragment_hint: list[str] = Field(default_factory=list)


class CriticResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    scores: list[dict[str, Any]]
