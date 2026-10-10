from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from creator_studio.domain.ids import ProjectId, new_id
from creator_studio.domain.timeutil import utc_now


class ProjectStatus(StrEnum):
    DRAFT = "draft"
    STORY = "story"
    VISUAL_PRODUCTION = "visual_production"
    CSP_FINISHING = "csp_finishing"
    RELEASE_READY = "release_ready"
    PUBLISHED = "published"
    ARCHIVED = "archived"


@dataclass
class Project:
    id: ProjectId
    title: str
    status: ProjectStatus = ProjectStatus.DRAFT
    content_rating: str = "general"
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    @classmethod
    def create(cls, title: str, content_rating: str = "general") -> Project:
        now = utc_now()
        return cls(
            id=ProjectId(new_id()),
            title=title.strip(),
            content_rating=content_rating,
            created_at=now,
            updated_at=now,
        )