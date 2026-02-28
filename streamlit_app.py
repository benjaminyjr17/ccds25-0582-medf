from __future__ import annotations

import io
import json
import math
import re
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any
from uuid import uuid4
import zipfile

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

from plot_theme import BG, TEXT, apply_plot_theme as _shared_apply_plot_theme

UNIFIED_DIMENSIONS = [
    "transparency_explainability",
    "fairness_nondiscrimination",
    "safety_robustness",
    "privacy_data_governance",
    "human_agency_oversight",
    "accountability",
]

SEM_SUCCESS_HEX = "#22C55E"
SEM_WARNING_HEX = "#F59E0B"
SEM_DANGER_HEX = "#EF4444"
SEM_INFO_HEX = "#38BDF8"
SEM_MUTED_HEX = "#9CA3AF"
SEM_CARD_BG_HEX = "#0F172A"
SEM_BORDER_HEX = "#1F2937"
PARCOORDS_TICKFONT_HEX = "#E6E6E6"

BRAND_BLUE_HEX = SEM_INFO_HEX
BRAND_BLUE_FILL_RGBA = "rgba(56, 189, 248, 0.22)"

DIMENSION_DISPLAY_NAMES = {
    "transparency_explainability": "Transparency and Explainability",
    "fairness_nondiscrimination": "Fairness and Non-discrimination",
    "safety_robustness": "Safety and Robustness",
    "privacy_data_governance": "Privacy and Data Governance",
    "human_agency_oversight": "Human Agency and Oversight",
    "accountability": "Accountability",
}

LIKERT_MIN = 1.0
LIKERT_MAX = 7.0
UNICODE_MINUS = "\u2212"


def _flip_likert_profile(profile: dict[str, float]) -> dict[str, float]:
    flipped = {
        dimension: round((LIKERT_MIN + LIKERT_MAX) - float(score), 1)
        for dimension, score in profile.items()
    }
    for dimension, score in flipped.items():
        if score < LIKERT_MIN or score > LIKERT_MAX:
            raise ValueError(f"Flipped preset score for '{dimension}' is out of range.")
    return flipped


BASELINE_DIMENSION_SCORES = {
    # Mixed-risk enterprise AI: strong safety/accountability controls, moderate privacy, and weaker fairness/transparency.
    "transparency_explainability": 3.5,
    "fairness_nondiscrimination": 3.0,
    "safety_robustness": 5.5,
    "privacy_data_governance": 4.5,
    "human_agency_oversight": 3.5,
    "accountability": 5.0,
}

FLIPPED_DIMENSION_SCORES = _flip_likert_profile(BASELINE_DIMENSION_SCORES)

PRESET_BASELINE = dict(BASELINE_DIMENSION_SCORES)
PRESET_FLIPPED = dict(FLIPPED_DIMENSION_SCORES)

# A system profile that emphasizes strong safety controls while keeping other dimensions moderate.
PRESET_SAFETY_HEAVY = {
    "transparency_explainability": 4.0,
    "fairness_nondiscrimination": 4.0,
    "safety_robustness": 7.0,
    "privacy_data_governance": 4.0,
    "human_agency_oversight": 4.0,
    "accountability": 4.0,
}

DEMO_SCENARIO_NAME = "Hiring Screening (Demo)"
DEMO_SCENARIO_DESCRIPTION = (
    "Automated resume screening for job applicants using ML scoring."
)
DEMO_DIMENSION_SCORES = dict(BASELINE_DIMENSION_SCORES)

DEMO_WEIGHTS = {
    "developer": {
        "transparency_explainability": 0.10,
        "fairness_nondiscrimination": 0.10,
        "safety_robustness": 0.40,
        "privacy_data_governance": 0.10,
        "human_agency_oversight": 0.10,
        "accountability": 0.20,
    },
    "regulator": {
        "transparency_explainability": 0.20,
        "fairness_nondiscrimination": 0.15,
        "safety_robustness": 0.20,
        "privacy_data_governance": 0.20,
        "human_agency_oversight": 0.10,
        "accountability": 0.15,
    },
    "affected_community": {
        "transparency_explainability": 0.15,
        "fairness_nondiscrimination": 0.35,
        "safety_robustness": 0.10,
        "privacy_data_governance": 0.15,
        "human_agency_oversight": 0.15,
        "accountability": 0.10,
    },
}

HARD_CAP_EVALS = 30_000
PARETO_PRESETS = {
    "Standard": {"n_solutions": 25, "pop_size": 80, "n_gen": 80},
    "Thorough": {"n_solutions": 30, "pop_size": 120, "n_gen": 120},
}

CASE_STUDY_FILES: tuple[str, ...] = (
    "facial_recognition.json",
    "hiring_algorithm.json",
    "healthcare_diagnostic.json",
)


def _validated_case_dimension_scores(raw_scores: Any, *, case_id: str) -> dict[str, float]:
    if not isinstance(raw_scores, dict):
        raise ValueError(f"Case '{case_id}' is missing a valid dimension_scores object.")

    normalized: dict[str, float] = {}
    for dimension in UNIFIED_DIMENSIONS:
        if dimension not in raw_scores:
            raise ValueError(f"Case '{case_id}' missing dimension '{dimension}'.")
        try:
            value = float(raw_scores[dimension])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Case '{case_id}' has non-numeric score for '{dimension}'.") from exc
        if value < LIKERT_MIN or value > LIKERT_MAX:
            raise ValueError(
                f"Case '{case_id}' score for '{dimension}' must be in [{LIKERT_MIN}, {LIKERT_MAX}]."
            )
        normalized[dimension] = value

    return normalized


def _load_case_studies_from_files() -> list[dict[str, Any]]:
    case_dir = Path(__file__).resolve().parent / "case_studies"
    cases: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for file_name in CASE_STUDY_FILES:
        file_path = case_dir / file_name
        if not file_path.exists():
            raise RuntimeError(f"Missing case study file: {file_path}")

        with file_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        if not isinstance(payload, dict):
            raise ValueError(f"Case study payload in '{file_name}' must be a JSON object.")

        case_id = str(payload.get("id", "")).strip()
        name = str(payload.get("name", "")).strip()
        description = str(payload.get("description", "")).strip()

        if not case_id or not name or not description:
            raise ValueError(
                f"Case study '{file_name}' must include non-empty id, name, and description."
            )
        if case_id in seen_ids:
            raise ValueError(f"Duplicate case study id detected: '{case_id}'.")
        seen_ids.add(case_id)

        dim_scores = _validated_case_dimension_scores(
            payload.get("dimension_scores"),
            case_id=case_id,
        )

        cases.append(
            {
                "id": case_id,
                "name": name,
                "description": description,
                "dimension_scores": dim_scores,
                "deployment_context": payload.get("deployment_context", {}),
                "source_reference": payload.get("source_reference", {}),
                "assumptions": payload.get("assumptions", ""),
            }
        )

    return cases


CASE_STUDIES_LOAD_ERROR: str | None = None
try:
    CASE_STUDIES = _load_case_studies_from_files()
except Exception as exc:
    CASE_STUDIES = []
    CASE_STUDIES_LOAD_ERROR = str(exc)


def _get_theme_base():
    try:
        base = str(st.get_option("theme.base") or "light").lower()
        if base not in {"dark", "light"}:
            return "light"
        return base
    except Exception:
        return "light"


def _ui_tokens(theme_base: str) -> dict[str, str]:
    _ = theme_base
    return {
        "BG": BG,
        "CARD_BG": SEM_CARD_BG_HEX,
        "TEXT": TEXT,
        "MUTED": SEM_MUTED_HEX,
        "ACCENT": SEM_INFO_HEX,
        "SUCCESS": SEM_SUCCESS_HEX,
        "WARNING": SEM_WARNING_HEX,
        "DANGER": SEM_DANGER_HEX,
        "INFO": SEM_INFO_HEX,
        "BORDER": SEM_BORDER_HEX,
    }

def inject_css(tokens: dict[str, str]) -> None:
    st.markdown(
        f"""
<style>
:root {{
    --medf-bg: {tokens["BG"]};
    --medf-card-bg: {tokens["CARD_BG"]};
    --medf-text: {tokens["TEXT"]};
    --medf-muted: {tokens["MUTED"]};
    --medf-border: {tokens["BORDER"]};
    --medf-info: {tokens["INFO"]};
}}

html, body, [data-testid="stAppViewContainer"] {{
    background: var(--medf-bg);
    color: var(--medf-text);
}}

[data-testid="stAppViewContainer"] .main .block-container {{
    max-width: 1280px;
    padding-top: 0.95rem;
    padding-bottom: 1.1rem;
    padding-left: 1.05rem;
    padding-right: 1.05rem;
}}

section[data-testid="stSidebar"] {{
    background: var(--medf-card-bg);
    border-right: 1px solid var(--medf-border);
}}

section[data-testid="stSidebar"] > div {{
    padding-top: 0.45rem;
    padding-left: 0.35rem;
    padding-right: 0.35rem;
}}

h1, h2, h3, h4 {{
    color: var(--medf-text);
    letter-spacing: 0.01em;
    margin-top: 0.25rem;
    margin-bottom: 0.5rem;
}}

[data-testid="stCaptionContainer"], .medf-muted {{
    color: var(--medf-muted);
}}

.medf-header {{
    margin-bottom: 0.55rem;
}}

.medf-title {{
    color: var(--medf-text);
    font-size: 1.62rem;
    font-weight: 650;
    letter-spacing: 0.008em;
    line-height: 1.3;
}}

.medf-subtitle {{
    color: var(--medf-muted);
    font-size: 0.94rem;
    line-height: 1.45;
    margin-top: 0.18rem;
}}

.medf-separator {{
    margin-top: 0.48rem;
    border-top: 1px solid var(--medf-border);
}}

.medf-kpi-strip {{
    margin-top: 0.38rem;
    margin-bottom: 0.95rem;
}}

.medf-kpi-card {{
    background: var(--medf-card-bg);
    border: 1px solid var(--medf-border);
    border-left: 4px solid var(--kpi-accent, var(--medf-info));
    border-radius: 10px;
    padding: 0.72rem 0.8rem;
    min-height: 106px;
}}

.medf-kpi-value {{
    color: var(--medf-text);
    font-size: 1.16rem;
    font-weight: 700;
    line-height: 1.2;
    margin-top: 0.08rem;
}}

.medf-kpi-label {{
    color: var(--medf-muted);
    font-size: 0.67rem;
    letter-spacing: 0.08em;
    font-weight: 600;
    margin-top: 0.33rem;
}}

.medf-kpi-note {{
    color: var(--medf-muted);
    font-size: 0.76rem;
    line-height: 1.24;
    margin-top: 0.18rem;
}}

[data-testid="stVerticalBlockBorderWrapper"] {{
    border-color: var(--medf-border) !important;
    border-radius: 10px;
    background: var(--medf-card-bg);
}}

div.stButton > button {{
    border: 1px solid var(--medf-border);
    border-radius: 8px;
    background: #111827;
    color: var(--medf-text);
    font-weight: 600;
}}

div.stButton > button:hover {{
    border-color: #334155;
    background: #0b1220;
}}

.medf-page-nav [data-testid="stRadio"] > div {{
    gap: 0.45rem;
}}

.medf-page-nav [data-testid="stRadio"] label {{
    border: 1px solid rgba(56,189,248,0.35);
    border-radius: 999px;
    padding: 0.25rem 0.68rem;
    background: rgba(56,189,248,0.08);
}}

.medf-page-nav [data-testid="stRadio"] label:hover {{
    border-color: {BRAND_BLUE_HEX};
    background: rgba(56,189,248,0.14);
}}

.medf-page-nav [data-testid="stRadio"] label [data-testid="stMarkdownContainer"] p {{
    color: var(--medf-text);
    font-weight: 600;
}}

.medf-page-nav [data-testid="stRadio"] label:has(input:checked) {{
    border-color: {BRAND_BLUE_HEX};
    background: rgba(56,189,248,0.2);
    box-shadow: 0 0 0 1px rgba(56,189,248,0.45) inset;
}}

.medf-page-nav [data-testid="stRadio"] label:has(input:checked) [data-testid="stMarkdownContainer"] p {{
    color: {BRAND_BLUE_HEX};
}}
</style>
""",
        unsafe_allow_html=True,
    )


def apply_plot_theme(fig: go.Figure, title: str | None = None) -> go.Figure:
    current_title = safe_str(getattr(getattr(fig.layout, "title", None), "text", None)).strip()
    title_text = safe_str(title).strip() if title is not None else current_title
    if title_text.lower() == "undefined":
        title_text = ""
    if title_text:
        fig.update_layout(title={"text": title_text})
    themed = _shared_apply_plot_theme(fig)
    raw_meta = getattr(themed.layout, "meta", None)
    meta = dict(raw_meta) if isinstance(raw_meta, dict) else {}
    meta["medf_plot_theme_applied"] = True
    themed.update_layout(meta=meta)
    return themed


def style_plotly(fig: go.Figure, tokens: dict[str, str]) -> go.Figure:
    _ = tokens
    existing_title = safe_str(getattr(getattr(fig.layout, "title", None), "text", None)).strip()
    title_text = existing_title if existing_title and existing_title.lower() != "undefined" else ""
    return apply_plot_theme(fig, title=title_text)


def _assert_tradeoff_parcoords_theme(fig: go.Figure) -> None:
    fig_json = fig.to_plotly_json()
    data = fig_json.get("data", [])
    if not data or data[0].get("type") != "parcoords":
        raise AssertionError("Tradeoff chart must be a parcoords figure.")

    dimensions = data[0].get("dimensions", [])
    if not isinstance(dimensions, list) or not dimensions:
        raise AssertionError("Parcoords dimensions are missing.")

    for index, dimension in enumerate(dimensions):
        label = safe_str(dimension.get("label", "")).strip()
        if not label or "_" in label or label != label.title():
            raise AssertionError(f"Parcoords dimension {index} label is not human-friendly: {label!r}")
        tickfont = dimension.get("tickfont", {})
        if not isinstance(tickfont, dict) or tickfont.get("color") != TEXT:
            raise AssertionError(f"Parcoords dimension {index} tickfont color must be {TEXT}.")

    line = data[0].get("line", {})
    colorbar = line.get("colorbar", {}) if isinstance(line, dict) else {}
    tickfont = colorbar.get("tickfont", {}) if isinstance(colorbar, dict) else {}
    if not isinstance(tickfont, dict) or tickfont.get("color") != TEXT:
        raise AssertionError(f"Parcoords colorbar tickfont color must be {TEXT}.")

    title = colorbar.get("title", {}) if isinstance(colorbar, dict) else {}
    title_font = title.get("font", {}) if isinstance(title, dict) else {}
    if not isinstance(title_font, dict) or title_font.get("color") != TEXT:
        raise AssertionError(f"Parcoords colorbar title font color must be {TEXT}.")


