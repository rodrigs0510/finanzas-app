import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import base64
import pytz

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="CAPIGASTOS", layout="wide", page_icon="🐹")

# --- 2. MOTOR DE ESTILOS (CSS AVANZADO PARA LEGIBILIDAD) ---
def cargar_estilos(imagen_local):
    try:
        with open(imagen_local, "rb") as f:
            b64_img = base64.b64encode(f.read()).decode()
        
        st.markdown(f"""
        <style>
        /* 1. FONDO DE PANTALLA FIJO */
        .stApp {{
            background-image: url(data:image/jpg;base64,{b64_img});
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}

        /* 2. CONTENEDORES (TARJETAS BLANCAS) */
        /* Esto crea el fondo blanco detrás de CADA bloque para que se lea */
        div[data-testid="stVerticalBlock"] > div > div {{
            background-color: rgba(255, 255, 255, 0.96); /* Blanco 96% opaco */
            border-radius: 12px;
            padding: 15px;
            box-shadow: 0px 4px 12px rgba(0,0,0,0.15);
            margin-bottom: 10px;
        }}
        
        /* Excepción: El contenedor principal transparente para que se vea el fondo general */
        .stApp > header, .stApp > div:first-child {{
            background-color: transparent;
        }}

        /* 3. TIPOGRAFÍA Y TÍTULOS */
        h1 {{
            color: #FFFFFF !important; /* Título principal Blanco */
            text-shadow: 0px 4px 8px rgba(0,0,0,0.8); /* Sombra negra fuerte */
            font-size: 3.5rem !important;
            font-weight: 900 !important;
            padding-bottom: 20px;
        }}
        
        h2, h3, h4, p, li, .stMarkdown {{
            color: #222222 !important; /* Texto negro intenso */
        }}

        /* 4. ARREGLO DE LOS INPUTS Y DROPDOWNS (Menús negros) */
        /* Forzamos fondo blanco y letra negra en todos los inputs */
        input, select, textarea, div[data-baseweb="select"] > div {{
            background-color: #FFFFFF !important;
            color: #000000 !important;
            border-color: #CCCCCC !important;
        }}
        div[data-baseweb="select"] span {{
            color: #000000 !important;
        }}
        /* El menú desplegable en sí */
        ul[data-baseweb="menu"] {{
            background-color: #FFFFFF !important;
        }}
        li[data-baseweb="menu-item"] {{
            color: #000000 !important;
        }}

        /* 5. MÉTRICAS (Números grandes) */
        div[data-testid="stMetricValue"] {{
            color: #000000 !important;
            font-size: 2rem !important;
        }}
        div[data-testid="stMetricLabel"] {{
            color: #555555 !important;
            font-weight: bold;
        }}
        
        /* 6. OCULTAR BARRA SUPERIOR ROJA DE STREAMLIT */
        header {{visibility: hidden;}}
        
        </style>
        """, unsafe_allow_html=True)
    except: pass

cargar_estilos("fondo.jpg")

# --- 3. CONEXIÓN ---
@st.cache_resource
def conectar_google():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    if "gcp_service_account" in st.secrets:
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    return gspread.authorize(creds).open("Finanzas_RodrigoKrys")

def intento_seguro(func):
    for i in range(3):
        try: return func()
        except: time.sleep(1)

try:
    sh = conectar_google()
    ws_reg = sh.worksheet("Registro")
    ws_cta = sh.worksheet("Cuentas")
    ws_pre = sh.worksheet("Presupuestos")
except:
    st.error("⚠️ Error de conexión. Recarga la página."); st.stop()

# --- 4. DATOS ---
def limpiar_cache(): st.cache_data.clear()

@st.cache_data(ttl=60)
def get_data():
    d = intento_seguro(lambda: ws_reg.get_all_records())
    if not d: return pd.DataFrame(columns=['ID','Fecha','Hora','Usuario','Cuenta','Tipo','Categoria','Monto','Descripcion'])
    df = pd.DataFrame(d)
    df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)
    df['Fecha_dt'] = pd.to_datetime(df['Fecha'], format="%Y-%m-%d", errors='coerce')
    df['ID'] = df.index + 2
    return df

@st.cache_data(ttl=300)
def get_cuentas():
    return intento_seguro(lambda: ws_cta.col_values(1))[1:] or ["Efectivo"]

