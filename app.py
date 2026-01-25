import streamlit as st
import base64
from layout.header import render_header
from layout.registro import render_registro
from layout.dashboard import render_dashboard

# CONFIGURACIÓN GENERAL
st.set_page_config(
    page_title="CAPIGASTOS",
    layout="wide",
    page_icon="❤️"
)

# FUNCIÓN PARA CARGAR IMAGEN DE FONDO
def load_image_base64(path):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except:
        return ""

bg_fondo = load_image_base64("assets/images/fondo.jpg")

# ESTILOS GENERALES
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@400;600&display=swap');

html, body, [class*="css"] {{
    font-family: 'Fredoka', sans-serif;
}}

.stApp {{
    background-image: url("data:image/jpg;base64,{bg_fondo}");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}}

.bloque-capigastos {{
    background-color: #FDF5E6;
    border: 2px solid #4A3B2A;
    border-radius: 16px;
    padding: 24px;
    margin: 24px;
    box-shadow: 6px 6px 0px rgba(0,0,0,0.25);
}}

header {{
    visibility: hidden;
}}
</style>
""", unsafe_allow_html=True)

# CONTENEDOR PRINCIPAL (EL PAPEL)
st.markdown('<div class="bloque-capigastos">', unsafe_allow_html=True)

render_header()
render_registro()
render_dashboard()

st.markdown('</div>', unsafe_allow_html=True)