def _render_institutional_header() -> None:
    st.markdown(
        """
<div class="medf-header">
    <div class="medf-title">MEDF: Multi-Stakeholder Ethical Decision Framework.</div>
    <div class="medf-subtitle">Governance-grade evaluation. Stakeholder conflict detection. Pareto-based resolution.</div>
    <div class="medf-separator"></div>
</div>
""",
        unsafe_allow_html=True,
    )


def _distance_semantic(distance: float) -> tuple[str, str]:
    if distance <= 0.20:
        return "Aligned", SEM_SUCCESS_HEX
    if distance <= 0.40:
        return "Moderate", SEM_WARNING_HEX
    return "High", SEM_DANGER_HEX


def _conflict_severity_rank(level: str) -> int:
    normalized = safe_str(level).strip().lower()
    if "critical" in normalized or "high" in normalized:
        return 3
    if "moderate" in normalized or "medium" in normalized:
        return 2
    if "low" in normalized:
        return 1
    return 0


def _conflict_semantic(level: str, rho: float | None) -> tuple[str, str]:
    normalized = safe_str(level).strip().lower()
    if normalized:
        if "critical" in normalized or "high" in normalized:
            return "High", SEM_DANGER_HEX
        if "moderate" in normalized or "medium" in normalized:
            return "Moderate", SEM_WARNING_HEX
        if "low" in normalized:
            return "Low", SEM_SUCCESS_HEX
    if rho is None:
        return "Unavailable", SEM_INFO_HEX
    if rho <= -0.35:
        return "High", SEM_DANGER_HEX
    if rho < 0.15:
        return "Moderate", SEM_WARNING_HEX
    return "Low", SEM_SUCCESS_HEX


def _conflict_overview(conflict_result: Any) -> dict[str, str]:
    default_value = "NO DATA."
    default_note = "No conflict output is available for this run."
    if not isinstance(conflict_result, dict):
        return {
            "value": default_value,
            "color": SEM_INFO_HEX,
            "note": default_note,
            "pair": "N/A",
        }

    conflicts = conflict_result.get("conflicts", [])
    if not isinstance(conflicts, list) or not conflicts:
        return {
            "value": "NO MATERIAL CONFLICT.",
            "color": SEM_SUCCESS_HEX,
            "note": "No stakeholder conflict pair is currently flagged.",
            "pair": "N/A",
        }

    worst: dict[str, Any] | None = None
    worst_key: tuple[float, float] = (-1.0, -1.0)
    for conflict in conflicts:
        if not isinstance(conflict, dict):
            continue
        level = safe_str(conflict.get("conflict_level")).strip()
        rho_raw = conflict.get("spearman_rho")
        rho_value = float(rho_raw) if isinstance(rho_raw, (int, float)) else None
        severity = float(_conflict_severity_rank(level))
        rho_rank = float(-rho_value) if rho_value is not None else -2.0
        if (severity, rho_rank) > worst_key:
            worst = conflict
            worst_key = (severity, rho_rank)

    if worst is None:
        return {
            "value": default_value,
            "color": SEM_INFO_HEX,
            "note": default_note,
            "pair": "N/A",
        }

    level = safe_str(worst.get("conflict_level")).strip()
    rho_raw = worst.get("spearman_rho")
    rho_value = float(rho_raw) if isinstance(rho_raw, (int, float)) else None
    semantic_label, semantic_color = _conflict_semantic(level, rho_value)
    pair = (
        f"{safe_str(worst.get('stakeholder_a_id')).strip()} vs "
        f"{safe_str(worst.get('stakeholder_b_id')).strip()}"
    ).strip()
    pair_value = pair if pair and pair != "vs" else "N/A"
    value = semantic_label.upper()
    if rho_value is not None:
        value = f"{value} ({fmt_small(rho_value)})."
    else:
        value = f"{value}."
    return {
        "value": value,
        "color": semantic_color,
        "note": f"Worst pairwise alignment: {pair_value}.",
        "pair": pair_value,
    }


def _consensus_overview(pareto_result: Any) -> dict[str, str]:
    default_overview = {
        "primary_dimension": "N/A.",
        "primary_dimension_color": SEM_INFO_HEX,
        "primary_dimension_note": "No Pareto solution is currently selected.",
        "divergence": "N/A.",
        "divergence_color": SEM_INFO_HEX,
        "divergence_note": "No stakeholder distance is currently available.",
    }
    if not isinstance(pareto_result, dict):
        return default_overview

    raw_solutions = pareto_result.get("pareto_solutions", [])
    if not isinstance(raw_solutions, list) or not raw_solutions:
        return default_overview

    valid_solutions = [item for item in raw_solutions if isinstance(item, dict)]
    if not valid_solutions:
        return default_overview

    selected_solution_id = safe_str(st.session_state.get("pareto_selected_id")).strip()
    selected_solution = next(
        (
            item
            for item in valid_solutions
            if safe_str(item.get("solution_id")).strip() == selected_solution_id
        ),
        valid_solutions[0],
    )

    consensus_raw = selected_solution.get("weights", {})
    consensus = {}
    if isinstance(consensus_raw, dict) and isinstance(consensus_raw.get("consensus"), dict):
        consensus = {
            dimension: float(consensus_raw["consensus"].get(dimension, 0.0))
            for dimension in UNIFIED_DIMENSIONS
        }
    if consensus:
        top_dimension = max(consensus.items(), key=lambda item: float(item[1]))[0]
        primary_dimension = f"{DIMENSION_DISPLAY_NAMES.get(top_dimension, top_dimension)}."
    else:
        primary_dimension = "N/A."

    objective_raw = selected_solution.get("objective_scores", {})
    objective_scores = (
        {safe_str(key): float(value) for key, value in objective_raw.items()}
        if isinstance(objective_raw, dict)
        else {}
    )
    divergence = "N/A."
    divergence_color = SEM_INFO_HEX
    divergence_note = "No stakeholder distance is currently available."
    if objective_scores:
        stakeholder_id, max_distance = max(objective_scores.items(), key=lambda item: float(item[1]))
        distance_label, distance_color = _distance_semantic(float(max_distance))
        divergence = f"{stakeholder_id}: {fmt_small(max_distance)}."
        divergence_color = distance_color
        divergence_note = f"Highest distance classification: {distance_label.lower()}."

    return {
        "primary_dimension": primary_dimension,
        "primary_dimension_color": SEM_INFO_HEX,
        "primary_dimension_note": "Top consensus weight in the selected solution.",
        "divergence": divergence,
        "divergence_color": divergence_color,
        "divergence_note": divergence_note,
    }


def _build_executive_kpis() -> list[dict[str, str]]:
    evaluate_result = st.session_state.get("last_evaluate_result")
    conflict_result = st.session_state.get("last_conflict_result")
    pareto_result = st.session_state.get("pareto_result")

    score_value = "N/A."
    score_color = SEM_INFO_HEX
    score_note = "No evaluation score is currently available."
    if isinstance(evaluate_result, dict) and isinstance(evaluate_result.get("overall_score"), (int, float)):
        overall_score = float(evaluate_result["overall_score"])
        risk_label, risk_color = _risk_label(overall_score)
        score_value = f"{fmt_score(overall_score)} ({risk_label})."
        score_color = risk_color
        score_note = "Normalized aggregate score from the latest evaluation run."

    conflict_overview = _conflict_overview(conflict_result)
    consensus_overview = _consensus_overview(pareto_result)
    divergence_value = safe_str(consensus_overview["divergence"])
    if ":" in divergence_value:
        raw_stakeholder_id, remainder = divergence_value.split(":", 1)
        divergence_value = f"{_format_kpi_stakeholder_label(raw_stakeholder_id.strip())}:{remainder}"

    return [
        {
            "icon": "■",
            "label": "Overall Ethical Score",
            "value": score_value,
            "note": score_note,
            "color": score_color,
        },
        {
            "icon": "⚖",
            "label": "Conflict Level",
            "value": conflict_overview["value"],
            "note": conflict_overview["note"],
            "color": conflict_overview["color"],
        },
        {
            "icon": "◇",
            "label": "Primary Consensus Dimension",
            "value": consensus_overview["primary_dimension"],
            "note": consensus_overview["primary_dimension_note"],
            "color": consensus_overview["primary_dimension_color"],
        },
        {
            "icon": "↔",
            "label": "Highest Stakeholder Divergence",
            "value": divergence_value,
            "note": consensus_overview["divergence_note"],
            "color": consensus_overview["divergence_color"],
        },
    ]


def _format_kpi_stakeholder_label(value: str) -> str:
    mapping = {
        "developer": "Developer",
        "regulator": "Regulator",
        "affected_community": "Affected Community",
    }
    return mapping.get(value, value)


