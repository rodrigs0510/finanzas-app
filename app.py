import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import pytz 
import base64

# --- 1. CONFIGURACIÓN (ARRANCAMOS EN MODO WIDE) ---
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
img_btn_add = get_image_as_base64("boton_agregar.png")
img_btn_del = get_image_as_base64("boton_eliminar.png")

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

@st.cache_data(ttl=60)
def obtener_datos():
    columnas_base = ['Fecha', 'Hora', 'Usuario', 'Cuenta', 'Tipo', 'Categoria', 'Monto', 'Descripcion']
    try:
        data = intento_seguro(lambda: ws_registro.get_all_records())
        if not data: return pd.DataFrame(columns=columnas_base)
        df = pd.DataFrame(data)
        for col in columnas_base:
            if col not in df.columns: df[col] = ""
        df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)
        df['Fecha'] = pd.to_datetime(df['Fecha'], format="%Y-%m-%d", errors='coerce')
        return df
    except: return pd.DataFrame(columns=columnas_base)

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

def limpiar_cache(): st.cache_data.clear()

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

# --- CSS NUCLEAR (SOLUCIÓN DEFINITIVA) ---
st.markdown(f"""
<style>
    /* 1. ELIMINAR LA BARRA SUPERIOR (HEADER) */
    header[data-testid="stHeader"] {{
        display: none !important;
        visibility: hidden !important;
    }}
    .stApp > header {{
        display: none !important;
    }}
    
    /* 2. SUBIR EL CONTENIDO AL TOPE */
    .block-container {{
        padding-top: 0rem !important;
        margin-top: 1rem !important;
        max-width: 98% !important;
    }}

    /* 3. VARIABLES GLOBALES (FORZAR MODO CLARO) */
    :root {{
        --primary-color: #8B4513;
        --background-color: #ffffff;
        --secondary-background-color: #f0f2f6;
        --text-color: #4A3B2A;
        --font: sans-serif;
    }}

    /* 4. FONDO DE PANTALLA */
    .stApp {{
        background-image: url("data:image/jpg;base64,{img_fondo}");
        background-size: cover; 
        background-position: center; 
        background-attachment: fixed;
    }}

    /* 5. CAJAS / CONTENEDORES (FONDO SÓLIDO OBLIGATORIO) */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: #FFF8DC !important; /* Beige Sólido */
        opacity: 1 !important; /* Opacidad al 100% */
        border: 3px solid #8B4513 !important; 
        border-radius: 15px !important;
        padding: 15px !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3) !important;
    }}
    /* Asegurarnos que el fondo beige tape el carpincho de atrás */
    div[data-testid="stVerticalBlockBorderWrapper"] > div {{
        background-color: inherit !important;
    }}

    /* 6. TEXTOS (NEGRO/MARRÓN SIEMPRE) */
    h1, h2, h3, h4, p, span, label, div, .stMarkdown, .stMetricLabel {{
        color: #4A3B2A !important;
        text-shadow: none !important;
    }}
    /* Excepción: Tarjetas (letras blancas) */
    .tarjeta-capigastos *, .tarjeta-capigastos div {{ 
        color: white !important; 
        text-shadow: 1px 1px 2px rgba(0,0,0,0.8) !important;
    }}

    /* 7. INPUTS (CUADROS BLANCOS) */
    .stTextInput input, .stNumberInput input, div[data-baseweb="select"] > div {{
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 2px solid #8B4513 !important;
        border-radius: 8px !important;
    }}

    /* 8. BOTONES IMAGEN (CON COLOR DE RESPALDO) */
    div.stButton > button[title="AGREGAR_IMG"] {{
        background-color: #9ACD32 !important; /* Verde por si falla la imagen */
        background-image: url("data:image/png;base64,{img_btn_add}");
        background-size: 100% 100%; border: none !important;
        height: 45px; width: 100%;
        color: transparent !important; /* Ocultar texto de respaldo */
    }}
    div.stButton > button[title="ELIMINAR_IMG"] {{
        background-color: #FA8072 !important; /* Rojo por si falla la imagen */
        background-image: url("data:image/png;base64,{img_btn_del}");
        background-size: 100% 100%; border: none !important;
        height: 45px; width: 100%;
        color: transparent !important;
    }}
    
    /* Botón Guardar Normal */
    div.stButton > button:not([title]) {{
        background-color: #8B4513 !important; color: white !important;
        border-radius: 20px; border: 2px solid #5e2f0d;
    }}

    /* 9. TARJETAS */
    .tarjeta-capigastos {{
        border-radius: 15px; padding: 15px; color: white !important; margin-bottom: 10px;
        box-shadow: 0 4px 8px 0 rgba(0,0,0,0.3); position: relative; height: 180px;
        background-size: 100% 100%; background-position: center;
        background-color: #8B4513; /* Color respaldo */
    }}
    .barra-fondo {{ background-color: rgba(255, 255, 255, 0.3); border-radius: 5px; height: 6px; width: 100%; margin-top: 5px; }}
    .barra-progreso {{ background-color: #4CAF50; height: 100%; border-radius: 5px; }}

</style>
""", unsafe_allow_html=True)

