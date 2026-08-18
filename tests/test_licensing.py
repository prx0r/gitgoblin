from gitgoblin.pipeline.licensing import classify_license


def test_permissive_license():
    decision = classify_license("MIT")
    assert decision.category == "permissive"
    assert "Reusable" in decision.recommendation


def test_agpl_is_not_treated_as_permissive():
    assert classify_license("AGPL-3.0").category == "copyleft"


def test_unknown_license_blocks_copy_assumption():
    decision = classify_license(None)
    assert decision.category == "unknown"
    assert "Do not copy" in decision.recommendation
