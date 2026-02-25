from __future__ import annotations

import io
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4
import zipfile

import plotly.graph_objects as go
import requests
import streamlit as st

UNIFIED_DIMENSIONS = [
    "transparency_explainability",
    "fairness_nondiscrimination",
    "safety_robustness",
    "privacy_data_governance",
    "human_agency_oversight",
    "accountability",
]

BRAND_BLUE_HEX = "#3B82F6"
BRAND_BLUE_FILL_RGBA = "rgba(59, 130, 246, 0.22)"

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

HARD_CAP_EVALS = 50_000

CASE_STUDIES = [
    {
        "id": "facial_recognition",
        "name": "Facial Recognition (High Stakeholder Disagreement)",
        "description": (
            "This scenario models law-enforcement facial recognition with low fairness and privacy ratings. "
            "It is designed to expose structural disagreement between technical and affected-community priorities. "
            "Expected behavior: Priority Conflict (Weights-Only) developer↔affected correlation is negative, "
            "and Pareto tradeoffs are visible."
        ),
        "dimension_scores": {
            "transparency_explainability": 2.5,
            "fairness_nondiscrimination": 1.0,
            "safety_robustness": 5.5,
            "privacy_data_governance": 1.0,
            "human_agency_oversight": 2.5,
            "accountability": 4.0,
        },
    },
    {
        "id": "hiring_recommendation",
        "name": "Hiring Recommendation (Fairness Dominant)",
        "description": (
            "This scenario represents algorithmic hiring support where fairness and oversight drive policy concerns. "
            "Scores are balanced overall but emphasize human-agency controls and accountability. "
            "It is useful for examining whether stakeholder conflict remains moderate under less extreme inputs."
        ),
        "dimension_scores": {
            "transparency_explainability": 4.0,
            "fairness_nondiscrimination": 2.5,
            "safety_robustness": 4.0,
            "privacy_data_governance": 4.0,
            "human_agency_oversight": 5.5,
            "accountability": 4.0,
        },
    },
    {
        "id": "healthcare_diagnostic",
        "name": "Healthcare Diagnostic AI (Safety Dominant)",
        "description": (
            "This scenario captures a clinical decision-support context where safety and robustness are primary. "
            "Privacy and accountability remain high, reflecting regulated healthcare deployment constraints. "
            "It helps illustrate consensus behavior when risk tolerance is low and reliability is prioritized."
        ),
        "dimension_scores": {
            "transparency_explainability": 4.0,
            "fairness_nondiscrimination": 4.0,
            "safety_robustness": 7.0,
            "privacy_data_governance": 5.5,
            "human_agency_oversight": 4.0,
            "accountability": 5.5,
        },
    },
]


def _get_theme_base():
    try:
        base = str(st.get_option("theme.base") or "light").lower()
        if base not in {"dark", "light"}:
            return "light"
        return base
    except Exception:
        return "light"


def _ui_tokens(theme_base: str) -> dict[str, str]:
    return {
        "bg": "#0B1220",
        "panel_bg": "#0F172A",
        "sidebar_bg": "#111C33",
        "text": "#E5E7EB",
        "muted_text": "#A7B0C0",
        "subtle_text": "#7C8598",
        "border": "#243045",
        "primary": "#3B82F6",
        "primary_hover": "#2563EB",
        "success": "#22C55E",
        "warning": "#F59E0B",
        "danger": "#EF4444",
    }

