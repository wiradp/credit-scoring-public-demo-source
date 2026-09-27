"""Streamlit app for the contract-driven portfolio demo."""

import sys
from pathlib import Path

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(_REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT))

from app.src.pages import PAGE_RENDERERS
from app.src.ui_text import APP_TITLE, GLOBAL_DISCLAIMER, STAGE_LABEL


def _get_streamlit():
    try:
        import streamlit as st
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Streamlit is required to run the contract demo app. "
            "Install project UI dependencies before launching the app."
        ) from exc
    return st


def configure_page() -> None:
    st = _get_streamlit()
    st.set_page_config(
        page_title=APP_TITLE,
        layout="wide",
        initial_sidebar_state="expanded",
    )


def render_sidebar() -> str:
    st = _get_streamlit()
    page_names = list(PAGE_RENDERERS.keys())
    st.sidebar.title("Contract Demo")
    st.sidebar.caption(STAGE_LABEL)
    return st.sidebar.radio("Navigation", page_names, index=0)


def render_global_disclaimer() -> None:
    st = _get_streamlit()
    st.warning(GLOBAL_DISCLAIMER)


def main() -> None:
    configure_page()
    selected_page = render_sidebar()
    render_global_disclaimer()
    PAGE_RENDERERS[selected_page]()


if __name__ == "__main__":
    main()
