from __future__ import annotations

from pathlib import Path

from creator_studio.adapters.image import ComfyImageBackend, FakeImageBackend
from creator_studio.adapters.llm import OpenAICompatibleProvider, StubLLMProvider
from creator_studio.adapters.runtime import ComfyRuntimeProbe, FakeRuntimeProbe
from creator_studio.adapters.secrets.store import SecretStore
from creator_studio.adapters.settings.file_store import FileUserSettingsStore
from creator_studio.adapters.vision import StubImageTagger
from creator_studio.application.assets.decisions import SetAssetDecision
from creator_studio.application.assets.store_asset import StoreAssetBytes
from creator_studio.application.assets.tag_asset import ListAssetTags, TagAsset
from creator_studio.application.capabilities.resolve import CapabilityService
from creator_studio.application.characters.manage import (
    CreateCharacter,
    GetCharacter,
    ListCharacters,
    UpdatePersona,
    UpdateVisualIdentity,
)
from creator_studio.application.dialogue.pipeline import DialoguePipeline
from creator_studio.application.integrations.diagnose_comfy import DiagnoseComfy
from creator_studio.application.jobs.manage_jobs import (
    ClaimAndRunStubJob,
    EnqueueJob,
    GetJob,
    ListJobs,
)
from creator_studio.application.projects.create_project import (
    CreateProject,
    GetProject,
    ListProjects,
)
from creator_studio.application.prompt.drafts import PromptDraftService
from creator_studio.application.prompt.renderer import PromptRenderer
from creator_studio.application.settings.service import SettingsService
from creator_studio.application.story.manage import CreateBeat, CreateScene
from creator_studio.application.csp.handoff import CspHandoffService, ReleasePreviewService
from creator_studio.application.shots.pipeline import ShotPipeline
from creator_studio.application.wardrobe.tryon import AdoptTryOn, RunTryOn, SearchMarket, SeedMarketplaceItem
from creator_studio.infrastructure.db.session import get_session_factory
from creator_studio.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from creator_studio.infrastructure.filesystem.asset_store import FilesystemAssetStore
from creator_studio.infrastructure.prompts import PromptRegistry
from creator_studio.infrastructure.settings import Settings, get_settings
from creator_studio.ports.image_backend import ImageBackend
from creator_studio.ports.image_tagger import ImageTagger
from creator_studio.ports.llm import LLMGateway
from creator_studio.ports.runtime_probe import RuntimeCapabilityProbe


