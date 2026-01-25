import streamlit as st
import base64
from layout.header import render_header
from layout.registro import render_registro
from layout.dashboard import render_dashboard


st.set_page_config(
    page_title="CAPIGASTOS",
    layout="wide",
    page_icon="❤️"
)

def load_image_base64(path):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except:
        return ""

bg_fondo = load_image_base64("images/fondo.jpg")

render_header()
render_registro()
render_dashboard()




