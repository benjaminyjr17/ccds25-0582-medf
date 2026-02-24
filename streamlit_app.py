from __future__ import annotations

import io
import json
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

DIMENSION_DISPLAY_NAMES = {
    "transparency_explainability": "Transparency and Explainability",
    "fairness_nondiscrimination": "Fairness and Non-discrimination",
    "safety_robustness": "Safety and Robustness",
    "privacy_data_governance": "Privacy and Data Governance",
    "human_agency_oversight": "Human Agency and Oversight",
    "accountability": "Accountability",
}

PRESET_BASELINE = {
    "transparency_explainability": 2,
    "fairness_nondiscrimination": 1,
    "safety_robustness": 4,
    "privacy_data_governance": 1,
    "human_agency_oversight": 2,
    "accountability": 3,
}

PRESET_FLIPPED = {
    "transparency_explainability": 4,
    "fairness_nondiscrimination": 5,
    "safety_robustness": 1,
    "privacy_data_governance": 5,
    "human_agency_oversight": 5,
    "accountability": 4,
}

PRESET_SAFETY_HEAVY = {
    "transparency_explainability": 3,
    "fairness_nondiscrimination": 3,
    "safety_robustness": 5,
    "privacy_data_governance": 3,
    "human_agency_oversight": 3,
    "accountability": 3,
}

CASE_STUDIES = [
    {
        "id": "facial_recognition",
        "name": "Facial Recognition (High Stakeholder Disagreement)",
        "description": (
            "This scenario models law-enforcement facial recognition with low fairness and privacy ratings. "
            "It is designed to expose structural disagreement between technical and affected-community priorities. "
            "Expected behavior: weights-only developer↔affected correlation is negative and Pareto tradeoffs are visible."
        ),
        "dimension_scores": {
            "transparency_explainability": 2,
            "fairness_nondiscrimination": 1,
            "safety_robustness": 4,
            "privacy_data_governance": 1,
            "human_agency_oversight": 2,
            "accountability": 3,
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
            "transparency_explainability": 3,
            "fairness_nondiscrimination": 2,
            "safety_robustness": 3,
            "privacy_data_governance": 3,
            "human_agency_oversight": 4,
            "accountability": 3,
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
            "transparency_explainability": 3,
            "fairness_nondiscrimination": 3,
            "safety_robustness": 5,
            "privacy_data_governance": 4,
            "human_agency_oversight": 3,
            "accountability": 4,
        },
    },
]


def _get_theme_base():
    try:
        return st.get_option("theme.base") or "light"
    except Exception:
        return "light"


def _theme_tokens():
    base = _get_theme_base()
    if base == "dark":
        return {
            "plot_text": "#e5e7eb",
            "plot_grid": "rgba(255,255,255,0.15)",
            "plot_axis": "rgba(255,255,255,0.30)",
            "panel_border": "rgba(255,255,255,0.08)",
        }
    return {
        "plot_text": "#111827",
        "plot_grid": "rgba(17,24,39,0.12)",
        "plot_axis": "rgba(17,24,39,0.22)",
        "panel_border": "rgba(17,24,39,0.08)",
    }


def _style_plotly(fig):
    tokens = _theme_tokens()

    fig.update_layout(
        font=dict(color=tokens["plot_text"], size=14),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=40, t=60, b=40),
    )

    if hasattr(fig.layout, "polar"):
        fig.update_layout(
            polar=dict(
                bgcolor="rgba(0,0,0,0)",
                radialaxis=dict(
                    gridcolor=tokens["plot_grid"],
                    linecolor=tokens["plot_axis"],
                    tickfont=dict(color=tokens["plot_text"]),
                    tickcolor=tokens["plot_axis"],
                ),
                angularaxis=dict(
                    gridcolor=tokens["plot_grid"],
                    linecolor=tokens["plot_axis"],
                    tickfont=dict(color=tokens["plot_text"]),
                    tickcolor=tokens["plot_axis"],
                ),
            )
        )

    if hasattr(fig.layout, "xaxis"):
        fig.update_layout(
            xaxis=dict(
                gridcolor=tokens["plot_grid"],
                tickfont=dict(color=tokens["plot_text"]),
                linecolor=tokens["plot_axis"],
            ),
            yaxis=dict(
                gridcolor=tokens["plot_grid"],
                tickfont=dict(color=tokens["plot_text"]),
                linecolor=tokens["plot_axis"],
            ),
        )

    return fig


