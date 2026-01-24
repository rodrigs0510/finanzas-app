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

# --- 2. CSS: DISEÑO "DARK GLASS" (VISIBILIDAD TOTAL) ---
def cargar_estilos(imagen_local):
    try:
        with open(imagen_local, "rb") as f:
            b64_img = base64.b64encode(f.read()).decode()
        
        st.markdown(f"""
        <style>
        /* FONDO FIJO */
        .stApp {{
            background-image: url(data:image/jpg;base64,{b64_img});
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}

        /* --- CRISTAL OSCURO PARA CONTENEDORES --- */
        div[data-testid="stVerticalBlock"] > div[data-testid="stContainer"], form, div[data-testid="stExpander"] {{
            background-color: rgba(30, 30, 40, 0.85) !important; /* Gris oscuro casi negro semi-transparente */
            backdrop-filter: blur(10px); /* Efecto borroso detrás */
            border-radius: 15px;
            padding: 20px;
            border: 1px solid rgba(255, 255, 255, 0.2); /* Borde finito blanco */
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }}

        /* --- TEXTO BLANCO PARA TODO --- */
        h1, h2, h3, h4, p, span, div, label, .stMarkdown {{
            color: #E0E0E0 !important; /* Blanco hueso para no quemar la vista */
        }}
        h1 {{ font-weight: 900 !important; text-shadow: 2px 2px 4px black; }}
        h3 {{ font-weight: 700 !important; }}

        /* --- INPUTS Y SELECTORES (OSCUROS) --- */
        .stTextInput input, .stNumberInput input, .stSelectbox div, .stTextInput div[data-baseweb="input"] {{
            background-color: rgba(50, 50, 60, 0.9) !important;
            color: #FFFFFF !important;
            border-radius: 10px !important;
            border: 1px solid #555 !important;
        }}
        /* Texto dentro de los selectores */
        div[data-baseweb="select"] span {{ color: #FFFFFF !important; }}
        /* Menú desplegable oscuro */
        ul[data-baseweb="menu"] {{ background-color: #333333 !important; }}
        li {{ color: #FFFFFF !important; }}

        /* --- MÉTRICAS (NÚMEROS GRANDES) --- */
        div[data-testid="stMetricValue"] {{
             color: #00D4FF !important; /* Un celeste neón para resaltar números */
             font-weight: 800;
        }}
        div[data-testid="stMetricLabel"] {{ color: #AAAAAA !important; }}

        /* BOTONES */
        button {{ font-weight: bold !important; border-radius: 8px !important; }}
        
        /* Separadores (hr) */
        hr {{ border-color: rgba(255,255,255,0.2) !important; }}

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

# --- 5. POPUPS ---
@st.dialog("➕ Nueva Cuenta")
def pop_add_cta():
    n = st.text_input("Nombre Cuenta")
    if st.button("Guardar"):
        if n: ws_cta.append_row([n]); limpiar(); st.rerun()

@st.dialog("➕ Nueva Meta")
def pop_add_meta():
    n = st.text_input("Categoría/Meta")
    t = st.number_input("Tope Mensual", min_value=0)
    if st.button("Guardar"):
        if n: ws_pre.append_row([n, t]); limpiar(); st.rerun()

@st.dialog("🗑️ Confirmar Borrado")
def pop_delete(tipo, id_o_nombre):
    st.warning(f"¿Seguro que quieres borrar **{id_o_nombre}**?")
    if st.button("Sí, BORRAR", type="primary"):
        if tipo == "reg": ws_reg.delete_rows(int(id_o_nombre))
        elif tipo == "cta": 
            c = ws_cta.find(id_o_nombre); ws_cta.delete_rows(c.row)
        elif tipo == "meta":
            c = ws_pre.find(id_o_nombre); ws_pre.delete_rows(c.row)
        limpiar(); st.rerun()

# --- 6. LÓGICA GLOBAL ---
pe_zone = pytz.timezone('America/Lima')
now = datetime.now(pe_zone)
df = get_data()
ctas = get_cuentas()
metas = get_metas()

# Calcular Saldos Actuales de Cuentas para el KPI
total_disponible = 0
for c in ctas:
    i = df[(df['Cuenta']==c)&(df['Tipo']=='Ingreso')]['Monto'].sum()
    g = df[(df['Cuenta']==c)&(df['Tipo']=='Gasto')]['Monto'].sum()
    total_disponible += (i - g)

# --- 7. HEADER DASHBOARD ---
with st.container():
    c_tit, c_kpi1, c_kpi2, c_filt = st.columns([2, 1.5, 1.5, 2], gap="medium")
    
    with c_tit:
        st.markdown("<h1>🐹 CAPIGASTOS</h1>", unsafe_allow_html=True)
    
    with c_kpi1:
        ahorro_vida = df[df['Tipo']=='Ingreso']['Monto'].sum() - df[df['Tipo']=='Gasto']['Monto'].sum()
        st.metric("💰 Ahorro Histórico", f"S/ {ahorro_vida:,.2f}", help="Ingresos - Gastos desde el inicio de los tiempos")

    with c_kpi2:
        # NUEVA MÉTRICA SOLICITADA
        st.metric("💵 Capital Disponible Hoy", f"S/ {total_disponible:,.2f}", help="Suma real del dinero en todas las cuentas ahora")
        
    with c_filt:
        cf1, cf2 = st.columns(2)
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        sel_mes = cf1.selectbox("Mes Visualización", meses, index=now.month-1)
        sel_anio = cf2.number_input("Año", value=now.year)
        mes_idx = meses.index(sel_mes) + 1

if not df.empty and 'Fecha_dt' in df.columns:
    df_f = df[(df['Fecha_dt'].dt.month == mes_idx) & (df['Fecha_dt'].dt.year == sel_anio)]
else: df_f = df

# --- 8. CUERPO PRINCIPAL ---
col_izq, col_der = st.columns([1.3, 2.7], gap="medium")

# === IZQUIERDA: OPERACIONES ===
with col_izq:
    with st.container():
        st.subheader("📝 Registrar Movimiento")
        op = st.radio("Tipo", ["Gasto 📤", "Ingreso 📥", "Transferencia 🔄"], horizontal=True, label_visibility="collapsed")
        st.divider()
        
        with st.form("frm_main", clear_on_submit=True):
            cats = [m['Categoria'] for m in metas] + ["Otros", "Sueldo", "Regalo"]
            u = st.selectbox("Usuario", ["Rodrigo", "Krys"])
            
            if op == "Transferencia 🔄":
                c1, c2 = st.columns(2)
                c_ori = c1.selectbox("Desde", ctas)
                c_des = c2.selectbox("Hacia", ctas)
            else:
                cta = st.selectbox("Cuenta", ctas)
                if "Gasto" in op: cat = st.selectbox("Categoría", cats)
                else: cat = st.selectbox("Fuente", ["Sueldo", "Negocio", "Regalo", "Otros"])
            
            monto = st.number_input("Monto S/", min_value=0.01, format="%.2f")
            desc = st.text_input("Nota / Descripción")
            
            st.write("")
            if st.form_submit_button("💾 Guardar Operación", use_container_width=True):
                fd = datetime.now(pe_zone).strftime("%Y-%m-%d")
                ft = datetime.now(pe_zone).strftime("%H:%M:%S")
                if op == "Transferencia 🔄":
                    if c_ori == c_des: st.error("¡Mismas cuentas!")
                    else:
                        ws_reg.append_row([fd, ft, u, c_ori, "Gasto", "Transferencia/Salida", monto, f"-> {c_des}: {desc}"])
                        ws_reg.append_row([fd, ft, u, c_des, "Ingreso", "Transferencia/Entrada", monto, f"<- {c_ori}: {desc}"])
                        limpiar(); st.success("Listo"); time.sleep(1); st.rerun()
                else:
                    t = "Gasto" if "Gasto" in op else "Ingreso"
                    ws_reg.append_row([fd, ft, u, cta, t, cat, monto, desc])
                    limpiar(); st.success("Listo"); time.sleep(1); st.rerun()

# === DERECHA: VISUALIZACIÓN ===
with col_der:
    # RESUMEN MES
    with st.container():
        st.subheader(f"📊 Resumen: {sel_mes}")
        m_ing = df_f[df_f['Tipo']=='Ingreso']['Monto'].sum()
        m_gas = df_f[df_f['Tipo']=='Gasto']['Monto'].sum()
        k1, k2, k3 = st.columns(3)
        k1.metric("Ingresos Mes", f"S/ {m_ing:,.2f}")
        k2.metric("Gastos Mes", f"S/ {m_gas:,.2f}")
        k3.metric("Balance Neto", f"S/ {m_ing - m_gas:,.2f}", delta="Ahorro Mes")

    # CUENTAS
    with st.container():
        c_h, c_b = st.columns([5, 1])
        c_h.subheader("💳 Saldos Reales")
        if c_b.button("➕ Agregar", key="add_c"): pop_add_cta()
        st.divider()
        
        cols_c = st.columns(3)
        for i, c in enumerate(ctas):
            ing = df[(df['Cuenta']==c)&(df['Tipo']=='Ingreso')]['Monto'].sum()
            gas = df[(df['Cuenta']==c)&(df['Tipo']=='Gasto')]['Monto'].sum()
            sal = ing - gas
            with cols_c[i % 3]:
                with st.container(border=True): # Tarjeta interna
                    h1, h2 = st.columns([4, 1])
                    h1.write(f"**{c}**")
                    if h2.button("❌", key=f"dc_{i}"): pop_delete("cta", c)
                    st.metric("Saldo", f"S/ {sal:,.2f}", label_visibility="collapsed")
                    if ing > 0: st.progress(min(max(sal/ing, 0.0), 1.0))

    # METAS
    with st.container():
        c_h, c_b = st.columns([5, 1])
        c_h.subheader("🚦 Presupuestos Mensuales")
        if c_b.button("➕ Agregar", key="add_m"): pop_add_meta()
        st.divider()

        g_cat = df_f[df_f['Tipo']=='Gasto'].groupby('Categoria')['Monto'].sum()
        cols_m = st.columns(2)
        for i, m in enumerate(metas):
            cat = m['Categoria']; top = m['Tope_Mensual']
            real = g_cat.get(cat, 0); pct = (real/top) if top > 0 else 0
            with cols_m[i % 2]:
                with st.container(border=True):
                    m1, m2 = st.columns([4, 1])
                    m1.write(f"**{cat}**")
                    if m2.button("❌", key=f"dm_{i}"): pop_delete("meta", cat)
                    st.caption(f"Gastado: S/ {real:,.0f} / S/ {top:,.0f}")
                    if pct > 1: st.progress(1.0); st.error("¡Excedido!")
                    else: st.progress(pct)

# --- 9. HISTORIAL RECIENTE ---
with st.container():
    st.subheader("📂 Últimos Movimientos")
    if not df.empty:
        rows = df_f.sort_values('ID_Fila', ascending=False).head(8)
        for idx, row in rows.iterrows():
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([0.8, 1.5, 2.5, 1.2, 0.5])
                c1.caption(row['Fecha_dt'].strftime('%d/%m'))
                c2.write(f"**{row['Usuario']}**")
                c3.write(row['Descripcion'] or row['Categoria'])
                col = "#00FF00" if row['Tipo']=="Ingreso" else "#FF4444"
                c4.markdown(f"<span style='color:{col}'><b>S/ {row['Monto']:.2f}</b></span>", unsafe_allow_html=True)
                if c5.button("🗑️", key=f"dr_{row['ID_Fila']}"): pop_delete("reg", row['ID_Fila'])
    else:
        st.info("Sin movimientos recientes.")