class Container:
    def __init__(self, settings: Settings | None = None) -> None:
        """Bootstrap assumes schema already exists via `alembic upgrade head`.

        Does not call create_all(); that would hide missing migrations.
        """
        self.settings = settings or get_settings()
        self._session_factory = get_session_factory(self.settings.sqlalchemy_url())
        self.asset_store = FilesystemAssetStore(self.settings.runtime_path() / "assets")
        self.prompts = PromptRegistry()
        self._image: ImageBackend | None = None
        self._image_config: tuple[str, str] | None = None
        self._image_tagger: ImageTagger | None = None
        self._image_tagger_key: str | None = None
        self._settings_service: SettingsService | None = None

    def uow(self) -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(self._session_factory)

    def settings_service(self) -> SettingsService:
        if self._settings_service is None:
            runtime = self.settings.runtime_path()
            self._settings_service = SettingsService(
                FileUserSettingsStore(runtime / "user_settings.json"),
                SecretStore(runtime / "secrets.json"),
                bootstrap=self.settings,
            )
        return self._settings_service

    def diagnose_comfy(self) -> DiagnoseComfy:
        return DiagnoseComfy()

    def llm(self) -> LLMGateway:
        svc = self.settings_service()
        user = svc.get()
        provider = user.get("llm_provider") or self.settings.llm_provider
        if provider == "openai_compatible":
            return OpenAICompatibleProvider(
                base_url=str(user.get("llm_base_url") or self.settings.llm_base_url),
                api_key=svc.llm_api_key(),
                model=str(user.get("llm_model") or self.settings.llm_model),
            )
        return StubLLMProvider()

    def image_backend(self) -> ImageBackend:
        backend = self.settings_service().effective_image_backend()
        comfy_url = self.settings_service().effective_comfy_url()
        config = (backend, comfy_url)
        if self._image is None or self._image_config != config:
            registry = (
                Path(self.settings.repo_root()) / self.settings.config_dir / "model_registry.yaml"
            )
            backend = self.settings_service().effective_image_backend()
            comfy_url = self.settings_service().effective_comfy_url()
            if backend == "comfy":
                self._image = ComfyImageBackend(
                    comfy_url,
                    repo_root=self.settings.repo_root(),
                    registry_path=registry,
                    asset_store=self.asset_store,
                    dry_run=False,
                    poll_timeout_seconds=self.settings.comfy_poll_timeout_seconds,
                    poll_interval_seconds=self.settings.comfy_poll_interval_seconds,
                )
            elif backend == "comfy_dry":
                self._image = ComfyImageBackend(
                    comfy_url,
                    repo_root=self.settings.repo_root(),
                    registry_path=registry,
                    asset_store=self.asset_store,
                    dry_run=True,
                    poll_timeout_seconds=self.settings.comfy_poll_timeout_seconds,
                    poll_interval_seconds=self.settings.comfy_poll_interval_seconds,
                )
            else:
                self._image = FakeImageBackend(delay_ms=self.settings.fake_image_delay_ms)
            self._image_config = config
        return self._image

    def create_project(self) -> CreateProject:
        return CreateProject(self.uow())

    def list_projects(self) -> ListProjects:
        return ListProjects(self.uow())

    def get_project(self) -> GetProject:
        return GetProject(self.uow())

    def enqueue_job(self) -> EnqueueJob:
        return EnqueueJob(self.uow())

    def list_jobs(self) -> ListJobs:
        return ListJobs(self.uow())

    def get_job(self) -> GetJob:
        return GetJob(self.uow())

    def claim_runner(self) -> ClaimAndRunStubJob:
        return ClaimAndRunStubJob(
            self.uow(),
            worker_id=self.settings.worker_id,
            lease_seconds=self.settings.job_lease_seconds,
        )

    def store_asset(self) -> StoreAssetBytes:
        return StoreAssetBytes(self.uow(), self.asset_store)

    def image_tagger(self) -> ImageTagger:
        key = self.settings.image_tagger.strip().lower()
        if self._image_tagger is None or self._image_tagger_key != key:
            if key == "pixai":
                from creator_studio.adapters.vision.pixai_tagger import PixAITaggerAdapter

                self._image_tagger = PixAITaggerAdapter(
                    model_id=self.settings.pixai_tagger_model,
                    threshold=self.settings.pixai_tagger_threshold,
                )
            else:
                self._image_tagger = StubImageTagger()
            self._image_tagger_key = key
        return self._image_tagger

    def tag_asset(self) -> TagAsset:
        return TagAsset(self.uow(), self.asset_store, self.image_tagger())

    def list_asset_tags(self) -> ListAssetTags:
        return ListAssetTags(self.uow())

    def set_asset_decision(self) -> SetAssetDecision:
        return SetAssetDecision(self.uow())

    def comfy_probe(self) -> RuntimeCapabilityProbe:
        backend = self.settings_service().effective_image_backend()
        if backend == "fake":
            return FakeRuntimeProbe()
        return ComfyRuntimeProbe(self.settings_service().effective_comfy_url())

    def capabilities(self) -> CapabilityService:
        registry_path = (
            Path(self.settings.repo_root()) / self.settings.config_dir / "model_registry.yaml"
        )
        return CapabilityService(registry_path, comfy_probe=self.comfy_probe())

    def create_character(self) -> CreateCharacter:
        return CreateCharacter(self.uow())

    def list_characters(self) -> ListCharacters:
        return ListCharacters(self.uow())

    def get_character(self) -> GetCharacter:
        return GetCharacter(self.uow())

    def update_persona(self) -> UpdatePersona:
        return UpdatePersona(self.uow())

    def update_visual_identity(self) -> UpdateVisualIdentity:
        return UpdateVisualIdentity(self.uow())

    def create_scene(self) -> CreateScene:
        return CreateScene(self.uow())

    def create_beat(self) -> CreateBeat:
        return CreateBeat(self.uow())

    def dialogue_pipeline(self) -> DialoguePipeline:
        def on_script_change(beat_id: str) -> None:
            self.shot_pipeline().invalidate_for_script_change(beat_id)

        return DialoguePipeline(
            self.uow(),
            self.llm(),
            self.prompts,
            on_script_change=on_script_change,
        )

    def search_market(self) -> SearchMarket:
        return SearchMarket(self.uow())

    def seed_marketplace_item(self) -> SeedMarketplaceItem:
        return SeedMarketplaceItem(self.uow())

    def run_tryon(self) -> RunTryOn:
        return RunTryOn(self.uow(), self.image_backend(), self.asset_store, self.prompts)

    def adopt_tryon(self) -> AdoptTryOn:
        return AdoptTryOn(self.uow())

    def prompt_renderer(self) -> PromptRenderer:
        return PromptRenderer()

    def prompt_draft_service(self) -> PromptDraftService:
        return PromptDraftService(self.uow(), self.prompt_renderer())

    def shot_pipeline(self) -> ShotPipeline:
        # Stateless facade; Shot/Plan/Attempt live in SQL (survives process restart).
        return ShotPipeline(
            self.uow(),
            self.llm(),
            self.image_backend(),
            self.asset_store,
            self.prompts,
            self.prompt_renderer(),
        )

    def csp_handoff(self) -> CspHandoffService:
        return CspHandoffService(
            self.settings.runtime_path(),
            uow_factory=self.uow,
            asset_store=self.asset_store,
            export_root=Path(str(self.settings_service().get()["csp_export_dir"]))
            if self.settings_service().get().get("csp_export_dir") else None,
        )

    def release_preview(self) -> ReleasePreviewService:
        return ReleasePreviewService()


_container: Container | None = None


def get_container() -> Container:
    global _container
    if _container is None:
        _container = Container()
    return _container


def reset_container() -> None:
    global _container
    _container = None