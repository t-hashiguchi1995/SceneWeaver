from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from creator_studio.domain.asset import ReviewDecision
from creator_studio.domain.ids import AssetId
from creator_studio.ports.asset_store import AssetStore
from creator_studio.ports.unit_of_work import UnitOfWork

_REVISION_RE = re.compile(r"^r(\d{3,})$")


@dataclass
class PanelSlot:
    panel_no: int
    shot_id: str
    script_event_ids: list[str]
    asset_id: str | None = None
    panel_slot_id: str | None = None


@dataclass
class PagePlan:
    page_no: int
    panels: list[PanelSlot] = field(default_factory=list)


@dataclass
class HandoffResult:
    revision: str
    path: str
    manifest: dict[str, Any]


class HandoffError(ValueError):
    """Handoff failed; no successful revision was published."""


@dataclass
class _ResolvedPanel:
    page_no: int
    panel: PanelSlot
    panel_slot_id: str
    asset_id: str
    sha256: str
    data: bytes
    filename: str


class CspHandoffService:
    """Build immutable CSP handoff revisions from adopted Asset bytes."""

    def __init__(
        self,
        runtime_root: Path,
        *,
        uow_factory: Callable[[], UnitOfWork],
        asset_store: AssetStore,
        export_root: Path | None = None,
    ) -> None:
        self._runtime_root = runtime_root
        self._export_root = export_root
        self._uow_factory = uow_factory
        self._store = asset_store

    def build(
        self,
        project_id: str,
        pages: list[PagePlan],
        *,
        script_rows: list[dict[str, str]],
        revision: str | None = None,
    ) -> HandoffResult:
        resolved = self._resolve_all_panels(pages)
        rev = revision or self._next_revision(project_id)
        root = self._revision_root(project_id, rev)
        if root.exists():
            raise HandoffError(
                f"handoff revision {rev} already exists; create a new revision instead of overwriting"
            )

        # Stage under .tmp then rename for near-atomic publish
        staging = root.with_name(f".{rev}.tmp")
        if staging.exists():
            raise HandoffError(f"handoff staging dir already exists for {rev}")
        try:
            pages_dir = staging / "pages"
            script_dir = staging / "script"
            pages_dir.mkdir(parents=True, exist_ok=True)
            script_dir.mkdir(parents=True, exist_ok=True)

            manifest_pages: list[dict[str, Any]] = []
            by_page: dict[int, list[_ResolvedPanel]] = {}
            for item in resolved:
                by_page.setdefault(item.page_no, []).append(item)

            for page_no in sorted(by_page):
                page_dir = pages_dir / f"page_{page_no:03d}"
                page_dir.mkdir(parents=True, exist_ok=True)
                panels_out: list[dict[str, Any]] = []
                for item in sorted(by_page[page_no], key=lambda p: p.panel.panel_no):
                    dest = page_dir / item.filename
                    dest.write_bytes(item.data)
                    written_hash = hashlib.sha256(dest.read_bytes()).hexdigest()
                    if written_hash != item.sha256:
                        raise HandoffError(
                            f"handoff panel hash mismatch for {item.panel_slot_id}: "
                            f"{written_hash} != {item.sha256}"
                        )
                    panels_out.append(
                        {
                            "panel_no": item.panel.panel_no,
                            "panel_slot_id": item.panel_slot_id,
                            "shot_id": item.panel.shot_id,
                            "script_event_ids": list(item.panel.script_event_ids),
                            "asset_id": item.asset_id,
                            "sha256": item.sha256,
                            "clean_art": item.filename,
                        }
                    )
                manifest_pages.append({"page_no": page_no, "panels": panels_out})

            tsv_lines = ["event_id\tkind\tspeaker\ttext"]
            for row in script_rows:
                tsv_lines.append(
                    f"{row.get('id','')}\t{row.get('kind','')}\t"
                    f"{row.get('speaker','')}\t{row.get('text','')}"
                )
            (script_dir / "script_events.tsv").write_text(
                "\n".join(tsv_lines) + "\n", encoding="utf-8"
            )
            (script_dir / "page_001.txt").write_text(
                "\n".join(r.get("text", "") for r in script_rows) + "\n",
                encoding="utf-8",
            )

            manifest = {
                "project_id": project_id,
                "revision": rev,
                "pages": manifest_pages,
                "lettering_hint": "upper_right preferred; geometry edited in CSP",
            }
            (staging / "project_manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (staging / "README.html").write_text(
                "<html><body><h1>CSP Handoff</h1>"
                "<p>Import clean panels and script_events.tsv into CLIP STUDIO.</p>"
                "</body></html>",
                encoding="utf-8",
            )
            staging.rename(root)
        except Exception:
            if staging.exists():
                # best-effort cleanup so failure leaves no published revision
                shutil.rmtree(staging, ignore_errors=True)
            raise

        return HandoffResult(revision=rev, path=str(root), manifest=manifest)

    def _resolve_all_panels(self, pages: list[PagePlan]) -> list[_ResolvedPanel]:
        if not pages:
            raise HandoffError("handoff requires at least one page")
        resolved: list[_ResolvedPanel] = []
        with self._uow_factory() as uow:
            for page in pages:
                for panel in page.panels:
                    if not panel.asset_id:
                        raise HandoffError(
                            f"panel {page.page_no}/{panel.panel_no} missing asset_id"
                        )
                    asset = uow.assets.get(AssetId(panel.asset_id))
                    if asset is None:
                        raise HandoffError(f"asset missing: {panel.asset_id}")
                    if asset.review_decision == ReviewDecision.REJECTED:
                        raise HandoffError(
                            f"rejected asset cannot be handed off: {panel.asset_id}"
                        )
                    if asset.review_decision != ReviewDecision.ADOPTED:
                        raise HandoffError(
                            f"asset not adopted (decision={asset.review_decision.value}): "
                            f"{panel.asset_id}"
                        )
                    try:
                        path = self._store.path_for_uri(asset.uri)
                        data = path.read_bytes()
                    except FileNotFoundError as exc:
                        raise HandoffError(
                            f"asset bytes missing on store: {panel.asset_id}"
                        ) from exc
                    digest = hashlib.sha256(data).hexdigest()
                    if digest != asset.sha256:
                        raise HandoffError(
                            f"corrupted asset bytes (hash mismatch): {panel.asset_id}"
                        )
                    slot_id = panel.panel_slot_id or (
                        f"page_{page.page_no:03d}_panel_{panel.panel_no:02d}"
                    )
                    resolved.append(
                        _ResolvedPanel(
                            page_no=page.page_no,
                            panel=panel,
                            panel_slot_id=slot_id,
                            asset_id=str(asset.id),
                            sha256=asset.sha256,
                            data=data,
                            filename=f"panel_{panel.panel_no:02d}_clean.png",
                        )
                    )
        return resolved

    def latest(self, project_id: str) -> dict[str, Any] | None:
        base = self._handoff_base(project_id)
        if not base.is_dir():
            return None
        revisions = [path for path in base.iterdir()
                     if path.is_dir() and _REVISION_RE.fullmatch(path.name)
                     and (path / "project_manifest.json").is_file()]
        if not revisions:
            return None
        path = max(revisions, key=lambda item: int(item.name[1:]))
        return {"revision": path.name, "path": str(path),
                "manifest": json.loads((path / "project_manifest.json").read_text(encoding="utf-8"))}

    def _handoff_base(self, project_id: str) -> Path:
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", project_id):
            raise HandoffError("invalid project id")
        if self._export_root is not None:
            return self._export_root / project_id / "csp_handoff"
        return self._runtime_root / "projects" / project_id / "csp_handoff"

    def _revision_root(self, project_id: str, revision: str) -> Path:
        if not _REVISION_RE.fullmatch(revision):
            raise HandoffError("invalid revision")
        return self._handoff_base(project_id) / revision

    def _next_revision(self, project_id: str) -> str:
        base = self._handoff_base(project_id)
        if not base.exists():
            return "r001"
        max_n = 0
        for child in base.iterdir():
            if not child.is_dir() or child.name.startswith("."):
                continue
            match = _REVISION_RE.match(child.name)
            if match:
                max_n = max(max_n, int(match.group(1)))
        return f"r{max_n + 1:03d}"


class ReleasePreviewService:
    def build_editions(
        self,
        *,
        title: str,
        summary: str,
        hashtags: list[str] | None = None,
    ) -> dict[str, Any]:
        tags = hashtags or ["#SceneWeaver"]
        return {
            "status": "ready",
            "editions": {
                "x": {
                    "platform": "x",
                    "text": f"{title} — {summary}"[:240],
                    "hashtags": tags,
                    "alt_text": [title],
                },
                "pixiv": {
                    "platform": "pixiv",
                    "title": title,
                    "description": summary,
                    "tags": [t.lstrip("#") for t in tags],
                    "ai_disclosure": True,
                },
                "patreon": {
                    "platform": "patreon",
                    "title": title,
                    "body_markdown": f"## {title}\n\n{summary}\n\nThank you for supporting.",
                    "attachment_order": [],
                },
            },
            "note": "Preview only. approve/publish interfaces reserved for post-MVP.",
        }
