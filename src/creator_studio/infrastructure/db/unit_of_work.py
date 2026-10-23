from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from creator_studio.infrastructure.db.repositories.asset_repo import SqlAlchemyAssetRepository
from creator_studio.infrastructure.db.repositories.asset_tag_repo import SqlAlchemyAssetTagRepository
from creator_studio.infrastructure.db.repositories.character_repo import SqlAlchemyCharacterRepository
from creator_studio.infrastructure.db.repositories.job_repo import SqlAlchemyJobRepository
from creator_studio.infrastructure.db.repositories.project_repo import SqlAlchemyProjectRepository
from creator_studio.infrastructure.db.repositories.story_repo import (
    SqlAlchemyBeatRepository,
    SqlAlchemySceneRepository,
    SqlAlchemyScriptEventRepository,
)
from creator_studio.infrastructure.db.repositories.prompt_repo import (
    SqlAlchemyLegacyImportRepository,
    SqlAlchemyPromptDraftRepository,
    SqlAlchemyPromptPresetRepository,
)
from creator_studio.infrastructure.db.repositories.shot_repo import (
    SqlAlchemyGenerationAttemptRepository,
    SqlAlchemyRenderPlanRepository,
    SqlAlchemyShotRepository,
)
from creator_studio.infrastructure.db.repositories.visual_library_repo import (
    SqlAlchemyVisualLibraryMetadataRepository,
)
from creator_studio.infrastructure.db.repositories.wardrobe_repo import (
    SqlAlchemyMarketplaceRepository,
    SqlAlchemyOutfitProfileRepository,
    SqlAlchemyTryOnSessionRepository,
)


class SqlAlchemyUnitOfWork:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self.session: Session | None = None
        self.projects: SqlAlchemyProjectRepository
        self.jobs: SqlAlchemyJobRepository
        self.assets: SqlAlchemyAssetRepository
        self.asset_tags: SqlAlchemyAssetTagRepository
        self.characters: SqlAlchemyCharacterRepository
        self.scenes: SqlAlchemySceneRepository
        self.beats: SqlAlchemyBeatRepository
        self.script_events: SqlAlchemyScriptEventRepository
        self.marketplace: SqlAlchemyMarketplaceRepository
        self.outfit_profiles: SqlAlchemyOutfitProfileRepository
        self.tryon_sessions: SqlAlchemyTryOnSessionRepository
        self.shots: SqlAlchemyShotRepository
        self.render_plans: SqlAlchemyRenderPlanRepository
        self.generation_attempts: SqlAlchemyGenerationAttemptRepository
        self.prompt_drafts: SqlAlchemyPromptDraftRepository
        self.prompt_presets: SqlAlchemyPromptPresetRepository
        self.legacy_imports: SqlAlchemyLegacyImportRepository
        self.visual_library_metadata: SqlAlchemyVisualLibraryMetadataRepository

    def __enter__(self) -> SqlAlchemyUnitOfWork:
        self.session = self._session_factory()
        self.projects = SqlAlchemyProjectRepository(self.session)
        self.jobs = SqlAlchemyJobRepository(self.session)
        self.assets = SqlAlchemyAssetRepository(self.session)
        self.asset_tags = SqlAlchemyAssetTagRepository(self.session)
        self.characters = SqlAlchemyCharacterRepository(self.session)
        self.scenes = SqlAlchemySceneRepository(self.session)
        self.beats = SqlAlchemyBeatRepository(self.session)
        self.script_events = SqlAlchemyScriptEventRepository(self.session)
        self.marketplace = SqlAlchemyMarketplaceRepository(self.session)
        self.outfit_profiles = SqlAlchemyOutfitProfileRepository(self.session)
        self.tryon_sessions = SqlAlchemyTryOnSessionRepository(self.session)
        self.shots = SqlAlchemyShotRepository(self.session)
        self.render_plans = SqlAlchemyRenderPlanRepository(self.session)
        self.generation_attempts = SqlAlchemyGenerationAttemptRepository(self.session)
        self.prompt_drafts = SqlAlchemyPromptDraftRepository(self.session)
        self.prompt_presets = SqlAlchemyPromptPresetRepository(self.session)
        self.legacy_imports = SqlAlchemyLegacyImportRepository(self.session)
        self.visual_library_metadata = SqlAlchemyVisualLibraryMetadataRepository(self.session)
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        assert self.session is not None
        if exc_type is not None:
            self.session.rollback()
        self.session.close()

    def commit(self) -> None:
        assert self.session is not None
        self.session.commit()

    def rollback(self) -> None:
        assert self.session is not None
        self.session.rollback()