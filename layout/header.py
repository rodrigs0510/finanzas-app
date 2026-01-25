import streamlit as st
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO_PATH = os.path.join(BASE_DIR, "assets", "imagenes", "logo.png")

def render_header():
    st.image(LOGO_PATH, width=80)
