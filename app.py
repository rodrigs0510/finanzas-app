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

bg_fondo = load_image_base64("assets/images/fondo.jpg")

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@400;600&display=swap');

/* RESET TOTAL */
html, body {{
    margin: 0;
    padding: 0;
}}

.block-container {{
    padding-top: 0rem !important;
    margin-top: 0rem !important;
}}

header {{
    display: none;
}}

.stApp {{
    background-image: url("data:image/jpg;base64,{bg_fondo}");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
    font-family: 'Fredoka', sans-serif;
}}

.bloque-capigastos {{
    background-color: #FDF5E6;
    border: 2px solid #4A3B2A;
    border-radius: 18px;
    padding: 32px;
    margin: 24px;
    box-shadow: 6px 6px 0px rgba(0,0,0,0.25);
}}
</style>
""", unsafe_allow_html=True)

# BLOQUE ÚNICO (COMO EL BOCETO)
st.markdown('<div class="bloque-capigastos">', unsafe_allow_html=True)

render_header()
render_registro()
render_dashboard()

st.markdown('</div>', unsafe_allow_html=True)

