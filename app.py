import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import base64

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Finanzas R&K", layout="centered", page_icon="💰")

# --- FUNCIÓN DE FONDO ---
def poner_fondo(imagen_local):
    with open(imagen_local, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()
    
    css = f"""
    <style>
    .stApp {{
        background-image: url(data:image/jpg;base64,{encoded_string});
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}
    div[data-testid="stExpander"], div[data-testid="stContainer"] {{
        background-color: rgba(255, 255, 255, 0.85);
        border-radius: 10px;
        padding: 10px;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# Intentar cargar fondo
try:
    poner_fondo("fondo.jpg")
except:
    pass # Si no hay fondo, no pasa nada

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

# Retry Logic
def intento_seguro(funcion_gspread):
    max_retries = 3
    for i in range(max_retries):
        try:
            return funcion_gspread()
        except gspread.exceptions.APIError as e:
            if i == max_retries - 1: raise e
            time.sleep(2 * (i + 1))
        except Exception as e:
            raise e

try:
    sh = conectar_google_sheets()
    ws_registro = sh.worksheet("Registro")
    ws_cuentas = sh.worksheet("Cuentas")
    ws_presupuestos = sh.worksheet("Presupuestos")
except:
    st.error("Error conectando. Recarga en 1 min.")
    st.stop()

# --- FUNCIONES DATOS ---
@st.cache_data(ttl=60)
def obtener_datos():
    data = intento_seguro(lambda: ws_registro.get_all_records())
    columnas = ['Fecha', 'Hora', 'Usuario', 'Cuenta', 'Tipo', 'Categoria', 'Monto', 'Descripcion']
    if not data: return pd.DataFrame(columns=columnas)
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
    return {row['Categoria']: row['Tope_Mensual'] for row in records}

def limpiar_cache(): st.cache_data.clear()

# --- INTERFAZ (SIDEBAR CORREGIDO) ---
with st.sidebar:
    st.header("⚙️ Config")
    with st.expander("➕ Cuentas"):
        nueva = st.text_input("Nueva Cuenta")
        # AQUÍ ESTABA EL ERROR: Agregamos key único
        if st.button("Crear", key="btn_crear_cuenta") and nueva:
            ws_cuentas.append_row([nueva])
            limpiar_cache()
            st.success("OK"); time.sleep(1); st.rerun()
            
    with st.expander("🎯 Presupuestos"):
        n_cat = st.text_input("Categoría")
        n_tope = st.number_input("Tope", min_value=0)
        # AQUÍ ESTABA EL ERROR: Agregamos key único
        if st.button("Crear", key="btn_crear_meta") and n_cat:
            ws_presupuestos.append_row([n_cat, n_tope])
            limpiar_cache()
            st.success("OK"); time.sleep(1); st.rerun()

st.title("💰 Finanzas Rodrigo & Krys")

try:
    df = obtener_datos()
    lista_cuentas = obtener_cuentas()
    presupuestos_dict = obtener_presupuestos()
except:
    st.warning("⚠️ Tráfico alto. Espera 5s..."); time.sleep(5); st.rerun()

# FILTROS
with st.container():
    c1, c2 = st.columns(2)
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    now = datetime.now()
    mes_nom = c1.selectbox("Mes", meses, index=now.month-1)
    anio = c2.number_input("Año", value=now.year, min_value=2024)
    mes_idx = meses.index(mes_nom) + 1

if not df.empty and df['Fecha'].notna().any():
    df_f = df[(df['Fecha'].dt.month == mes_idx) & (df['Fecha'].dt.year == anio)]
else: df_f = df

saldos = {c: (df[(df['Cuenta']==c)&(df['Tipo']=='Ingreso')]['Monto'].sum() - df[(df['Cuenta']==c)&(df['Tipo']=='Gasto')]['Monto'].sum()) if not df.empty else 0 for c in lista_cuentas}
total_cap = sum(saldos.values())

# 1. RESUMEN
with st.container():
    st.subheader(f"📊 {mes_nom} {anio}")
    ing_m = df_f[df_f['Tipo']=='Ingreso']['Monto'].sum() if not df_f.empty else 0
    gas_m = df_f[df_f['Tipo']=='Gasto']['Monto'].sum() if not df_f.empty else 0
    m1, m2, m3 = st.columns(3)
    m1.metric("Ingresos", f"S/ {ing_m:.2f}")
    m2.metric("Gastos", f"S/ {gas_m:.2f}")
    m3.metric("Ahorro", f"S/ {ing_m - gas_m:.2f}")

st.divider()

# 2. CUENTAS
with st.container():
    st.subheader(f"💳 Total: S/ {total_cap:.2f}")
    cc = st.columns(3)
    ix = 0
    for c, s in saldos.items():
        with cc[ix%3]:
            if s >= 0: st.success(f"**{c}**\n\nS/ {s:.2f}")
            else: st.error(f"**{c}**\n\nS/ {s:.2f}")
        ix += 1

st.divider()

# 3. METAS
with st.container():
    st.subheader("🚦 Metas")
    gastos_cat = df_f[df_f['Tipo']=='Gasto'].groupby('Categoria')['Monto'].sum() if not df_f.empty else {}
    cp = st.columns(2)
    ip = 0
    for cat, tope in presupuestos_dict.items():
        real = gastos_cat.get(cat, 0)
        pct = (real/tope) if tope>0 else 0
        with cp[ip%2]:
            st.write(f"**{cat}**")
            st.progress(min(pct, 1.0))
            st.caption(f"{real:.0f} / {tope}")
        ip += 1

st.divider()

# 4. REGISTRO
with st.container():
    st.subheader("📝 Nuevo")
    op = st.radio("Acción", ["Gasto 📤", "Ingreso 📥", "Transferencia 🔄"], horizontal=True)
    with st.form("op_form", clear_on_submit=True):
        fc1, fc2 = st.columns(2)
        u = fc1.selectbox("Usuario", ["Rodrigo", "Krys"])
        if op == "Transferencia 🔄":
            c_origen = fc2.selectbox("Desde", lista_cuentas)
            c_dest = st.selectbox("Hacia", lista_cuentas)
            cat = "Transferencia"
        else:
            cta = fc2.selectbox("Cuenta", lista_cuentas)
            if "Gasto" in op: cat = st.selectbox("Categoría", list(presupuestos_dict.keys())+["Otros"])
            else: cat = st.selectbox("Categoría", ["Sueldo", "Negocio", "Regalo", "Otros"])
        monto = st.number_input("Monto", min_value=0.01, format="%.2f")
        desc = st.text_input("Detalle")
        
        if st.form_submit_button("Guardar"):
            now_str = datetime.now().strftime("%Y-%m-%d")
            time_str = datetime.now().strftime("%H:%M:%S")
            try:
                if op == "Transferencia 🔄":
                    if c_origen == c_dest: st.error("Cuentas iguales")
                    else:
                        intento_seguro(lambda: ws_registro.append_row([now_str, time_str, u, c_origen, "Gasto", "Transferencia/Salida", monto, f"-> {c_dest}: {desc}"]))
                        intento_seguro(lambda: ws_registro.append_row([now_str, time_str, u, c_dest, "Ingreso", "Transferencia/Entrada", monto, f"<- {c_origen}: {desc}"]))
                        limpiar_cache(); st.success("OK"); time.sleep(1); st.rerun()
                else:
                    tipo = "Gasto" if "Gasto" in op else "Ingreso"
                    intento_seguro(lambda: ws_registro.append_row([now_str, time_str, u, cta, tipo, cat, monto, desc]))
                    limpiar_cache(); st.success("OK"); time.sleep(1); st.rerun()
            except Exception as e: st.error(f"Error: {e}")

# 5. BORRAR
with st.expander("🗑️"):
    if not df.empty:
        if st.button("Borrar Último", key="btn_borrar"): # También le puse key a este por si acaso
            try:
                intento_seguro(lambda: ws_registro.delete_rows(len(ws_registro.get_all_values())))
                limpiar_cache(); st.success("Borrado"); time.sleep(1); st.rerun()
            except: pass
