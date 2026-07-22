from __future__ import annotations

import html

import streamlit as st

_FINANCE_SVG = """data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='1600' height='900' viewBox='0 0 1600 900'%3E%3Cdefs%3E%3ClinearGradient id='g' x1='0' x2='1' y1='0' y2='1'%3E%3Cstop stop-color='%230cb4ff' offset='0'/%3E%3Cstop stop-color='%2336d399' offset='1'/%3E%3C/linearGradient%3E%3C/defs%3E%3Crect fill='%23050b14' width='1600' height='900'/%3E%3Cg opacity='.12'%3E%3Cpath d='M0 690 C240 620 360 730 600 560 S980 430 1200 300 S1450 260 1600 170' fill='none' stroke='url(%23g)' stroke-width='6'/%3E%3Cpath d='M0 760 C250 700 380 780 640 640 S1020 550 1280 410 S1500 360 1600 300' fill='none' stroke='%235aa9ff' stroke-opacity='.6' stroke-width='4'/%3E%3C/g%3E%3Cg fill='%23ffffff' fill-opacity='.06'%3E%3Crect x='1080' y='560' width='40' height='190' rx='10'/%3E%3Crect x='1140' y='500' width='40' height='250' rx='10'/%3E%3Crect x='1200' y='420' width='40' height='330' rx='10'/%3E%3Crect x='1260' y='350' width='40' height='400' rx='10'/%3E%3C/g%3E%3Cg fill='none' stroke='%2336d399' stroke-opacity='.16'%3E%3Ccircle cx='260' cy='190' r='115'/%3E%3Ccircle cx='260' cy='190' r='165'/%3E%3C/g%3E%3C/svg%3E"""