def inject_css(tokens: dict[str, str]) -> None:
    st.markdown(
        f"""
<style>
html, body, [data-testid="stAppViewContainer"] {{
    background: {tokens["bg"]};
    color: {tokens["text"]};
}}
[data-testid="stAppViewContainer"] .main .block-container {{
    max-width: 1240px;
    padding-top: 1.35rem;
    padding-bottom: 1.15rem;
    padding-left: 1.1rem;
    padding-right: 1.1rem;
}}
section[data-testid="stSidebar"] {{
    background: {tokens["sidebar_bg"]};
    border-right: 1px solid {tokens["border"]};
    padding-top: 0.6rem;
}}
h1, h2, h3, h4 {{
    color: {tokens["text"]};
    letter-spacing: 0.01em;
}}
[data-testid="stMarkdownContainer"], p, label {{
    color: {tokens["text"]};
}}
[data-testid="stCaptionContainer"] {{
    color: {tokens["muted_text"]};
}}
.medf-card {{
    background: {tokens["panel_bg"]};
    border: 1px solid {tokens["border"]} !important;
    border-radius: 12px;
    padding: 0.95rem 1rem;
}}
[data-testid="stExpander"], [data-testid="stDataFrame"], .stTable {{
    background: {tokens["panel_bg"]};
    border: 1px solid {tokens["border"]};
    border-radius: 12px;
}}
[data-testid="stHorizontalBlock"] hr, hr {{
    border-color: {tokens["border"]};
}}
</style>
""",
        unsafe_allow_html=True,
    )


def apply_plotly_style(fig: go.Figure, title: str | None = None) -> go.Figure:
    current_title = safe_str(getattr(getattr(fig.layout, "title", None), "text", None)).strip()
    title_text = safe_str(title).strip() if title is not None else current_title
    if title_text.lower() == "undefined":
        title_text = ""

    existing_margin = getattr(fig.layout, "margin", None)

    def _margin_value(side: str, default: int) -> int:
        raw_value = getattr(existing_margin, side, None) if existing_margin is not None else None
        if raw_value is None:
            return default
        return max(default, int(raw_value))

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E5E7EB", size=13),
        title=dict(
            text=title_text,
            font=dict(color="#E5E7EB", size=18),
            y=0.98,
            yanchor="top",
        ),
        legend=dict(
            font=dict(color="#A7B0C0", size=12),
            title=dict(font=dict(color="#A7B0C0", size=12)),
        ),
        margin=dict(
            t=_margin_value("t", 80),
            r=_margin_value("r", 30),
            b=_margin_value("b", 50),
            l=_margin_value("l", 60),
        ),
    )
    fig.update_xaxes(
        tickfont=dict(color="#A7B0C0", size=11),
        title_font=dict(color="#E5E7EB", size=13),
        title_standoff=14,
        gridcolor="rgba(167,176,192,0.18)",
        linecolor="#243045",
        zerolinecolor="#243045",
    )
    fig.update_yaxes(
        tickfont=dict(color="#A7B0C0", size=11),
        title_font=dict(color="#E5E7EB", size=13),
        title_standoff=16,
        gridcolor="rgba(167,176,192,0.18)",
        linecolor="#243045",
        zerolinecolor="#243045",
    )

    if hasattr(fig.layout, "polar"):
        fig.update_layout(
            polar=dict(
                bgcolor="rgba(0,0,0,0)",
                radialaxis=dict(
                    gridcolor="rgba(167,176,192,0.18)",
                    linecolor="#243045",
                    tickfont=dict(color="#A7B0C0"),
                    tickcolor="#A7B0C0",
                    titlefont=dict(color="#E5E7EB"),
                    showline=True,
                ),
                angularaxis=dict(
                    gridcolor="rgba(167,176,192,0.18)",
                    linecolor="#243045",
                    tickfont=dict(color="#A7B0C0"),
                    tickcolor="#A7B0C0",
                    showline=True,
                ),
            )
        )

    for trace in fig.data:
        if isinstance(trace, go.Heatmap):
            if trace.colorbar is None:
                trace.colorbar = {}
            trace.colorbar.tickfont = dict(color="#A7B0C0", size=11)
            if trace.colorbar.title is None:
                trace.colorbar.title = {}
            trace.colorbar.title.font = dict(color="#E5E7EB", size=12)

        if isinstance(trace, go.Parcoords):
            parcoords_dimensions: list[dict[str, Any]] = []
            for dimension in getattr(trace, "dimensions", []) or []:
                label = safe_str(getattr(dimension, "label", "")).strip()
                if label:
                    if label.lower() == "affected community":
                        label = "Affected community"
                    elif label in {"developer", "regulator", "affected_community"}:
                        label = label.replace("_", " ").title()
                parcoords_dimensions.append(
                    {
                        "label": label,
                        "values": list(getattr(dimension, "values", []) or []),
                    }
                )
            if parcoords_dimensions:
                trace.dimensions = parcoords_dimensions
            trace.labelfont = dict(color="#E5E7EB", size=12)
            trace.tickfont = dict(color="#A7B0C0", size=11)
            if getattr(trace, "line", None) is not None:
                colorbar = getattr(trace.line, "colorbar", None)
                if colorbar is not None:
                    title_obj = getattr(colorbar, "title", None)
                    colorbar_title = safe_str(getattr(title_obj, "text", None)).strip()
                    if not colorbar_title:
                        colorbar_title = "Total distance"
                    colorbar.tickfont = dict(color="#A7B0C0", size=11)
                    colorbar.title = dict(
                        text=colorbar_title,
                        side="right",
                        font=dict(color="#E5E7EB", size=11),
                    )
                    colorbar.x = 1.08
                    colorbar.xanchor = "left"
                    fig.update_layout(
                        margin=dict(
                            t=_margin_value("t", 110),
                            r=_margin_value("r", 140),
                            b=_margin_value("b", 50),
                            l=_margin_value("l", 60),
                        ),
                        title=dict(y=0.98, yanchor="top"),
                    )

    return fig


