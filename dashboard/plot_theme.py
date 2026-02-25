from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

DARK_PLOT_CANVAS = "#0f172a"
PLOT_TEXT_COLOR = "#f8fafc"
PLOT_AXIS_COLOR = "rgba(248,250,252,0.65)"
PLOT_GRID_COLOR = "rgba(226,232,240,0.18)"
LEGEND_TEXT_COLOR = "#e2e8f0"


def _axis_style(*, text_color: str, axis_color: str, grid_color: str) -> dict[str, Any]:
    return {
        "gridcolor": grid_color,
        "tickcolor": axis_color,
        "tickfont": {"color": text_color},
        "titlefont": {"color": text_color},
        "linecolor": axis_color,
        "zerolinecolor": axis_color,
        "showline": True,
    }


def dark_plot_layout(
    *,
    title_text: str,
    canvas_bg: str = DARK_PLOT_CANVAS,
    text_color: str = PLOT_TEXT_COLOR,
    axis_color: str = PLOT_AXIS_COLOR,
    grid_color: str = PLOT_GRID_COLOR,
    legend_color: str = LEGEND_TEXT_COLOR,
) -> dict[str, Any]:
    return {
        "template": "plotly_dark",
        "font": {"color": text_color, "size": 14},
        "font_color": text_color,
        "paper_bgcolor": canvas_bg,
        "plot_bgcolor": canvas_bg,
        "margin": {"l": 40, "r": 40, "t": 84, "b": 48},
        "title": {
            "text": title_text,
            "font": {"color": text_color},
            "y": 0.98,
            "yanchor": "top",
        },
        "legend": {
            "font": {"color": legend_color},
            "title": {"font": {"color": legend_color}},
        },
        "xaxis": _axis_style(
            text_color=text_color,
            axis_color=axis_color,
            grid_color=grid_color,
        ),
        "yaxis": _axis_style(
            text_color=text_color,
            axis_color=axis_color,
            grid_color=grid_color,
        ),
        "polar": {
            "bgcolor": canvas_bg,
            "radialaxis": {
                "showgrid": True,
                "gridcolor": grid_color,
                "linecolor": axis_color,
                "tickfont": {"color": text_color},
                "tickcolor": axis_color,
                "titlefont": {"color": text_color},
                "showline": True,
            },
            "angularaxis": {
                "showgrid": True,
                "gridcolor": grid_color,
                "linecolor": axis_color,
                "tickfont": {"color": text_color},
                "tickcolor": axis_color,
                "showline": True,
            },
        },
    }


def apply_dark_plot_theme(
    fig: go.Figure,
    *,
    title_text: str,
    canvas_bg: str = DARK_PLOT_CANVAS,
) -> go.Figure:
    normalized_title = str(title_text).strip()
    if normalized_title.lower() == "undefined":
        normalized_title = ""

    fig.update_layout(
        **dark_plot_layout(
            title_text=normalized_title,
            canvas_bg=canvas_bg,
        )
    )
    fig.update_xaxes(title_standoff=12)
    fig.update_yaxes(title_standoff=14)

    for trace in fig.data:
        if isinstance(trace, go.Heatmap):
            if trace.colorbar is None:
                trace.colorbar = {}
            trace.colorbar.tickfont = {"color": PLOT_TEXT_COLOR}
            if trace.colorbar.title is None:
                trace.colorbar.title = {}
            trace.colorbar.title.font = {"color": PLOT_TEXT_COLOR}

        if isinstance(trace, go.Parcoords):
            trace.labelfont = {"color": PLOT_TEXT_COLOR, "size": 12}
            trace.tickfont = {"color": PLOT_TEXT_COLOR, "size": 11}
            if getattr(trace, "line", None) is not None:
                colorbar = getattr(trace.line, "colorbar", None)
                if colorbar is not None:
                    colorbar.tickfont = {"color": PLOT_TEXT_COLOR}
                    if colorbar.title is not None:
                        colorbar.title.font = {"color": PLOT_TEXT_COLOR}

    return fig