def _risk_label(score: float) -> tuple[str, str]:
    if score >= 0.8:
        return "LOW", "green"
    if score >= 0.6:
        return "MEDIUM", "goldenrod"
    if score >= 0.4:
        return "HIGH", "orange"
    return "CRITICAL", "red"


def _apply_dimension_preset(preset: dict[str, int]) -> None:
    for dimension, score in preset.items():
        st.session_state[f"score_{dimension}"] = int(score)


@st.cache_data(show_spinner=False, ttl=60)
def load_frameworks(backend_url: str) -> list[dict[str, Any]]:
    response = requests.get(f"{backend_url}/api/frameworks", timeout=15)
    response.raise_for_status()
    try:
        payload = response.json()
    except ValueError as exc:
        raise ValueError("Invalid JSON received from /api/frameworks.") from exc
    if not isinstance(payload, list):
        raise ValueError("Unexpected /api/frameworks response shape.")
    return payload


@st.cache_data(show_spinner=False, ttl=60)
def load_stakeholders(backend_url: str) -> list[dict[str, Any]]:
    response = requests.get(f"{backend_url}/api/stakeholders", timeout=15)
    response.raise_for_status()
    try:
        payload = response.json()
    except ValueError as exc:
        raise ValueError("Invalid JSON received from /api/stakeholders.") from exc
    if not isinstance(payload, list):
        raise ValueError("Unexpected /api/stakeholders response shape.")
    return payload


