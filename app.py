import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pytz
import base64

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="CAPIGASTOS", layout="wide", page_icon="🐹")

# --- 2. PALETA DE COLORES (ESTILO CAPIGASTOS) ---
COLOR_FONDO = "#F5E6CA"  # Beige suave
COLOR_MARRON_OSCURO = "#5C4033" # Texto y bordes fuertes
COLOR_MARRON_CLARO = "#D2B48C" # Fondo de paneles
COLOR_VERDE = "#8FBC8F" # Botones Agregar/Pagado
COLOR_ROJO = "#CD5C5C" # Botones Eliminar/No Pagado
COLOR_TARJETA = "#8B4513" # Color de las tarjetas de crédito

# --- 3. CSS MAESTRO (LA MAGIA VISUAL) ---
def cargar_estilos():
    st.markdown(f"""
    <style>
    /* IMPORTAR FUENTE (Opcional, estilo redondeado) */
    @import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@400;600&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Fredoka', sans-serif;
        color: {COLOR_MARRON_OSCURO};
    }}

    /* FONDO GENERAL */
    .stApp {{
        background-color: {COLOR_FONDO};
        /* Si tienes una imagen de fondo de paisaje capibara, descomenta esto: */
        /* background-image: url("https://tu-imagen.com/fondo.jpg"); */
        background-size: cover;
    }}

    /* --- BOTONES OVALADOS (ESTILO KRY&ROD) --- */
    div.stButton > button {{
        background-color: {COLOR_MARRON_CLARO};
        color: {COLOR_MARRON_OSCURO};
        border: 2px solid {COLOR_MARRON_OSCURO};
        border-radius: 20px; /* Borde muy redondo */
        font-weight: bold;
        box-shadow: 2px 2px 0px {COLOR_MARRON_OSCURO};
        transition: all 0.2s;
    }}
    div.stButton > button:hover {{
        transform: translateY(-2px);
        box-shadow: 4px 4px 0px {COLOR_MARRON_OSCURO};
    }}
    
    /* Botones Verdes (Agregar/Pagado) */
    .btn-verde {{
        background-color: {COLOR_VERDE} !important;
    }}
    
    /* --- TARJETAS (CONTENEDORES) --- */
    .caja-marron {{
        background-color: #E6D2B5;
        border: 3px solid {COLOR_MARRON_OSCURO};
        border-radius: 15px;
        padding: 15px;
        margin-bottom: 10px;
    }}

    /* --- INPUTS PERSONALIZADOS --- */
    .stTextInput input, .stNumberInput input, .stSelectbox div, .stDateInput input {{
        background-color: #FFF8DC !important;
        border: 2px solid {COLOR_MARRON_OSCURO} !important;
        border-radius: 10px !important;
        color: {COLOR_MARRON_OSCURO} !important;
    }}

    /* OCULTAR COSAS DE STREAMLIT */
    header {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    
    </style>
    """, unsafe_allow_html=True)

cargar_estilos()

# --- 4. CONEXIÓN (TU CÓDIGO DE SIEMPRE) ---
@st.cache_resource
def conectar():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    if "gcp_service_account" in st.secrets:
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    return gspread.authorize(creds).open("Finanzas_RodrigoKrys")

# --- 5. ESTRUCTURA DEL GRID (LAYOUT) ---
# Dividimos la pantalla en:
# COL 1: PANEL IZQUIERDO (Registro) - 25% ancho
# COL 2: PANEL DERECHO (Dashboard) - 75% ancho

col_registro, col_dashboard = st.columns([1, 3], gap="large")

# === PANEL IZQUIERDO (REGISTRO) ===
with col_registro:
    # Simulación del cuadro beige de la izquierda
    with st.container(border=True):
        # LOGO Y USUARIO
        c_logo, c_user = st.columns([1, 2])
        c_logo.write("🐹 LOGO") # Aquí pondremos tu imagen luego
        c_user.selectbox("USUARIO:", ["RODRIGO", "KRYS"], label_visibility="collapsed")
        
        st.markdown("---")
        st.markdown("### REGISTRO")
        
        # Tipo de Registro (Radio buttons pero bonitos)
        tipo = st.radio("TIPO:", ["GASTO", "INGRESO", "TRANSFERENCIA"])
        
        # Campos
        st.text_input("CATEGORIA")
        st.number_input("MONTO S/", min_value=0.0)
        st.text_input("DESCRIPCION")
        
        # Botón Guardar Grande
        st.button("GUARDAR", use_container_width=True)

# === PANEL DERECHO (DASHBOARD) ===
with col_dashboard:
    
    # 1. HEADER (Botones Superiores)
    c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 2, 2])
    c1.markdown("## RESUMEN ENERO:") # Título
    c2.button("MES")
    c3.button("AÑO")
    c4.metric("SALDO TOTAL", "S/ 0.00")
    c5.metric("AHORRO TOTAL", "S/ 0.00")
    
    st.markdown("---")
    
    # 2. SECCIÓN CUENTAS (CARRUSEL)
    # Título y Botones Agregar/Eliminar en la misma línea
    col_h1, col_h2, col_h3 = st.columns([2, 1, 1])
    col_h1.markdown("### 💳 MIS CUENTAS")
    col_h2.button("AGREGAR", key="add_c")
    col_h3.button("ELIMINAR", key="del_c")
    
    # Aquí irán las tarjetas marrones
    col_card_prev, col_cards, col_card_next = st.columns([0.2, 4, 0.2])
    with col_card_prev:
        st.button("◀", key="prev_c")
    with col_cards:
        # Simulamos 3 tarjetas como en tu imagen
        cc1, cc2, cc3 = st.columns(3)
        with cc1:
            st.info("💳 BCP\n\nS/ 1,500") # Placeholder
        with cc2:
            st.info("💳 INTERBANK\n\nS/ 200")
        with cc3:
            st.info("💳 EFECTIVO\n\nS/ 50")
    with col_card_next:
        st.button("▶", key="next_c")
        
    st.markdown("---")

    # 3. SECCIÓN PRESUPUESTOS
    col_p1, col_p2, col_p3 = st.columns([2, 1, 1])
    col_p1.markdown("### 📊 PRESUPUESTOS")
    col_p2.button("AGREGAR", key="add_p")
    col_p3.button("ELIMINAR", key="del_p")
    
    # Barras de progreso
    cp1, cp2 = st.columns(2)
    with cp1:
        st.progress(70)
        st.caption("COMIDA: S/ 300 / S/ 500")
    with cp2:
        st.progress(20)
        st.caption("SALIDAS: S/ 100 / S/ 400")

    st.markdown("---")
    
    # 4. MOVIMIENTOS Y PAGOS PENDIENTES
    col_mov, col_pagos = st.columns([2, 1])
    
    with col_mov:
        st.markdown("### MOVIMIENTOS 🐹")
        # Tabla placeholder
        df_fake = pd.DataFrame({
            "N°": [1, 2], "Fecha": ["24/01", "24/01"], "Monto": [20, 50], "Acción": ["🗑️", "🗑️"]
        })
        st.dataframe(df_fake, use_container_width=True, hide_index=True)
        
    with col_pagos:
        st.markdown("### PAGOS PENDIENTES 🐻")
        # Lista placeholder
        st.warning("Luz del Sur - S/ 150 (Vence 30/01)")
        c_pay1, c_pay2 = st.columns(2)
        c_pay1.button("PAGADO", key="p1")
        c_pay2.button("NO PAGADO", key="np1")
