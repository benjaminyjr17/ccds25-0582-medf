from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

BG = "#0B1220"
CARD_BG = "#0F172A"
TEXT = "#E6E6E6"
MUTED = "#9CA3AF"
ACCENT = "#22C55E"
GRID = "rgba(156,163,175,0.10)"
AXIS_LINE = "rgba(156,163,175,0.24)"


def _coerce_margin_value(value: Any, fallback: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed > 0 else fallback


def _human_label(label: str) -> str:
    return label.replace("_", " ").strip().title()


def apply_plot_theme(fig: go.Figure) -> go.Figure:
    title_text = str(getattr(getattr(fig.layout, "title", None), "text", "") or "").strip()
    if title_text.lower() == "undefined":
        title_text = ""

    raw_margin: dict[str, Any] = {}
    if getattr(fig.layout, "margin", None) is not None:
        raw_margin = fig.layout.margin.to_plotly_json()
    margin = {
        "l": max(_coerce_margin_value(raw_margin.get("l"), 56), 56),
        "r": max(_coerce_margin_value(raw_margin.get("r"), 56), 56),
        "t": max(_coerce_margin_value(raw_margin.get("t"), 72), 72),
        "b": max(_coerce_margin_value(raw_margin.get("b"), 56), 56),
    }

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        font=dict(color=TEXT, size=13),
        title=dict(text=title_text, font=dict(color=TEXT, size=16), y=0.98, yanchor="top"),
        legend=dict(
            font=dict(color=TEXT, size=12),
            title=dict(font=dict(color=TEXT, size=12)),
        ),
        margin=margin,
    )
    fig.update_xaxes(
        tickfont=dict(color=TEXT, size=12),
        titlefont=dict(color=TEXT, size=13),
        automargin=True,
        gridcolor=GRID,
        linecolor=AXIS_LINE,
        zerolinecolor=AXIS_LINE,
        showline=True,
    )
    fig.update_yaxes(
        tickfont=dict(color=TEXT, size=12),
        titlefont=dict(color=TEXT, size=13),
        automargin=True,
        gridcolor=GRID,
        linecolor=AXIS_LINE,
        zerolinecolor=AXIS_LINE,
        showline=True,
    )

    if hasattr(fig.layout, "polar"):
        current_height = getattr(fig.layout, "height", None)
        normalized_height = _coerce_margin_value(current_height, 0)
        if normalized_height < 460:
            fig.update_layout(height=460)
        fig.update_layout(
            polar=dict(
                bgcolor=BG,
                radialaxis=dict(
                    gridcolor=GRID,
                    linecolor=AXIS_LINE,
                    tickfont=dict(color=TEXT, size=12),
                    tickcolor=TEXT,
                    titlefont=dict(color=TEXT, size=13),
                    showline=True,
                ),
                angularaxis=dict(
                    gridcolor=GRID,
                    linecolor=AXIS_LINE,
                    tickfont=dict(color=TEXT, size=12),
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
