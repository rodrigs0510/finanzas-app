import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import base64
import pytz

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="CAPIGASTOS", layout="wide", page_icon="🐹")

# --- 2. ESTILOS "CLEAN UI" (SIN CAJAS FEAS) ---
def cargar_estilos(imagen_local):
    try:
        with open(imagen_local, "rb") as f:
            b64_img = base64.b64encode(f.read()).decode()
        
        st.markdown(f"""
        <style>
        /* 1. FONDO GENERAL */
        .stApp {{
            background-image: url(data:image/jpg;base64,{b64_img});
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        
        /* 2. FUERA CAJAS GLOBALES (Limpieza) */
        /* Eliminamos los bordes y fondos por defecto de Streamlit para empezar de cero */
        div[data-testid="stVerticalBlock"] {{
            gap: 1rem;
        }}

        /* 3. FORMULARIO Y TARJETAS ESPECÍFICAS (Las "Islas") */
        /* Solo el formulario y los contenedores marcados tendrán fondo blanco */
        form, div[data-testid="stMetric"], div[data-testid="stExpander"] {{
            background-color: rgba(255, 255, 255, 0.95) !important;
            border-radius: 20px !important; /* Bordes MUY redondeados */
            padding: 20px !important;
            box-shadow: 0 8px 16px rgba(0,0,0,0.1) !important;
            border: none !important;
        }}

        /* 4. TÍTULOS (Flotando sobre el fondo) */
        h1 {{
            color: #FFFFFF !important;
            text-shadow: 0px 4px 10px rgba(0,0,0,0.6);
            font-size: 3.5rem !important;
            font-weight: 900 !important;
            margin-bottom: 0px !important;
        }}
        
        h3 {{
            color: #333333 !important;
            font-weight: 700 !important;
        }}
