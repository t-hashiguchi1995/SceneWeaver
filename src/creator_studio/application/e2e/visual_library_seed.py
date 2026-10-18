"""Seed PromptPreset + MarketplaceItem + VisualLibraryMetadata for CE-2 E2E.

Preview bytes come from ``tests/fixtures/visual_library/`` when present so UI
review can evaluate meaning-aligned representative images (not production art).
"""

from __future__ import annotations

from typing import Any

from creator_studio.application.assets.store_asset import StoreAssetBytes, StoreBytesCommand
from creator_studio.application.wardrobe.tryon import SeedMarketplaceItem
from creator_studio.domain.asset import AssetKind
from creator_studio.domain.ids import AssetId, new_id
from creator_studio.domain.timeutil import utc_now
from creator_studio.domain.wardrobe import MarketplaceItem
from creator_studio.infrastructure.db.models.prompt import PromptPresetRow
from creator_studio.infrastructure.db.models.visual_library import VisualLibraryMetadataRow
from creator_studio.infrastructure.settings.config import REPO_ROOT
from creator_studio.ports.unit_of_work import UnitOfWork

_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
    b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)

_FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "visual_library"

# kind -> fixture rows (mixed preview / no-preview)
_PRESET_SPECS: list[dict[str, Any]] = [
    {
        "kind": "pose",
        "label": "look over shoulder",
        "label_ja": "振り向き",
        "description_ja": "体を前に向けたまま、顔や上半身を後方へ向けるポーズ。",
        "tags": ["立ち", "振り向き"],
        "prompt": "looking back, over shoulder, standing",
        "preview": True,
        "preview_kind": "curated",
        "fixture": "pose_look_over_shoulder.png",
    },
    {
        "kind": "pose",
        "label": "front standing",
        "label_ja": "正面立ち",
        "description_ja": "正面を向いてまっすぐ立つ基本ポーズ。",
        "tags": ["立ち", "正面"],
        "prompt": "standing, facing viewer, straight posture",
        "preview": False,
    },
    {
        "kind": "pose",
        "label": "hand on hip",
        "label_ja": "腰に手",
        "description_ja": "片手を腰に当てた立ちポーズ。",
        "tags": ["立ち", "腰"],
        "prompt": "hand on own hip, standing",
        "preview": True,
        "preview_kind": "generated",
        "fixture": "pose_hand_on_hip.png",
    },
    {
        "kind": "expression",
        "label": "gentle smile",
        "label_ja": "やさしい笑顔",
        "description_ja": "口角を軽く上げた穏やかな表情。",
        "tags": ["笑顔", "穏やか"],
        "prompt": "gentle smile, soft expression",
        "preview": True,
        "preview_kind": "curated",
        "fixture": "expression_gentle_smile.png",
    },
    {
        "kind": "expression",
        "label": "surprised",
        "label_ja": "驚き",
        "description_ja": "目を見開いた短い驚きの表情。",
        "tags": ["驚き"],
        "prompt": "surprised, wide eyes, open mouth",
        "preview": False,
    },
    {
        "kind": "camera",
        "label": "medium shot",
        "label_ja": "ミディアム",
        "description_ja": "腰から上を収める標準的な構図。",
        "tags": ["構図", "ミディアム"],
        "prompt": "medium shot, upper body",
        "preview": True,
        "preview_kind": "curated",
        "fixture": "camera_medium_shot.png",
    },
    {
        "kind": "camera",
        "label": "close-up",
        "label_ja": "クローズアップ",
        "description_ja": "顔まわりを大きく切り取った構図。",
        "tags": ["構図", "寄り"],
        "prompt": "close-up, face focus",
        "preview": False,
    },
    {
        "kind": "lighting",
        "label": "soft indoor",
        "label_ja": "柔らかい室内光",
        "description_ja": "窓辺のような拡散した室内照明。",
        "tags": ["照明", "室内"],
        "prompt": "soft indoor lighting, gentle shadows",
        "preview": True,
        "preview_kind": "generated",
        "fixture": "lighting_soft_indoor.png",
    },
    {
        "kind": "lighting",
        "label": "rim light",
        "label_ja": "リムライト",
        "description_ja": "輪郭を縁取る逆光寄りの照明。",
        "tags": ["照明", "輪郭"],
        "prompt": "rim light, backlit outline",
        "preview": False,
    },
    {
        "kind": "background",
        "label": "cafe interior",
        "label_ja": "カフェ内観",
        "description_ja": "テーブルと窓がある落ち着いたカフェの背景。",
        "tags": ["背景", "カフェ"],
        "prompt": "cafe interior, window seat",
        "preview": True,
        "preview_kind": "imported_reference",
        "fixture": "background_cafe_interior.png",
    },
    {
        "kind": "background",
        "label": "park path",
        "label_ja": "公園の小道",
        "description_ja": "木立と小道のある屋外背景。",
        "tags": ["背景", "屋外"],
        "prompt": "park path, trees, daylight",
        "preview": False,
    },
    {
        "kind": "snippet",
        "category": "legacy_misc_xyz",
        "label": "misc snippet",
        "label_ja": "その他スニペット",
        "description_ja": "分類不明のレガシー断片。",
        "tags": ["その他"],
        "prompt": "misc legacy fragment",
        "preview": False,
        "force_other": True,
    },
]

