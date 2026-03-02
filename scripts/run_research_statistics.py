from __future__ import annotations

import argparse
import csv
import json
import math
from itertools import combinations
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any

import numpy as np
from scipy import stats


ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "research" / "data" / "raw"
OUT_DIR = ROOT / "docs" / "research"
OUT_JSON = OUT_DIR / "statistical_results.json"
OUT_MD = OUT_DIR / "statistical_summary.md"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def _compute_cvi() -> dict[str, Any]:
    rows = _read_csv(RAW_DIR / "cvi_expert_ratings.csv")
    by_item: dict[str, list[float]] = {}
    for row in rows:
        item_id = str(row["item_id"]).strip()
        rating = float(row["rating"])
        by_item.setdefault(item_id, []).append(rating)

    i_cvi = {
        item_id: float(sum(1 for rating in ratings if rating >= 3.0) / len(ratings))
        for item_id, ratings in sorted(by_item.items())
        if ratings
    }
    s_cvi_ave = float(mean(i_cvi.values())) if i_cvi else 0.0
    return {
        "n_items": len(i_cvi),
        "i_cvi_by_item": i_cvi,
        "s_cvi_ave": s_cvi_ave,
    }


def _krippendorff_alpha_ordinal(units: dict[str, list[float]]) -> float:
    valid_units = [ratings for ratings in units.values() if len(ratings) >= 2]
    if not valid_units:
        return 0.0

    all_values = [float(value) for ratings in valid_units for value in ratings]
    value_min = float(min(all_values))
    value_max = float(max(all_values))
    value_span = value_max - value_min
    if value_span <= 0.0:
        return 1.0

    def delta(a: float, b: float) -> float:
        return ((a - b) / value_span) ** 2

    observed_n = 0
    observed_sum = 0.0
    for ratings in valid_units:
        for left, right in combinations(ratings, 2):
            observed_sum += delta(float(left), float(right))
            observed_n += 1
    if observed_n == 0:
        return 0.0
    observed_disagreement = observed_sum / observed_n

    counts: dict[float, int] = {}
    for value in all_values:
        counts[value] = counts.get(value, 0) + 1
    total = float(sum(counts.values()))
    if total <= 0.0:
        return 0.0
    probs = {value: count / total for value, count in counts.items()}
    expected_disagreement = 0.0
    for value_a, prob_a in probs.items():
        for value_b, prob_b in probs.items():
            expected_disagreement += prob_a * prob_b * delta(value_a, value_b)

    if expected_disagreement <= 0.0:
        return 1.0
    alpha = 1.0 - (observed_disagreement / expected_disagreement)
    return float(np.clip(alpha, -1.0, 1.0))


def _compute_krippendorff(seed: int, n_boot: int) -> dict[str, Any]:
    rows = _read_csv(RAW_DIR / "krippendorff_annotations.csv")
    units: dict[str, list[float]] = {}
    for row in rows:
        unit_id = str(row["unit_id"]).strip()
        value = float(row["value"])
        units.setdefault(unit_id, []).append(value)

    alpha = _krippendorff_alpha_ordinal(units)
    unit_ids = sorted(units.keys())
    rng = np.random.default_rng(seed)
    boot_values: list[float] = []
    if unit_ids:
        for _ in range(n_boot):
            sampled = rng.choice(unit_ids, size=len(unit_ids), replace=True)
            sampled_units = {
                f"boot_{idx}": list(units[unit_id])
                for idx, unit_id in enumerate(sampled)
            }
            boot_values.append(_krippendorff_alpha_ordinal(sampled_units))
    if boot_values:
        ci_low = float(np.percentile(boot_values, 2.5))
        ci_high = float(np.percentile(boot_values, 97.5))
    else:
        ci_low = alpha
        ci_high = alpha

    return {
        "alpha_ordinal": alpha,
        "bootstrap_ci_95": [ci_low, ci_high],
        "n_bootstrap": int(n_boot),
        "seed": int(seed),
    }


def _compute_sus() -> dict[str, Any]:
    rows = _read_csv(RAW_DIR / "sus_responses.csv")
    participant_scores: dict[str, float] = {}
    for row in rows:
        participant_id = str(row["participant_id"]).strip()
        answers = [int(row[f"q{i}"]) for i in range(1, 11)]
        transformed = 0.0
        for index, value in enumerate(answers, start=1):
            if index % 2 == 1:
                transformed += float(value - 1)
            else:
                transformed += float(5 - value)
        participant_scores[participant_id] = transformed * 2.5

    values = list(participant_scores.values())
    return {
        "n_participants": len(values),
        "participant_scores": participant_scores,
        "mean": float(mean(values)) if values else 0.0,
        "median": float(median(values)) if values else 0.0,
        "std_dev": float(stdev(values)) if len(values) >= 2 else 0.0,
        "min": float(min(values)) if values else 0.0,
        "max": float(max(values)) if values else 0.0,
    }


def _compute_wilcoxon() -> dict[str, Any]:
    rows = _read_csv(RAW_DIR / "wilcoxon_paired_scores.csv")
    before = np.array([float(row["before"]) for row in rows], dtype=float)
    after = np.array([float(row["after"]) for row in rows], dtype=float)
    statistic, pvalue = stats.wilcoxon(before, after, zero_method="wilcox", alternative="two-sided")
    return {
        "n_pairs": int(before.shape[0]),
        "statistic": float(statistic),
        "p_value": float(pvalue),
    }


