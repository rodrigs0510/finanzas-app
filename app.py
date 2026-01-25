import streamlit as st

with open("styles.css", "r", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

import streamlit as st

# ---------------- CONFIG GENERAL ----------------
st.set_page_config(
    page_title="CAPIGASTOS",
    layout="wide",
    page_icon="🐹"
)

# ---------------- CARGAR CSS ----------------
with open("styles.css", "r", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ---------------- FONDO ----------------
st.markdown(
    """
    <style>
    .stApp {
        background-image: url("assets/images/fondo.jpg");
        background-size: cover;
        background-attachment: fixed;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------- IMPORTAR SECCIONES ----------------
from layout.header import render_header
from layout.registro import render_registro
from layout.dashboard import render_dashboard

# ---------------- EJECUCIÓN ----------------
render_header()

col_izq, col_der = st.columns([1, 3], gap="medium")

with col_izq:
    render_registro()

with col_der:
    render_dashboard()