@st.cache_data(ttl=300)
def get_metas():
    return intento_seguro(lambda: ws_pre.get_all_records())

# --- 5. LOGICA GLOBAL ---
pe_zone = pytz.timezone('America/Lima')
now = datetime.now(pe_zone)
df = get_data()

# Ahorro Histórico (Suma total de todos los tiempos)
ahorro_total = df[df['Tipo']=='Ingreso']['Monto'].sum() - df[df['Tipo']=='Gasto']['Monto'].sum()

# --- 6. INTERFAZ: ENCABEZADO ---
# Fila superior: Título Grande y KPI Principal
c_title, c_kpi, c_filtros = st.columns([3, 2, 2])

with c_title:
    st.markdown("<h1>🐹 CAPIGASTOS</h1>", unsafe_allow_html=True)

with c_kpi:
    # Usamos container para que tenga fondo blanco
    with st.container():
        st.metric("💰 Ahorro Total (Vida)", f"S/ {ahorro_total:,.2f}")

with c_filtros:
    with st.container():
        c_m, c_a = st.columns(2)
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        sel_mes = c_m.selectbox("Mes", meses, index=now.month-1)
        sel_anio = c_a.number_input("Año", value=now.year, min_value=2024)
        mes_idx = meses.index(sel_mes) + 1

# Filtro de Dataframe
if not df.empty and 'Fecha_dt' in df.columns:
    df_f = df[(df['Fecha_dt'].dt.month == mes_idx) & (df['Fecha_dt'].dt.year == sel_anio)]
else: df_f = df

# --- 7. CUERPO PRINCIPAL (LAYOUT 1/3 - 2/3) ---
col_L, col_R = st.columns([1, 2.2], gap="medium")

# === IZQUIERDA: PANEL DE ACCIÓN ===
with col_L:
    st.subheader("📝 Registrar")
    
    # Formulario de Registro
    with st.container():
        op = st.radio("Operación", ["Gasto 📤", "Ingreso 📥", "Transferencia 🔄"], horizontal=True, label_visibility="collapsed")
        
        with st.form("frm_main", clear_on_submit=True):
            us = st.selectbox("Usuario", ["Rodrigo", "Krys"])
            ctas = get_cuentas()
            metas = get_metas()
            cats = [m['Categoria'] for m in metas] + ["Otros", "Sueldo", "Regalo"]
            
            if op == "Transferencia 🔄":
                c_ori = st.selectbox("Desde", ctas)
                c_des = st.selectbox("Hacia", ctas)
                cat = "Transferencia"
            else:
                cta = st.selectbox("Cuenta", ctas)
                if "Gasto" in op: cat = st.selectbox("Categoría", cats)
                else: cat = st.selectbox("Fuente", ["Sueldo", "Negocio", "Regalo", "Otros"])
            
            monto = st.number_input("Monto S/", min_value=0.01, format="%.2f")
            desc = st.text_input("Detalle")
            
            if st.form_submit_button("💾 Guardar", use_container_width=True):
                f_d = datetime.now(pe_zone).strftime("%Y-%m-%d")
                f_t = datetime.now(pe_zone).strftime("%H:%M:%S")
                
                if op == "Transferencia 🔄":
                    if c_ori == c_des: st.error("Misma cuenta")
                    else:
                        ws_reg.append_row([f_d, f_t, us, c_ori, "Gasto", "Transferencia/Salida", monto, f"-> {c_des}: {desc}"])
                        ws_reg.append_row([f_d, f_t, us, c_des, "Ingreso", "Transferencia/Entrada", monto, f"<- {c_ori}: {desc}"])
                        limpiar_cache(); st.success("OK"); time.sleep(1); st.rerun()
                else:
                    tipo = "Gasto" if "Gasto" in op else "Ingreso"
                    ws_reg.append_row([f_d, f_t, us, cta, tipo, cat, monto, desc])
                    limpiar_cache(); st.success("OK"); time.sleep(1); st.rerun()

    st.write("")
    
    # Gestión (Expandible para no ocupar espacio)
    with st.expander("🛠️ Administrar Cuentas y Metas"):
        pestanas = st.tabs(["Cuentas", "Metas"])
        with pestanas[0]:
            n_cta = st.text_input("Nueva Cuenta")
            if st.button("Crear Cta") and n_cta:
                ws_cta.append_row([n_cta]); limpiar_cache(); st.rerun()
            d_cta = st.selectbox("Eliminar", ["-"]+ctas)
            if st.button("Borrar Cta") and d_cta != "-":
                cell = ws_cta.find(d_cta); ws_cta.delete_rows(cell.row); limpiar_cache(); st.rerun()
        with pestanas[1]:
            n_met = st.text_input("Nueva Meta")
            n_top = st.number_input("Tope", 0)
            if st.button("Crear Meta") and n_met:
                ws_pre.append_row([n_met, n_top]); limpiar_cache(); st.rerun()
            d_met = st.selectbox("Eliminar Meta", ["-"]+[m['Categoria'] for m in metas])
            if st.button("Borrar Meta") and d_met != "-":
                cell = ws_pre.find(d_met); ws_pre.delete_rows(cell.row); limpiar_cache(); st.rerun()


