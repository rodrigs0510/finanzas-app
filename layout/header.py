import streamlit as st
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO = os.path.join(BASE_DIR, "assets", "images", "logo.png")

def render_header():
    col1, col2 = st.columns([1, 5])
    with col1:
        st.image(LOGO, width=80)
    with col2:
        st.title("CAPIGASTOS 🐹")
