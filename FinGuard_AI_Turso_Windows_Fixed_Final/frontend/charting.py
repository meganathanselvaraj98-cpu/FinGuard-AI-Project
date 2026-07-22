from __future__ import annotations

import io
import re
import unicodedata
from typing import Any

import streamlit as st


def _plain_title(fig: Any, fallback: str = "FinGuard chart") -> str:
    try:
        title = fig.layout.title.text
    except Exception:
        title = None
    if isinstance(title, str) and title.strip():
        return re.sub(r"<[^>]+>", "", title).strip()
    return fallback


def _filename(title: str) -> str:
    normalized = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^A-Za-z0-9]+", "_", normalized).strip("_").lower()
    return slug[:80] or "finguard_chart"


def chart_config(fig: Any) -> dict[str, Any]:
    title = _plain_title(fig)
    return {
        "displaylogo": False,
        "displayModeBar": True,
        "responsive": True,
        "scrollZoom": True,
        "doubleClick": "reset+autosize",
        "showTips": True,
        "modeBarButtonsToAdd": ["drawline", "drawrect", "eraseshape"],
        "toImageButtonOptions": {
            "format": "png",
            "filename": _filename(title),
            "height": 900,
            "width": 1600,
            "scale": 2,
        },
    }


def polish_figure(fig: Any) -> Any:
    title = _plain_title(fig)
    fig.update_layout(
        title={"text": title, "x": 0.02, "xanchor": "left"},
        hoverlabel={"namelength": -1},
        transition={"duration": 220, "easing": "cubic-in-out"},
        uirevision="finguard-stable-view",
    )
    return fig


def show_chart(fig: Any, *, container: Any = st, key: str | None = None) -> None:
    fig = polish_figure(fig)
    container.plotly_chart(
        fig,
        width="stretch",
        key=key,
        config=chart_config(fig),
    )


def show_matplotlib(fig: Any, title: str, *, container: Any = st, key: str | None = None) -> None:
    if not getattr(fig, "_suptitle", None):
        fig.suptitle(title, fontsize=14, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    container.pyplot(fig, width="stretch")
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=220, bbox_inches="tight", facecolor=fig.get_facecolor())
    buffer.seek(0)
    container.download_button(
        f"Download {title}",
        data=buffer.getvalue(),
        file_name=f"{_filename(title)}.png",
        mime="image/png",
        key=key,
        width="stretch",
    )