THEME_CSS = f"""
<style>
:root {{
    --fg-bg: #050b14;
    --fg-panel: #0b1726;
    --fg-panel2: #102238;
    --fg-border: rgba(145, 167, 194, 0.18);
    --fg-text: #f4f8fc;
    --fg-muted: #91a7c2;
    --fg-green: #36d399;
    --fg-blue: #5aa9ff;
    --fg-gold: #f5c451;
}}

html,
body,
[class*="css"] {{
    font-family: Inter, "Segoe UI", Arial, sans-serif;
}}

.stApp {{
    background-image:
        linear-gradient(rgba(5, 11, 20, 0.90), rgba(5, 11, 20, 0.95)),
        url("{_FINANCE_SVG}");
    background-size: cover, cover;
    background-attachment: fixed;
    background-color: var(--fg-bg);
    color: var(--fg-text);
}}

/* Header must remain available because Streamlit places sidebar controls here. */
header[data-testid="stHeader"],
[data-testid="stHeader"] {{
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
    pointer-events: auto !important;
    height: 3.2rem !important;
    background: rgba(5, 11, 20, 0.60) !important;
    backdrop-filter: blur(12px);
}}

[data-testid="stSidebar"] {{
    background: linear-gradient(
        180deg,
        rgba(8, 19, 34, 0.98),
        rgba(6, 16, 28, 0.98)
    );
    border-right: 1px solid var(--fg-border);
    min-width: 300px;
}}

/* Sidebar reopen control for different Streamlit versions. */
div[data-testid="collapsedControl"],
div[data-testid="stSidebarCollapsedControl"] {{
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    pointer-events: auto !important;
    position: fixed !important;
    top: 0.65rem !important;
    left: 0.75rem !important;
    z-index: 999999 !important;
    width: 2.75rem !important;
    height: 2.75rem !important;
    align-items: center !important;
    justify-content: center !important;
    background: rgba(11, 23, 38, 0.98) !important;
    border: 1px solid rgba(90, 169, 255, 0.55) !important;
    border-radius: 11px !important;
    box-shadow: 0 8px 28px rgba(0, 0, 0, 0.35) !important;
}}

div[data-testid="collapsedControl"]:hover,
div[data-testid="stSidebarCollapsedControl"]:hover {{
    background: rgba(21, 48, 77, 0.98) !important;
    border-color: rgba(54, 211, 153, 0.48) !important;
}}

div[data-testid="collapsedControl"] button,
div[data-testid="stSidebarCollapsedControl"] button,
button[aria-label="Open sidebar"],
button[aria-label="Expand sidebar"] {{
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    pointer-events: auto !important;
    align-items: center !important;
    justify-content: center !important;
    width: 100% !important;
    height: 100% !important;
    color: var(--fg-text) !important;
}}

div[data-testid="collapsedControl"] svg,
div[data-testid="stSidebarCollapsedControl"] svg,
button[aria-label="Open sidebar"] svg,
button[aria-label="Expand sidebar"] svg {{
    width: 1.45rem !important;
    height: 1.45rem !important;
    color: var(--fg-text) !important;
    fill: var(--fg-text) !important;
}}

/* Sidebar close control. */
[data-testid="stSidebarCollapseButton"],
button[aria-label="Collapse sidebar"] {{
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    pointer-events: auto !important;
}}

/* Do not hide the complete toolbar because it can contain sidebar controls. */
[data-testid="stToolbar"] {{
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    pointer-events: auto !important;
    background: transparent !important;
}}

/* Hide only unwanted Streamlit controls. */
[data-testid="stStatusWidget"],
[data-testid="stDecoration"],
[data-testid="stDeployButton"],
[data-testid="stMainMenu"] {{
    display: none !important;
}}

.block-container {{
    max-width: 1500px;
    padding-top: 1rem;
    padding-bottom: 4rem;
}}

h1,
h2,
h3 {{
    color: var(--fg-text);
    letter-spacing: -0.025em;
}}

[data-testid="stPlotlyChart"] {{
    border: 1px solid var(--fg-border);
    border-radius: 16px;
    overflow: hidden;
    background: rgba(7, 18, 31, 0.52);
}}

.fg-brand {{
    display: flex;
    align-items: center;
    gap: 0.8rem;
    padding: 0.3rem 0 1rem;
}}

.fg-logo {{
    width: 42px;
    height: 42px;
    border-radius: 14px;
    display: grid;
    place-items: center;
    font-weight: 900;
    color: #04110d;
    background: linear-gradient(135deg, #36d399, #66b4ff);
    box-shadow: 0 10px 28px rgba(54, 211, 153, 0.22);
}}

.fg-brand-title {{
    color: #ffffff !important;
    font-size: 1.05rem;
    font-weight: 800;
    margin: 0 !important;
}}

.fg-brand-sub {{
    color: var(--fg-muted) !important;
    font-size: 0.73rem;
    margin: 0.1rem 0 0 !important;
}}

.fg-hero {{
    position: relative;
    overflow: hidden;
    padding: 1.45rem 1.55rem;
    border: 1px solid var(--fg-border);
    border-radius: 22px;
    background: linear-gradient(
        135deg,
        rgba(16, 34, 56, 0.97),
        rgba(8, 22, 37, 0.95)
    );
    box-shadow: 0 18px 60px rgba(0, 0, 0, 0.22);
    margin-bottom: 1.2rem;
}}

.fg-hero::after {{
    content: "";
    position: absolute;
    width: 260px;
    height: 260px;
    right: -100px;
    top: -160px;
    border-radius: 50%;
    background: radial-gradient(
        circle,
        rgba(54, 211, 153, 0.18),
        transparent 68%
    );
}}

.fg-eyebrow {{
    color: var(--fg-green);
    font-size: 0.76rem;
    font-weight: 800;
    letter-spacing: 0.16em;
    text-transform: uppercase;
}}

.fg-hero h1 {{
    margin: 0.35rem 0;
    font-size: clamp(1.8rem, 3vw, 3.05rem);
    line-height: 1.06;
}}

.fg-hero p {{
    color: var(--fg-muted);
    max-width: 900px;
    margin: 0;
}}

.fg-card {{
    min-height: 128px;
    border: 1px solid var(--fg-border);
    border-radius: 18px;
    padding: 1rem 1.05rem;
    background: linear-gradient(
        145deg,
        rgba(16, 34, 56, 0.96),
        rgba(8, 23, 38, 0.94)
    );
    box-shadow: 0 14px 38px rgba(0, 0, 0, 0.18);
    transition: transform 0.18s ease, border-color 0.18s ease;
}}

.fg-card:hover {{
    transform: translateY(-2px);
    border-color: rgba(90, 169, 255, 0.38);
}}

.fg-card-label {{
    color: var(--fg-muted);
    font-size: 0.76rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}}

.fg-card-value {{
    color: #ffffff;
    font-size: 1.62rem;
    font-weight: 800;
    margin: 0.38rem 0;
}}

.fg-card-note {{
    color: var(--fg-muted);
    font-size: 0.78rem;
}}

.fg-security {{
    border: 1px solid rgba(54, 211, 153, 0.22);
    background: rgba(54, 211, 153, 0.08);
    color: #bff5df;
    border-radius: 14px;
    padding: 0.75rem 0.9rem;
    font-size: 0.82rem;
}}

.fg-chip {{
    display: inline-block;
    padding: 0.25rem 0.55rem;
    border: 1px solid var(--fg-border);
    border-radius: 999px;
    color: var(--fg-muted);
    font-size: 0.74rem;
    margin: 0.15rem 0.2rem 0.15rem 0;
    background: rgba(10, 24, 40, 0.75);
}}

div[data-testid="stForm"] {{
    border: 1px solid var(--fg-border);
    border-radius: 20px;
    padding: 1.15rem;
    background: rgba(10, 24, 40, 0.82);
}}

.stButton > button,
.stDownloadButton > button,
[data-testid="baseButton-primary"] {{
    border-radius: 11px !important;
    border: 1px solid rgba(90, 169, 255, 0.35) !important;
    min-height: 2.55rem;
    font-weight: 700;
}}

[data-testid="stMetric"] {{
    border: 1px solid var(--fg-border);
    background: rgba(11, 23, 38, 0.90);
    border-radius: 16px;
    padding: 0.75rem;
}}

[data-testid="stDataFrame"] {{
    border: 1px solid var(--fg-border);
    border-radius: 14px;
    overflow: hidden;
}}

.stTabs [data-baseweb="tab-list"] {{
    gap: 0.4rem;
    background: rgba(10, 24, 40, 0.72);
    padding: 0.35rem;
    border-radius: 13px;
    overflow-x: auto;
}}

.stTabs [data-baseweb="tab"] {{
    border-radius: 10px;
    padding: 0.45rem 0.8rem;
}}

.stTabs [aria-selected="true"] {{
    background: #15304d !important;
}}

[data-testid="stSidebar"] [data-testid="stRadio"] label {{
    border: 1px solid var(--fg-border);
    border-radius: 12px;
    padding: 0.55rem 0.7rem !important;
    margin-bottom: 0.38rem;
    background: rgba(9, 22, 38, 0.68);
}}

[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {{
    background: rgba(90, 169, 255, 0.10);
    border-color: rgba(90, 169, 255, 0.30);
}}

[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {{
    background: linear-gradient(
        135deg,
        rgba(54, 211, 153, 0.20),
        rgba(90, 169, 255, 0.18)
    );
    border-color: rgba(54, 211, 153, 0.48);
}}

[data-testid="stFileUploaderDropzone"] {{
    border: 1px dashed rgba(90, 169, 255, 0.45);
    background: rgba(10, 24, 40, 0.78);
    border-radius: 16px;
}}

[data-testid="stExpander"] {{
    border: 1px solid var(--fg-border);
    border-radius: 14px;
    background: rgba(8, 20, 34, 0.58);
}}

footer,
#MainMenu {{
    display: none !important;
}}

@media (max-width: 900px) {{
    .block-container {{
        padding-left: 0.8rem;
        padding-right: 0.8rem;
    }}

    .fg-hero {{
        padding: 1.1rem;
    }}

    .fg-card {{
        min-height: 108px;
    }}

    div[data-testid="collapsedControl"],
    div[data-testid="stSidebarCollapsedControl"] {{
        top: 0.5rem !important;
        left: 0.5rem !important;
    }}
}}
</style>
"""


def apply_theme() -> None:
    """Apply the FinGuard application theme."""
    st.markdown(THEME_CSS, unsafe_allow_html=True)


def hero(eyebrow: str, title: str, subtitle: str) -> None:
    """Render a reusable page hero section."""
    st.markdown(
        '<section class="fg-hero">'
        f'<div class="fg-eyebrow">{html.escape(eyebrow)}</div>'
        f'<h1>{html.escape(title)}</h1>'
        f'<p>{html.escape(subtitle)}</p>'
        "</section>",
        unsafe_allow_html=True,
    )
