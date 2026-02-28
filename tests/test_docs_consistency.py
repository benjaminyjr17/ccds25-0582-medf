from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def test_required_docs_are_non_empty() -> None:
    required_paths = [
        ROOT / "docs" / "requirements_traceability.md",
        ROOT / "docs" / "regulatory_traceability.md",
        ROOT / "docs" / "reproducibility_audit.md",
        ROOT / "docs" / "scope_boundary.md",
        ROOT / "docs" / "demo_runbook.md",
        ROOT / "docs" / "presentation_checklist.md",
    ]
    for path in required_paths:
        assert path.exists(), f"Missing required documentation file: {path}"
        text = path.read_text(encoding="utf-8").strip()
        assert text, f"Documentation file is empty: {path}"


def test_freeze_and_docs_do_not_contain_unresolved_placeholders() -> None:
    targets = [
        ROOT / "FREEZE.md",
        ROOT / "docs" / "data_model_spec.md",
        ROOT / "docs" / "architecture_description.md",
        ROOT / "docs" / "novelty_attack_simulation.md",
    ]
    disallowed_literals = [
        "<commit_sha>",
        "<YYYY-MM-DD>",
        "stub scoring",
        "stub conflict detection",
    ]

    for path in targets:
        assert path.exists(), f"Expected file missing: {path}"
        text = path.read_text(encoding="utf-8")
        lower_text = text.lower()
        for literal in disallowed_literals:
            if literal.startswith("stub"):
                assert literal not in lower_text, f"Found stale placeholder text '{literal}' in {path}"
            else:
                assert literal not in text, f"Found unresolved literal '{literal}' in {path}"
