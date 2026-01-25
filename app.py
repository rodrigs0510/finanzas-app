import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import pytz 

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="CAPIGASTOS", layout="centered", page_icon="🐹")

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

# --- HEADER CON LOGO ---
col_logo, col_titulo = st.columns([1, 4]) 

with col_logo:
    try:
        st.image("logo.png", width=100) 
    except:
        st.write("🐹") 

with col_titulo:
    st.title("CAPIGASTOS")

# ZONA HORARIA PERÚ
zona_peru = pytz.timezone('America/Lima')

try:
    df = obtener_datos()
    lista_cuentas = obtener_cuentas()
    presupuestos_dict = obtener_presupuestos()
except Exception:
    st.warning("Cargando datos...")
    time.sleep(2)
    st.rerun()

# --- CÁLCULOS GLOBALES (LO NUEVO) ---
# Usamos el DataFrame completo (df) sin filtrar por mes para los totales históricos
total_ingresos_historico = 0
total_gastos_historico = 0
saldo_cuentas_total = 0

if not df.empty:
    total_ingresos_historico = df[df['Tipo'] == 'Ingreso']['Monto'].sum()
    total_gastos_historico = df[df['Tipo'] == 'Gasto']['Monto'].sum()
    
    # Saldo real calculado cuenta por cuenta
    saldos = {}
    for c in lista_cuentas:
        i = df[(df['Cuenta'] == c) & (df['Tipo'] == 'Ingreso')]['Monto'].sum()
        g = df[(df['Cuenta'] == c) & (df['Tipo'] == 'Gasto')]['Monto'].sum()
        saldos[c] = i - g
    saldo_cuentas_total = sum(saldos.values())
else:
    saldos = {c: 0 for c in lista_cuentas}

ahorro_total_historico = total_ingresos_historico - total_gastos_historico

# --- VISUALIZACIÓN: ESTADO GLOBAL ---
st.subheader("Estado Global (Histórico)")
col_g1, col_g2 = st.columns(2)
# Mostramos el dinero que tienen disponible HOY (Saldo Total)
col_g1.metric("Saldo Total Disponible", f"S/ {saldo_cuentas_total:.2f}")
# Mostramos el performance histórico (Ahorro Total)
col_g2.metric("Ahorro Total Acumulado", f"S/ {ahorro_total_historico:.2f}", 
              delta="Total Histórico")

st.divider()

# --- FILTROS DE TIEMPO ---
with st.container(border=True):
    c1, c2 = st.columns(2)
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
             "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    
    now = datetime.now(zona_peru)
    mes_nom = c1.selectbox("Mes", meses, index=now.month-1)
    anio = c2.number_input("Año", value=now.year, min_value=2024, max_value=2030)
    mes_idx = meses.index(mes_nom) + 1

# Lógica Datos Filtrados
if not df.empty and df['Fecha'].notna().any():
    df_f = df[(df['Fecha'].dt.month == mes_idx) & (df['Fecha'].dt.year == anio)]
else:
    df_f = df

# 1. Resumen Mes
st.subheader(f"Resumen {mes_nom} {anio}")
if not df_f.empty:
    ing_m = df_f[df_f['Tipo']=='Ingreso']['Monto'].sum()
    gas_m = df_f[df_f['Tipo']=='Gasto']['Monto'].sum()
    bal_m = ing_m - gas_m
else:
    ing_m, gas_m, bal_m = 0,0,0

m1, m2, m3 = st.columns(3)
m1.metric("Ingresos (Mes)", f"S/ {ing_m:.2f}")
m2.metric("Gastos (Mes)", f"S/ {gas_m:.2f}", delta_color="inverse")
m3.metric("Ahorro (Mes)", f"S/ {bal_m:.2f}", delta=f"{(bal_m/ing_m)*100:.0f}%" if ing_m>0 else None)

st.divider()

