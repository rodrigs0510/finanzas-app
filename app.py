import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import pytz
import base64

# -------------------------------------------------
# CONFIGURACIÓN GENERAL
# -------------------------------------------------
st.set_page_config(
    page_title="CAPIGASTOS",
    layout="wide",
    page_icon="🐹",
    initial_sidebar_state="collapsed"
)

# -------------------------------------------------
# CARGA DE IMÁGENES
# -------------------------------------------------
def get_image_as_base64(file_path):
    try:
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except:
        return ""

img_logo   = get_image_as_base64("logo.png")
img_fondo  = get_image_as_base64("fondo.jpg")
img_tarjeta = get_image_as_base64("Tarjeta fondo.png")

# -------------------------------------------------
# CSS — FONDO + HOJAS (CLAVE)
# -------------------------------------------------
st.markdown(f"""
<style>

/* Fondo general */
.stApp {{
    background-image: url("data:image/jpg;base64,{img_fondo}");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}}

/* HOJA (superficie sólida) */
.hoja {{
    background-color: rgba(255,255,255,0.96);
    border-radius: 20px;
    padding: 24px;
    margin-bottom: 22px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.25);
}}

/* Texto oscuro legible */
.hoja h1, .hoja h2, .hoja h3, .hoja h4,
.hoja p, .hoja span, .hoja label {{
    color: #3A2E2A !important;
}}

/* Inputs */
.stTextInput input,
.stNumberInput input,
div[data-baseweb="select"] > div {{
    background-color: #FFFFFF !important;
    color: #000000 !important;
    border: 2px solid #8B4513 !important;
    border-radius: 10px;
}}

/* Botones */
div.stButton > button {{
    width: 100%;
    border-radius: 30px;
    border: 2px solid #5e2f0d;
    font-weight: 800;
    padding: 10px;
    background-color: #8B4513;
    color: white;
}}

/* Tarjetas de cuentas */
.tarjeta-capigastos {{
    background-color: #8B4513;
    border-radius: 15px;
    padding: 15px;
    height: 180px;
    position: relative;
    background-size: cover;
    box-shadow: 0 4px 10px rgba(0,0,0,0.35);
}}

.barra-fondo {{
    background-color: rgba(255,255,255,0.3);
    border-radius: 6px;
    height: 6px;
}}

.barra-progreso {{
    background-color: #4CAF50;
    height: 100%;
    border-radius: 6px;
}}

</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# CONEXIÓN GOOGLE SHEETS
# -------------------------------------------------
@st.cache_resource
def conectar_google():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["gcp_service_account"], scope
    )
    client = gspread.authorize(creds)
    sh = client.open("Finanzas_RodrigoKrys")
    return (
        sh.worksheet("Registro"),
        sh.worksheet("Cuentas"),
        sh.worksheet("Presupuestos")
    )

ws_registro, ws_cuentas, ws_presupuestos = conectar_google()

# -------------------------------------------------
# DATOS
# -------------------------------------------------
@st.cache_data(ttl=60)
def cargar_datos():
    df = pd.DataFrame(ws_registro.get_all_records())
    if df.empty:
        return df
    df["Monto"] = pd.to_numeric(df["Monto"], errors="coerce").fillna(0)
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df = df.dropna(subset=["Fecha"])
    return df

df = cargar_datos()
lista_cuentas = ws_cuentas.col_values(1)[1:]

zona = pytz.timezone("America/Lima")
now = datetime.now(zona)

# -------------------------------------------------
# HEADER
# -------------------------------------------------
st.markdown('<div class="hoja">', unsafe_allow_html=True)
c1, c2, c3 = st.columns([1.5, 1.5, 1.5])

with c1:
    if img_logo:
        st.markdown(
            f'<img src="data:image/png;base64,{img_logo}" width="70">',
            unsafe_allow_html=True
        )
    st.markdown("## CAPIGASTOS")

with c2:
    meses = [
        "Enero","Febrero","Marzo","Abril","Mayo","Junio",
        "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"
    ]
    mes = st.selectbox("Mes", meses, index=now.month-1)
    anio = st.number_input("Año", value=now.year)

with c3:
    ing = df[df["Tipo"]=="Ingreso"]["Monto"].sum()
    gas = df[df["Tipo"]=="Gasto"]["Monto"].sum()
    st.markdown(
        f"<div style='text-align:right'><b>Saldo Total:</b> S/ {ing-gas:,.2f}</div>",
        unsafe_allow_html=True
    )

st.markdown('</div>', unsafe_allow_html=True)

# -------------------------------------------------
# CONSOLIDADO
# -------------------------------------------------
st.markdown('<div class="hoja">', unsafe_allow_html=True)

mes_idx = meses.index(mes)+1
df_m = df[(df["Fecha"].dt.month==mes_idx) & (df["Fecha"].dt.year==anio)]

i = df_m[df_m["Tipo"]=="Ingreso"]["Monto"].sum()
g = df_m[df_m["Tipo"]=="Gasto"]["Monto"].sum()

st.markdown(f"### CONSOLIDADO {mes.upper()} {anio}")
c1,c2,c3 = st.columns(3)
c1.metric("Ingresos", f"S/ {i:,.2f}")
c2.metric("Gastos", f"S/ {g:,.2f}")
c3.metric("Ahorro", f"S/ {i-g:,.2f}")

st.markdown('</div>', unsafe_allow_html=True)

# -------------------------------------------------
# CUERPO
# -------------------------------------------------
col_izq, col_der = st.columns([1,2])

# FORMULARIO
with col_izq:
    st.markdown('<div class="hoja">', unsafe_allow_html=True)
    st.markdown("### 📝 FORMULARIO")
    with st.form("form"):
        u = st.selectbox("Usuario", ["Rodrigo","Krys"])
        cta = st.selectbox("Cuenta", lista_cuentas)
        tipo = st.radio("Tipo", ["Ingreso","Gasto"], horizontal=True)
        monto = st.number_input("Monto", min_value=0.01)
        desc = st.text_input("Descripción")
        if st.form_submit_button("GUARDAR"):
            ws_registro.append_row([
                now.strftime("%Y-%m-%d"),
                now.strftime("%H:%M:%S"),
                u, cta, tipo, "General", monto, desc
            ])
            st.cache_data.clear()
            st.success("Guardado")
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# CUENTAS
with col_der:
    st.markdown('<div class="hoja">', unsafe_allow_html=True)
    st.markdown("### 💳 CUENTAS")
    cols = st.columns(3)
    for i, cta in enumerate(lista_cuentas):
        ing_c = df[(df["Cuenta"]==cta)&(df["Tipo"]=="Ingreso")]["Monto"].sum()
        gas_c = df[(df["Cuenta"]==cta)&(df["Tipo"]=="Gasto")]["Monto"].sum()
        saldo = ing_c - gas_c
        pct = min(saldo/ing_c,1) if ing_c>0 else 0
        with cols[i%3]:
            st.markdown(f"""
            <div class="tarjeta-capigastos" style="background-image:url('data:image/png;base64,{img_tarjeta}')">
                <b>{cta}</b><br>
                <div style="font-size:22px">S/ {saldo:,.2f}</div>
                <div class="barra-fondo">
                    <div class="barra-progreso" style="width:{pct*100}%"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
