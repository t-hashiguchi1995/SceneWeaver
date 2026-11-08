import re

from creator_studio.domain.character import Persona


def validate_candidate(text: str, persona: Persona) -> list[str]:
    issues = []
    if not text.strip():
        issues.append("empty_text")
    if len(text) > persona.max_chars:
        issues.append("too_long")
    if len([s for s in re.split(r"[。．！？…、]+", text) if s.strip()]) > persona.max_fragments:
        issues.append("too_many_fragments")
    issues.extend(f"forbidden_pattern:{p}" for p in persona.forbidden_patterns if p in text)
    return issues
