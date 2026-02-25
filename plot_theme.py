from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

BG = "#0B1220"
CARD_BG = "#111827"
TEXT = "#E6E6E6"
MUTED = "#A7B0C0"
ACCENT = "#22C55E"


def _human_label(label: str) -> str:
    return label.replace("_", " ").strip().title()


def apply_plot_theme(fig: go.Figure) -> go.Figure:
    title_text = str(getattr(getattr(fig.layout, "title", None), "text", "") or "").strip()
    if title_text.lower() == "undefined":
        title_text = ""

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        font=dict(color=TEXT, size=13),
        title=dict(text=title_text, font=dict(color=TEXT), y=0.98, yanchor="top"),
        legend=dict(
            font=dict(color=TEXT, size=12),
            title=dict(font=dict(color=TEXT, size=12)),
        ),
    )
    fig.update_xaxes(
        tickfont=dict(color=TEXT),
        titlefont=dict(color=TEXT),
        gridcolor="rgba(167,176,192,0.16)",
        linecolor="rgba(167,176,192,0.28)",
        zerolinecolor="rgba(167,176,192,0.28)",
    )
    fig.update_yaxes(
        tickfont=dict(color=TEXT),
        titlefont=dict(color=TEXT),
        gridcolor="rgba(167,176,192,0.16)",
        linecolor="rgba(167,176,192,0.28)",
        zerolinecolor="rgba(167,176,192,0.28)",
    )

    if hasattr(fig.layout, "polar"):
        fig.update_layout(
            polar=dict(
                bgcolor=BG,
                radialaxis=dict(
                    gridcolor="rgba(167,176,192,0.16)",
                    linecolor="rgba(167,176,192,0.28)",
                    tickfont=dict(color=TEXT),
                    tickcolor=TEXT,
                    titlefont=dict(color=TEXT),
                    showline=True,
                ),
                angularaxis=dict(
                    gridcolor="rgba(167,176,192,0.16)",
                    linecolor="rgba(167,176,192,0.28)",
                    tickfont=dict(color=TEXT),
                    tickcolor=TEXT,
                    showline=True,
                ),
            )
        )

    for trace in fig.data:
        if isinstance(trace, go.Heatmap):
            if trace.colorbar is None:
                trace.colorbar = {}
            trace.colorbar.tickfont = dict(color=TEXT)
            if trace.colorbar.title is None:
                trace.colorbar.title = {}
            trace.colorbar.title.font = dict(color=TEXT)

        if isinstance(trace, go.Parcoords):
            trace.labelfont = dict(color=TEXT, size=12)
            trace.tickfont = dict(color=TEXT, size=11)

            raw_dimensions: list[dict[str, Any]] = trace._props.get("dimensions", [])
            for raw_dimension in raw_dimensions:
                raw_dimension["label"] = _human_label(str(raw_dimension.get("label", "")))
                # Plotly parcoords dimensions do not expose tickfont in the Python schema,
                # so we inject it in trace JSON for explicit high-contrast tick styling.
                raw_dimension["tickfont"] = {"color": TEXT}

            if getattr(trace, "line", None) is not None:
                colorbar = getattr(trace.line, "colorbar", None)
                if colorbar is not None:
                    title_obj = getattr(colorbar, "title", None)
                    colorbar_title = str(getattr(title_obj, "text", "") or "").strip() or "Total Distance"
                    colorbar.tickfont = dict(color=TEXT)
                    colorbar.title = dict(text=colorbar_title, font=dict(color=TEXT))
                    colorbar.x = 1.08
                    colorbar.xanchor = "left"

    return fig
