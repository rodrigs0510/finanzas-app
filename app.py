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
    lista_cuentas = obtener_cuentas()
    presupuestos_dict = obtener_presupuestos()
except Exception:
    st.warning("Cargando datos...")
    time.sleep(2)
    st.rerun()

# --- CÁLCULOS GLOBALES ---
total_ingresos_historico = 0
total_gastos_historico = 0
saldo_cuentas_total = 0

if not df.empty:
    total_ingresos_historico = df[df['Tipo'] == 'Ingreso']['Monto'].sum()
    total_gastos_historico = df[df['Tipo'] == 'Gasto']['Monto'].sum()
    ahorro_total_historico = total_ingresos_historico - total_gastos_historico
    
    for c in lista_cuentas:
        i = df[(df['Cuenta'] == c) & (df['Tipo'] == 'Ingreso')]['Monto'].sum()
        g = df[(df['Cuenta'] == c) & (df['Tipo'] == 'Gasto')]['Monto'].sum()
        saldo_cuentas_total += (i - g)
else:
    ahorro_total_historico = 0
    saldo_cuentas_total = 0

# --- ESTADO GLOBAL ---
st.subheader("Estado Global (Histórico)")
col_g1, col_g2 = st.columns(2)
col_g1.metric("Saldo Total Disponible", f"S/ {saldo_cuentas_total:.2f}")
col_g2.metric("Ahorro Total Acumulado", f"S/ {ahorro_total_historico:.2f}", delta="Total Histórico")

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

# ==========================================
# 2. CUENTAS (CORRECCIÓN DE HTML) 💳
# ==========================================
st.subheader("CUENTAS")

st.markdown("""
<style>
    .tarjeta-capigastos {
        border-radius: 15px;
        padding: 20px;
        color: white;
        margin-bottom: 15px;
        box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);
        position: relative;
        height: 200px;
        background-size: cover; 
        background-position: center;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .texto-sombra { text-shadow: 1px 1px 2px rgba(0,0,0,0.8); }
    .barra-fondo { background-color: rgba(255, 255, 255, 0.3); border-radius: 5px; height: 10px; width: 100%; margin-top: 5px; }
    .barra-progreso { background-color: #4CAF50; height: 100%; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

cols_c = st.columns(2)
idx_c = 0

for cuenta in lista_cuentas:
    # Cálculos
    if not df.empty:
        ingresos_h = df[(df['Cuenta'] == cuenta) & (df['Tipo'] == 'Ingreso')]['Monto'].sum()
        gastos_h = df[(df['Cuenta'] == cuenta) & (df['Tipo'] == 'Gasto')]['Monto'].sum()
        saldo_d = ingresos_h - gastos_h
    else:
        ingresos_h, gastos_h, saldo_d = 0, 0, 0

    if ingresos_h > 0:
        pct = min(max(saldo_d / ingresos_h, 0.0), 1.0) * 100
    else:
        pct = 0

    bg = f"background-image: url('data:image/png;base64,{img_tarjeta}');" if img_tarjeta else "background-color: #8B4513;"

    # CONSTRUCCIÓN HTML SEGURA (SIN SALTOS DE LÍNEA EXCESIVOS)
    html = f"""
    <div class="tarjeta-capigastos" style="{bg}">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div>
                <h3 class="texto-sombra" style="margin:0; color:white; font-size:18px;">{cuenta}</h3>
                <small class="texto-sombra" style="opacity:0.9;">Capigastos Card</small>
            </div>
            <div style="text-align: right;">
                <small class="texto-sombra">Saldo Disponible</small>
                <h2 class="texto-sombra" style="margin:0; color:white;">S/ {saldo_d:,.2f}</h2>
            </div>
        </div>
        <div style="margin-top: 10px;">
            <span class="texto-sombra" style="font-size:12px; margin-right:15px;">⬇ Ingresos: S/ {ingresos_h:,.2f}</span>
            <span class="texto-sombra" style="font-size:12px; color:#ffcccb;">⬆ Gastado: S/ {gastos_h:,.2f}</span>
        </div>
        <div style="margin-top: auto;">
            <div style="display:flex; justify-content:space-between; font-size:12px;" class="texto-sombra">
                <span>Estado de Cuenta</span><span>{pct:.0f}%</span>
            </div>
            <div class="barra-fondo">
                <div class="barra-progreso" style="width: {pct}%;"></div>
            </div>
        </div>
    </div>
    """

    with cols_c[idx_c % 2]:
        st.markdown(html, unsafe_allow_html=True)
    
    idx_c += 1

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