def style_plotly(fig: go.Figure, tokens: dict[str, str]) -> go.Figure:
    _ = tokens
    existing_title = safe_str(getattr(getattr(fig.layout, "title", None), "text", None)).strip()
    title_text = existing_title if existing_title and existing_title.lower() != "undefined" else ""
    return apply_plotly_style(fig, title=title_text)


def _risk_label(score: float) -> tuple[str, str]:
    if score >= 0.8:
        return "LOW", "#22C55E"
    if score >= 0.6:
        return "MEDIUM", "#F59E0B"
    if score >= 0.4:
        return "HIGH", "#EF4444"
    return "CRITICAL", "#EF4444"


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


def fmt_minus(s: str) -> str:
    return str(s).replace("-", UNICODE_MINUS).replace("–", UNICODE_MINUS)


def render_if_present(label: str, value: Any) -> None:
    text = safe_str(value).strip()
    if not text or text.lower() == "undefined":
        return

    if label:
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
        margin={"l": 40, "r": 40, "t": 60, "b": 40},
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
        margin={"l": 40, "r": 40, "t": 60, "b": 40},
    )
    return figure


def main() -> None:
    st.set_page_config(page_title="MEDF Dashboard", layout="wide")
    tokens = _ui_tokens(_get_theme_base())
    inject_css(tokens)
    st.title("MEDF Dashboard")
    with st.expander("About Methodology"):
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

    page = st.radio(
        "Page",
        ["Evaluate", "Conflict Detection", "Pareto Resolution", "Case Studies"],
        index=0,
        horizontal=True,
    )
    st.subheader(page)
    _render_bundle_export()
    if "demo_mode" not in st.session_state:
        st.session_state["demo_mode"] = False
    if "demo_scenario_results" not in st.session_state:
        st.session_state["demo_scenario_results"] = {}
    if "pareto_result" not in st.session_state:
        st.session_state["pareto_result"] = None
    if "pareto_result_stakeholder_ids" not in st.session_state:
        st.session_state["pareto_result_stakeholder_ids"] = []

    with st.sidebar:
        st.header("Configuration")
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
        pareto_n_solutions = 8
        pareto_pop_size = 40
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

            st.markdown("**Search Parameters**")
            pareto_n_solutions = st.slider("n_solutions", min_value=1, max_value=42, value=8, step=1)
            pareto_pop_size = st.slider("pop_size", min_value=10, max_value=250, value=40, step=10)
            pareto_n_gen = st.slider("n_gen", min_value=0, max_value=500, value=150, step=10)

            approx_evals = pareto_pop_size * (max(pareto_n_gen, 1) + 1)
            pareto_n_gen_effective = pareto_n_gen
            if approx_evals > HARD_CAP_EVALS:
                pareto_n_gen_effective = max(0, math.floor(HARD_CAP_EVALS / pareto_pop_size) - 1)
                st.warning("The selected search size is large; n_gen will be capped to keep the demo responsive.")
                st.caption(
                    f"Note: n_gen was capped to {pareto_n_gen_effective} to keep the demo responsive."
                )

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
        col_left, col_right = st.columns([1, 1])
        with col_left:
            ai_system_id = st.text_input("AI system id", value=ai_system_id)
            ai_system_name = st.text_input("AI system name", value=ai_system_name)
            ai_system_description = st.text_area("AI system description", value=ai_system_description)

        with col_right:
            st.subheader("Dimension Scores (Likert 1–7)")
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
                dimension_scores[dimension] = float(
                    st.slider(
                        DIMENSION_DISPLAY_NAMES[dimension],
                        min_value=LIKERT_MIN,
                        max_value=LIKERT_MAX,
                        value=float(st.session_state[f"score_{dimension}"]),
                        step=0.1,
                        format="%.1f",
                        key=f"score_{dimension}",
                    )
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
            overall_score = float(result.get("overall_score", 0.0))
            label, color = _risk_label(overall_score)

            st.subheader("Results")
            metric_col, label_col = st.columns([1, 2])
            with metric_col:
                st.metric("Overall Score", fmt_score(overall_score))
            with label_col:
                st.markdown(
                    f"<span style='color:{color};font-size:1.1rem;font-weight:600;'>Risk: {label}</span>",
                    unsafe_allow_html=True,
                )
            render_if_present("Framework", framework_id)
            render_if_present("Stakeholders", stakeholder_id)
            render_if_present("Scoring Method", scoring_method.upper())
            framework_weighting_mode = _extract_framework_weighting_mode(result.get("notes"))
            render_if_present("Framework Weighting Mode", framework_weighting_mode)

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
                margin={"l": 40, "r": 40, "t": 40, "b": 40},
            )
            st.plotly_chart(style_plotly(fig, tokens), use_container_width=True, key="evaluate_radar")

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
            st.subheader("Per-Framework Scores")
            st.dataframe(table_rows, width="stretch", hide_index=True)
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
            st.subheader("Conflict Detection Results")
            summary_text = result.get("summary")
            if summary_text is not None and str(summary_text).strip().lower() not in {"", "undefined"}:
                st.info(str(summary_text))
            if not screenshot_mode:
                st.info(
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

            demo_box = st.container(border=True)
            with demo_box:
                st.markdown("**Demo Summary**")
                metric_col_1, metric_col_2 = st.columns(2)
                metric_col_1.metric("rho_priority(dev, affected)", rho_weights_dev_affected)
                metric_col_2.metric("rho_contribution(dev, affected)", rho_contrib_dev_affected)

                stakeholders_for_top1 = list(conflict_stakeholder_ids)
                if not stakeholders_for_top1:
                    stakeholders_for_top1 = list(
                        {
                            *(
                                rankings_weights.keys()
                                if isinstance(rankings_weights, dict)
                                else []
                            ),
                            *(
                                rankings_contrib.keys()
                                if isinstance(rankings_contrib, dict)
                                else []
                            ),
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

            pairwise_rho_weights = metadata.get("pairwise_rho_weights")
            include_rho_weights = isinstance(pairwise_rho_weights, dict)
            if isinstance(conflicts, list) and conflicts:
                rows = []
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
                st.dataframe(rows, width="stretch", hide_index=True)
            else:
                st.info("No stakeholder conflicts were returned.")

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
                st.plotly_chart(style_plotly(heatmap, tokens), use_container_width=True, key="conflict_heatmap")
            else:
                st.info("No correlation matrix returned in metadata.")
    elif page == "Pareto Resolution":
        if generate_pareto_clicked:
            if not framework_id:
                st.error("Please select a framework.")
                return
            if len(pareto_stakeholder_ids) < 2:
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

        st.subheader("Pareto Resolution Results")
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

        st.subheader("Solutions")
        st.dataframe(table_rows, width="stretch", hide_index=True)

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
                    f"- Rank: {selected_rank}",
                    f"- Total distance: {fmt_score(selected_total_distance)}",
                    f"- Utility (WSM ablation): {utility_text}",
                    f"- Top-1 consensus dimension: {top_dimension}",
                    f"- Highest stakeholder distance: {highest_distance_stakeholder}",
                ]
            )
        )

        st.subheader("Consensus Weights Radar")
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
            margin={"l": 40, "r": 40, "t": 40, "b": 40},
        )
        st.plotly_chart(
            style_plotly(radar_figure, tokens),
            use_container_width=True,
            key=f"pareto_weights_radar_{selected_solution_id}",
        )

        st.subheader("Stakeholder Distance (Lower = Better Alignment)")
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
            title="Stakeholder Distance (Lower = Better Alignment)",
            xaxis_title="Stakeholder",
            yaxis_title="Distance",
            margin={"l": 40, "r": 40, "t": 60, "b": 40},
        )
        st.plotly_chart(
            style_plotly(bar_figure, tokens),
            use_container_width=True,
            key=f"pareto_distance_bar_{selected_solution_id}",
        )

        st.subheader("Tradeoff Visualization")
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
                    marker={"size": 14, "color": "#d62728", "symbol": "diamond"},
                )
            )
            scatter_figure.update_layout(
                title=f"Tradeoff: {stakeholder_a} vs {stakeholder_b}",
                xaxis_title=f"{stakeholder_a} distance",
                yaxis_title=f"{stakeholder_b} distance",
                margin={"l": 40, "r": 40, "t": 60, "b": 40},
            )
            st.plotly_chart(
                style_plotly(scatter_figure, tokens),
                use_container_width=True,
                key=f"pareto_tradeoff_scatter_{stakeholder_a}_{stakeholder_b}",
            )
        elif len(stakeholder_ids) >= 3:
            stakeholder_display_labels = {
                "developer": "Developer",
                "regulator": "Regulator",
                "affected_community": "Affected community",
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
                                "text": "Total distance",
                                "side": "right",
                                "font": {"color": "#E5E7EB", "size": 11},
                            },
                            "tickfont": {"color": "#A7B0C0"},
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
                labelfont={"color": "#E5E7EB", "size": 12},
                tickfont={"color": "#A7B0C0", "size": 11},
            )
            parallel_figure.update_layout(
                font={"color": "#E5E7EB"},
                title={
                    "text": "Stakeholder Distance Tradeoffs",
                    "y": 0.99,
                    "yanchor": "top",
                    "x": 0.01,
                    "xanchor": "left",
                },
                margin={"l": 40, "r": 140, "t": 130, "b": 48},
            )
            st.plotly_chart(
                style_plotly(parallel_figure, tokens),
                use_container_width=True,
                key=f"pareto_tradeoff_parallel_{len(stakeholder_ids)}",
            )
            st.caption(f"Selected solution: {selected_solution_id} (rank {selected_rank})")
        else:
            st.info("Select at least 2 stakeholders to view tradeoffs.")
    else:
        case_framework_ids = [framework_id] if framework_id else []
        case_stakeholder_ids = ["developer", "regulator", "affected_community"]

        for case in CASE_STUDIES:
            case_id = str(case["id"])
            case_name = str(case["name"])
            case_description = str(case["description"])
            case_scores = {
                dimension: float(case["dimension_scores"][dimension])
                for dimension in UNIFIED_DIMENSIONS
            }
            framework_key = framework_id or "no_framework_selected"
            case_result_key = f"case_result_{case_id}_{framework_key}"
            case_export_key = f"case_export_{case_id}_{framework_key}"

            with st.expander(f"Case: {case_name}", expanded=not case_screenshot_mode):
                st.write(case_description)
                if not case_screenshot_mode:
                    st.caption(
                        "Input dimension scores: "
                        + ", ".join(
                            f"{DIMENSION_DISPLAY_NAMES[dimension]}={case_scores[dimension]:.1f}"
                            for dimension in UNIFIED_DIMENSIONS
                        )
                    )

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

    st.caption("MEDF v1.0.0: Feature Frozen Build • Reproducible Artifact.")


if __name__ == "__main__":
    main()
