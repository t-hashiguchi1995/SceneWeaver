"""Scratch Shot lifecycle: draft → generated → adopted (materialize=copy) | abandoned."""

from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import create_app
from creator_studio.application.assets.store_asset import StoreBytesCommand
from creator_studio.domain.asset import AssetKind
from creator_studio.domain.ids import CharacterId
from creator_studio.domain.wardrobe import OutfitProfile
from creator_studio.infrastructure.container import Container

_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
    b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _seed_character(container: Container, name: str = "StudioHero") -> tuple[str, str]:
    char = container.create_character().execute(name)
    base = container.store_asset().execute(
        StoreBytesCommand(
            data=_PNG + name.encode(),
            kind=AssetKind.REFERENCE,
            mime="image/png",
            relative_dir="characters",
            filename=f"{name}.png",
        )
    )
    container.update_visual_identity().execute(
        char.id,
        {
            "tryon_base_asset_id": base.id,
            "identity_tags": [f"char_{name}"],
            "hair": f"{name}_hair",
        },
    )
    outfit = OutfitProfile.create(
        f"{name} Casual",
        character_id=CharacterId(char.id),
        semantic={"garment_description": "simple casual clothes"},
    )
    with container.uow() as uow:
        uow.outfit_profiles.add(outfit)
        uow.commit()
    return char.id, outfit.id


def test_quick_studio_scratch_lifecycle(container: Container) -> None:
    char_id, outfit_id = _seed_character(container)
    client = TestClient(create_app())

    poses = client.get("/api/v1/references/poses")
    assert poses.status_code == 200
    pose = poses.json()[0]
    pose_id = pose["id"]
    pose_view = pose["default_view"]

    created = client.post(
        "/api/v1/studio/sessions",
        json={"character_id": char_id, "outfit_profile_id": outfit_id},
    )
    assert created.status_code == 200, created.text
    session = created.json()
    shot_id = session["shot_id"]
    assert session["lifecycle"] == "draft"
    assert session["hidden"] is True

    applied = client.post(
        f"/api/v1/studio/sessions/{shot_id}/pose",
        json={"pose_id": pose_id, "pose_view": pose_view, "control_strength": 1.0},
    )
    assert applied.status_code == 200, applied.text
    body = applied.json()
    assert body["pose_provenance"]["pose_id"] == pose_id
    assert body["pose_provenance"]["pose_view"] == pose_view
    assert body["render_spec"].get("pose_asset_uri", "").startswith("asset://")

    rendered = client.post(f"/api/v1/studio/sessions/{shot_id}/render", json={})
    assert rendered.status_code == 200, rendered.text
    result = rendered.json()
    assert result["output_asset_ids"]
    assert result["session"]["lifecycle"] == "generated"
    attempt_id = result["generation_attempt_id"]
    scratch_assets = list(result["output_asset_ids"])

    # Provenance on attempt payload
    attempt = client.get(f"/api/v1/generation-attempts/{attempt_id}")
    assert attempt.status_code == 200
    payload = attempt.json()["payload"]
    assert payload["pose_provenance"]["pose_id"] == pose_id
    assert payload["pose_provenance"]["pose_source"] == "shisei"

    adopted = client.post(
        f"/api/v1/studio/sessions/{shot_id}/materialize",
        json={"generation_attempt_id": attempt_id},
    )
    assert adopted.status_code == 200, adopted.text
    mat = adopted.json()
    assert mat["lifecycle"] == "adopted"
    formal_id = mat["formal_shot_id"]
    assert formal_id
    assert mat["output_asset_ids"] == scratch_assets  # copy, not rerender

    formal = client.get(f"/api/v1/shots/{formal_id}")
    assert formal.status_code == 200
    fspec = formal.json()["render_spec"]
    assert fspec.get("_adopted_from_scratch_shot_id") == shot_id
    assert "_studio" not in fspec

    # Abandoned path on a fresh session
    created2 = client.post(
        "/api/v1/studio/sessions",
        json={"character_id": char_id, "outfit_profile_id": outfit_id},
    )
    shot2 = created2.json()["shot_id"]
    abandoned = client.post(f"/api/v1/studio/sessions/{shot2}/abandon")
    assert abandoned.status_code == 200
    assert abandoned.json()["lifecycle"] == "abandoned"

    # Cannot materialize abandoned
    bad = client.post(f"/api/v1/studio/sessions/{shot2}/materialize", json={})
    assert bad.status_code == 400


def test_pose_provenance_snapshot(container: Container) -> None:
    char_id, _ = _seed_character(container, "ProvHero")
    client = TestClient(create_app())
    pose = client.get("/api/v1/references/poses").json()[0]
    session = client.post(
        "/api/v1/studio/sessions", json={"character_id": char_id}
    ).json()
    shot_id = session["shot_id"]
    client.post(
        f"/api/v1/studio/sessions/{shot_id}/pose",
        json={"pose_id": pose["id"], "pose_view": pose["default_view"]},
    )
    snap1 = client.get(f"/api/v1/studio/sessions/{shot_id}").json()["pose_provenance"]
    assert snap1["pose_id"] == pose["id"]
    assert snap1["pose_asset_sha256"]
    # Re-get is stable (immutable snapshot fields)
    snap2 = client.get(f"/api/v1/studio/sessions/{shot_id}").json()["pose_provenance"]
    assert snap2 == snap1


def test_list_outfit_profiles_for_character(container: Container) -> None:
    char_id, outfit_id = _seed_character(container, "OutfitList")
    client = TestClient(create_app())
    listed = client.get(f"/api/v1/characters/{char_id}/outfit-profiles")
    assert listed.status_code == 200
    rows = listed.json()
    assert any(r["id"] == outfit_id for r in rows)
