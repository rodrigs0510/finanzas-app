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
        
        /* 5. INPUTS Y SELECTORES (Adiós al negro feo) */
        /* Forzamos que todos los inputs sean blancos con borde suave */
        .stTextInput input, .stNumberInput input, .stSelectbox div, .stDateInput input {{
            background-color: #FFFFFF !important;
            color: #333333 !important;
            border-radius: 12px !important;
            border: 1px solid #E0E0E0 !important;
        }}
        /* Arreglar el texto dentro de los selectores */
        div[data-baseweb="select"] span {{
            color: #333333 !important;
        }}
        /* Menú desplegable blanco */
        ul[data-baseweb="menu"] {{
            background-color: #FFFFFF !important;
        }}

        /* 6. BOTONES REDONDOS (Estilo Pastilla) */
        .stButton > button {{
            border-radius: 30px !important; /* Redondos */
            padding: 10px 25px !important;
            font-weight: bold !important;
            border: none !important;
            transition: all 0.3s ease;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .stButton > button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        }}

        /* Botones pequeños (borrar) */
        button[kind="secondary"] {{
            background-color: #f0f2f6 !important;
            color: #ff4b4b !important;
        }}
        
        /* 7. BARRA DE PROGRESO BONITA */
        .stProgress > div > div > div > div {{
            border-radius: 10px;
        }}

        /* Ocultar header rojo */
        header {{visibility: hidden;}}
        </style>
        """, unsafe_allow_html=True)
    except: pass

cargar_estilos("fondo.jpg")

# --- 3. CONEXIÓN ---
@st.cache_resource
def conectar():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    if "gcp_service_account" in st.secrets:
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    return gspread.authorize(creds).open("Finanzas_RodrigoKrys")

def intento(func):
    try: return func()
    except: time.sleep(1)

try:
    sh = conectar()
    ws_reg = sh.worksheet("Registro")
    ws_cta = sh.worksheet("Cuentas")
    ws_pre = sh.worksheet("Presupuestos")
except:
    st.error("⚠️ Error de conexión."); st.stop()

# --- 4. DATOS ---
def limpiar(): st.cache_data.clear()

@st.cache_data(ttl=60)
def get_data():
    d = intento(lambda: ws_reg.get_all_records())
    if not d: return pd.DataFrame(columns=['ID','Fecha','Hora','Usuario','Cuenta','Tipo','Categoria','Monto','Descripcion'])
    df = pd.DataFrame(d)
    df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)
    df['Fecha_dt'] = pd.to_datetime(df['Fecha'], format="%Y-%m-%d", errors='coerce')
    df['ID_Fila'] = df.index + 2
    return df

@st.cache_data(ttl=300)
def get_cuentas():
    return intento(lambda: ws_cta.col_values(1))[1:] or ["Efectivo"]

@st.cache_data(ttl=300)
def get_metas():
    return intento(lambda: ws_pre.get_all_records())

# --- 5. DIALOGS (POPUPS) ---
@st.dialog("➕ Nueva Cuenta")
def pop_add_cta():
    n = st.text_input("Nombre")
    if st.button("Guardar"):
        ws_cta.append_row([n]); limpiar(); st.rerun()

@st.dialog("➕ Nueva Meta")
def pop_add_meta():
    n = st.text_input("Categoría")
    t = st.number_input("Tope Mensual", min_value=0)
    if st.button("Guardar"):
        ws_pre.append_row([n, t]); limpiar(); st.rerun()

@st.dialog("🗑️ Confirmar Eliminación")
def pop_delete(tipo, id_o_nombre):
    st.write(f"¿Borrar **{id_o_nombre}**?")
    if st.button("Sí, Borrar", type="primary"):
        if tipo == "reg": ws_reg.delete_rows(int(id_o_nombre))
        elif tipo == "cta": 
            c = ws_cta.find(id_o_nombre)
            ws_cta.delete_rows(c.row)
        elif tipo == "meta":
            c = ws_pre.find(id_o_nombre)
            ws_pre.delete_rows(c.row)
        limpiar(); st.rerun()

# --- 6. LOGICA ---
pe_zone = pytz.timezone('America/Lima')
now = datetime.now(pe_zone)
df = get_data()

# --- 7. HEADER LIMPIO (Sin Cajas) ---
# Título y Filtros flotando directamente sobre el fondo
c1, c2 = st.columns([1.5, 1], gap="large")

with c1:
    st.markdown("<h1>🐹 CAPIGASTOS</h1>", unsafe_allow_html=True)

with c2:
    # Filtros estilo "Glass" minimalista (usando columnas nativas)
    fc1, fc2, fc3 = st.columns([1.5, 1, 1])
    # Ahorro Total (KPI limpio)
    ahorro_vida = df[df['Tipo']=='Ingreso']['Monto'].sum() - df[df['Tipo']=='Gasto']['Monto'].sum()
    with fc1:
        st.metric("💰 Ahorro Vida", f"S/ {ahorro_vida:,.0f}")
    
    # Selectores
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    sel_mes = fc2.selectbox("Mes", meses, index=now.month-1, label_visibility="collapsed")
    sel_anio = fc3.number_input("Año", value=now.year, label_visibility="collapsed")
    mes_idx = meses.index(sel_mes) + 1

# Filtro Data
if not df.empty and 'Fecha_dt' in df.columns:
    df_f = df[(df['Fecha_dt'].dt.month == mes_idx) & (df['Fecha_dt'].dt.year == sel_anio)]
else: df_f = df

st.write("") # Espacio aireado

# --- 8. CUERPO (LAYOUT LIMPIO) ---
# Dos grandes columnas invisibles, el contenido dentro son las "islas"
col_L, col_R = st.columns([1, 2], gap="large")

# === IZQUIERDA: TARJETA DE REGISTRO ÚNICA ===
with col_L:
    # Usamos st.form que ahora tiene estilo de tarjeta blanca redondeada gracias al CSS
    with st.form("frm_registro", clear_on_submit=True):
        st.markdown("### 📝 Nuevo Registro")
        
        # Tipo de operación con radio buttons horizontales
        op = st.radio("Tipo", ["Gasto 📤", "Ingreso 📥", "Transferencia 🔄"], horizontal=True, label_visibility="collapsed")
        st.write("") # Separador
        
        ctas = get_cuentas()
        metas = get_metas()
        cats = [m['Categoria'] for m in metas] + ["Otros", "Sueldo", "Regalo"]
        
        u = st.selectbox("Usuario", ["Rodrigo", "Krys"])
        
        if op == "Transferencia 🔄":
            col_t1, col_t2 = st.columns(2)
            c_ori = col_t1.selectbox("Desde", ctas)
            c_des = col_t2.selectbox("Hacia", ctas)
        else:
            cta = st.selectbox("Cuenta", ctas)
            if "Gasto" in op: cat = st.selectbox("Categoría", cats)
            else: cat = st.selectbox("Fuente", ["Sueldo", "Otros"])
            
        monto = st.number_input("Monto S/", min_value=0.01, format="%.2f")
        desc = st.text_input("Nota", placeholder="¿En qué gastaste?")
        
        st.write("")
        if st.form_submit_button("💾 Guardar", use_container_width=True):
            fd = datetime.now(pe_zone).strftime("%Y-%m-%d")
            ft = datetime.now(pe_zone).strftime("%H:%M:%S")
            
            if op == "Transferencia 🔄":
                if c_ori == c_des: st.error("¡Mismas cuentas!")
                else:
                    ws_reg.append_row([fd, ft, u, c_ori, "Gasto", "Transferencia/Salida", monto, f"-> {c_des}: {desc}"])
                    ws_reg.append_row([fd, ft, u, c_des, "Ingreso", "Transferencia/Entrada", monto, f"<- {c_ori}: {desc}"])
                    limpiar(); st.success("Hecho"); time.sleep(1); st.rerun()
            else:
                tipo = "Gasto" if "Gasto" in op else "Ingreso"
                ws_reg.append_row([fd, ft, u, cta, tipo, cat, monto, desc])
                limpiar(); st.success("Hecho"); time.sleep(1); st.rerun()

    # Panel de Gestión Pequeño (Debajo del registro)
    with st.expander("⚙️ Configurar (Cuentas/Metas)"):
        c_conf1, c_conf2 = st.columns(2)
        if c_conf1.button("➕ Cta"): pop_add_cta()
        if c_conf2.button("➕ Meta"): pop_add_meta()

# === DERECHA: DASHBOARD DE ISLAS ===
with col_R:
    # A. KPI CARDS (RESUMEN)
    m_ing = df_f[df_f['Tipo']=='Ingreso']['Monto'].sum()
    m_gas = df_f[df_f['Tipo']=='Gasto']['Monto'].sum()
    
    # 3 Tarjetas flotantes separadas
    kp1, kp2, kp3 = st.columns(3)
    kp1.metric("Ingresos Mes", f"S/ {m_ing:,.2f}")
    kp2.metric("Gastos Mes", f"S/ {m_gas:,.2f}", delta="-Gasto", delta_color="inverse")
    kp3.metric("Ahorro Mes", f"S/ {m_ing - m_gas:,.2f}", delta="Neto")
    
    st.write("") # Aire

    # B. CUENTAS (GRID)
    st.subheader("💳 Mis Cuentas")
    
    cols_grid = st.columns(3)
    for i, c in enumerate(ctas):
        ing = df[(df['Cuenta']==c)&(df['Tipo']=='Ingreso')]['Monto'].sum()
        gas = df[(df['Cuenta']==c)&(df['Tipo']=='Gasto')]['Monto'].sum()
        sal = ing - gas
        
        # Cada cuenta es su propia isla (usamos container que ahora tiene estilo de tarjeta)
        with cols_grid[i % 3]:
            with st.container():
                # Fila título + borrar
                h1, h2 = st.columns([3, 1])
                h1.write(f"**{c}**")
                if h2.button("🗑️", key=f"del_c_{i}"): pop_delete("cta", c)
                
                st.metric("Saldo", f"S/ {sal:,.2f}", label_visibility="collapsed")
                if ing > 0: st.progress(min(max(sal/ing, 0.0), 1.0))

    st.write("")

    # C. METAS (GRID)
    st.subheader("🚦 Presupuestos")
    g_cat = df_f[df_f['Tipo']=='Gasto'].groupby('Categoria')['Monto'].sum()
    
    cols_met = st.columns(2)
    for i, m in enumerate(metas):
        cat = m['Categoria']
        top = m['Tope_Mensual']
        real = g_cat.get(cat, 0)
        pct = (real/top) if top > 0 else 0
        
        with cols_met[i % 2]:
            with st.container():
                m1, m2 = st.columns([4, 1])
                m1.write(f"**{cat}**")
                if m2.button("🗑️", key=f"del_m_{i}"): pop_delete("meta", cat)
                
                st.caption(f"S/ {real:.0f} de {top}")
                if pct > 1: st.progress(1.0); st.error("Excedido")
                elif pct > 0.8: st.progress(pct); st.warning("Alerta")
                else: st.progress(pct)

# --- 9. HISTORIAL COMPACTO ---
st.write("")
with st.expander("📂 Últimos Movimientos (Historial)"):
    if not df.empty:
        # Lista visual simple en vez de tabla gigante
        rows = df_f.sort_values('ID_Fila', ascending=False).head(10)
        for idx, row in rows.iterrows():
            with st.container():
                hc1, hc2, hc3, hc4 = st.columns([1, 3, 2, 1])
                hc1.caption(row['Fecha_dt'].strftime('%d/%b'))
                hc2.write(f"**{row['Categoria']}**")
                hc3.write(f"S/ {row['Monto']:.2f} ({row['Usuario']})")
                if hc4.button("🗑️", key=f"del_r_{row['ID_Fila']}"):
                    pop_delete("reg", row['ID_Fila'])
