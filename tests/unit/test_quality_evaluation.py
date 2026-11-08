import json

import pytest
from PIL import Image

from creator_studio.application.image.quality_evaluation import (
    AXES,
    WEIGHTS,
    Finding,
    ImageUnreadableError,
    QualityEvaluation,
    average_hash,
    basic_image_info,
    compute_gate,
    evaluate_image,
    hamming_distance,
    sha256_of_file,
)
from creator_studio.application.image.quality_evaluation_store import (
    list_evaluations,
    load_evaluation,
    save_evaluation,
    save_review,
)


def scores(value=90, **changes):
    return dict(dict.fromkeys(AXES, value), **changes)


def test_weights():
    assert sum(WEIGHTS.values()) == pytest.approx(1)


@pytest.mark.parametrize(
    "values,gate,reason",
    [
        (scores(), "PASS", None),
        (scores(80), "REVIEW", "score_below_85"),
        (scores(65), "FAIL", "total_below_70"),
        (scores(pose=59), "FAIL", "pose_below_60"),
        (scores(pose=None), "REVIEW", "insufficient_reference_data"),
        (scores(90, pose=74), "REVIEW", "pose_boundary_60_75"),
        (scores(60, pose=None, anatomy=None, identity=None), "REVIEW", "insufficient_evidence"),
    ],
)
def test_gates(values, gate, reason):
    actual, reasons, _ = compute_gate(values, [])
    assert actual == gate
    if reason:
        assert reason in reasons


@pytest.mark.parametrize(
    "finding,reason",
    [
        (Finding("anatomy", 3, "confirmed", confirmed=True), "critical_defect_confirmed"),
        (Finding("pose_violation", 1, "confirmed", confirmed=True), "pose_violation_confirmed"),
    ],
)
def test_confirmed_overrides(finding, reason):
    gate, reasons, _ = compute_gate(scores(), [finding])
    assert gate == "FAIL"
    assert reason in reasons
    finding.confirmed = False
    assert compute_gate(scores(), [finding])[0] == "PASS"


def test_blocked_and_interval():
    values = scores(80, pose=None, hands=None)
    gate, reasons, interval = compute_gate(values, [], ["image_unreadable"])
    assert gate == "BLOCKED"
    assert reasons == ["image_unreadable"]
    assert interval == pytest.approx([52, 87])
    assert compute_gate(values, [])[2] == pytest.approx([52, 87])
    assert compute_gate({}, [])[2] == pytest.approx([0, 100])


def test_image_checks_and_duplicate(tmp_path):
    path = tmp_path / "image.png"
    copy = tmp_path / "copy.png"
    image = Image.new("RGB", (128, 128))
    for x in range(128):
        for y in range(128):
            image.putpixel((x, y), (x * 2, y * 2, 100))
    image.save(path)
    image.resize((120, 120)).save(copy)
    hashed = average_hash(path)
    assert average_hash(path) == hashed
    assert hamming_distance(hashed, average_hash(copy)) <= 5
    assert basic_image_info(path) == {"width": 128, "height": 128, "format": "PNG", "mode": "RGB"}
    assert len(sha256_of_file(path)) == 64
    record = evaluate_image(path, known_hashes={"previous": hashed})
    assert record.gate == "REVIEW"
    assert record.unavailable_metrics == list(AXES)
    finding = record.findings[0]
    assert finding.category == "duplicate"
    assert finding.severity == 1 and not finding.confirmed
    assert "previous" in finding.evidence
    record.findings.append(Finding("test", 2, bbox_norm_xyxy=(0.1, 0.2, 0.3, 0.4)))
    assert QualityEvaluation.from_dict(json.loads(json.dumps(record.to_dict()))) == record


def test_unreadable(tmp_path):
    path = tmp_path / "bad.png"
    path.write_bytes(b"broken")
    with pytest.raises(ImageUnreadableError):
        basic_image_info(path)
    record = evaluate_image(path)
    assert record.gate == "BLOCKED"
    assert record.gate_reasons == ["image_unreadable"]
    assert record.image_sha256 == sha256_of_file(path)
    assert evaluate_image(tmp_path / "missing").gate == "BLOCKED"


def test_provider(tmp_path):
    path = tmp_path / "image.png"
    Image.new("RGB", (8, 8)).save(path)

    class Provider:
        def score(self, image_path, context):
            assert context["reference_ids"]["character"] == "character-1"
            return scores()

    record = evaluate_image(path, provider=Provider(), reference_ids={"character": "character-1"})
    assert record.gate == "PASS"
    assert record.unavailable_metrics == []


def test_store(tmp_path):
    record = QualityEvaluation()
    save_evaluation(record, directory=tmp_path)
    assert load_evaluation(record.quality_evaluation_id, directory=tmp_path) == record
    assert list_evaluations(directory=tmp_path) == [record]
    save_review(
        record.quality_evaluation_id,
        "human",
        "PASS",
        ["looks good"],
        "2026-11-08",
        directory=tmp_path,
    )
    updated = load_evaluation(record.quality_evaluation_id, directory=tmp_path)
    assert updated.human_verdict == "PASS"
    payload = json.loads(next(tmp_path.glob("*.json")).read_text())
    assert payload["review"]["reasons"] == ["looks good"]
    with pytest.raises(FileNotFoundError):
        load_evaluation("../outside", directory=tmp_path)