def _compute_friedman() -> dict[str, Any]:
    rows = _read_csv(RAW_DIR / "friedman_repeated_scores.csv")
    condition_a = np.array([float(row["condition_a"]) for row in rows], dtype=float)
    condition_b = np.array([float(row["condition_b"]) for row in rows], dtype=float)
    condition_c = np.array([float(row["condition_c"]) for row in rows], dtype=float)
    statistic, pvalue = stats.friedmanchisquare(condition_a, condition_b, condition_c)
    return {
        "n_participants": int(condition_a.shape[0]),
        "statistic": float(statistic),
        "p_value": float(pvalue),
    }


def _cliffs_delta(x: np.ndarray, y: np.ndarray) -> float:
    n_x = x.shape[0]
    n_y = y.shape[0]
    if n_x == 0 or n_y == 0:
        return 0.0
    greater = 0
    lower = 0
    for x_value in x:
        for y_value in y:
            if x_value > y_value:
                greater += 1
            elif x_value < y_value:
                lower += 1
    return float((greater - lower) / (n_x * n_y))


def _cliffs_magnitude(delta: float) -> str:
    absolute = abs(delta)
    if absolute < 0.147:
        return "negligible"
    if absolute < 0.33:
        return "small"
    if absolute < 0.474:
        return "medium"
    return "large"


def _compute_cliffs_delta() -> dict[str, Any]:
    rows = _read_csv(RAW_DIR / "cliffs_delta_groups.csv")
    by_group: dict[str, list[float]] = {}
    for row in rows:
        group = str(row["group"]).strip().lower()
        value = float(row["value"])
        by_group.setdefault(group, []).append(value)

    baseline = np.array(by_group.get("baseline", []), dtype=float)
    medf = np.array(by_group.get("medf", []), dtype=float)
    delta = _cliffs_delta(medf, baseline)
    return {
        "n_baseline": int(baseline.shape[0]),
        "n_medf": int(medf.shape[0]),
        "delta": float(delta),
        "magnitude": _cliffs_magnitude(delta),
    }


def run(*, seed: int = 42, n_boot: int = 2000) -> dict[str, Any]:
    results = {
        "metadata": {
            "seed": int(seed),
            "n_bootstrap": int(n_boot),
        },
        "cvi": _compute_cvi(),
        "krippendorff": _compute_krippendorff(seed=seed, n_boot=n_boot),
        "sus": _compute_sus(),
        "wilcoxon": _compute_wilcoxon(),
        "friedman": _compute_friedman(),
        "cliffs_delta": _compute_cliffs_delta(),
    }
    return results


def _summary_markdown(results: dict[str, Any]) -> str:
    cvi = results["cvi"]
    kripp = results["krippendorff"]
    sus = results["sus"]
    wilc = results["wilcoxon"]
    frie = results["friedman"]
    cliffs = results["cliffs_delta"]
    ci_low, ci_high = kripp["bootstrap_ci_95"]

    return "\n".join(
        [
            "# Statistical Results Summary",
            "",
            "This file is generated by `scripts/run_research_statistics.py`.",
            "",
            "## CVI",
            f"- S-CVI/Ave: `{cvi['s_cvi_ave']:.4f}`",
            f"- Items scored: `{cvi['n_items']}`",
            "",
            "## Krippendorff's Alpha (Ordinal)",
            f"- Alpha: `{kripp['alpha_ordinal']:.4f}`",
            f"- 95% bootstrap CI: `[{ci_low:.4f}, {ci_high:.4f}]`",
            f"- Bootstrap samples: `{kripp['n_bootstrap']}` (seed `{kripp['seed']}`)",
            "",
            "## SUS",
            f"- Participants: `{sus['n_participants']}`",
            f"- Mean SUS: `{sus['mean']:.2f}`",
            f"- Median SUS: `{sus['median']:.2f}`",
            f"- Std Dev: `{sus['std_dev']:.2f}`",
            "",
            "## Wilcoxon Signed-Rank",
            f"- n pairs: `{wilc['n_pairs']}`",
            f"- Statistic: `{wilc['statistic']:.4f}`",
            f"- p-value: `{wilc['p_value']:.6f}`",
            "",
            "## Friedman",
            f"- n participants: `{frie['n_participants']}`",
            f"- Statistic: `{frie['statistic']:.4f}`",
            f"- p-value: `{frie['p_value']:.6f}`",
            "",
            "## Cliff's Delta",
            f"- Delta: `{cliffs['delta']:.4f}`",
            f"- Magnitude: `{cliffs['magnitude']}`",
        ]
    )


def write_outputs(results: dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUT_JSON.open("w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2, sort_keys=True)
    with OUT_MD.open("w", encoding="utf-8") as handle:
        handle.write(_summary_markdown(results))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run MEDF research statistics pipeline.")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic random seed.")
    parser.add_argument(
        "--n-boot",
        type=int,
        default=2000,
        help="Bootstrap iterations for Krippendorff confidence interval.",
    )
    args = parser.parse_args()

    if args.n_boot <= 0:
        raise SystemExit("--n-boot must be positive.")

    results = run(seed=int(args.seed), n_boot=int(args.n_boot))
    write_outputs(results)
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {OUT_MD}")


if __name__ == "__main__":
    main()