_OUTFIT_SPECS: list[dict[str, Any]] = [
    {
        "title": "Soft Knit Cardigan",
        "label_ja": "やわらかカーディガン",
        "description_ja": "クリーム色のオーバーサイズニットカーディガン。",
        "category": "outerwear",
        "region": "tops",
        "garment_description": "soft cream oversized knit cardigan",
        "style_tags": ["soft", "casual", "立ち"],
        "with_plate": True,
        "fixture": "outfit_soft_cardigan.png",
    },
    {
        "title": "School Blazer",
        "label_ja": "スクールブレザー",
        "description_ja": "クラシックな紺ブレザー。",
        "category": "outerwear",
        "region": "tops",
        "garment_description": "navy school blazer, gold buttons",
        "style_tags": ["school", "formal"],
        "with_plate": False,
    },
]


def _load_visual_fixture(name: str, *, fallback_key: str) -> bytes:
    path = _FIXTURE_DIR / name
    if path.exists():
        return path.read_bytes()
    return _PNG + fallback_key.encode()


def seed_visual_library_catalog(
    uow: UnitOfWork,
    store: StoreAssetBytes,
    seed_market: SeedMarketplaceItem,
) -> dict[str, Any]:
    """Create CE-2 fixture catalog. Returns summary ids for extras."""
    preset_ids: list[str] = []
    market_ids: list[str] = []
    preview_asset_ids: list[str] = []
    preview_fixtures: dict[str, str] = {}

    thumbs: dict[str, str] = {}
    for spec in _PRESET_SPECS:
        key = f"{spec['kind']}:{spec['label']}"
        if not spec.get("preview"):
            continue
        fixture_name = str(spec.get("fixture") or f"{spec['kind']}.png")
        asset = store.execute(
            StoreBytesCommand(
                data=_load_visual_fixture(fixture_name, fallback_key=key),
                kind=AssetKind.REFERENCE,
                mime="image/png",
                relative_dir="visual_library",
                filename=fixture_name,
            )
        )
        thumbs[key] = asset.id
        preview_asset_ids.append(asset.id)
        preview_fixtures[asset.id] = f"tests/fixtures/visual_library/{fixture_name}"

    now = utc_now()
    with uow as session_uow:
        for spec in _PRESET_SPECS:
            key = f"{spec['kind']}:{spec['label']}"
            preset_id = new_id()
            row = PromptPresetRow(
                id=preset_id,
                kind=spec["kind"],
                label=spec["label"],
                prompt_fragment=spec["prompt"],
                category=spec.get("category") or spec["kind"],
                content_rating="general",
                enabled=True,
                payload_json={},
                source="e2e_visual_library",
                source_file="e2e/visual_library.yaml",
                legacy_key=key,
                content_hash=new_id()[:16],
                created_at=now,
                updated_at=now,
            )
            session_uow.prompt_presets.add_row(row)
            preset_ids.append(preset_id)

            visual_kind = "other" if spec.get("force_other") else spec["kind"]
            meta = VisualLibraryMetadataRow(
                id=new_id(),
                source_type="prompt_preset",
                source_id=preset_id,
                visual_kind=visual_kind,
                label_ja=spec.get("label_ja"),
                description_ja=spec.get("description_ja"),
                thumbnail_asset_id=thumbs.get(key),
                preview_kind=spec.get("preview_kind"),
                subcategory=spec.get("category") or spec["kind"],
                tags_json=list(spec.get("tags") or []),
                model_scope_json=["anima"],
                related_refs_json=[],
                created_at=now,
                updated_at=now,
            )
            session_uow.visual_library_metadata.add(meta)
        session_uow.commit()

    for spec in _OUTFIT_SPECS:
        plate_id = None
        if spec.get("with_plate"):
            fixture_name = str(spec.get("fixture") or "outfit.png")
            plate = store.execute(
                StoreBytesCommand(
                    data=_load_visual_fixture(
                        fixture_name, fallback_key=f"outfit:{spec['title']}"
                    ),
                    kind=AssetKind.PLATE,
                    mime="image/png",
                    relative_dir="plates",
                    filename=fixture_name,
                )
            )
            plate_id = plate.id
            preview_asset_ids.append(plate_id)
            preview_fixtures[plate_id] = f"tests/fixtures/visual_library/{fixture_name}"

        item = MarketplaceItem.create(
            title=spec["title"],
            category=spec["category"],
            region=spec["region"],
            garment_description=spec["garment_description"],
            canonical_plate_asset_id=AssetId(plate_id) if plate_id else None,
            style_tags=list(spec["style_tags"]),
            colors=[],
        )
        seed_market.execute(item)
        market_ids.append(item.id)

        with uow as session_uow:
            meta = VisualLibraryMetadataRow(
                id=new_id(),
                source_type="marketplace_item",
                source_id=item.id,
                visual_kind="outfit",
                label_ja=spec.get("label_ja"),
                description_ja=spec.get("description_ja"),
                thumbnail_asset_id=None,
                preview_kind="imported_reference" if plate_id else None,
                subcategory=spec["category"],
                tags_json=list(spec["style_tags"]),
                model_scope_json=["anima"],
                related_refs_json=[],
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            session_uow.visual_library_metadata.add(meta)
            session_uow.commit()

    return {
        "preset_ids": preset_ids,
        "marketplace_item_ids": market_ids,
        "preview_asset_ids": preview_asset_ids,
        "preview_fixtures": preview_fixtures,
        "counts": {
            "pose": 3,
            "expression": 2,
            "camera": 2,
            "lighting": 2,
            "background": 2,
            "outfit": 2,
            "other": 1,
        },
    }
