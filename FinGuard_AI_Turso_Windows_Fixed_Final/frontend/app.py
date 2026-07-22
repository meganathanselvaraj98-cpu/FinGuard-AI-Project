"""Compatibility launcher: run with `streamlit run frontend/app.py`."""

from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().parents[1] / "app.py"), run_name="__main__")
