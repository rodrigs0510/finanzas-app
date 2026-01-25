import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import pytz 
import base64

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="CAPIGASTOS", layout="centered", page_icon="🐹")

# --- CARGAR IMÁGENES ---
def get_image_as_base64(file_path):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except Exception:
        return None

img_tarjeta = get_image_as_base64("Tarjeta fondo.png")
img_logo = get_image_as_base64("logo.png") 

# --- CONEXIÓN ---
@st.cache_resource
def conectar_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    if "gcp_service_account" in st.secrets:
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open("Finanzas_RodrigoKrys")
    return sheet

try:
    sh = conectar_google_sheets()
    ws_registro = sh.worksheet("Registro")
    ws_cuentas = sh.worksheet("Cuentas")
    ws_presupuestos = sh.worksheet("Presupuestos")
except Exception as e:
    st.error("Error conectando a Google. Espera 1 minuto y recarga.")
    st.stop()

# --- FUNCIONES BLINDADAS ---
def intento_seguro(funcion_gspread):
    max_retries = 3
    for i in range(max_retries):
        try:
            return funcion_gspread()
        except gspread.exceptions.APIError as e:
            if i == max_retries - 1:
                raise e
            time.sleep(2 * (i + 1))
        except Exception as e:
            raise e

@st.cache_data(ttl=60)
def obtener_datos():
    data = intento_seguro(lambda: ws_registro.get_all_records())
    columnas = ['Fecha', 'Hora', 'Usuario', 'Cuenta', 'Tipo', 'Categoria', 'Monto', 'Descripcion']
    if not data:
        df = pd.DataFrame(columns=columnas)
    else:
        df = pd.DataFrame(data)

    df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)
    df['Fecha'] = pd.to_datetime(df['Fecha'], format="%Y-%m-%d", errors='coerce')
    return df

@st.cache_data(ttl=600)
def obtener_cuentas():
    cuentas = intento_seguro(lambda: ws_cuentas.col_values(1))
    return cuentas[1:] if len(cuentas) > 1 else ["Efectivo"]

@st.cache_data(ttl=600)
def obtener_presupuestos():
    records = intento_seguro(lambda: ws_presupuestos.get_all_records())
    presupuestos = {row['Categoria']: row['Tope_Mensual'] for row in records}
    return presupuestos

def limpiar_cache():
    st.cache_data.clear()

# --- SIDEBAR ---
with st.sidebar:
    st.header("Configuración")
    with st.expander("Cuentas"):
        nueva = st.text_input("Nueva Cuenta")
        if st.button("Crear"):
            if nueva:
                ws_cuentas.append_row([nueva])
                limpiar_cache()
                st.success("Creada")
                time.sleep(1)
                st.rerun()

    with st.expander("Presupuestos"):
        n_cat = st.text_input("Categoría")
        n_tope = st.number_input("Tope", min_value=0)
        if st.button("Crear Meta"):
            if n_cat:
                ws_presupuestos.append_row([n_cat, n_tope])
                limpiar_cache()
                st.success("Creada")
                time.sleep(1)
                st.rerun()

# --- HEADER ---
col_logo, col_titulo = st.columns([1, 4]) 
with col_logo:
    if img_logo:
        st.markdown(f'<img src="data:image/png;base64,{img_logo}" width="80">', unsafe_allow_html=True)
    else:
        st.write("🐹") 
with col_titulo:
    st.title("CAPIGASTOS")

# ZONA HORARIA PERÚ
zona_peru = pytz.timezone('America/Lima')

try:
    df = obtener_datos()
    lista_cuentas = obtener
