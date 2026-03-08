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
        text = path.read_text(encoding="utf-8", errors="ignore").strip()
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
        text = path.read_text(encoding="utf-8", errors="ignore")
        lower_text = text.lower()
        for literal in disallowed_literals:
            if literal.startswith("stub"):
                assert literal not in lower_text, f"Found stale placeholder text '{literal}' in {path}"
            else:
                assert literal not in text, f"Found unresolved literal '{literal}' in {path}"


def _iter_repo_text_targets() -> list[Path]:
    targets = [
        ROOT / "README.md",
        ROOT / "docs",
        ROOT / ".github",
        ROOT / "scripts",
        ROOT / "tools",
        ROOT / "tests" / "test_docs_consistency.py",
    ]
    skipped_suffixes = {".svg", ".png", ".json", ".csv"}
    discovered: list[Path] = []

    for target in targets:
        if target.is_file():
            if "__pycache__" not in target.parts and target.suffix not in skipped_suffixes:
                discovered.append(target)
            continue
        for path in target.rglob("*"):
            if not path.is_file():
                continue
            if "__pycache__" in path.parts or path.suffix in skipped_suffixes:
                continue
            discovered.append(path)

    return discovered


def test_removed_internal_module_is_not_referenced() -> None:
    forbidden_tokens = (
        "".join(("conflict", "_", "detection", ".", "py")),
        "".join(("app", ".", "conflict", "_", "detection")),
    )

    for path in _iter_repo_text_targets():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in forbidden_tokens:
            assert token not in text, f"Found removed internal-module reference in {path}"


def test_architecture_diagram_source_is_unique_and_canonical() -> None:
    old_source = ROOT / "docs" / "system_architecture.mmd"
    wrapper_doc = ROOT / "docs" / "system_architecture.md"
    render_script = ROOT / "tools" / "render_architecture_diagram.sh"

    assert not old_source.exists(), f"Unexpected file present: {old_source}"

    wrapper_text = wrapper_doc.read_text(encoding="utf-8", errors="ignore")
    assert "docs/architecture/system_architecture.mmd" in wrapper_text
    assert "docs/architecture/system_architecture.svg" in wrapper_text

    render_text = render_script.read_text(encoding="utf-8", errors="ignore")
    assert "docs/architecture/system_architecture.mmd" in render_text
    assert "docs/architecture/system_architecture.svg" in render_text
