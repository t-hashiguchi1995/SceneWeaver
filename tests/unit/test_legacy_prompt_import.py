from __future__ import annotations

from pathlib import Path

import yaml

from creator_studio.infrastructure.container import Container
from scripts.import_legacy_prompts import (
    SOURCE,
    apply_plan,
    build_plan,
    reconcile_idempotency,
)


def _write_fixture(root: Path) -> None:
    (root / "dynamic").mkdir(parents=True)
    (root / "characters").mkdir(parents=True)
    (root / "dynamic" / "sfw_expressions.yaml").write_text(
        yaml.safe_dump(
            {
                "expressions": [
                    {
                        "name": "soft_smile",
                        "prompt": "soft smile, gentle eyes",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (root / "dynamic" / "presets_r18.yaml").write_text(
        yaml.safe_dump({"expressions": [{"name": "x", "prompt": "adult"}]}),
        encoding="utf-8",
    )
    (root / "characters" / "demo_girl.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "Demo Girl",
                "prompt": {"identity": "1girl, brown hair", "includes": ["sfw_base"]},
            }
        ),
        encoding="utf-8",
    )


def test_legacy_import_idempotent_and_skips_adult(tmp_path: Path, container: Container) -> None:
    fixture = tmp_path / "prompts"
    _write_fixture(fixture)

    planned = reconcile_idempotency(build_plan(fixture), container)
    statuses = {row.status for row in planned}
    assert "create" in statuses
    adultish = [r for r in planned if "r18" in r.source_file.lower()]
    assert adultish
    assert all(r.status == "adult-tagged" for r in adultish)

    creates = [r for r in planned if r.status == "create"]
    assert creates

    first = apply_plan(planned, container)
    assert first["create"] >= 1

    planned2 = reconcile_idempotency(build_plan(fixture), container)
    unchanged = [r for r in planned2 if r.status == "unchanged"]
    assert unchanged
    assert all(r.status != "create" for r in planned2 if r.entity_type in {"prompt_preset", "character"})

    second = apply_plan(planned2, container)
    assert second.get("create", 0) == 0

    with container.uow() as uow:
        for row in unchanged:
            assert uow.legacy_imports.get(SOURCE, row.source_file, row.legacy_key) is not None
        presets = uow.prompt_presets.list_by_kind("snippet")
        assert len(presets) >= 1