# --- LOGICA ---
zona_peru = pytz.timezone('America/Lima')
try:
    df = obtener_datos()
    lista_cuentas = obtener_cuentas()
    presupuestos_dict = obtener_presupuestos()
except:
    st.warning("Cargando..."); time.sleep(1); st.rerun()

# --- DATOS GLOBALES ---
ing_hist, gas_hist, ahorro_vida, saldo_actual = 0,0,0,0
if not df.empty:
    ing_hist = df[df['Tipo']=='Ingreso']['Monto'].sum()
    gas_hist = df[df['Tipo']=='Gasto']['Monto'].sum()
    ahorro_vida = ing_hist - gas_hist
    for c in lista_cuentas:
        i = df[(df['Cuenta']==c)&(df['Tipo']=='Ingreso')]['Monto'].sum()
        g = df[(df['Cuenta']==c)&(df['Tipo']=='Gasto')]['Monto'].sum()
        saldo_actual += (i-g)

# ==============================================================================
# 1. HEADER (LOGO | SELECCION MES | TOTALES)
# ==============================================================================
with st.container(border=True): # CAJA BEIGE SOLIDA
    c1, c2, c3 = st.columns([1.5, 1.5, 1.5], vertical_alignment="center")
    with c1:
        cc1, cc2 = st.columns([1, 3])
        with cc1:
            if img_logo: st.markdown(f'<img src="data:image/png;base64,{img_logo}" width="80">', unsafe_allow_html=True)
        with cc2: st.markdown("<h2>CAPIGASTOS</h2>", unsafe_allow_html=True)
    with c2:
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        now = datetime.now(zona_peru)
        cm, ca = st.columns(2)
        sel_mes = cm.selectbox("Mes", meses, index=now.month-1, label_visibility="collapsed")
        sel_anio = ca.number_input("Año", value=now.year, label_visibility="collapsed")
        mes_idx = meses.index(sel_mes) + 1
    with c3:
        st.markdown(f"<div style='text-align:right;'><b>Saldo Total:</b> S/ {saldo_actual:,.2f}<br><b>Ahorro Histórico:</b> S/ {ahorro_vida:,.2f}</div>", unsafe_allow_html=True)

# ==============================================================================
# 2. CONSOLIDADO
# ==============================================================================
if not df.empty and 'Fecha' in df.columns:
    df_f = df[(df['Fecha'].dt.month == mes_idx) & (df['Fecha'].dt.year == sel_anio)]
else: df_f = pd.DataFrame(columns=df.columns)

ing_m = df_f[df_f['Tipo']=='Ingreso']['Monto'].sum() if not df_f.empty else 0
gas_m = df_f[df_f['Tipo']=='Gasto']['Monto'].sum() if not df_f.empty else 0
bal_m = ing_m - gas_m

with st.container(border=True): # CAJA BEIGE SOLIDA
    st.markdown(f"<h4 style='text-align:center; margin:0;'>CONSOLIDADO: {sel_mes.upper()} {sel_anio}</h4>", unsafe_allow_html=True)
    k1, k2, k3 = st.columns(3)
    k1.metric("Ingresos", f"S/ {ing_m:,.2f}")
    k2.metric("Gastos", f"S/ {gas_m:,.2f}")
    k3.metric("Ahorro", f"S/ {bal_m:,.2f}")

st.write("")

# ==============================================================================
# 3. CUERPO
# ==============================================================================
col_izq, col_der = st.columns([1, 1.8], gap="medium")

# --- IZQUIERDA ---
with col_izq:
    with st.container(border=True): # CAJA BEIGE SOLIDA
        st.markdown
