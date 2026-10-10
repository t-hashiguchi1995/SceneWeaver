from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.main import create_app
from creator_studio.application.assets.store_asset import StoreBytesCommand
from creator_studio.domain.asset import AssetKind
from creator_studio.domain.ids import AssetId
from creator_studio.domain.wardrobe import MarketplaceItem
from creator_studio.infrastructure.container import Container
from creator_studio.infrastructure.settings import Settings

_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
    b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


def test_api_vertical_slice_preview(container: Container, settings: Settings) -> None:
    client = TestClient(create_app())

    project = client.post("/api/v1/projects", json={"title": "Slice"}).json()
    character = client.post("/api/v1/characters", json={"display_name": "リゼ"}).json()
    base = container.store_asset().execute(
        StoreBytesCommand(
            data=_PNG + b"slicebase",
            kind=AssetKind.REFERENCE,
            mime="image/png",
            relative_dir="characters",
            filename="base.png",
        )
    )
    client.put(
        f"/api/v1/characters/{character['id']}/visual-identity",
        json={"tryon_base_asset_id": base.id},
    )
    client.put(
        f"/api/v1/characters/{character['id']}/persona",
        json={
            "first_person": "私",
            "voice_examples": [{"text": "えへへ", "polarity": "positive"}],
        },
    )
    scene = client.post(
        f"/api/v1/projects/{project['id']}/scenes",
        json={"title": "Cafe", "objective": "stay"},
    ).json()
    beat = client.post(
        f"/api/v1/scenes/{scene['id']}/beats",
        json={"intent": "stay together", "speaker_id": character["id"]},
    ).json()
    candidates = client.post(
        f"/api/v1/beats/{beat['id']}/script-events/candidates",
        json={"character_id": character["id"]},
    ).json()
    assert len(candidates["candidates"]) == 3
    locked = client.put(
        f"/api/v1/script-events/{candidates['candidates'][0]['id']}/lock",
        json={"text": candidates["candidates"][0]["text"]},
    ).json()
    assert locked["locked"] is True

    plate = container.store_asset().execute(
        StoreBytesCommand(
            data=_PNG + b"sliceplate",
            kind=AssetKind.PLATE,
            mime="image/png",
            relative_dir="plates",
            filename="outfit.png",
        )
    )
    item = MarketplaceItem.create(
        title="Cardigan",
        category="outerwear",
        region="tops",
        garment_description="soft cardigan",
        canonical_plate_asset_id=AssetId(plate.id),
    )
    container.seed_marketplace_item().execute(item)
    market = client.get("/api/v1/market/items?q=cardigan").json()
    assert market

    tryon = client.post(
        "/api/v1/tryon/sessions",
        json={
            "character_id": character["id"],
            "marketplace_item_id": item.id,
            "scene_id": scene["id"],
        },
    ).json()
    assert len(tryon["candidate_asset_ids"]) == 4
    adopted = client.post(
        f"/api/v1/tryon/sessions/{tryon['session_id']}/adopt",
        json={"asset_id": tryon["candidate_asset_ids"][0], "scene_id": scene["id"]},
    ).json()
    assert adopted["outfit_profile_id"]

    shot = client.post(f"/api/v1/beats/{beat['id']}/shots/plan").json()
    rendered = client.post(
        f"/api/v1/shots/{shot['id']}/render",
        json={"use_pose": True, "pose_asset_uri": "asset://pose/fixture.png"},
    ).json()
    assert len(rendered["output_asset_ids"]) == 4
    adopted_id = rendered["output_asset_ids"][0]
    decision = client.put(
        f"/api/v1/assets/{adopted_id}/decision",
        json={"decision": "adopted"},
    ).json()
    assert decision["decision"] == "adopted"

    handoff = client.post(
        "/api/v1/csp/handoffs",
        json={
            "project_id": project["id"],
            "pages": [
                {
                    "page_no": 1,
                    "panels": [
                        {
                            "panel_no": 1,
                            "shot_id": shot["id"],
                            "script_event_ids": [locked["id"]],
                            "asset_id": adopted_id,
                        }
                    ],
                }
            ],
            "script_rows": [
                {
                    "id": locked["id"],
                    "kind": "speech",
                    "speaker": character["display_name"],
                    "text": locked["text"],
                }
            ],
        },
    ).json()
    assert handoff["revision"] == "r001"
    panel = handoff["manifest"]["pages"][0]["panels"][0]
    assert panel["asset_id"] == adopted_id
    assert panel["sha256"] == decision["sha256"]
    assert Path(handoff["path"], "pages", "page_001", "panel_01_clean.png").exists()

    preview = client.post(
        "/api/v1/releases/preview",
        json={"title": "Slice Release", "summary": "teaser", "hashtags": ["#SceneWeaver"]},
    ).json()
    assert "x" in preview["editions"]
    assert "pixiv" in preview["editions"]
    assert "patreon" in preview["editions"]