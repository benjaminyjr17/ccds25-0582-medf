from __future__ import annotations

import json
from pathlib import Path

from scripts.run_research_statistics import OUT_JSON, run


ROOT = Path(__file__).resolve().parent.parent


def test_research_statistics_runner_returns_expected_metrics() -> None:
    results = run(seed=42, n_boot=200)

    for key in ("cvi", "krippendorff", "sus", "wilcoxon", "friedman", "cliffs_delta"):
        assert key in results, f"Missing statistics key '{key}'."

    assert 0.0 <= float(results["cvi"]["s_cvi_ave"]) <= 1.0
    assert -1.0 <= float(results["krippendorff"]["alpha_ordinal"]) <= 1.0
    assert 0.0 <= float(results["sus"]["mean"]) <= 100.0
    assert 0.0 <= float(results["wilcoxon"]["p_value"]) <= 1.0
    assert 0.0 <= float(results["friedman"]["p_value"]) <= 1.0
    assert -1.0 <= float(results["cliffs_delta"]["delta"]) <= 1.0


def test_research_statistics_runner_is_deterministic_for_fixed_seed() -> None:
    first = run(seed=42, n_boot=200)
    second = run(seed=42, n_boot=200)
    assert first == second


def test_committed_statistical_results_file_exists_and_has_required_keys() -> None:
    assert OUT_JSON.exists(), f"Missing committed statistics output: {OUT_JSON}"
    with OUT_JSON.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    assert isinstance(payload, dict)
    for key in ("cvi", "krippendorff", "sus", "wilcoxon", "friedman", "cliffs_delta"):
        assert key in payload, f"Missing key '{key}' in committed statistics output."