# 2. Cuentas
st.subheader(f"Detalle por Cuentas")
cc = st.columns(3)
ix = 0
for c, s in saldos.items():
    with cc[ix%3]:
        with st.container(border=True):
            st.write(f"**{c}**")
            if s >= 0:
                st.metric("Saldo", f"S/ {s:.2f}")
                st.progress(min((s/saldo_cuentas_total) if saldo_cuentas_total>0 else 0, 1.0))
            else:
                st.metric("Deuda", f"S/ {s:.2f}", delta_color="inverse")
    ix += 1

st.divider()

# 3. Metas
st.subheader("Metas del Mes")
if not df_f.empty:
    gastos_cat = df_f[df_f['Tipo']=='Gasto'].groupby('Categoria')['Monto'].sum()
else:
    gastos_cat = {}

cp = st.columns(2)
ip = 0
for cat, tope in presupuestos_dict.items():
    real = gastos_cat.get(cat, 0)
    pct = (real/tope) if tope>0 else 0
    with cp[ip%2]:
        st.write(f"**{cat}**")
        st.progress(min(pct, 1.0))
        st.caption(f"{real:.0f} / {tope} ({pct*100:.0f}%)")
    ip += 1

st.divider()

# 4. Registro
st.subheader("Operación")
op = st.radio("Tipo", ["Gasto", "Ingreso", "Transferencia"], horizontal=True)

with st.form("op_form", clear_on_submit=True):
    fc1, fc2 = st.columns(2)
    u = fc1.selectbox("Usuario", ["Rodrigo", "Krys"])
    
    if op == "Transferencia":
        c_origen = fc2.selectbox("Desde", lista_cuentas)
        c_dest = st.selectbox("Hacia", lista_cuentas)
        cat = "Transferencia"
    else:
        cta = fc2.selectbox("Cuenta", lista_cuentas)
        if "Gasto" in op:
            cat = st.selectbox("Categoría", list(presupuestos_dict.keys())+["Otros"])
        else:
            cat = st.selectbox("Categoría", ["Sueldo", "Negocio", "Regalo", "Otros"])
            
    monto = st.number_input("Monto", min_value=0.01, format="%.2f")
    desc = st.text_input("Detalle")
    
    if st.form_submit_button("Guardar"):
        try:
            now_str = datetime.now(zona_peru).strftime("%Y-%m-%d")
            time_str = datetime.now(zona_peru).strftime("%H:%M:%S")
            
            if op == "Transferencia":
                if c_origen == c_dest:
                    st.error("Cuentas iguales")
                else:
                    r1 = [now_str, time_str, u, c_origen, "Gasto", "Transferencia/Salida", monto, f"-> {c_dest}: {desc}"]
                    r2 = [now_str, time_str, u, c_dest, "Ingreso", "Transferencia/Entrada", monto, f"<- {c_origen}: {desc}"]
                    intento_seguro(lambda: ws_registro.append_row(r1))
                    intento_seguro(lambda: ws_registro.append_row(r2))
                    limpiar_cache()
                    st.success("Transferencia OK")
                    time.sleep(1)
                    st.rerun()
            else:
                tipo = "Gasto" if "Gasto" in op else "Ingreso"
                row = [now_str, time_str, u, cta, tipo, cat, monto, desc]
                intento_seguro(lambda: ws_registro.append_row(row))
                limpiar_cache()
                st.success("Guardado OK")
                time.sleep(1)
                st.rerun()
        except Exception as e:
            st.error(f"Error guardando: {e}")

# 5. Borrar
with st.expander("Borrar Último"):
    if not df.empty:
        st.dataframe(df.sort_values("Fecha", ascending=False).head(3), use_container_width=True)
        if st.button("BORRAR"):
            try:
                rows = len(ws_registro.get_all_values())
                if rows > 1:
                    intento_seguro(lambda: ws_registro.delete_rows(rows))
                    limpiar_cache()
                    st.success("Borrado")
                    time.sleep(1)
                    st.rerun()
            except Exception as e:
                st.error(f"Error borrando: {e}")