# === DERECHA: DASHBOARD VISUAL ===
with col_R:
    # 1. Resumen Mes
    ing_m = df_f[df_f['Tipo']=='Ingreso']['Monto'].sum()
    gas_m = df_f[df_f['Tipo']=='Gasto']['Monto'].sum()
    bal_m = ing_m - gas_m
    
    st.subheader(f"📊 Resumen {sel_mes}")
    with st.container():
        k1, k2, k3 = st.columns(3)
        k1.metric("Ingresos", f"S/ {ing_m:,.2f}")
        k2.metric("Gastos", f"S/ {gas_m:,.2f}", delta="-Gasto", delta_color="inverse")
        k3.metric("Balance Mes", f"S/ {bal_m:,.2f}", delta="Neto")

    # 2. Cuentas (Grid)
    st.subheader("💳 Estado de Cuentas")
    cols_c = st.columns(3)
    for i, c in enumerate(ctas):
        ing = df[(df['Cuenta']==c)&(df['Tipo']=='Ingreso')]['Monto'].sum()
        gas = df[(df['Cuenta']==c)&(df['Tipo']=='Gasto')]['Monto'].sum()
        sal = ing - gas
        
        with cols_c[i % 3]:
            with st.container():
                st.write(f"**{c}**")
                st.metric("Saldo", f"S/ {sal:,.2f}", label_visibility="collapsed")
                if ing > 0: st.progress(min(max(sal/ing, 0.0), 1.0))
    
    # 3. Metas (2 Columnas)
    st.subheader("🚦 Presupuestos")
    g_cat = df_f[df_f['Tipo']=='Gasto'].groupby('Categoria')['Monto'].sum()
    
    cp1, cp2 = st.columns(2)
    for i, m in enumerate(metas):
        cat = m['Categoria']
        tope = m['Tope_Mensual']
        real = g_cat.get(cat, 0)
        pct = (real/tope) if tope > 0 else 0
        
        with cp1 if i%2==0 else cp2:
            with st.container():
                c1, c2 = st.columns([2,1])
                c1.write(f"**{cat}**")
                c2.caption(f"{real:.0f} / {tope}")
                if pct > 1: st.progress(1.0); st.error("Excedido")
                elif pct > 0.8: st.progress(pct); st.warning("Alerta")
                else: st.progress(pct)

# --- 8. HISTORIAL (ABAJO) ---
st.markdown("---")
with st.expander("📂 Historial Detallado y Borrado"):
    if not df.empty:
        df_show = df[['ID','Fecha','Usuario','Cuenta','Tipo','Categoria','Monto','Descripcion']].copy()
        df_show['Fecha'] = pd.to_datetime(df_show['Fecha']).dt.strftime('%d/%m/%Y')
        st.dataframe(df_show.sort_values('ID', ascending=False), use_container_width=True)
        
        cx1, cx2 = st.columns([4, 1])
        del_id = cx1.number_input("ID a Borrar", min_value=0)
        if cx2.button("❌ Borrar") and del_id > 0:
            try:
                ws_reg.delete_rows(int(del_id))
                limpiar_cache()
                st.success("Eliminado")
                time.sleep(1); st.rerun()
            except: st.error("ID no válido")
