from __future__ import annotations

from typing import Any

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


def _risk_label(score: float) -> tuple[str, str]:
    if score >= 0.8:
        return "LOW", "green"
    if score >= 0.6:
        return "MEDIUM", "goldenrod"
    if score >= 0.4:
        return "HIGH", "orange"
    return "CRITICAL", "red"


@st.cache_data(show_spinner=False)
def load_frameworks(backend_url: str) -> list[dict[str, Any]]:
    response = requests.get(f"{backend_url}/api/frameworks", timeout=15)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise ValueError("Unexpected /api/frameworks response shape.")
    return payload


@st.cache_data(show_spinner=False)
def load_stakeholders(backend_url: str) -> list[dict[str, Any]]:
    response = requests.get(f"{backend_url}/api/stakeholders", timeout=15)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise ValueError("Unexpected /api/stakeholders response shape.")
    return payload


def main() -> None:
    st.set_page_config(page_title="MEDF Demo", layout="wide")
    st.title("MEDF Demo")
    st.caption("Stage 2D MVP frontend for evaluating one framework and one stakeholder.")

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
        scoring_method = st.radio("Scoring method", ["topsis", "wsm"], horizontal=True)

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
        selected_stakeholder: dict[str, Any] | None = None
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
            base_weights = {dimension: 1.0 / len(UNIFIED_DIMENSIONS) for dimension in UNIFIED_DIMENSIONS}

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

    col_left, col_right = st.columns([1, 1])
    with col_left:
        ai_system_id = st.text_input("AI system id", value="demo_facerec")
        ai_system_name = st.text_input("AI system name", value="Demo Facial Recognition System")
        ai_system_description = st.text_area("AI system description", value="MVP evaluation input")

    with col_right:
        st.subheader("Dimension Scores (Likert 1–5)")
        dimension_scores: dict[str, float] = {}
        default_scores = {
            "transparency_explainability": 2,
            "fairness_nondiscrimination": 1,
            "safety_robustness": 4,
            "privacy_data_governance": 1,
            "human_agency_oversight": 2,
            "accountability": 3,
        }
        for dimension in UNIFIED_DIMENSIONS:
            dimension_scores[dimension] = float(
                st.slider(
                    DIMENSION_DISPLAY_NAMES[dimension],
                    min_value=1,
                    max_value=5,
                    value=int(default_scores[dimension]),
                    step=1,
                    key=f"score_{dimension}",
                )
            )

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
            st.error(f"Backend error {response.status_code}: {response.text}")
            return

        result = response.json()
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
        st.plotly_chart(fig, width="stretch")

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


if __name__ == "__main__":
    main()
