from __future__ import annotations

import html

import streamlit as st


def brand() -> None:
    st.sidebar.markdown(
        '<div class="fg-brand"><div class="fg-logo">F</div><div>'
        '<p class="fg-brand-title">FinGuard AI</p>'
        '<p class="fg-brand-sub">Smart personal finance workspace</p>'
        '</div></div>',
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, note: str = "") -> None:
    st.markdown(
        '<div class="fg-card">'
        f'<div class="fg-card-label">{html.escape(label)}</div>'
        f'<div class="fg-card-value">{html.escape(value)}</div>'
        f'<div class="fg-card-note">{html.escape(note)}</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def security_notice() -> None:
    st.markdown(
        '<div class="fg-security">Your sign-in, profile, and account records are protected and organized for each user.</div>',
        unsafe_allow_html=True,
    )


def local_only_notice() -> None:
    return None


def feature_chips(items: list[str]) -> None:
    chips = ''.join(f'<span class="fg-chip">{html.escape(item)}</span>' for item in items)
    st.markdown(chips, unsafe_allow_html=True)