def _safe_json(value: Any) -> Any:
    try:
        return json.loads(json.dumps(value, default=str))
    except Exception:
        return str(value)


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

    figure = go.Figure()
    figure.add_trace(
        go.Scatterpolar(
            r=radar_values_closed,
            theta=radar_labels_closed,
            fill="toself",
            name=title,
        )
    )
    figure.update_layout(
        title=title,
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
    z_text = [[f"{value:.2f}" for value in row] for row in z_values]

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
    st.markdown(
        """
<style>
.block-container {
    padding-top: 2rem;
}
section[data-testid="stSidebar"] {
    border-right: 1px solid rgba(128,128,128,0.15);
}
button[kind="primary"] {
    border-radius: 8px !important;
}
button[kind="secondary"] {
    border-radius: 8px !important;
}
</style>
""",
        unsafe_allow_html=True,
    )
    st.title("MEDF Dashboard")

    page = st.radio(
        "Page",
        ["Evaluate", "Conflict Detection", "Pareto Resolution", "Case Studies"],
        index=0,
        horizontal=True,
    )
    st.subheader(page)
    _render_bundle_export()

    with st.sidebar:
        st.header("Configuration")
        backend_url = st.text_input("Backend URL", value="http://127.0.0.1:8000").rstrip("/")

        frameworks: list[dict[str, Any]] = []
        stakeholders: list[dict[str, Any]] = []
        with st.spinner("Loading frameworks and stakeholders..."):
            try:
                frameworks = load_frameworks(backend_url)
                stakeholders = load_stakeholders(backend_url)
            except Exception as exc:
                st.error(f"Failed to load backend data: {exc}")

        framework_id = ""
        stakeholder_id = ""
        scoring_method = "topsis"
        conflict_metric = "Weights-only (priority conflict)"
        detect_clicked = False
        screenshot_mode = False
        selected_stakeholder: dict[str, Any] | None = None
        conflict_stakeholder_ids: list[str] = []
        pareto_stakeholder_ids: list[str] = []
        pareto_n_solutions = 8
        pareto_pop_size = 40
        pareto_n_gen = 80
        generate_pareto_clicked = False
        case_screenshot_mode = False

        framework_options = {
            f"{item.get('name', item.get('id', 'unknown'))} ({item.get('id', 'unknown')})": item
            for item in frameworks
            if isinstance(item, dict)
        }
        if framework_options:
            framework_label = st.selectbox("Framework", list(framework_options.keys()))
            framework_id = str(framework_options[framework_label].get("id", ""))
        else:
            st.warning("No frameworks available from backend.")

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
            scoring_method = st.radio("Scoring method", ["topsis", "wsm"], horizontal=True)

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
            conflict_metric = st.radio(
                "Conflict metric",
                ["Weights-only (priority conflict)", "Contrib-based (system-salience conflict)"],
                index=0,
            )
            screenshot_mode = st.checkbox("Screenshot mode", value=False)
            detect_clicked = st.button("Detect Conflicts", type="primary")
        elif page == "Pareto Resolution":
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

            pareto_n_solutions = st.slider("n_solutions", min_value=1, max_value=20, value=8, step=1)
            pareto_pop_size = st.slider("pop_size", min_value=16, max_value=128, value=40, step=8)
            pareto_n_gen = st.slider("n_gen", min_value=20, max_value=200, value=80, step=10)

            if len(pareto_stakeholder_ids) < 2:
                st.warning("Select at least 2 stakeholders to enable Pareto generation.")
            generate_pareto_clicked = st.button(
                "Generate Pareto Solutions",
                type="primary",
                disabled=len(pareto_stakeholder_ids) < 2,
            )
        else:
            case_screenshot_mode = st.checkbox("Screenshot Mode", value=False)
            st.caption("Case Studies runs fixed scenarios through Evaluate → Conflicts → Pareto.")

    ai_system_id = "demo_facerec"
    ai_system_name = "Demo Facial Recognition System"
    ai_system_description = "MVP evaluation input"
    dimension_scores: dict[str, float] = {
        dimension: float(value)
        for dimension, value in PRESET_BASELINE.items()
    }

    if page != "Case Studies":
        col_left, col_right = st.columns([1, 1])
        with col_left:
            ai_system_id = st.text_input("AI system id", value="demo_facerec")
            ai_system_name = st.text_input("AI system name", value="Demo Facial Recognition System")
            ai_system_description = st.text_area("AI system description", value="MVP evaluation input")

        with col_right:
            st.subheader("Dimension Scores (Likert 1–5)")
            if page in {"Conflict Detection", "Pareto Resolution"}:
                preset_col_1, preset_col_2, preset_col_3 = st.columns(3)
                if preset_col_1.button("Preset: Baseline (2,1,4,1,2,3)"):
                    _apply_dimension_preset(PRESET_BASELINE)
                if preset_col_2.button("Preset: Flipped (4,5,1,5,5,4)"):
                    _apply_dimension_preset(PRESET_FLIPPED)
                if preset_col_3.button("Preset: Safety-heavy (3,3,5,3,3,3)"):
                    _apply_dimension_preset(PRESET_SAFETY_HEAVY)

            default_scores = PRESET_BASELINE
            for dimension in UNIFIED_DIMENSIONS:
                session_key = f"score_{dimension}"
                if session_key not in st.session_state:
                    st.session_state[session_key] = int(default_scores[dimension])
            for dimension in UNIFIED_DIMENSIONS:
                dimension_scores[dimension] = float(
                    st.slider(
                        DIMENSION_DISPLAY_NAMES[dimension],
                        min_value=1,
                        max_value=5,
                        value=int(st.session_state[f"score_{dimension}"]),
                        step=1,
                        key=f"score_{dimension}",
                    )
                )
    else:
        if not case_screenshot_mode:
            st.caption("Fixed framework: eu_altai | Fixed stakeholders: developer, regulator, affected_community")

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
                try:
                    response = requests.post(
                        f"{backend_url}/api/evaluate",
                        json=payload,
                        timeout=30,
                    )
                except Exception as exc:
                    st.error(f"Request failed: {exc}")
                    return

            if response.status_code != 200:
                st.error(response.text)
                return

            result = response.json()
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
                st.metric("Overall Score", f"{overall_score:.4f}")
            with label_col:
                st.markdown(
                    f"<span style='color:{color};font-size:1.1rem;font-weight:600;'>Risk: {label}</span>",
                    unsafe_allow_html=True,
                )

            framework_scores = result.get("framework_scores", [])
            if not framework_scores:
                st.warning("No framework scores returned.")
                return

            first_framework = framework_scores[0]
            dim_scores = first_framework.get("dimension_scores", {})
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
                    name=first_framework.get("framework_id", "framework"),
                )
            )
            fig.update_layout(
                polar={"radialaxis": {"visible": True, "range": [0, 1]}},
                showlegend=False,
                margin={"l": 40, "r": 40, "t": 40, "b": 40},
            )
            st.plotly_chart(_style_plotly(fig), width="stretch", key="evaluate_radar")

            table_rows = []
            for row in framework_scores:
                row_score = float(row.get("score", 0.0))
                row_risk = row.get("risk_level")
                if row_risk is None:
                    row_risk = _risk_label(row_score)[0].lower()
                table_rows.append(
                    {
                        "framework_id": row.get("framework_id"),
                        "score": round(row_score, 4),
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
                try:
                    response = requests.post(
                        f"{backend_url}/api/conflicts",
                        json=payload,
                        timeout=30,
                    )
                except Exception as exc:
                    st.error(f"Request failed: {exc}")
                    return

            if response.status_code != 200:
                st.error(response.text)
                return

            result = response.json()
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
            if result.get("summary"):
                st.info(str(result["summary"]))
            if not screenshot_mode:
                st.caption("Switch conflict metric in the sidebar to compare weights-only vs contrib-based views.")

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
                    rho_weights_dev_affected = f"{float(rho_weights_raw):.4f}"
            if isinstance(correlation_matrix_contrib, dict):
                rho_contrib_raw = (
                    correlation_matrix_contrib.get("developer", {})
                    .get("affected_community")
                )
                if isinstance(rho_contrib_raw, (int, float)):
                    rho_contrib_dev_affected = f"{float(rho_contrib_raw):.4f}"

            demo_box = st.container(border=True)
            with demo_box:
                st.markdown("**Demo Summary**")
                metric_col_1, metric_col_2 = st.columns(2)
                metric_col_1.metric("rho_weights(dev, affected)", rho_weights_dev_affected)
                metric_col_2.metric("rho_contrib(dev, affected)", rho_contrib_dev_affected)

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
                            "top1_contrib": contrib_top_1,
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
                        "spearman_rho": round(float(conflict.get("spearman_rho", 0.0)), 4),
                        "conflict_level": conflict.get("conflict_level"),
                        "conflicting_dimensions": conflict.get("conflicting_dimensions", []),
                    }
                    if include_rho_weights:
                        stakeholder_a = str(conflict.get("stakeholder_a_id", ""))
                        stakeholder_b = str(conflict.get("stakeholder_b_id", ""))
                        pair_key = "|".join(sorted((stakeholder_a, stakeholder_b)))
                        rho_weights = pairwise_rho_weights.get(pair_key)
                        row["rho_weights"] = (
                            round(float(rho_weights), 4)
                            if rho_weights is not None
                            else None
                        )
                    rows.append(row)
                st.dataframe(rows, width="stretch", hide_index=True)
            else:
                st.info("No stakeholder conflicts were returned.")

            if conflict_metric == "Weights-only (priority conflict)":
                correlation_matrix = correlation_matrix_weights
                matrix_title = "Stakeholder Spearman Correlation Matrix (Weights-only)"
            else:
                correlation_matrix = correlation_matrix_contrib
                matrix_title = "Stakeholder Spearman Correlation Matrix (Contrib-based)"

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
                    [f"{value:.2f}" for value in row]
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
                st.plotly_chart(_style_plotly(heatmap), width="stretch", key="conflict_heatmap")
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
                "n_gen": pareto_n_gen,
            }

            with st.spinner("Generating Pareto solutions..."):
                try:
                    response = requests.post(
                        f"{backend_url}/api/pareto",
                        json=payload,
                        timeout=60,
                    )
                except Exception as exc:
                    st.error(f"Request failed: {exc}")
                    return

            if response.status_code != 200:
                st.error(response.text)
                return

            result = response.json()
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
                    "n_gen": pareto_n_gen,
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
            st.subheader("Pareto Resolution Results")
            summary = result.get("summary")
            if summary:
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
                stakeholder_ids = list(pareto_stakeholder_ids)
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
                    "total_distance": round(total_distance, 4),
                    "utility_wsm": round(utility_wsm, 4) if utility_wsm is not None else None,
                }
                for stakeholder_id in stakeholder_ids:
                    row[stakeholder_id] = round(float(objective_scores.get(stakeholder_id, 0.0)), 4)
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

            solution_ids = [item["solution_id"] for item in parsed_solutions]
            selected_solution_id = st.selectbox("Select Solution", options=solution_ids)
            selected_solution = next(
                item for item in parsed_solutions if item["solution_id"] == selected_solution_id
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

            utility_text = "N/A"
            if isinstance(selected_utility, float):
                utility_text = f"{selected_utility:.4f}"

            st.info(
                "\n".join(
                    [
                        "**Resolution Summary**",
                        f"- Rank: {selected_rank}",
                        f"- Total distance: {selected_total_distance:.4f}",
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
            radar_figure = go.Figure()
            radar_figure.add_trace(
                go.Scatterpolar(
                    r=radar_values_closed,
                    theta=radar_labels_closed,
                    fill="toself",
                    name=selected_solution_id,
                )
            )
            radar_figure.update_layout(
                polar={"radialaxis": {"visible": True, "range": [0, 1]}},
                showlegend=False,
                margin={"l": 40, "r": 40, "t": 40, "b": 40},
            )
            st.plotly_chart(
                _style_plotly(radar_figure),
                width="stretch",
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
                _style_plotly(bar_figure),
                width="stretch",
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
                        marker={"size": 9, "color": "#1f77b4"},
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
                    _style_plotly(scatter_figure),
                    width="stretch",
                    key=f"pareto_tradeoff_scatter_{stakeholder_a}_{stakeholder_b}",
                )
            elif len(stakeholder_ids) >= 3:
                dimension_specs = [
                    {
                        "label": stakeholder_id,
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
                            "colorbar": {"title": "Total distance"},
                        },
                        dimensions=dimension_specs,
                    )
                )
                parallel_figure.update_layout(
                    title="Stakeholder Distance Tradeoffs",
                    margin={"l": 40, "r": 40, "t": 60, "b": 40},
                )
                st.plotly_chart(
                    _style_plotly(parallel_figure),
                    width="stretch",
                    key=f"pareto_tradeoff_parallel_{len(stakeholder_ids)}",
                )
                st.caption(f"Selected solution: {selected_solution_id} (rank {selected_rank})")
            else:
                st.info("Select at least 2 stakeholders to view tradeoffs.")
    else:
        case_framework_ids = ["eu_altai"]
        case_stakeholder_ids = ["developer", "regulator", "affected_community"]

        for case in CASE_STUDIES:
            case_id = str(case["id"])
            case_name = str(case["name"])
            case_description = str(case["description"])
            case_scores = {
                dimension: float(case["dimension_scores"][dimension])
                for dimension in UNIFIED_DIMENSIONS
            }
            case_result_key = f"case_result_{case_id}"
            case_export_key = f"case_export_{case_id}"

            with st.expander(f"Case: {case_name}", expanded=not case_screenshot_mode):
                st.write(case_description)
                if not case_screenshot_mode:
                    st.caption(
                        "Input dimension scores: "
                        + ", ".join(
                            f"{DIMENSION_DISPLAY_NAMES[dimension]}={int(case_scores[dimension])}"
                            for dimension in UNIFIED_DIMENSIONS
                        )
                    )

                run_case_clicked = st.button("Run Case Study", key=f"run_case_{case_id}", type="primary")

                if run_case_clicked:
                    try:
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
                            try:
                                evaluate_response = requests.post(
                                    f"{backend_url}/api/evaluate",
                                    json=evaluate_payload,
                                    timeout=60,
                                )
                                if evaluate_response.status_code != 200:
                                    st.error(evaluate_response.text)
                                    continue

                                conflicts_response = requests.post(
                                    f"{backend_url}/api/conflicts",
                                    json=conflicts_payload,
                                    timeout=60,
                                )
                                if conflicts_response.status_code != 200:
                                    st.error(conflicts_response.text)
                                    continue

                                pareto_response = requests.post(
                                    f"{backend_url}/api/pareto",
                                    json=pareto_payload,
                                    timeout=90,
                                )
                                if pareto_response.status_code != 200:
                                    st.error(pareto_response.text)
                                    continue
                            except Exception as exc:
                                st.error(f"Case API call failed: {exc}")
                                continue

                        st.session_state[case_result_key] = {
                            "evaluate_payload": evaluate_payload,
                            "conflicts_payload": conflicts_payload,
                            "pareto_payload": pareto_payload,
                            "evaluate_response": evaluate_response.json(),
                            "conflicts_response": conflicts_response.json(),
                            "pareto_response": pareto_response.json(),
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
                                "evaluate": evaluate_response.json(),
                                "conflicts": conflicts_response.json(),
                                "pareto": pareto_response.json(),
                            },
                            ui_context={
                                "page": page,
                                "framework_id": case_framework_ids[0],
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
                                    "evaluate": evaluate_response.json(),
                                    "conflicts": conflicts_response.json(),
                                    "pareto": pareto_response.json(),
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

                st.markdown("---")
                st.markdown("### SECTION A — Evaluation Result")
                overall_score = float(evaluate_result.get("overall_score", 0.0))
                st.metric("Overall Score", f"{overall_score:.4f}")

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
                            _style_plotly(eval_radar),
                            width="stretch",
                            key=f"case_{case_id}_evaluation_radar",
                        )
                    else:
                        st.warning("Evaluation dimension scores were not returned.")
                else:
                    st.warning("No evaluation framework scores returned.")

                st.markdown("---")
                st.markdown("### SECTION B — Conflict Analysis")
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
                            title="Weights-only Correlation",
                        )
                        st.plotly_chart(
                            _style_plotly(weights_heatmap),
                            width="stretch",
                            key=f"case_{case_id}_weights_heatmap",
                        )
                    else:
                        st.info("Weights-only matrix unavailable.")
                with matrix_col_2:
                    if isinstance(matrix_contrib, dict):
                        contrib_heatmap = _build_correlation_heatmap(
                            matrix_contrib,
                            labels=matrix_labels,
                            title="Contrib-based Correlation",
                        )
                        st.plotly_chart(
                            _style_plotly(contrib_heatmap),
                            width="stretch",
                            key=f"case_{case_id}_contrib_heatmap",
                        )
                    else:
                        st.info("Contrib-based matrix unavailable.")

                rho_weights = "N/A"
                rho_contrib = "N/A"
                if isinstance(matrix_weights, dict):
                    rho_value = matrix_weights.get("developer", {}).get("affected_community")
                    if isinstance(rho_value, (int, float)):
                        rho_weights = f"{float(rho_value):.4f}"
                if isinstance(matrix_contrib, dict):
                    rho_value = matrix_contrib.get("developer", {}).get("affected_community")
                    if isinstance(rho_value, (int, float)):
                        rho_contrib = f"{float(rho_value):.4f}"

                rho_col_1, rho_col_2 = st.columns(2)
                rho_col_1.metric("dev↔affected weights rho", rho_weights)
                rho_col_2.metric("dev↔affected contrib rho", rho_contrib)

                st.markdown("---")
                st.markdown("### SECTION C — Pareto Resolution")
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
                        "total_distance": round(total_distance, 4),
                        "utility_wsm": round(utility_value, 4) if utility_value is not None else None,
                    }
                    for stakeholder_id in case_stakeholder_ids:
                        row[stakeholder_id] = round(float(objective_scores.get(stakeholder_id, 0.0)), 4)

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
                        _style_plotly(consensus_radar),
                        width="stretch",
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
                        _style_plotly(stakeholder_distance_bar),
                        width="stretch",
                        key=f"case_{case_id}_distance_bar_{rank_1_solution['solution_id']}",
                    )
                else:
                    st.warning("No Pareto solutions were returned.")

                st.markdown("---")
                st.markdown("### SECTION D — Export JSON")
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

    st.caption("MEDF v1.0 — Feature Frozen Build • Reproducible Artifact")


if __name__ == "__main__":
    main()
