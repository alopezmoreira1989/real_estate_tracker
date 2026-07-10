"""Streamlit dashboard entry point: `streamlit run src/real_estate/dashboard.py`.

Bridges the composition root (which knows every concrete adapter) and the presentation
layer's pure rendering functions — mirrors how composition.py wires CliContext for the CLI,
except Streamlit's execution model requires an actual runnable script rather than a function
composition.py can call into on its own, so this one-line bootstrap lives beside __main__.py
instead of inside presentation/.
"""

from real_estate.composition import run_dashboard

run_dashboard()
