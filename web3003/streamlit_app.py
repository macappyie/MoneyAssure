import streamlit as st
import subprocess
import time
import os

st.set_page_config(page_title="Intraday Scanner", layout="wide")

st.title("📊 Intraday Scanner Dashboard")

st.markdown("Flask backend starting...")

# Start Flask server only once
if "flask_started" not in st.session_state:
    st.session_state.flask_started = True
    subprocess.Popen(["python", "app.py"])
    time.sleep(3)

st.success("Backend running")

st.markdown(
    """
    ### Open Scanner:
    👉 http://localhost:3002
    """
)

st.components.v1.iframe(
    src="http://localhost:3002",
    height=900,
    scrolling=True
)