def _render_kpi_strip(cards: list[dict[str, str]]) -> None:
    if not cards:
        return
    st.markdown('<div class="medf-kpi-strip">', unsafe_allow_html=True)
    columns = st.columns(len(cards))
    for index, card in enumerate(cards):
        icon = escape(safe_str(card.get("icon", "•")))
        label = escape(safe_str(card.get("label", "")).upper())
        value = escape(safe_str(card.get("value", "N/A.")))
        note = escape(safe_str(card.get("note", "")))
        color = escape(safe_str(card.get("color", SEM_INFO_HEX)))
        columns[index].markdown(
            f"""
<div class="medf-kpi-card" style="--kpi-accent:{color};">
    <div>{icon}</div>
    <div class="medf-kpi-value">{value}</div>
    <div class="medf-kpi-label">{label}</div>
    <div class="medf-kpi-note">{note}</div>
</div>
""",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


def _assert_ui_contract(
    *,
    kpi_cards: list[dict[str, str]],
    themed_figures: list[go.Figure] | None = None,
    parcoords_figure: go.Figure | None = None,
    pareto_weights: dict[str, float] | None = None,
    enforce_pareto_weights_sum_to_one: bool = False,
) -> None:
    if not kpi_cards:
        raise AssertionError("KPI strip must render at least one card.")
    for index, card in enumerate(kpi_cards):
        value = safe_str(card.get("value")).strip()
        if not value:
            raise AssertionError(f"KPI card {index} rendered an empty value.")

    for figure in themed_figures or []:
        figure_json = figure.to_plotly_json()
        layout = figure_json.get("layout", {})
        meta = layout.get("meta", {}) if isinstance(layout, dict) else {}
        if not isinstance(meta, dict) or meta.get("medf_plot_theme_applied") is not True:
            raise AssertionError("Plotly figures must be routed through apply_plot_theme(fig).")

    if parcoords_figure is not None:
        _assert_tradeoff_parcoords_theme(parcoords_figure)
        figure_json = parcoords_figure.to_plotly_json()
        data = figure_json.get("data", [])
        if not data or data[0].get("type") != "parcoords":
            raise AssertionError("UI contract expected a parcoords figure.")
        for index, dimension in enumerate(data[0].get("dimensions", [])):
            tickfont = dimension.get("tickfont", {})
            if not isinstance(tickfont, dict) or tickfont.get("color") != PARCOORDS_TICKFONT_HEX:
                raise AssertionError(
                    f"Parcoords dimension {index} tickfont color must remain {PARCOORDS_TICKFONT_HEX}."
                )

    if pareto_weights is not None:
        if not isinstance(pareto_weights, dict) or not pareto_weights:
            raise AssertionError("Pareto weights vector must be non-empty.")
        weight_sum = 0.0
        for dimension, raw_value in pareto_weights.items():
            try:
                value = float(raw_value)
            except (TypeError, ValueError) as exc:
                raise AssertionError(f"Pareto weight for '{dimension}' must be numeric.") from exc
            if not math.isfinite(value):
                raise AssertionError(f"Pareto weight for '{dimension}' must be finite.")
            weight_sum += value
        if enforce_pareto_weights_sum_to_one and abs(weight_sum - 1.0) > 1e-6:
            raise AssertionError(
                f"Pareto weights must sum to 1.0 (±1e-6); got {weight_sum:.10f}."
            )


def _sync_pareto_controls_from_preset(selected_preset: str) -> None:
    preset = PARETO_PRESETS.get(selected_preset, PARETO_PRESETS["Standard"])
    last_preset = st.session_state.get(
        "last_pareto_preset",
        st.session_state.get("pareto_preset_applied"),
    )
    if last_preset == selected_preset:
        return
    st.session_state["pareto_options_to_show"] = int(preset["n_solutions"])
    st.session_state["pareto_search_breadth"] = int(preset["pop_size"])
    st.session_state["pareto_search_depth"] = int(preset["n_gen"])
    st.session_state["last_pareto_preset"] = selected_preset


def _risk_label(score: float) -> tuple[str, str]:
    if score >= 0.8:
        return "LOW", SEM_SUCCESS_HEX
    if score >= 0.6:
        return "MODERATE", SEM_WARNING_HEX
    if score >= 0.4:
        return "HIGH", SEM_DANGER_HEX
    return "CRITICAL", SEM_DANGER_HEX


def _apply_dimension_preset(preset: dict[str, float]) -> None:
    for dimension, score in preset.items():
        st.session_state[f"score_{dimension}"] = float(score)


class APICallError(Exception):
    def __init__(self, error_text: str, data: Any = None):
        super().__init__(error_text)
        self.error_text = error_text
        self.data = data


def api_call(method: str, url: str, payload: Any = None, timeout: int = 30) -> tuple[bool, Any, str]:
    try:
        response = requests.request(
            method=method.upper(),
            url=url,
            json=payload if payload is not None else None,
            timeout=timeout,
        )
    except Exception as exc:
        return False, None, f"Request failed: {exc}"

    try:
        data: Any = response.json()
    except ValueError:
        data = response.text

    if response.status_code != 200:
        detail = ""
        if isinstance(data, dict):
            raw_detail = data.get("detail")
            if raw_detail is not None:
                detail = str(raw_detail)
        elif isinstance(data, str):
            detail = data.strip()
        detail_suffix = f" {detail}" if detail else ""
        return (
            False,
            data,
            f"{method.upper()} request failed with status {response.status_code}.{detail_suffix}".strip(),
        )

    return True, data, ""


def _format_debug_payload(value: Any) -> str:
    safe_value = _safe_json(value)
    if isinstance(safe_value, (dict, list)):
        return json.dumps(safe_value, indent=2, sort_keys=True)
    return str(safe_value)


def show_api_error(context: str, error_text: str, data: Any) -> None:
    st.error(f"{context}: {error_text}")
    if data is None:
        return
    with st.expander("API error details"):
        st.code(_format_debug_payload(data), language="json")


@st.cache_data(show_spinner=False, ttl=60)
def load_frameworks(backend_url: str) -> list[dict[str, Any]]:
    ok, payload, error_text = api_call("GET", f"{backend_url}/api/frameworks", timeout=15)
    if not ok:
        raise APICallError(error_text, payload)
    if not isinstance(payload, list):
        raise APICallError("Unexpected /api/frameworks response shape.", payload)
    return payload


@st.cache_data(show_spinner=False, ttl=60)
def load_stakeholders(backend_url: str) -> list[dict[str, Any]]:
    ok, payload, error_text = api_call("GET", f"{backend_url}/api/stakeholders", timeout=15)
    if not ok:
        raise APICallError(error_text, payload)
    if not isinstance(payload, list):
        raise APICallError("Unexpected /api/stakeholders response shape.", payload)
    return payload


def _safe_json(value: Any) -> Any:
    try:
        return json.loads(json.dumps(value, default=str))
    except Exception:
        return str(value)


def safe_str(x: Any) -> str:
    return "" if x is None else str(x)


_DISPLAY_MINUS_PATTERN = re.compile(r"(?<!\w)-(?=\d)")


def fmt_minus(s: str) -> str:
    text = safe_str(s).replace("–", UNICODE_MINUS)
    return _DISPLAY_MINUS_PATTERN.sub(UNICODE_MINUS, text)


def _format_sentence_like_bullet(text: Any) -> str:
    cleaned = safe_str(text).strip()
    if not cleaned:
        return ""
    if cleaned.startswith(("http://", "https://")):
        return cleaned
    if cleaned.endswith((".", "!", "?", ":", ";")):
        return cleaned
    if " " in cleaned and any(character.isalpha() for character in cleaned):
        return f"{cleaned}."
    return cleaned


def render_if_present(label: str, value: Any) -> None:
    text = safe_str(value).strip()
    if not text or text.lower() == "undefined":
        return

    if label:
        period_labels = {
            "Framework",
            "Stakeholder",
            "Scoring Method",
            "Framework Weighting Mode",
        }
        if label in period_labels:
            st.caption(f"{label}: {text.rstrip('.')}.")
        else:
            st.caption(f"{label}: {text}")
    else:
        st.caption(text)


def fmt_score(x: Any) -> str:
    if x is None:
        return "N/A"
    try:
        return fmt_minus(f"{float(x):.4f}")
    except (TypeError, ValueError):
        return "N/A"


def fmt_small(x: Any) -> str:
    if x is None:
        return "N/A"
    try:
        return fmt_minus(f"{float(x):.3f}")
    except (TypeError, ValueError):
        return "N/A"


def _round_to_multiple(value: float, multiple: int) -> int:
    if multiple <= 0:
        raise ValueError("multiple must be positive.")
    return int(round(float(value) / multiple) * multiple)


def _clamp_int(value: int, min_value: int, max_value: int) -> int:
    return max(min_value, min(max_value, int(value)))


def _normalize_pareto_mode(value: Any) -> str:
    text = safe_str(value).strip().lower()
    if text in {"auto", "automatic (recommended)", "auto (recommended)"}:
        return "auto"
    if text in {"manual", "manual (advanced)"}:
        return "manual"
    return "auto"


def _derive_auto_pareto_search_params(budget: int, bias: int) -> tuple[int, int]:
    explore_weight = float(bias) / 100.0
    p_raw = 40 + (140 - 40) * explore_weight
    population = _clamp_int(_round_to_multiple(p_raw, 5), 20, 150)

    generations = math.floor(int(budget) / max(population, 1))
    generations = _clamp_int(_round_to_multiple(generations, 5), 20, 200)

    while population * generations > int(budget) and generations > 20:
        generations -= 5

    if generations == 200 and population * generations <= int(budget):
        while population < 150 and (population + 5) * generations <= int(budget):
            population += 5

    while population * generations > int(budget) and generations > 20:
        generations -= 5

    return population, generations


def _extract_framework_weighting_mode(notes: Any) -> str | None:
    if not isinstance(notes, str):
        return None
    marker = "framework_weighting="
    if marker not in notes:
        return None
    return notes.split(marker, 1)[1].strip().split()[0]


def _extract_run_id_from_responses(responses: dict[str, Any]) -> str:
    for response in responses.values():
        if not isinstance(response, dict):
            continue
        metadata = response.get("metadata")
        if isinstance(metadata, dict) and isinstance(metadata.get("run_id"), str):
            return metadata["run_id"]
        notes = response.get("notes")
        if isinstance(notes, str) and "run_id=" in notes:
            return notes.split("run_id=", 1)[1].strip().split()[0]
    return str(uuid4())


def _update_last_run_bundle(
    *,
    page_name: str,
    backend_url: str,
    requests_payloads: dict[str, Any],
    responses_payloads: dict[str, Any],
    ui_context: dict[str, Any],
) -> dict[str, Any]:
    run_id = _extract_run_id_from_responses(responses_payloads)
    bundle = {
        "run_id": run_id,
        "timestamp_utc": datetime.utcnow().isoformat() + "Z",
        "backend_url": backend_url,
        "page_name": page_name,
        "requests": _safe_json(requests_payloads),
        "responses": _safe_json(responses_payloads),
        "ui_context": _safe_json(ui_context),
    }
    st.session_state["last_run_bundle"] = bundle
    return bundle


def _write_ui_run_log(
    *,
    run_id: str,
    page_name: str,
    case_name: str,
    payload: dict[str, Any],
) -> None:
    try:
        ui_dir = Path("data") / "ui_runs"
        ui_dir.mkdir(parents=True, exist_ok=True)
        safe_page = page_name.lower().replace(" ", "_")
        safe_case = case_name.lower().replace(" ", "_")
        file_path = ui_dir / f"{run_id}_{safe_page}_{safe_case}.json"
        file_path.write_text(json.dumps(_safe_json(payload), indent=2, sort_keys=True), encoding="utf-8")
    except Exception:
        return


def _build_bundle_zip(bundle: dict[str, Any]) -> bytes:
    in_memory = io.BytesIO()
    requests_payloads = bundle.get("requests", {}) if isinstance(bundle.get("requests"), dict) else {}
    responses_payloads = bundle.get("responses", {}) if isinstance(bundle.get("responses"), dict) else {}

    with zipfile.ZipFile(in_memory, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        manifest = {
            "run_id": bundle.get("run_id"),
            "timestamp_utc": bundle.get("timestamp_utc"),
            "backend_url": bundle.get("backend_url"),
            "page_name": bundle.get("page_name"),
            "app_version": "unknown",
        }
        archive.writestr("manifest.json", json.dumps(_safe_json(manifest), indent=2, sort_keys=True))

        file_map = (
            ("evaluate_request.json", requests_payloads.get("evaluate")),
            ("evaluate_response.json", responses_payloads.get("evaluate")),
            ("conflicts_request.json", requests_payloads.get("conflicts")),
            ("conflicts_response.json", responses_payloads.get("conflicts")),
            ("pareto_request.json", requests_payloads.get("pareto")),
            ("pareto_response.json", responses_payloads.get("pareto")),
        )
        for filename, data in file_map:
            if data is not None:
                archive.writestr(filename, json.dumps(_safe_json(data), indent=2, sort_keys=True))

        archive.writestr(
            "ui_context.json",
            json.dumps(_safe_json(bundle.get("ui_context", {})), indent=2, sort_keys=True),
        )

    return in_memory.getvalue()


def _render_bundle_export() -> None:
    bundle = st.session_state.get("last_run_bundle")
    if not isinstance(bundle, dict):
        return

    run_id = str(bundle.get("run_id", "unknown"))
    zip_bytes = _build_bundle_zip(bundle)
    st.download_button(
        "Export Full Analysis Bundle (ZIP)",
        data=zip_bytes,
        file_name=f"medf_bundle_{run_id}.zip",
        mime="application/zip",
        key=f"bundle_export_{run_id}",
    )


def _build_radar_chart(
    values_by_dimension: dict[str, float],
    *,
    title: str,
    radial_max: float = 1.0,
) -> go.Figure:
    radar_labels = [DIMENSION_DISPLAY_NAMES[dimension] for dimension in UNIFIED_DIMENSIONS]
    radar_values = [float(values_by_dimension.get(dimension, 0.0)) for dimension in UNIFIED_DIMENSIONS]
    radar_labels_closed = radar_labels + [radar_labels[0]]
    radar_values_closed = radar_values + [radar_values[0]]
    title_text = safe_str(title).strip()
    if title_text.lower() == "undefined":
        title_text = ""

    figure = go.Figure()
    figure.add_trace(
        go.Scatterpolar(
            r=radar_values_closed,
            theta=radar_labels_closed,
            fill="toself",
            name=title_text,
            line={"color": BRAND_BLUE_HEX, "width": 2},
            fillcolor=BRAND_BLUE_FILL_RGBA,
        )
    )
    figure.update_layout(
        title_text=title_text,
        polar={"radialaxis": {"visible": True, "range": [0, radial_max]}},
        showlegend=False,
        height=460,
        margin={"l": 52, "r": 52, "t": 62, "b": 52},
    )
    return figure


def _build_correlation_heatmap(
    matrix: dict[str, dict[str, float]],
    *,
    labels: list[str],
    title: str,
) -> go.Figure:
    z_values = [
        [float(matrix.get(row, {}).get(col, 0.0)) for col in labels]
        for row in labels
    ]
    z_text = [[fmt_minus(f"{value:.2f}") for value in row] for row in z_values]

    figure = go.Figure(
        data=go.Heatmap(
            z=z_values,
            text=z_text,
            texttemplate="%{text}",
            x=labels,
            y=labels,
            zmin=-1,
            zmax=1,
            colorscale="RdBu",
            colorbar={"title": "rho"},
        )
    )
    figure.update_layout(
        title=title,
        margin={"l": 52, "r": 52, "t": 62, "b": 52},
    )
    return figure


def main() -> None:
    st.set_page_config(page_title="MEDF Governance Platform", layout="wide")
    tokens = _ui_tokens(_get_theme_base())
    inject_css(tokens)
    # Root cause: the toggle was not key-bound and was mirrored manually, which created two
    # competing state paths and occasional one-rerun-late visibility updates.
    st.session_state.setdefault("conference_mode", False)
    _render_institutional_header()

    if "demo_mode" not in st.session_state:
        st.session_state["demo_mode"] = False
    if "demo_scenario_results" not in st.session_state:
        st.session_state["demo_scenario_results"] = {}
    if "pareto_result" not in st.session_state:
        st.session_state["pareto_result"] = None
    if "pareto_result_stakeholder_ids" not in st.session_state:
        st.session_state["pareto_result_stakeholder_ids"] = []
    if "last_evaluate_result" not in st.session_state:
        st.session_state["last_evaluate_result"] = None
    if "last_conflict_result" not in st.session_state:
        st.session_state["last_conflict_result"] = None

    st.markdown('<div class="medf-page-nav">', unsafe_allow_html=True)
    page = st.radio(
        "Page",
        ["Evaluate", "Conflict Detection", "Pareto Resolution", "Case Studies"],
        index=0,
        horizontal=True,
        label_visibility="collapsed",
    )
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown(f"# {page}")

    executive_kpis = _build_executive_kpis()
    _render_kpi_strip(executive_kpis)
    _assert_ui_contract(kpi_cards=executive_kpis)

    _render_bundle_export()

    with st.expander("Methodology Summary", expanded=False):
        st.markdown("### 1. Unified Six-Dimension Ontology")
        st.markdown(
            """
- Transparency and Explainability.
- Fairness and Non-Discrimination.
- Safety and Robustness.
- Privacy and Data Governance.
- Human Agency and Oversight.
- Accountability.
"""
        )

        st.markdown("---")
        st.markdown("### 2. Framework-Derived Prior")
        st.markdown(
            "Framework weights are derived from internal structure "
            "(e.g., requirements, subcategories, principles) mapped to the unified dimensions."
        )
        st.latex(r"w^{fw}_i = \frac{c_i}{\sum_{j=1}^{6} c_j}")
        st.markdown("where $c_i$ is the framework coverage count for dimension $i$.")

        st.markdown("---")
        st.markdown("### 3. Stakeholder Preference Modeling")
        st.markdown(
            "Each stakeholder provides a preference vector over the same six dimensions."
        )
        st.latex(r"\tilde{w}_i = w^{stake}_i \times w^{fw}_i")
        st.latex(r"w^{eff}_i = \frac{\tilde{w}_i}{\sum_{j=1}^{6} \tilde{w}_j}")

        st.markdown("---")
        st.markdown("### 4. Scoring Methods")
        st.markdown(
            """
- TOPSIS (Technique for Order Preference by Similarity to Ideal Solution).
- Weighted Sum Model (WSM).
"""
        )

        st.markdown("---")
        st.markdown("### 5. Conflict Detection")
        st.markdown(
            """
- Priority Conflict (Weights-Only) compares stakeholder priorities directly.
- System-Salience Conflict (Contribution-Based) compares stakeholder rankings after accounting for system performance.
- Contribution (Contrib) is the stakeholder-weighted impact of each dimension for the selected AI system.
"""
        )
        st.latex(r"\text{contrib}_i = \hat{x}_i \times w^{stake}_i")
        st.markdown("where $\\hat{x}_i$ is the normalized system score on dimension $i$.")

        st.markdown("---")
        st.markdown("### 6. Pareto Frontier")
        st.markdown("Multi-stakeholder trade-offs are summarized using Pareto dominance.")
        st.markdown("- Only non-dominated solutions are retained on the Pareto frontier.")

    conference_mode = st.session_state["conference_mode"]

    with st.sidebar:
        st.header("Configuration")
        conference_mode = st.toggle(
            "Conference Mode",
            key="conference_mode",
            help="Prioritize executive visuals and preset controls.",
        )
        st.caption("Conference Mode prioritizes primary outputs.")

        st.markdown("**Backend URL**")
        backend_url = st.text_input("Backend URL", value="http://127.0.0.1:8000").rstrip("/")

        frameworks: list[dict[str, Any]] = []
        stakeholders: list[dict[str, Any]] = []
        with st.spinner("Loading frameworks and stakeholders..."):
            try:
                frameworks = load_frameworks(backend_url)
                stakeholders = load_stakeholders(backend_url)
            except APICallError as exc:
                show_api_error("Failed to load backend data", exc.error_text, exc.data)
            except Exception as exc:
                st.error(f"Failed to load backend data: {exc}")

        framework_id = ""
        framework_label = ""
        stakeholder_id = ""
        scoring_method = "topsis"
        conflict_metric = "Priority Conflict (Weights-Only)"
        detect_clicked = False
        screenshot_mode = False
        selected_stakeholder: dict[str, Any] | None = None
        conflict_stakeholder_ids: list[str] = []
        pareto_stakeholder_ids: list[str] = []
        pareto_n_solutions = 25
        pareto_pop_size = 80
        pareto_n_gen = 80
        pareto_n_gen_effective = pareto_n_gen
        generate_pareto_clicked = False
        case_screenshot_mode = False

        framework_options = {
            f"{item.get('name', item.get('id', 'unknown'))} ({item.get('id', 'unknown')})": item
            for item in frameworks
            if isinstance(item, dict)
        }
        if framework_options:
            st.markdown("**Framework**")
            framework_label = st.selectbox("Framework", list(framework_options.keys()))
            framework_id = str(framework_options[framework_label].get("id", ""))
        else:
            st.warning("No frameworks available from backend.")

        st.markdown("**Demo**")
        if st.button("Run Demo Scenario"):
            st.session_state["demo_mode"] = True

        stakeholder_options = {
            f"{item.get('name', item.get('id', 'unknown'))} ({item.get('id', 'unknown')})": item
            for item in stakeholders
            if isinstance(item, dict)
        }
        stakeholder_labels_by_id = {
            str(item.get("id", "")): label
            for label, item in stakeholder_options.items()
        }

        weights_for_request: dict[str, float] = {
            dimension: 1.0 / len(UNIFIED_DIMENSIONS)
            for dimension in UNIFIED_DIMENSIONS
        }

        if page == "Evaluate":
            st.markdown("**Method**")
            scoring_method = st.radio("Scoring method", ["topsis", "wsm"], horizontal=True)

            st.markdown("**Stakeholders**")
            if stakeholder_options:
                stakeholder_label = st.selectbox("Stakeholder", list(stakeholder_options.keys()))
                selected_stakeholder = stakeholder_options[stakeholder_label]
                stakeholder_id = str(selected_stakeholder.get("id", ""))
            else:
                st.warning("No stakeholders available from backend.")

            base_weights: dict[str, float] = {}
            if selected_stakeholder and isinstance(selected_stakeholder.get("weights"), dict):
                raw_weights = selected_stakeholder["weights"]
                base_weights = {
                    dimension: float(raw_weights.get(dimension, 0.0))
                    for dimension in UNIFIED_DIMENSIONS
                }
            else:
                base_weights = {
                    dimension: 1.0 / len(UNIFIED_DIMENSIONS)
                    for dimension in UNIFIED_DIMENSIONS
                }

            override_weights = st.checkbox("Override stakeholder weights", value=False)
            weights_for_request = dict(base_weights)
            if override_weights:
                st.caption("Custom weights (auto-normalized before submission)")
                raw_custom: dict[str, float] = {}
                for dimension in UNIFIED_DIMENSIONS:
                    raw_custom[dimension] = st.slider(
                        f"{DIMENSION_DISPLAY_NAMES[dimension]} weight",
                        min_value=0.0,
                        max_value=1.0,
                        value=float(base_weights.get(dimension, 0.0)),
                        step=0.01,
                        key=f"weight_{dimension}",
                    )
                raw_sum = float(sum(raw_custom.values()))
                if raw_sum > 0.0:
                    weights_for_request = {
                        dimension: float(value / raw_sum)
                        for dimension, value in raw_custom.items()
                    }
                    st.caption(
                        f"Raw sum: {raw_sum:.4f} | Normalized sum: {sum(weights_for_request.values()):.4f}"
                    )
                else:
                    st.error("Weight sum cannot be zero.")
                    weights_for_request = {}
            else:
                st.caption(f"Using stakeholder default weights (sum: {sum(base_weights.values()):.4f})")
        elif page == "Conflict Detection":
            st.markdown("**Stakeholders**")
            if stakeholder_options:
                labels = list(stakeholder_options.keys())
                default_ids = ["developer", "regulator", "affected_community"]
                default_labels = [
                    stakeholder_labels_by_id[stakeholder_id]
                    for stakeholder_id in default_ids
                    if stakeholder_id in stakeholder_labels_by_id
                ]
                if not default_labels:
                    default_labels = labels[:2]
                selected_labels = st.multiselect(
                    "Stakeholders (2–3)",
                    labels,
                    default=default_labels,
                    max_selections=3,
                )
                conflict_stakeholder_ids = [
                    str(stakeholder_options[label].get("id", ""))
                    for label in selected_labels
                ]
            else:
                st.warning("No stakeholders available from backend.")
            st.markdown("**Method**")
            conflict_metric = st.radio(
                "Conflict metric",
                [
                    "Priority Conflict (Weights-Only)",
                    "System-Salience Conflict (Contribution-Based)",
                ],
                index=0,
            )
            st.caption(
                "Contribution (Contrib) is the stakeholder-weighted impact of a dimension for the selected AI system: "
                "contrib_i = normalized_score_i × stakeholder_weight_i. "
                "System-Salience Conflict compares stakeholders after accounting for system performance, "
                "not only stated priorities."
            )
            st.markdown("**Display**")
            screenshot_mode = st.checkbox("Screenshot mode", value=False)
            detect_clicked = st.button("Detect Conflicts", type="primary")
        elif page == "Pareto Resolution":
            st.markdown("**Stakeholders**")
            if stakeholder_options:
                labels = list(stakeholder_options.keys())
                default_ids = ["developer", "regulator", "affected_community"]
                default_labels = [
                    stakeholder_labels_by_id[stakeholder_id]
                    for stakeholder_id in default_ids
                    if stakeholder_id in stakeholder_labels_by_id
                ]
                if not default_labels:
                    default_labels = labels[:2]
                selected_labels = st.multiselect(
                    "Stakeholders",
                    labels,
                    default=default_labels,
                )
                pareto_stakeholder_ids = [
                    str(stakeholder_options[label].get("id", ""))
                    for label in selected_labels
                ]
            else:
                st.warning("No stakeholders available from backend.")

            st.markdown("**Presets**")
            pareto_preset = st.radio(
                "Search profile",
                list(PARETO_PRESETS.keys()),
                horizontal=True,
                key="pareto_preset_choice",
            )
            _sync_pareto_controls_from_preset(pareto_preset)
            preset_values = PARETO_PRESETS.get(pareto_preset, PARETO_PRESETS["Standard"])
            if pareto_preset == "Standard":
                st.caption("Standard balances runtime and coverage.")
            else:
                st.caption("Thorough increases search depth for higher exploration.")

            pareto_n_solutions = int(
                st.session_state.get("pareto_options_to_show", preset_values["n_solutions"])
            )
            pareto_pop_size = int(
                st.session_state.get("pareto_search_breadth", preset_values["pop_size"])
            )
            pareto_n_gen = int(
                st.session_state.get("pareto_search_depth", preset_values["n_gen"])
            )
            pareto_search_mode = _normalize_pareto_mode(st.session_state.get("pareto_search_mode", "auto"))
            st.session_state["pareto_search_mode"] = pareto_search_mode
            pareto_search_mode_label = (
                "Automatic (Recommended)"
                if pareto_search_mode == "auto"
                else "Manual (Advanced)"
            )
            pareto_compute_budget = int(st.session_state.get("pareto_compute_budget", 10_000))
            pareto_explore_bias = int(st.session_state.get("pareto_explore_bias", 60))
            pareto_n_gen_effective = pareto_n_gen

            with st.expander("Advanced Settings", expanded=False):
                if conference_mode:
                    st.caption("Advanced settings are hidden while Conference Mode is enabled.")
                    st.caption(
                        "Current values in use: "
                        f"options={pareto_n_solutions}, mode={pareto_search_mode_label}, "
                        f"breadth={pareto_pop_size}, depth={pareto_n_gen}."
                    )
                else:
                    pareto_n_solutions = st.slider(
                        "Pareto Solutions Displayed",
                        min_value=5,
                        max_value=50,
                        value=_clamp_int(
                            int(st.session_state.get("pareto_options_to_show", pareto_n_solutions)),
                            5,
                            50,
                        ),
                        step=1,
                        help="Number of non-dominated trade-off solutions shown in the UI.",
                        key="pareto_options_to_show",
                    )
                    pareto_search_mode = st.radio(
                        "Search Mode",
                        ["auto", "manual"],
                        format_func=lambda mode: (
                            "Automatic (Recommended)" if mode == "auto" else "Manual (Advanced)"
                        ),
                        horizontal=True,
                        key="pareto_search_mode",
                    )
                    if pareto_search_mode == "auto":
                        pareto_compute_budget = st.slider(
                            "Compute Budget (evaluations)",
                            min_value=2_000,
                            max_value=30_000,
                            value=_clamp_int(
                                int(st.session_state.get("pareto_compute_budget", pareto_compute_budget)),
                                2_000,
                                30_000,
                            ),
                            step=500,
                            key="pareto_compute_budget",
                        )
                        pareto_explore_bias = st.slider(
                            "Explore vs. Refine",
                            min_value=0,
                            max_value=100,
                            value=_clamp_int(
                                int(st.session_state.get("pareto_explore_bias", pareto_explore_bias)),
                                0,
                                100,
                            ),
                            step=1,
                            key="pareto_explore_bias",
                        )
                    else:
                        pareto_pop_size = st.slider(
                            "Search Breadth (Population)",
                            min_value=20,
                            max_value=150,
                            value=_clamp_int(
                                int(st.session_state.get("pareto_search_breadth", pareto_pop_size)),
                                20,
                                150,
                            ),
                            step=1,
                            key="pareto_search_breadth",
                        )
                        pareto_n_gen = st.slider(
                            "Search Depth (Generations)",
                            min_value=20,
                            max_value=200,
                            value=_clamp_int(
                                int(st.session_state.get("pareto_search_depth", pareto_n_gen)),
                                20,
                                200,
                            ),
                            step=1,
                            key="pareto_search_depth",
                        )

            pareto_n_solutions = _clamp_int(
                int(st.session_state.get("pareto_options_to_show", pareto_n_solutions)),
                5,
                50,
            )
            pareto_pop_size = _clamp_int(
                int(st.session_state.get("pareto_search_breadth", pareto_pop_size)),
                20,
                150,
            )
            pareto_n_gen = _clamp_int(
                int(st.session_state.get("pareto_search_depth", pareto_n_gen)),
                20,
                200,
            )
            pareto_search_mode = _normalize_pareto_mode(
                st.session_state.get("pareto_search_mode", pareto_search_mode)
            )
            pareto_compute_budget = _clamp_int(
                int(st.session_state.get("pareto_compute_budget", pareto_compute_budget)),
                2_000,
                30_000,
            )
            pareto_explore_bias = _clamp_int(
                int(st.session_state.get("pareto_explore_bias", pareto_explore_bias)),
                0,
                100,
            )

            if pareto_search_mode == "auto":
                pareto_pop_size, pareto_n_gen_effective = _derive_auto_pareto_search_params(
                    pareto_compute_budget,
                    pareto_explore_bias,
                )
                st.caption(f"Computed Population: {pareto_pop_size}.")
                st.caption(f"Computed Generations: {pareto_n_gen_effective}.")
                st.caption(f"Estimated evaluations = {pareto_pop_size * pareto_n_gen_effective}.")
            else:
                entered_pop_size = pareto_pop_size
                entered_n_gen = pareto_n_gen
                pareto_n_gen_effective = entered_n_gen
                while entered_pop_size * pareto_n_gen_effective > HARD_CAP_EVALS and pareto_n_gen_effective > 20:
                    pareto_n_gen_effective -= 5
                if pareto_n_gen_effective != entered_n_gen:
                    st.warning(
                        "Manual search exceeded the evaluation cap; generations were adjusted to remain within limit."
                    )
                    st.caption(f"Entered: p={entered_pop_size}, g={entered_n_gen}.")
                    st.caption(f"Effective: p={entered_pop_size}, g={pareto_n_gen_effective}.")
                st.caption(f"Estimated evaluations = {entered_pop_size * pareto_n_gen_effective}.")

            if len(pareto_stakeholder_ids) < 2:
                st.warning("Select at least 2 stakeholders to enable Pareto generation.")
            generate_pareto_clicked = st.button(
                "Generate Pareto Solutions",
                type="primary",
                disabled=len(pareto_stakeholder_ids) < 2,
            )
        else:
            st.markdown("**Display**")
            case_screenshot_mode = st.checkbox("Screenshot Mode", value=False)
            st.caption("Case Studies runs fixed scenarios through Evaluate → Conflicts → Pareto.")

    demo_active = bool(st.session_state.get("demo_mode"))
    ai_system_id = "demo_facerec"
    ai_system_name = "Demo Facial Recognition System"
    ai_system_description = "MVP evaluation input"
    if demo_active:
        ai_system_id = "demo_hiring_screening_system"
        ai_system_name = str(DEMO_SCENARIO_NAME)
        ai_system_description = str(DEMO_SCENARIO_DESCRIPTION)
        for dimension, value in DEMO_DIMENSION_SCORES.items():
            st.session_state[f"score_{dimension}"] = float(value)
    dimension_scores: dict[str, float] = {
        dimension: float(value)
        for dimension, value in PRESET_BASELINE.items()
    }

    if page != "Case Studies":
        input_card = st.container(border=True)
        with input_card:
            col_left, col_right = st.columns([1, 1])
            with col_left:
                ai_system_id = st.text_input("AI system id", value=ai_system_id)
                ai_system_name = st.text_input("AI system name", value=ai_system_name)
                ai_system_description = st.text_area("AI system description", value=ai_system_description)

            with col_right:
                st.subheader("Dimension Scores (Likert 1–7)")
                st.markdown(
                    f"""
<style>
.medf-likert-row {{ position: relative; margin-top: 2px; margin-bottom: -10px; }}
.medf-likert-rail {{
  height: 4px;
  border-radius: 999px;
  background: rgba(255,255,255,0.12);
  overflow: hidden;
}}
.medf-likert-fill {{
  height: 100%;
  border-radius: 999px;
  background: {BRAND_BLUE_HEX};
}}
</style>
""",
                    unsafe_allow_html=True,
                )
                if page in {"Conflict Detection", "Pareto Resolution"}:
                    preset_col_1, preset_col_2, preset_col_3 = st.columns(3)
                    if preset_col_1.button("Preset: Baseline (3.5,3.0,5.5,4.5,3.5,5.0)"):
                        _apply_dimension_preset(PRESET_BASELINE)
                    if preset_col_2.button("Preset: Flipped (4.5,5.0,2.5,3.5,4.5,3.0)"):
                        _apply_dimension_preset(PRESET_FLIPPED)
                    if preset_col_3.button("Preset: Safety-heavy (4.0,4.0,7.0,4.0,4.0,4.0)"):
                        _apply_dimension_preset(PRESET_SAFETY_HEAVY)

                default_scores = PRESET_BASELINE
                for dimension in UNIFIED_DIMENSIONS:
                    session_key = f"score_{dimension}"
                    if session_key not in st.session_state:
                        st.session_state[session_key] = float(default_scores[dimension])
                for dimension in UNIFIED_DIMENSIONS:
                    slider_col, badge_col = st.columns([0.86, 0.14])
                    with slider_col:
                        current_value = float(st.session_state[f"score_{dimension}"])
                        norm = (current_value - LIKERT_MIN) / (LIKERT_MAX - LIKERT_MIN)
                        pct = int(round(max(0.0, min(1.0, norm)) * 100))
                        st.markdown(
                            f"""
<div class="medf-likert-row">
  <div class="medf-likert-rail">
    <div class="medf-likert-fill" style="width: {pct}%;"></div>
  </div>
</div>
""",
                            unsafe_allow_html=True,
                        )
                        dimension_scores[dimension] = float(
                            st.slider(
                                DIMENSION_DISPLAY_NAMES[dimension],
                                min_value=LIKERT_MIN,
                                max_value=LIKERT_MAX,
                                value=current_value,
                                step=0.1,
                                format="%.1f",
                                key=f"score_{dimension}",
                            )
                        )
                    with badge_col:
                        st.markdown(
                            f"""
<div style="
  display:inline-block;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(56,189,248,0.15);
  border: 1px solid rgba(56,189,248,0.55);
  color: {BRAND_BLUE_HEX};
  font-weight: 700;
  text-align: center;
  min-width: 56px;
">
  {dimension_scores[dimension]:.1f}
</div>
""",
                            unsafe_allow_html=True,
                        )
    else:
        if not case_screenshot_mode:
            selected_framework_text = framework_id or "N/A"
            if framework_label:
                selected_framework_text = f"{framework_label} [{framework_id}]"
            st.caption(
                f"Selected framework: {selected_framework_text} | "
                "Fixed stakeholders: developer, regulator, affected_community"
            )

    if demo_active and stakeholder_id in DEMO_WEIGHTS:
        weights_for_request = {
            dimension: float(DEMO_WEIGHTS[stakeholder_id][dimension])
            for dimension in UNIFIED_DIMENSIONS
        }

    if page == "Evaluate":
        evaluate_clicked = st.button("Evaluate", type="primary")

        if evaluate_clicked:
            if not framework_id:
                st.error("Please select a framework.")
                return
            if not stakeholder_id:
                st.error("Please select a stakeholder.")
                return
            if not weights_for_request:
                st.error("Weights are invalid. Please adjust and try again.")
                return

            payload = {
                "ai_system": {
                    "id": ai_system_id,
                    "name": ai_system_name,
                    "description": ai_system_description,
                    "context": {"dimension_scores": dimension_scores},
                },
                "framework_ids": [framework_id],
                "stakeholder_ids": [stakeholder_id],
                "weights": {stakeholder_id: weights_for_request},
                "scoring_method": scoring_method,
            }

            with st.spinner("Evaluating..."):
                ok, result, error_text = api_call(
                    "POST",
                    f"{backend_url}/api/evaluate",
                    payload=payload,
                    timeout=30,
                )

            if not ok:
                show_api_error("Evaluation failed", error_text, result)
                return
            _update_last_run_bundle(
                page_name="Evaluate",
                backend_url=backend_url,
                requests_payloads={"evaluate": payload},
                responses_payloads={"evaluate": result},
                ui_context={
                    "page": page,
                    "framework_id": framework_id,
                    "stakeholder_ids": [stakeholder_id],
                    "scoring_method": scoring_method,
                },
            )
            st.session_state["last_evaluate_result"] = result
            overall_score = float(result.get("overall_score", 0.0))
            label, color = _risk_label(overall_score)
            framework_weighting_mode = _extract_framework_weighting_mode(result.get("notes"))

            evaluate_results_card = st.container(border=True)
            with evaluate_results_card:
                st.markdown("## Primary Visualization")
                st.caption("Executive summary of the current evaluation run.")
                metric_col, label_col = st.columns([1, 2])
                with metric_col:
                    st.metric("Overall Ethical Score", fmt_score(overall_score))
                with label_col:
                    st.markdown(
                        f"<span style='color:{color};font-size:1.1rem;font-weight:600;'>Conflict posture: {label}</span>",
                        unsafe_allow_html=True,
                    )

                framework_scores = result.get("framework_scores", [])
                if not framework_scores:
                    st.warning("No framework scores returned.")
                    return

                first_framework = framework_scores[0]
                dim_scores = first_framework.get("dimension_scores", {})
                framework_trace_name = safe_str(first_framework.get("framework_id", "framework")).strip()
                if framework_trace_name.lower() == "undefined":
                    framework_trace_name = ""
                radar_labels = [DIMENSION_DISPLAY_NAMES[dimension] for dimension in UNIFIED_DIMENSIONS]
                radar_values = [float(dim_scores.get(dimension, 0.0)) for dimension in UNIFIED_DIMENSIONS]
                radar_labels_closed = radar_labels + [radar_labels[0]]
                radar_values_closed = radar_values + [radar_values[0]]

                fig = go.Figure()
                fig.add_trace(
                    go.Scatterpolar(
                        r=radar_values_closed,
                        theta=radar_labels_closed,
                        fill="toself",
                        name=framework_trace_name,
                        line={"color": BRAND_BLUE_HEX, "width": 2},
                        fillcolor=BRAND_BLUE_FILL_RGBA,
                    )
                )
                fig.update_layout(
                    polar={"radialaxis": {"visible": True, "range": [0, 1]}},
                    showlegend=False,
                    height=460,
                    margin={"l": 52, "r": 52, "t": 56, "b": 52},
                )
                styled_evaluate_radar = style_plotly(fig, tokens)
                st.plotly_chart(styled_evaluate_radar, use_container_width=True, key="evaluate_radar")
                _assert_ui_contract(kpi_cards=executive_kpis, themed_figures=[styled_evaluate_radar])

                table_rows = []
                for row in framework_scores:
                    row_score = float(row.get("score", 0.0))
                    row_risk = row.get("risk_level")
                    if row_risk is None or str(row_risk).strip().lower() in {"", "undefined"}:
                        row_risk = _risk_label(row_score)[0].lower()
                    row_framework_id = row.get("framework_id")
                    if row_framework_id is None or str(row_framework_id).strip().lower() in {"", "undefined"}:
                        row_framework_id = "framework"
                    table_rows.append(
                        {
                            "framework_id": row_framework_id,
                            "score": fmt_score(row_score),
                            "risk_level": row_risk,
                        }
                    )

                def _render_evaluate_supporting_analysis() -> None:
                    st.markdown("### Per-Framework Scores")
                    st.dataframe(table_rows, width="stretch", hide_index=True)

                def _render_evaluate_technical_detail() -> None:
                    render_if_present("Framework", framework_id)
                    render_if_present("Stakeholder", stakeholder_id)
                    render_if_present("Scoring Method", scoring_method.upper())
                    render_if_present("Framework Weighting Mode", framework_weighting_mode)

                if conference_mode:
                    with st.expander("Supporting Analysis", expanded=False):
                        _render_evaluate_supporting_analysis()
                    with st.expander("Technical Details", expanded=False):
                        _render_evaluate_technical_detail()
                else:
                    st.markdown("## Supporting Analysis")
                    _render_evaluate_supporting_analysis()
                    st.markdown("## Technical Details")
                    _render_evaluate_technical_detail()
    elif page == "Conflict Detection":
        if detect_clicked:
            if not framework_id:
                st.error("Please select a framework.")
                return
            if len(conflict_stakeholder_ids) < 2:
                st.warning("Please select at least 2 stakeholders.")
                return

            payload = {
                "ai_system": {
                    "id": ai_system_id,
                    "name": ai_system_name,
                    "description": ai_system_description,
                    "context": {"dimension_scores": dimension_scores},
                },
                "framework_ids": [framework_id],
                "stakeholder_ids": conflict_stakeholder_ids,
            }

            with st.spinner("Detecting conflicts..."):
                ok, result, error_text = api_call(
                    "POST",
                    f"{backend_url}/api/conflicts",
                    payload=payload,
                    timeout=30,
                )

            if not ok:
                show_api_error("Conflict detection failed", error_text, result)
                return
            _update_last_run_bundle(
                page_name="Conflict Detection",
                backend_url=backend_url,
                requests_payloads={"conflicts": payload},
                responses_payloads={"conflicts": result},
                ui_context={
                    "page": page,
                    "framework_id": framework_id,
                    "stakeholder_ids": conflict_stakeholder_ids,
                    "conflict_metric": conflict_metric,
                },
            )
            st.session_state["last_conflict_result"] = result
            st.markdown("## Primary Visualization")
            st.caption("Cross-stakeholder alignment and conflict concentration.")
            summary_text = result.get("summary")
            if summary_text is not None and str(summary_text).strip().lower() not in {"", "undefined"}:
                st.info(str(summary_text))
            technical_note = ""
            if not screenshot_mode:
                technical_note = (
                    "Contribution (Contrib) is the stakeholder-weighted impact of each dimension for the selected "
                    "AI system: contrib_i = normalized_score_i × stakeholder_weight_i. "
                    "Priority Conflict compares stakeholder priorities directly. "
                    "System-Salience Conflict compares stakeholder rankings after accounting for system performance."
                )

            conflicts = result.get("conflicts", [])
            metadata = result.get("metadata", {}) if isinstance(result, dict) else {}
            correlation_matrix_weights = (
                metadata.get("correlation_matrix_weights")
                if isinstance(metadata, dict)
                else None
            )
            correlation_matrix_contrib = (
                metadata.get("correlation_matrix_contrib")
                if isinstance(metadata, dict)
                else None
            )
            rankings_weights = metadata.get("stakeholder_rankings_weights")
            rankings_contrib = metadata.get("stakeholder_rankings_contrib")

            rho_weights_dev_affected: str = "N/A"
            rho_contrib_dev_affected: str = "N/A"
            if isinstance(correlation_matrix_weights, dict):
                rho_weights_raw = (
                    correlation_matrix_weights.get("developer", {})
                    .get("affected_community")
                )
                if isinstance(rho_weights_raw, (int, float)):
                    rho_weights_dev_affected = fmt_score(rho_weights_raw)
            if isinstance(correlation_matrix_contrib, dict):
                rho_contrib_raw = (
                    correlation_matrix_contrib.get("developer", {})
                    .get("affected_community")
                )
                if isinstance(rho_contrib_raw, (int, float)):
                    rho_contrib_dev_affected = fmt_score(rho_contrib_raw)

            pairwise_rho_weights = metadata.get("pairwise_rho_weights")
            include_rho_weights = isinstance(pairwise_rho_weights, dict)
            rows = []
            if isinstance(conflicts, list) and conflicts:
                for conflict in conflicts:
                    row = {
                        "stakeholder_a_id": conflict.get("stakeholder_a_id"),
                        "stakeholder_b_id": conflict.get("stakeholder_b_id"),
                        "spearman_rho": fmt_score(conflict.get("spearman_rho")),
                        "conflict_level": conflict.get("conflict_level"),
                        "conflicting_dimensions": conflict.get("conflicting_dimensions", []),
                    }
                    if include_rho_weights:
                        stakeholder_a = str(conflict.get("stakeholder_a_id", ""))
                        stakeholder_b = str(conflict.get("stakeholder_b_id", ""))
                        pair_key = "|".join(sorted((stakeholder_a, stakeholder_b)))
                        rho_weights = pairwise_rho_weights.get(pair_key)
                        row["rho_weights"] = fmt_score(rho_weights)
                    rows.append(row)

            if conflict_metric == "Priority Conflict (Weights-Only)":
                correlation_matrix = correlation_matrix_weights
                matrix_title = "Stakeholder Spearman Correlation Matrix (Priority Conflict, Weights-Only)"
            else:
                correlation_matrix = correlation_matrix_contrib
                matrix_title = "Stakeholder Spearman Correlation Matrix (System-Salience Conflict, Contribution-Based)"

            if isinstance(correlation_matrix, dict) and correlation_matrix:
                labels = [
                    stakeholder_id
                    for stakeholder_id in conflict_stakeholder_ids
                    if stakeholder_id in correlation_matrix
                ]
                if not labels:
                    labels = list(correlation_matrix.keys())
                z_values = [
                    [float(correlation_matrix.get(row, {}).get(col, 0.0)) for col in labels]
                    for row in labels
                ]
                z_text = [
                    [fmt_small(value) for value in row]
                    for row in z_values
                ]

                heatmap = go.Figure(
                    data=go.Heatmap(
                        z=z_values,
                        text=z_text,
                        texttemplate="%{text}",
                        x=labels,
                        y=labels,
                        zmin=-1,
                        zmax=1,
                        colorscale="RdBu",
                        colorbar={"title": "rho"},
                    )
                )
                heatmap.update_layout(
                    title=matrix_title,
                    margin={"l": 40, "r": 40, "t": 60, "b": 40},
                )
                styled_conflict_heatmap = style_plotly(heatmap, tokens)
                st.plotly_chart(styled_conflict_heatmap, use_container_width=True, key="conflict_heatmap")
                _assert_ui_contract(kpi_cards=executive_kpis, themed_figures=[styled_conflict_heatmap])
            else:
                st.info("No correlation matrix returned in metadata.")

            def _render_conflict_supporting_analysis() -> None:
                demo_box = st.container(border=True)
                with demo_box:
                    st.markdown("### Correlation Snapshot")
                    metric_col_1, metric_col_2 = st.columns(2)
                    metric_col_1.metric("rho_priority(dev, affected)", rho_weights_dev_affected)
                    metric_col_2.metric("rho_contribution(dev, affected)", rho_contrib_dev_affected)

                    stakeholders_for_top1 = list(conflict_stakeholder_ids)
                    if not stakeholders_for_top1:
                        stakeholders_for_top1 = list(
                            {
                                *(rankings_weights.keys() if isinstance(rankings_weights, dict) else []),
                                *(rankings_contrib.keys() if isinstance(rankings_contrib, dict) else []),
                            }
                        )

                    top1_rows = []
                    for stakeholder_id in stakeholders_for_top1:
                        weights_top_1 = "N/A"
                        contrib_top_1 = "N/A"

                        if isinstance(rankings_weights, dict):
                            ranking_weights = rankings_weights.get(stakeholder_id)
                            if isinstance(ranking_weights, list) and ranking_weights:
                                weights_top_1 = str(ranking_weights[0])

                        if isinstance(rankings_contrib, dict):
                            ranking_contrib = rankings_contrib.get(stakeholder_id)
                            if isinstance(ranking_contrib, list) and ranking_contrib:
                                contrib_top_1 = str(ranking_contrib[0])

                        top1_rows.append(
                            {
                                "stakeholder_id": stakeholder_id,
                                "top1_weights": weights_top_1,
                                "top1_contribution": contrib_top_1,
                            }
                        )

                    if top1_rows:
                        st.table(top1_rows)

                if rows:
                    st.dataframe(rows, width="stretch", hide_index=True)
                else:
                    st.info("No stakeholder conflicts were returned.")

            if conference_mode:
                with st.expander("Supporting Analysis", expanded=False):
                    _render_conflict_supporting_analysis()
            else:
                st.markdown("## Supporting Analysis")
                _render_conflict_supporting_analysis()

            if technical_note:
                if conference_mode:
                    with st.expander("Technical Details", expanded=False):
                        st.info(technical_note)
                else:
                    st.markdown("## Technical Details")
                    st.info(technical_note)
    elif page == "Pareto Resolution":
        if generate_pareto_clicked:
            if not framework_id:
                st.error("Please select a framework.")
                return
            if len(pareto_stakeholder_ids) < 2:
                st.warning("Please select at least 2 stakeholders.")
                return
            st.caption(
                "Pareto request parameters (effective): "
                f"n_solutions={pareto_n_solutions}, pop_size={pareto_pop_size}, n_gen={pareto_n_gen_effective}."
            )

            payload = {
                "ai_system": {
                    "id": ai_system_id,
                    "name": ai_system_name,
                    "description": ai_system_description,
                    "context": {"dimension_scores": dimension_scores},
                },
                "framework_ids": [framework_id],
                "stakeholder_ids": pareto_stakeholder_ids,
                "n_solutions": pareto_n_solutions,
                "pop_size": pareto_pop_size,
                "n_gen": pareto_n_gen_effective,
            }

            with st.spinner("Generating Pareto solutions..."):
                ok, result, error_text = api_call(
                    "POST",
                    f"{backend_url}/api/pareto",
                    payload=payload,
                    timeout=60,
                )

            if (
                not ok
                and payload.get("n_gen") == 0
                and "status 422" in error_text.lower()
            ):
                st.caption("Note: n_gen=0 is not supported by the backend, so it was adjusted to 1.")
                payload = dict(payload)
                payload["n_gen"] = 1
                with st.spinner("Retrying Pareto generation with n_gen=1..."):
                    ok, result, error_text = api_call(
                        "POST",
                        f"{backend_url}/api/pareto",
                        payload=payload,
                        timeout=60,
                    )

            if not ok:
                show_api_error("Pareto generation failed", error_text, result)
                return
            st.session_state["pareto_result"] = result
            st.session_state["pareto_result_stakeholder_ids"] = list(pareto_stakeholder_ids)
            bundle = _update_last_run_bundle(
                page_name="Pareto Resolution",
                backend_url=backend_url,
                requests_payloads={"pareto": payload},
                responses_payloads={"pareto": result},
                ui_context={
                    "page": page,
                    "framework_id": framework_id,
                    "stakeholder_ids": pareto_stakeholder_ids,
                    "n_solutions": pareto_n_solutions,
                    "pop_size": pareto_pop_size,
                    "n_gen": payload.get("n_gen", pareto_n_gen_effective),
                },
            )
            _write_ui_run_log(
                run_id=str(bundle.get("run_id", str(uuid4()))),
                page_name="pareto_resolution",
                case_name="manual",
                payload={
                    "timestamp_utc": datetime.utcnow().isoformat() + "Z",
                    "request": payload,
                    "response": result,
                },
            )
        result = st.session_state.get("pareto_result")
        if not isinstance(result, dict):
            return

        st.markdown("## Primary Visualization")
        st.caption("Consensus profile and stakeholder distance for the selected solution.")
        summary = result.get("summary")
        if summary is not None and str(summary).strip().lower() not in {"", "undefined"}:
            st.info(str(summary))

        solutions = result.get("pareto_solutions", [])
        metadata = result.get("metadata", {}) if isinstance(result, dict) else {}
        if not isinstance(solutions, list) or not solutions:
            st.warning("No Pareto solutions were returned.")
            return

        metadata_stakeholder_ids = metadata.get("stakeholder_ids")
        if isinstance(metadata_stakeholder_ids, list):
            stakeholder_ids = [str(item) for item in metadata_stakeholder_ids]
        else:
            stakeholder_ids = [str(item) for item in st.session_state.get("pareto_result_stakeholder_ids", [])]
        if not stakeholder_ids:
            stakeholder_ids = list(pareto_stakeholder_ids)

        ablation_utility = metadata.get("ablation_utility_by_solution")
        if not isinstance(ablation_utility, dict):
            ablation_utility = {}

        parsed_solutions: list[dict[str, Any]] = []
        table_rows: list[dict[str, Any]] = []
        for raw_solution in solutions:
            solution_id = str(raw_solution.get("solution_id", "")).strip()
            if not solution_id:
                continue

            raw_rank = raw_solution.get("rank", 0)
            try:
                rank = int(raw_rank)
            except (TypeError, ValueError):
                rank = 0

            raw_objectives = raw_solution.get("objective_scores", {})
            objective_scores = (
                {str(key): float(value) for key, value in raw_objectives.items()}
                if isinstance(raw_objectives, dict)
                else {}
            )
            total_distance = sum(float(objective_scores.get(stakeholder_id, 0.0)) for stakeholder_id in stakeholder_ids)

            raw_consensus = raw_solution.get("weights", {}).get("consensus", {})
            consensus_weights = (
                {dimension: float(raw_consensus.get(dimension, 0.0)) for dimension in UNIFIED_DIMENSIONS}
                if isinstance(raw_consensus, dict)
                else {dimension: 0.0 for dimension in UNIFIED_DIMENSIONS}
            )

            raw_utility = ablation_utility.get(solution_id)
            utility_wsm: float | None = None
            if isinstance(raw_utility, (int, float)):
                utility_wsm = float(raw_utility)

            row: dict[str, Any] = {
                "rank": rank,
                "solution_id": solution_id,
                "total_distance": fmt_score(total_distance),
                "utility_wsm": fmt_score(utility_wsm),
            }
            for stakeholder_id in stakeholder_ids:
                row[stakeholder_id] = fmt_score(objective_scores.get(stakeholder_id))
            table_rows.append(row)
            parsed_solutions.append(
                {
                    "rank": rank,
                    "solution_id": solution_id,
                    "total_distance": total_distance,
                    "utility_wsm": utility_wsm,
                    "consensus_weights": consensus_weights,
                    "objective_scores": objective_scores,
                }
            )

        if not parsed_solutions:
            st.warning("No valid Pareto solutions were returned.")
            return

        parsed_solutions.sort(key=lambda item: (item["rank"] if item["rank"] > 0 else 10**9, item["solution_id"]))
        table_rows.sort(key=lambda item: (item["rank"] if item["rank"] > 0 else 10**9, item["solution_id"]))

        solution_ids = [str(item["solution_id"]) for item in parsed_solutions]
        if "pareto_selected_id" not in st.session_state:
            st.session_state["pareto_selected_id"] = solution_ids[0]
        if st.session_state["pareto_selected_id"] not in solution_ids:
            st.session_state["pareto_selected_id"] = solution_ids[0]
        if st.session_state.get("pareto_solution_select") not in solution_ids:
            st.session_state["pareto_solution_select"] = st.session_state["pareto_selected_id"]

        selected_solution_id = st.selectbox(
            "Select Solution",
            solution_ids,
            index=solution_ids.index(st.session_state["pareto_selected_id"]),
            key="pareto_solution_select",
        )
        st.session_state["pareto_selected_id"] = selected_solution_id
        selected_solution = next(
            item for item in parsed_solutions if item["solution_id"] == st.session_state["pareto_selected_id"]
        )

        selected_consensus = selected_solution["consensus_weights"]
        selected_objectives = selected_solution["objective_scores"]
        selected_total_distance = float(selected_solution["total_distance"])
        selected_utility = selected_solution["utility_wsm"]
        selected_rank = int(selected_solution["rank"])
        top_dimension = max(selected_consensus.items(), key=lambda item: float(item[1]))[0]
        top_dimension_label = DIMENSION_DISPLAY_NAMES.get(top_dimension, top_dimension)
        highest_distance_stakeholder = "N/A"
        if selected_objectives:
            highest_distance_stakeholder = max(
                selected_objectives.items(), key=lambda item: float(item[1])
            )[0]

        utility_text = fmt_score(selected_utility)

        st.info(
            "\n".join(
                [
                    "**Resolution Summary**",
                    f"- Rank: {selected_rank}.",
                    f"- Total distance: {fmt_score(selected_total_distance)}.",
                    f"- Utility (WSM ablation): {utility_text}.",
                    f"- Top-1 consensus dimension: {top_dimension_label}.",
                    f"- Highest stakeholder distance: {highest_distance_stakeholder}.",
                ]
            )
        )

        st.markdown("### Consensus Weights Radar")
        st.markdown(
            "Weights shown are derived from backend "
            f"<code style='color:{BRAND_BLUE_HEX};'>/api/pareto</code> output "
            f"(<code style='color:{BRAND_BLUE_HEX};'>pareto_solutions[*].weights.consensus</code>): "
            "candidate consensus vectors are simplex-normalized and selected using salience-weighted "
            "distance objectives against stakeholder weight vectors.",
            unsafe_allow_html=True,
        )
        radar_labels = [DIMENSION_DISPLAY_NAMES[dimension] for dimension in UNIFIED_DIMENSIONS]
        radar_values = [float(selected_consensus.get(dimension, 0.0)) for dimension in UNIFIED_DIMENSIONS]
        radar_labels_closed = radar_labels + [radar_labels[0]]
        radar_values_closed = radar_values + [radar_values[0]]
        solution_trace_name = safe_str(selected_solution_id).strip()
        if solution_trace_name.lower() == "undefined":
            solution_trace_name = ""
        radar_figure = go.Figure()
        radar_figure.add_trace(
            go.Scatterpolar(
                r=radar_values_closed,
                theta=radar_labels_closed,
                fill="toself",
                name=solution_trace_name,
                line={"color": BRAND_BLUE_HEX, "width": 2},
                fillcolor=BRAND_BLUE_FILL_RGBA,
            )
        )
        radar_figure.update_layout(
            polar={"radialaxis": {"visible": True, "range": [0, 1]}},
            showlegend=False,
            height=460,
            margin={"l": 52, "r": 52, "t": 56, "b": 52},
        )
        styled_pareto_radar = style_plotly(radar_figure, tokens)
        st.plotly_chart(
            styled_pareto_radar,
            use_container_width=True,
            key=f"pareto_weights_radar_{selected_solution_id}",
        )

        st.markdown("### Stakeholder Distance (Lower = Better Alignment)")
        distance_values = [float(selected_objectives.get(stakeholder_id, 0.0)) for stakeholder_id in stakeholder_ids]
        bar_figure = go.Figure(
            data=[
                go.Bar(
                    x=stakeholder_ids,
                    y=distance_values,
                    name="Distance",
                    marker={"color": BRAND_BLUE_HEX},
                )
            ]
        )
        bar_figure.update_layout(
            xaxis_title="Stakeholder",
            yaxis_title="Distance",
            margin={"l": 40, "r": 40, "t": 60, "b": 40},
        )
        styled_pareto_distance_bar = style_plotly(bar_figure, tokens)
        st.plotly_chart(
            styled_pareto_distance_bar,
            use_container_width=True,
            key=f"pareto_distance_bar_{selected_solution_id}",
        )
        _assert_ui_contract(
            kpi_cards=executive_kpis,
            themed_figures=[styled_pareto_radar, styled_pareto_distance_bar],
            pareto_weights=selected_consensus,
            enforce_pareto_weights_sum_to_one=True,
        )

        def _render_pareto_supporting_analysis() -> None:
            st.markdown("### Candidate Solutions")
            st.dataframe(table_rows, width="stretch", hide_index=True)
            st.markdown("### Tradeoff Visualization")
            if len(stakeholder_ids) == 2:
                stakeholder_a, stakeholder_b = stakeholder_ids
                all_x = [
                    float(item["objective_scores"].get(stakeholder_a, 0.0))
                    for item in parsed_solutions
                ]
                all_y = [
                    float(item["objective_scores"].get(stakeholder_b, 0.0))
                    for item in parsed_solutions
                ]
                all_ranks = [str(item["rank"]) for item in parsed_solutions]

                selected_x = float(selected_objectives.get(stakeholder_a, 0.0))
                selected_y = float(selected_objectives.get(stakeholder_b, 0.0))

                scatter_figure = go.Figure()
                scatter_figure.add_trace(
                    go.Scatter(
                        x=all_x,
                        y=all_y,
                        mode="markers+text",
                        text=all_ranks,
                        textposition="top center",
                        name="Pareto solutions",
                        marker={"size": 9, "color": BRAND_BLUE_HEX},
                    )
                )
                scatter_figure.add_trace(
                    go.Scatter(
                        x=[selected_x],
                        y=[selected_y],
                        mode="markers",
                        name="Selected",
                        marker={"size": 14, "color": TEXT, "symbol": "diamond"},
                    )
                )
                scatter_figure.update_layout(
                    title=f"Tradeoff: {stakeholder_a} vs {stakeholder_b}",
                    xaxis_title=f"{stakeholder_a} distance",
                    yaxis_title=f"{stakeholder_b} distance",
                    margin={"l": 40, "r": 40, "t": 60, "b": 40},
                )
                styled_scatter_figure = style_plotly(scatter_figure, tokens)
                st.plotly_chart(
                    styled_scatter_figure,
                    use_container_width=True,
                    key=f"pareto_tradeoff_scatter_{stakeholder_a}_{stakeholder_b}",
                )
                _assert_ui_contract(kpi_cards=executive_kpis, themed_figures=[styled_scatter_figure])
            elif len(stakeholder_ids) >= 3:
                stakeholder_display_labels = {
                    "developer": "Developer",
                    "regulator": "Regulator",
                    "affected_community": "Affected Community",
                }
                dimension_specs = [
                    {
                        "label": stakeholder_display_labels.get(
                            stakeholder_id,
                            stakeholder_id.replace("_", " ").title(),
                        ),
                        "values": [
                            float(item["objective_scores"].get(stakeholder_id, 0.0))
                            for item in parsed_solutions
                        ],
                    }
                    for stakeholder_id in stakeholder_ids
                ]
                line_color = [float(item["total_distance"]) for item in parsed_solutions]
                parallel_figure = go.Figure(
                    data=go.Parcoords(
                        line={
                            "color": line_color,
                            "colorscale": "Viridis",
                            "showscale": True,
                            "colorbar": {
                                "title": {
                                    "text": "Total Distance",
                                    "side": "right",
                                    "font": {"color": TEXT, "size": 11},
                                },
                                "tickfont": {"color": TEXT},
                                "x": 1.08,
                                "xanchor": "left",
                            },
                        },
                        dimensions=dimension_specs,
                    )
                )
                parallel_figure.update_traces(
                    domain={"y": [0.0, 0.86]},
                    dimensions=dimension_specs,
                    labelfont={"color": TEXT, "size": 12},
                    tickfont={"color": TEXT, "size": 11},
                )
                parallel_figure.update_layout(
                    font={"color": TEXT},
                    title={
                        "text": "Stakeholder Distance Tradeoffs",
                        "y": 0.99,
                        "yanchor": "top",
                        "x": 0.01,
                        "xanchor": "left",
                    },
                    margin={"l": 40, "r": 140, "t": 130, "b": 48},
                )
                parallel_figure = style_plotly(parallel_figure, tokens)
                st.plotly_chart(
                    parallel_figure,
                    use_container_width=True,
                    key=f"pareto_tradeoff_parallel_{len(stakeholder_ids)}",
                )
                _assert_ui_contract(
                    kpi_cards=executive_kpis,
                    themed_figures=[parallel_figure],
                    parcoords_figure=parallel_figure,
                )
                st.caption(f"Selected solution: {selected_solution_id} (rank {selected_rank}).")
            else:
                st.info("Select at least 2 stakeholders to view tradeoffs.")

        def _render_pareto_technical_detail() -> None:
            st.caption(
                "Search parameters: "
                f"options={pareto_n_solutions}, breadth={pareto_pop_size}, depth={pareto_n_gen_effective}."
            )
            st.caption(f"Stakeholders in scope: {', '.join(stakeholder_ids)}.")

        if conference_mode:
            with st.expander("Supporting Analysis", expanded=False):
                _render_pareto_supporting_analysis()
            with st.expander("Technical Details", expanded=False):
                _render_pareto_technical_detail()
        else:
            st.markdown("## Supporting Analysis")
            _render_pareto_supporting_analysis()
            st.markdown("## Technical Details")
            _render_pareto_technical_detail()
    else:
        case_framework_ids = [framework_id] if framework_id else []
        case_stakeholder_ids = ["developer", "regulator", "affected_community"]

        if not CASE_STUDIES:
            st.error("No case studies were loaded from `case_studies/*.json`.")
            if CASE_STUDIES_LOAD_ERROR:
                st.caption(f"Case study load error: {CASE_STUDIES_LOAD_ERROR}")

        for case in CASE_STUDIES:
            case_id = str(case["id"])
            case_name = str(case["name"])
            case_description = str(case["description"])
            case_source_reference = case.get("source_reference")
            case_assumptions = case.get("assumptions")
            case_scores = {
                dimension: float(case["dimension_scores"][dimension])
                for dimension in UNIFIED_DIMENSIONS
            }
            framework_key = framework_id or "no_framework_selected"
            case_result_key = f"case_result_{case_id}_{framework_key}"
            case_export_key = f"case_export_{case_id}_{framework_key}"

            with st.expander(
                f"Case: {case_name}",
                expanded=(not case_screenshot_mode and not conference_mode),
            ):
                st.write(case_description)
                if not case_screenshot_mode:
                    source_citation = ""
                    source_url = ""
                    framing_sentence = (
                        "This is a deployment-inspired synthetic scenario constructed for MEDF evaluation."
                    )
                    if isinstance(case_source_reference, dict):
                        source_citation = str(case_source_reference.get("citation", "")).strip()
                        source_url = str(case_source_reference.get("url", "")).strip()
                    elif isinstance(case_source_reference, str):
                        source_citation = case_source_reference.strip()

                    source_citation_display = source_citation
                    methodological_framing = ""
                    if framing_sentence in source_citation:
                        methodological_framing = framing_sentence
                        source_citation_display = source_citation.replace(framing_sentence, "", 1).strip()
                        if source_citation_display.startswith("."):
                            source_citation_display = source_citation_display[1:].strip()
                    elif "deployment-inspired synthetic scenario" in source_citation.lower():
                        methodological_framing = source_citation
                        source_citation_display = ""

                    if source_citation or source_url:
                        st.markdown("**Source Reference**")
                        if source_citation_display:
                            st.write(source_citation_display)
                        if source_url:
                            st.markdown(f"[{source_url}]({source_url})")
                    st.divider()

                    st.markdown("**Methodological Framing**")
                    if methodological_framing:
                        st.write(methodological_framing)
                    else:
                        st.write(framing_sentence)
                    st.divider()

                    st.markdown("**Assumptions**")
                    if isinstance(case_assumptions, list) and case_assumptions:
                        for assumption in case_assumptions:
                            formatted_assumption = _format_sentence_like_bullet(assumption)
                            if formatted_assumption:
                                st.markdown(f"- {formatted_assumption}")
                    elif isinstance(case_assumptions, str) and case_assumptions.strip():
                        formatted_assumption = _format_sentence_like_bullet(case_assumptions)
                        if formatted_assumption:
                            st.markdown(f"- {formatted_assumption}")
                    st.divider()

                    st.markdown("**Input Dimension Scores**")
                    score_rows = [
                        {
                            "Dimension": DIMENSION_DISPLAY_NAMES[dimension],
                            "Score": f"{case_scores[dimension]:.1f}",
                        }
                        for dimension in UNIFIED_DIMENSIONS
                    ]
                    score_table = pd.DataFrame(score_rows)
                    score_table.index = range(1, len(score_table) + 1)
                    st.table(score_table)

                run_case_clicked = st.button("Run Case Study", key=f"run_case_{case_id}", type="primary")

                if run_case_clicked:
                    st.session_state.pop(case_result_key, None)
                    try:
                        if not framework_id:
                            st.error("Please select a framework in the sidebar before running a case study.")
                            continue

                        stakeholder_by_id = {
                            str(item.get("id", "")): item
                            for item in stakeholders
                            if isinstance(item, dict) and item.get("id")
                        }
                        weights_payload: dict[str, dict[str, float]] = {}
                        missing_stakeholder = False
                        for stakeholder_id in case_stakeholder_ids:
                            stakeholder_obj = stakeholder_by_id.get(stakeholder_id)
                            if stakeholder_obj is None:
                                st.error(
                                    f"Stakeholder '{stakeholder_id}' not found in /api/stakeholders; cannot run evaluation."
                                )
                                missing_stakeholder = True
                                break

                            raw_weights = stakeholder_obj.get("weights")
                            if not isinstance(raw_weights, dict):
                                st.error(
                                    f"Stakeholder '{stakeholder_id}' has no valid weights in /api/stakeholders; cannot run evaluation."
                                )
                                missing_stakeholder = True
                                break

                            missing_dimensions = [
                                dimension for dimension in UNIFIED_DIMENSIONS if dimension not in raw_weights
                            ]
                            if missing_dimensions:
                                st.error(
                                    f"Stakeholder '{stakeholder_id}' weights missing dimensions: {', '.join(missing_dimensions)}."
                                )
                                missing_stakeholder = True
                                break

                            weights_payload[stakeholder_id] = {
                                dimension: float(raw_weights[dimension])
                                for dimension in UNIFIED_DIMENSIONS
                            }

                        if missing_stakeholder:
                            continue

                        evaluate_payload = {
                            "ai_system": {
                                "id": f"case_{case_id}",
                                "name": case_name,
                                "description": case_description,
                                "context": {"dimension_scores": case_scores},
                            },
                            "framework_ids": case_framework_ids,
                            "stakeholder_ids": case_stakeholder_ids,
                            "weights": weights_payload,
                            "scoring_method": "topsis",
                        }
                        conflicts_payload = {
                            "ai_system": {
                                "id": f"case_{case_id}",
                                "name": case_name,
                                "description": case_description,
                                "context": {"dimension_scores": case_scores},
                            },
                            "framework_ids": case_framework_ids,
                            "stakeholder_ids": case_stakeholder_ids,
                        }
                        pareto_payload = {
                            "ai_system": {
                                "id": f"case_{case_id}",
                                "name": case_name,
                                "description": case_description,
                                "context": {"dimension_scores": case_scores},
                            },
                            "framework_ids": case_framework_ids,
                            "stakeholder_ids": case_stakeholder_ids,
                            "n_solutions": 8,
                            "pop_size": 40,
                            "n_gen": 80,
                        }

                        with st.spinner("Running Evaluate → Conflicts → Pareto..."):
                            ok_eval, evaluate_data, evaluate_error = api_call(
                                "POST",
                                f"{backend_url}/api/evaluate",
                                payload=evaluate_payload,
                                timeout=60,
                            )
                            if not ok_eval:
                                show_api_error(
                                    f"Case Study '{case_name}' evaluation failed",
                                    evaluate_error,
                                    evaluate_data,
                                )
                                continue

                            ok_conflict, conflicts_data, conflicts_error = api_call(
                                "POST",
                                f"{backend_url}/api/conflicts",
                                payload=conflicts_payload,
                                timeout=60,
                            )
                            if not ok_conflict:
                                show_api_error(
                                    f"Case Study '{case_name}' conflict detection failed",
                                    conflicts_error,
                                    conflicts_data,
                                )
                                continue

                            ok_pareto, pareto_data, pareto_error = api_call(
                                "POST",
                                f"{backend_url}/api/pareto",
                                payload=pareto_payload,
                                timeout=90,
                            )
                            if not ok_pareto:
                                show_api_error(
                                    f"Case Study '{case_name}' pareto generation failed",
                                    pareto_error,
                                    pareto_data,
                                )
                                continue

                        st.session_state[case_result_key] = {
                            "evaluate_payload": evaluate_payload,
                            "conflicts_payload": conflicts_payload,
                            "pareto_payload": pareto_payload,
                            "evaluate_response": evaluate_data,
                            "conflicts_response": conflicts_data,
                            "pareto_response": pareto_data,
                        }
                        bundle = _update_last_run_bundle(
                            page_name="Case Studies",
                            backend_url=backend_url,
                            requests_payloads={
                                "evaluate": evaluate_payload,
                                "conflicts": conflicts_payload,
                                "pareto": pareto_payload,
                            },
                            responses_payloads={
                                "evaluate": evaluate_data,
                                "conflicts": conflicts_data,
                                "pareto": pareto_data,
                            },
                            ui_context={
                                "page": page,
                                "framework_id": framework_id,
                                "stakeholder_ids": case_stakeholder_ids,
                                "case_id": case_id,
                                "case_name": case_name,
                            },
                        )
                        _write_ui_run_log(
                            run_id=str(bundle.get("run_id", str(uuid4()))),
                            page_name="case_studies",
                            case_name=case_id,
                            payload={
                                "timestamp_utc": datetime.utcnow().isoformat() + "Z",
                                "requests": {
                                    "evaluate": evaluate_payload,
                                    "conflicts": conflicts_payload,
                                    "pareto": pareto_payload,
                                },
                                "responses": {
                                    "evaluate": evaluate_data,
                                    "conflicts": conflicts_data,
                                    "pareto": pareto_data,
                                },
                            },
                        )
                    except Exception as exc:
                        st.error(f"Case '{case_name}' failed: {exc}")

                case_result = st.session_state.get(case_result_key)
                if not isinstance(case_result, dict):
                    st.info("Run Case Study to generate report outputs.")
                    continue

                evaluate_result = case_result.get("evaluate_response", {})
                conflicts_result = case_result.get("conflicts_response", {})
                pareto_result = case_result.get("pareto_response", {})

                st.divider()
                st.markdown("### Section A: Evaluation Result")
                overall_score = float(evaluate_result.get("overall_score", 0.0))
                st.metric("Overall Score", fmt_score(overall_score))

                framework_scores = evaluate_result.get("framework_scores", [])
                if isinstance(framework_scores, list) and framework_scores:
                    first_framework = framework_scores[0]
                    dim_scores = (
                        first_framework.get("dimension_scores", {})
                        if isinstance(first_framework, dict)
                        else {}
                    )
                    if isinstance(dim_scores, dict):
                        eval_radar = _build_radar_chart(
                            {dimension: float(dim_scores.get(dimension, 0.0)) for dimension in UNIFIED_DIMENSIONS},
                            title="Evaluation Dimension Scores",
                            radial_max=1.0,
                        )
                        st.plotly_chart(
                            style_plotly(eval_radar, tokens),
                            use_container_width=True,
                            key=f"case_{case_id}_evaluation_radar",
                        )
                    else:
                        st.warning("Evaluation dimension scores were not returned.")
                else:
                    st.warning("No evaluation framework scores returned.")

                st.divider()
                st.markdown("### Section B: Conflict Analysis")
                conflict_metadata = conflicts_result.get("metadata", {}) if isinstance(conflicts_result, dict) else {}
                matrix_weights = (
                    conflict_metadata.get("correlation_matrix_weights")
                    if isinstance(conflict_metadata, dict)
                    else None
                )
                matrix_contrib = (
                    conflict_metadata.get("correlation_matrix_contrib")
                    if isinstance(conflict_metadata, dict)
                    else None
                )

                matrix_labels = list(case_stakeholder_ids)
                if isinstance(matrix_weights, dict):
                    matrix_labels = [stakeholder_id for stakeholder_id in case_stakeholder_ids if stakeholder_id in matrix_weights]
                    if not matrix_labels:
                        matrix_labels = list(matrix_weights.keys())

                matrix_col_1, matrix_col_2 = st.columns(2)
                with matrix_col_1:
                    if isinstance(matrix_weights, dict):
                        weights_heatmap = _build_correlation_heatmap(
                            matrix_weights,
                            labels=matrix_labels,
                            title="Priority Conflict (Weights-Only) Correlation",
                        )
                        st.plotly_chart(
                            style_plotly(weights_heatmap, tokens),
                            use_container_width=True,
                            key=f"case_{case_id}_weights_heatmap",
                        )
                    else:
                        st.info("Priority Conflict matrix is unavailable.")
                with matrix_col_2:
                    if isinstance(matrix_contrib, dict):
                        contrib_heatmap = _build_correlation_heatmap(
                            matrix_contrib,
                            labels=matrix_labels,
                            title="System-Salience Conflict (Contribution-Based) Correlation",
                        )
                        st.plotly_chart(
                            style_plotly(contrib_heatmap, tokens),
                            use_container_width=True,
                            key=f"case_{case_id}_contrib_heatmap",
                        )
                    else:
                        st.info("System-Salience Conflict matrix is unavailable.")

                rho_weights = "N/A"
                rho_contrib = "N/A"
                if isinstance(matrix_weights, dict):
                    rho_value = matrix_weights.get("developer", {}).get("affected_community")
                    if isinstance(rho_value, (int, float)):
                        rho_weights = fmt_score(rho_value)
                if isinstance(matrix_contrib, dict):
                    rho_value = matrix_contrib.get("developer", {}).get("affected_community")
                    if isinstance(rho_value, (int, float)):
                        rho_contrib = fmt_score(rho_value)

                rho_col_1, rho_col_2 = st.columns(2)
                rho_col_1.metric("dev↔affected weights rho", rho_weights)
                rho_col_2.metric("dev↔affected contribution rho", rho_contrib)

                st.divider()
                st.markdown("### Section C: Pareto Resolution")
                pareto_solutions = pareto_result.get("pareto_solutions", []) if isinstance(pareto_result, dict) else []
                pareto_metadata = pareto_result.get("metadata", {}) if isinstance(pareto_result, dict) else {}
                ablation_utilities = (
                    pareto_metadata.get("ablation_utility_by_solution")
                    if isinstance(pareto_metadata, dict)
                    else None
                )
                if not isinstance(ablation_utilities, dict):
                    ablation_utilities = {}

                parsed_solutions: list[dict[str, Any]] = []
                solution_rows: list[dict[str, Any]] = []
                for solution in pareto_solutions if isinstance(pareto_solutions, list) else []:
                    if not isinstance(solution, dict):
                        continue
                    solution_id = str(solution.get("solution_id", "")).strip()
                    if not solution_id:
                        continue
                    try:
                        rank = int(solution.get("rank", 0))
                    except (TypeError, ValueError):
                        rank = 0

                    raw_objectives = solution.get("objective_scores", {})
                    objective_scores = (
                        {str(key): float(value) for key, value in raw_objectives.items()}
                        if isinstance(raw_objectives, dict)
                        else {}
                    )

                    total_distance = float(sum(objective_scores.values()))
                    utility_wsm = ablation_utilities.get(solution_id)
                    utility_value: float | None = None
                    if isinstance(utility_wsm, (int, float)):
                        utility_value = float(utility_wsm)

                    row: dict[str, Any] = {
                        "rank": rank,
                        "solution_id": solution_id,
                        "total_distance": fmt_score(total_distance),
                        "utility_wsm": fmt_score(utility_value),
                    }
                    for stakeholder_id in case_stakeholder_ids:
                        row[stakeholder_id] = fmt_score(objective_scores.get(stakeholder_id))

                    consensus_raw = solution.get("weights", {}).get("consensus", {})
                    consensus_weights = (
                        {dimension: float(consensus_raw.get(dimension, 0.0)) for dimension in UNIFIED_DIMENSIONS}
                        if isinstance(consensus_raw, dict)
                        else {dimension: 0.0 for dimension in UNIFIED_DIMENSIONS}
                    )

                    solution_rows.append(row)
                    parsed_solutions.append(
                        {
                            "rank": rank,
                            "solution_id": solution_id,
                            "objective_scores": objective_scores,
                            "consensus_weights": consensus_weights,
                            "utility_wsm": utility_value,
                            "total_distance": total_distance,
                        }
                    )

                parsed_solutions.sort(key=lambda item: (item["rank"] if item["rank"] > 0 else 10**9, item["solution_id"]))
                solution_rows.sort(key=lambda item: (item["rank"] if item["rank"] > 0 else 10**9, item["solution_id"]))
                top_rows = solution_rows[:5]

                if top_rows:
                    st.dataframe(top_rows, width="stretch", hide_index=True)
                    rank_1_solution = parsed_solutions[0]
                    rank_1_consensus = rank_1_solution["consensus_weights"]
                    rank_1_objectives = rank_1_solution["objective_scores"]

                    consensus_radar = _build_radar_chart(
                        rank_1_consensus,
                        title="Rank 1 Consensus Weights",
                        radial_max=1.0,
                    )
                    st.markdown(
                        "Weights shown are derived from backend "
                        f"<code style='color:{BRAND_BLUE_HEX};'>/api/pareto</code> output "
                        f"(<code style='color:{BRAND_BLUE_HEX};'>pareto_solutions[*].weights.consensus</code>) "
                        "and are displayed without UI-side reweighting.",
                        unsafe_allow_html=True,
                    )
                    st.plotly_chart(
                        style_plotly(consensus_radar, tokens),
                        use_container_width=True,
                        key=f"case_{case_id}_consensus_radar_{rank_1_solution['solution_id']}",
                    )

                    stakeholder_distance_bar = go.Figure(
                        data=[
                            go.Bar(
                                x=case_stakeholder_ids,
                                y=[
                                    float(rank_1_objectives.get(stakeholder_id, 0.0))
                                    for stakeholder_id in case_stakeholder_ids
                                ],
                                name="Distance",
                                marker={"color": BRAND_BLUE_HEX},
                            )
                        ]
                    )
                    stakeholder_distance_bar.update_layout(
                        title="Stakeholder Distance (Lower = Better Alignment)",
                        xaxis_title="Stakeholder",
                        yaxis_title="Distance",
                        margin={"l": 40, "r": 40, "t": 60, "b": 40},
                    )
                    st.plotly_chart(
                        style_plotly(stakeholder_distance_bar, tokens),
                        use_container_width=True,
                        key=f"case_{case_id}_distance_bar_{rank_1_solution['solution_id']}",
                    )
                else:
                    st.warning("No Pareto solutions were returned.")

                st.divider()
                st.markdown("### Section D: Export JSON")
                export_clicked = st.button("Export Case JSON", key=f"export_case_{case_id}")
                if export_clicked:
                    st.session_state[case_export_key] = True
                if st.session_state.get(case_export_key, False):
                    export_payload = {
                        "case_id": case_id,
                        "case_name": case_name,
                        "dimension_scores": case_scores,
                        "evaluate": evaluate_result,
                        "conflicts": conflicts_result,
                        "pareto": pareto_result,
                    }
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"case_{case_id}_{timestamp}.json"
                    st.download_button(
                        "Download Case JSON",
                        data=json.dumps(export_payload, indent=2, sort_keys=True),
                        file_name=filename,
                        mime="application/json",
                        key=f"download_case_{case_id}",
                    )

                if not case_screenshot_mode:
                    with st.expander("Raw API Results"):
                        st.json(
                            {
                                "evaluate": evaluate_result,
                                "conflicts": conflicts_result,
                                "pareto": pareto_result,
                            }
                        )

    demo_results_by_context = st.session_state.get("demo_scenario_results", {})
    if not isinstance(demo_results_by_context, dict):
        demo_results_by_context = {}
        st.session_state["demo_scenario_results"] = demo_results_by_context

    resolved_framework_id = framework_id
    if not resolved_framework_id:
        for item in frameworks:
            if isinstance(item, dict) and item.get("id"):
                resolved_framework_id = str(item["id"])
                break

    demo_scoring_method = scoring_method if scoring_method in {"topsis", "wsm"} else "topsis"
    demo_result_key = f"{resolved_framework_id or '__no_framework__'}|{demo_scoring_method}"

    if demo_active:
        st.session_state["demo_mode"] = False
        if not resolved_framework_id:
            st.error("No framework is available to run the demo scenario.")
        else:
            demo_results_by_context.pop(demo_result_key, None)
            demo_stakeholder_ids = ["developer", "regulator", "affected_community"]
            demo_weights_payload = {
                stakeholder_id: {
                    dimension: float(DEMO_WEIGHTS[stakeholder_id][dimension])
                    for dimension in UNIFIED_DIMENSIONS
                }
                for stakeholder_id in demo_stakeholder_ids
            }
            demo_ai_system_payload = {
                "id": "demo_hiring_screening_system",
                "name": DEMO_SCENARIO_NAME,
                "description": DEMO_SCENARIO_DESCRIPTION,
                "context": {
                    "dimension_scores": {
                        dimension: float(DEMO_DIMENSION_SCORES[dimension])
                        for dimension in UNIFIED_DIMENSIONS
                    }
                },
            }

            demo_evaluate_payload = {
                "ai_system": demo_ai_system_payload,
                "framework_ids": [resolved_framework_id],
                "stakeholder_ids": demo_stakeholder_ids,
                "weights": demo_weights_payload,
                "scoring_method": demo_scoring_method,
            }
            demo_conflicts_payload = {
                "ai_system": demo_ai_system_payload,
                "framework_ids": [resolved_framework_id],
                "stakeholder_ids": demo_stakeholder_ids,
                "weights": demo_weights_payload,
            }
            demo_pareto_payload = {
                "ai_system": demo_ai_system_payload,
                "framework_ids": [resolved_framework_id],
                "stakeholder_ids": demo_stakeholder_ids,
                "weights": demo_weights_payload,
                "n_solutions": 8,
                "pop_size": 40,
                "n_gen": 80,
                "seed": 7,
                "deterministic_mode": True,
            }

            with st.spinner("Running demo scenario (Evaluate → Conflicts → Pareto)..."):
                ok_eval, evaluate_data, evaluate_error = api_call(
                    "POST",
                    f"{backend_url}/api/evaluate",
                    payload=demo_evaluate_payload,
                    timeout=60,
                )
                if not ok_eval:
                    show_api_error("Demo scenario evaluation failed", evaluate_error, evaluate_data)
                else:
                    ok_conflict, conflicts_data, conflicts_error = api_call(
                        "POST",
                        f"{backend_url}/api/conflicts",
                        payload=demo_conflicts_payload,
                        timeout=60,
                    )
                    if not ok_conflict:
                        show_api_error(
                            "Demo scenario conflict detection failed",
                            conflicts_error,
                            conflicts_data,
                        )
                    else:
                        ok_pareto, pareto_data, pareto_error = api_call(
                            "POST",
                            f"{backend_url}/api/pareto",
                            payload=demo_pareto_payload,
                            timeout=90,
                        )
                        if not ok_pareto:
                            show_api_error(
                                "Demo scenario pareto generation failed",
                                pareto_error,
                                pareto_data,
                            )
                        else:
                            demo_results_by_context[demo_result_key] = {
                                "framework_id": resolved_framework_id,
                                "scoring_method": demo_scoring_method,
                                "evaluate_payload": demo_evaluate_payload,
                                "conflicts_payload": demo_conflicts_payload,
                                "pareto_payload": demo_pareto_payload,
                                "evaluate_response": evaluate_data,
                                "conflicts_response": conflicts_data,
                                "pareto_response": pareto_data,
                            }
                            bundle = _update_last_run_bundle(
                                page_name="Demo Scenario",
                                backend_url=backend_url,
                                requests_payloads={
                                    "evaluate": demo_evaluate_payload,
                                    "conflicts": demo_conflicts_payload,
                                    "pareto": demo_pareto_payload,
                                },
                                responses_payloads={
                                    "evaluate": evaluate_data,
                                    "conflicts": conflicts_data,
                                    "pareto": pareto_data,
                                },
                                ui_context={
                                    "page": page,
                                    "framework_id": resolved_framework_id,
                                    "stakeholder_ids": demo_stakeholder_ids,
                                    "scoring_method": demo_scoring_method,
                                    "scenario_name": DEMO_SCENARIO_NAME,
                                },
                            )
                            _write_ui_run_log(
                                run_id=str(bundle.get("run_id", str(uuid4()))),
                                page_name="demo_scenario",
                                case_name="hiring_screening_demo",
                                payload={
                                    "timestamp_utc": datetime.utcnow().isoformat() + "Z",
                                    "requests": {
                                        "evaluate": demo_evaluate_payload,
                                        "conflicts": demo_conflicts_payload,
                                        "pareto": demo_pareto_payload,
                                    },
                                    "responses": {
                                        "evaluate": evaluate_data,
                                        "conflicts": conflicts_data,
                                        "pareto": pareto_data,
                                    },
                                },
                            )
            st.session_state["demo_scenario_results"] = demo_results_by_context

    demo_result = demo_results_by_context.get(demo_result_key)
    if isinstance(demo_result, dict):
        demo_evaluate_result = demo_result.get("evaluate_response", {})
        demo_conflicts_result = demo_result.get("conflicts_response", {})
        demo_pareto_result = demo_result.get("pareto_response", {})

        st.divider()
        st.subheader("Demo Scenario Results")
        st.success(
            f"{DEMO_SCENARIO_NAME} completed using framework '{demo_result.get('framework_id')}'."
        )
        render_if_present("Scoring Method", str(demo_result.get("scoring_method", "")).upper())

        st.markdown("### Evaluation")
        demo_overall = float(demo_evaluate_result.get("overall_score", 0.0))
        st.metric("Overall Score", fmt_score(demo_overall))

        stakeholder_scores: dict[str, float] = {}
        evaluate_stakeholder_scores = demo_evaluate_result.get("stakeholder_scores")
        if isinstance(evaluate_stakeholder_scores, dict):
            for stakeholder_id, value in evaluate_stakeholder_scores.items():
                if isinstance(value, (int, float)):
                    stakeholder_scores[str(stakeholder_id)] = float(value)
                elif isinstance(value, dict):
                    raw_score = value.get("overall_score")
                    if isinstance(raw_score, (int, float)):
                        stakeholder_scores[str(stakeholder_id)] = float(raw_score)

        if not stakeholder_scores and isinstance(demo_conflicts_result, dict):
            metadata = demo_conflicts_result.get("metadata", {})
            if isinstance(metadata, dict):
                metadata_scores = metadata.get("stakeholder_scores")
                if isinstance(metadata_scores, dict):
                    for stakeholder_id, value in metadata_scores.items():
                        if isinstance(value, (int, float)):
                            stakeholder_scores[str(stakeholder_id)] = float(value)

        if stakeholder_scores:
            stakeholder_rows = [
                {"stakeholder": stakeholder_id, "overall_score": fmt_score(score)}
                for stakeholder_id, score in stakeholder_scores.items()
            ]
            stakeholder_rows.sort(key=lambda item: item["stakeholder"])
            st.dataframe(stakeholder_rows, width="stretch", hide_index=True)

        st.markdown("### Conflicts")
        top_conflict_pair = "N/A"
        top_conflict_level = "N/A"
        top_conflict_rho: float | None = None
        conflicts = demo_conflicts_result.get("conflicts", []) if isinstance(demo_conflicts_result, dict) else []
        if isinstance(conflicts, list) and conflicts:
            conflict_candidates: list[dict[str, Any]] = []
            for conflict in conflicts:
                if not isinstance(conflict, dict):
                    continue
                rho = conflict.get("spearman_rho")
                if not isinstance(rho, (int, float)):
                    continue
                stakeholder_a = str(conflict.get("stakeholder_a_id", "")).strip()
                stakeholder_b = str(conflict.get("stakeholder_b_id", "")).strip()
                if not stakeholder_a or not stakeholder_b:
                    continue
                conflict_candidates.append(
                    {
                        "pair": f"{stakeholder_a} vs {stakeholder_b}",
                        "level": str(conflict.get("conflict_level", "N/A")),
                        "rho": float(rho),
                    }
                )
            if conflict_candidates:
                top_conflict = min(conflict_candidates, key=lambda item: item["rho"])
                top_conflict_pair = top_conflict["pair"]
                top_conflict_level = top_conflict["level"]
                top_conflict_rho = float(top_conflict["rho"])

        render_if_present("Top conflicting pair", top_conflict_pair)
        render_if_present("Conflict level", top_conflict_level)
        render_if_present("Spearman rho", fmt_score(top_conflict_rho))

        st.markdown("### Pareto Frontier")
        pareto_solutions = demo_pareto_result.get("pareto_solutions", []) if isinstance(demo_pareto_result, dict) else []
        pareto_count = len(pareto_solutions) if isinstance(pareto_solutions, list) else 0
        render_if_present("Pareto points", pareto_count)

        sample_rows: list[dict[str, Any]] = []
        if isinstance(pareto_solutions, list):
            for solution in pareto_solutions:
                if not isinstance(solution, dict):
                    continue
                solution_id = str(solution.get("solution_id", "")).strip()
                if not solution_id:
                    continue
                objective_scores = solution.get("objective_scores", {})
                total_distance = 0.0
                if isinstance(objective_scores, dict):
                    total_distance = float(
                        sum(float(value) for value in objective_scores.values() if isinstance(value, (int, float)))
                    )
                sample_rows.append(
                    {
                        "solution_id": solution_id,
                        "rank": int(solution.get("rank", 0)) if isinstance(solution.get("rank"), (int, float)) else 0,
                        "total_distance": total_distance,
                    }
                )

        if sample_rows:
            sample_rows.sort(key=lambda item: (item["total_distance"], item["rank"], item["solution_id"]))
            sample_table = [
                {
                    "solution_id": item["solution_id"],
                    "rank": item["rank"] if item["rank"] > 0 else "N/A",
                    "total_distance": fmt_score(item["total_distance"]),
                }
                for item in sample_rows[:3]
            ]
            st.dataframe(sample_table, width="stretch", hide_index=True)

    st.caption("MEDF v1.0.1: Feature Frozen Build • Reproducible Artifact.")


if __name__ == "__main__":
    main()
