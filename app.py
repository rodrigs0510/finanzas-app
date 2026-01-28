import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import pytz 
import base64

# --- 1. CONFIGURACIÓN ---
st.set_page_config(
    page_title="CAPIGASTOS", 
    layout="wide",
    page_icon="🐹",
    initial_sidebar_state="collapsed"
)

# --- CARGAR IMÁGENES ---
def get_image_as_base64(file_path):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except Exception:
        return ""

img_tarjeta = get_image_as_base64("Tarjeta fondo.png")
img_logo = get_image_as_base64("logo.png") 
img_fondo = get_image_as_base64("fondo.jpg") 

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

# --- FUNCIONES ---
def intento_seguro(funcion_gspread):
    max_retries = 3
    for i in range(max_retries):
        try:
            return funcion_gspread()
        except gspread.exceptions.APIError as e:
            if i == max_retries - 1: raise e
            time.sleep(2 * (i + 1))
        except Exception as e: raise e

def limpiar_cache(): 
    st.cache_data.clear()

@st.cache_data(ttl=60)
def obtener_datos():
    columnas_base = ['Fecha', 'Hora', 'Usuario', 'Cuenta', 'Tipo', 'Categoria', 'Monto', 'Descripcion']
    try:
        data = intento_seguro(lambda: ws_registro.get_all_records())
        if not data: 
            return pd.DataFrame(columns=columnas_base + ['Fila_Original'])
        
        df = pd.DataFrame(data)
        
        # Validación de columnas
        for col in columnas_base:
            if col not in df.columns: df[col] = ""
        
        # CRÍTICO: Guardamos el número de fila original antes de filtrar nada
        # (Index 0 del DF = Fila 2 del Excel porque la 1 es header)
        df['Fila_Original'] = df.index + 2 
        
        df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)
        df['Fecha'] = pd.to_datetime(df['Fecha'], format="%Y-%m-%d", errors='coerce')
        return df
    except:
        return pd.DataFrame(columns=columnas_base + ['Fila_Original'])

@st.cache_data(ttl=600)
def obtener_cuentas():
    try:
        cuentas = intento_seguro(lambda: ws_cuentas.col_values(1))
        return cuentas[1:] if len(cuentas) > 1 else ["Efectivo"]
    except: return ["Efectivo"]

@st.cache_data(ttl=600)
def obtener_presupuestos():
    try:
        records = intento_seguro(lambda: ws_presupuestos.get_all_records())
        return {row['Categoria']: row['Tope_Mensual'] for row in records}
    except: return {}

# --- ACCIÓN DE BORRADO ---
def borrar_fila_especifica(numero_fila):
    try:
        ws_registro.delete_rows(numero_fila)
        limpiar_cache()
        st.toast(f"✅ Registro eliminado correctamente")
        time.sleep(1)
    except Exception as e:
        st.error(f"Error al borrar: {e}")

# --- DIALOGS ---
@st.dialog("Agregar Nueva Cuenta")
def dialog_agregar_cuenta():
    nombre_cuenta = st.text_input("Nombre de la cuenta")
    if st.button("Crear Cuenta"):
        if nombre_cuenta:
            ws_cuentas.append_row([nombre_cuenta])
            limpiar_cache(); st.success("¡Creada!"); time.sleep(1); st.rerun()

@st.dialog("Eliminar Cuenta")
def dialog_eliminar_cuenta(lista_actual):
    cuenta_a_borrar = st.selectbox("Selecciona cuenta:", lista_actual)
    st.warning(f"¿Eliminar **{cuenta_a_borrar}**?")
    c1, c2 = st.columns(2)
    if c1.button("Sí, Eliminar"):
        cell = ws_cuentas.find(cuenta_a_borrar)
        ws_cuentas.delete_rows(cell.row)
        limpiar_cache(); st.success("Eliminada"); time.sleep(1); st.rerun()
    if c2.button("Cancelar"): st.rerun()

# --- CSS NUCLEAR ---
st.markdown(f"""
<style>
    /* 1. FONDO DE PANTALLA */
    .stApp {{
        background-image: url("data:image/jpg;base64,{img_fondo}");
        background-size: cover; 
        background-position: center; 
        background-attachment: fixed;
    }}

    /* 2. CAJAS BLANCAS SÓLIDAS */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: #FFF8DC !important;
        border: 3px solid #8B4513 !important;
        border-radius: 15px !important;
        padding: 15px !important;
        opacity: 1 !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3) !important;
    }}
    div[data-testid="stVerticalBlockBorderWrapper"] > div {{
        background-color: transparent !important;
    }}

    /* 3. TEXTOS NEGROS/MARRONES */
    h1, h2, h3, h4, p, span, label, div, .stMarkdown, .stMetricLabel {{
        color: #4A3B2A !important;
        text-shadow: none !important;
    }}
    
    /* 4. TARJETAS (TEXTO BLANCO) */
    .tarjeta-capigastos *, .tarjeta-capigastos div {{ 
        color: white !important; 
        text-shadow: 1px 1px 2px rgba(0,0,0,0.8) !important;
    }}

    /* 5. INPUTS */
    .stTextInput input, .stNumberInput input, div[data-baseweb="select"] > div {{
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 2px solid #8B4513 !important;
    }}

    /* 6. BOTONES ESTILO PASTILLA */
    div.stButton > button:has(p:contains('Agregar')) {{
        background-color: #9ACD32 !important; color: #2F4F4F !important;
        border: 3px solid #556B2F !important; border-radius: 50px !important;
        font-weight: 900 !important;
    }}
    div.stButton > button:has(p:contains('Eliminar')) {{
        background-color: #FA8072 !important; color: #581818 !important;
        border: 3px solid #8B0000 !important; border-radius: 50px !important;
        font-weight: 900 !important;
    }}
    /* Botón Guardar */
    div.stButton > button:has(p:contains('GUARDAR')) {{
        background-color: #8B4513 !important; color: white !important;
        border: 2px solid #5e2f0d !important; border-radius: 20px !important;
    }}
    /* Botón Pequeño de Borrar Fila (Icono) */
    div.stButton > button:has(p:contains('🗑️')) {{
        background-color: #FFE4E1 !important;
        color: red !important;
        border: 1px solid red !important;
        border-radius: 5px !important;
        padding: 0px 5px !important;
        height: 35px !important;
    }}

    /* 7. TARJETA VISUAL */
    .tarjeta-capigastos {{
        background-color: #8B4513;
        border-radius: 15px; padding: 15px; margin-bottom: 10px;
        box-shadow: 0 4px 8px 0 rgba(0,0,0,0.3); position: relative; height: 180px;
        background-size: 100% 100%; background-position: center;
    }}
    .barra-fondo {{ background-color: rgba(255, 255, 255, 0.3); border-radius: 5px; height: 6px; width: 100%; margin-top: 5px; }}
    .barra-progreso {{ background-color: #4CAF50; height: 100%; border-radius: 5px; }}
    
    /* 8. LISTA DE MOVIMIENTOS (Fila estilizada) */
    .fila-movimiento {{
        background-color: #FFFFFF;
        border-bottom: 1px solid #D3D3D3;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 5px;
    }}

</style>
""", unsafe_allow_html=True)

# --- LOGICA ---
zona_peru = pyt
