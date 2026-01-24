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

# --- 2. CSS: ESTILO "COMIC / STICKER" (VISIBILIDAD EXTREMA) ---
def cargar_estilos(imagen_local):
    try:
        with open(imagen_local, "rb") as f:
            b64_img = base64.b64encode(f.read()).decode()
        
        st.markdown(f"""
        <style>
        /* FONDO */
        .stApp {{
            background-image: url(data:image/jpg;base64,{b64_img});
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}

        /* --- LAS TARJETAS (CAJAS SÓLIDAS) --- */
        /* Esto afecta a todos los bloques principales */
        div[data-testid="stVerticalBlock"] > div > div[data-testid="stContainer"], 
        div[data-testid="stVerticalBlock"] > div > div[data-testid="stForm"],
        div[data-testid="stExpander"] {{
            background-color: #FFFFFF !important; /* BLANCO PURO */
            border: 2px solid #000000 !important; /* BORDE NEGRO */
            border-radius: 15px !important;
            padding: 20px !important;
            box-shadow: 6px 6px 0px rgba(0,0,0,0.8) !important; /* SOMBRA DURA TIPO COMIC */
        }}

        /* --- TIPOGRAFÍA (NEGRO PURO) --- */
        h1, h2, h3, h4, h5, p, span, div, label, li {{
            color: #000000 !important;
            font-family: sans-serif;
        }}
        h1 {{
            text-shadow: 4px 4px 0px #000000;
            color: #FFFFFF !important; /* El título principal sí en blanco */
            font-weight: 900 !important;
            font-size: 3.5rem !important;
            -webkit-text-stroke: 1.5px black; /* Borde negro a las letras */
        }}
        
        /* --- INPUTS (CAJAS DE TEXTO) --- */
        .stTextInput input, .stNumberInput input, .stSelectbox div, .stDateInput input {{
            background-color: #FFFFFF !important;
            color: #000000 !important;
            border: 2px solid #000000 !important; /* Borde negro */
            border-radius: 8px !important;
            font-weight: bold !important;
        }}
        
        /* --- BOTONES --- */
        .stButton > button {{
            background-color: #FF9F9F !important; /* Color salmón para resaltar (como la imagen) */
            color: #000000 !important;
            border: 2px solid #000000 !important;
            border-radius: 10px !important;
            font-weight: bold !important;
            box-shadow: 3px 3px 0px #000000 !important;
        }}
        .stButton > button:active {{
            transform: translateY(2px);
            box-shadow: 1px 1px 0px #000000 !important;
        }}
        
        /* Botones de borrar (pequeños) */
        button[kind="secondary"] {{
            background-color: #FFFFFF !important;
        }}

        /* --- MÉTRICAS --- */
        div[data-testid="stMetric"] {{
            background-color: #F0F0F0 !important;
            border: 2px solid #000000 !important;
            border-radius: 10px;
            padding: 10px;
            box-shadow: 3px 3px 0px rgba(0,0,0,0.2);
            text-align: center;
        }}
        div[data-testid="stMetricValue"] {{
            font-size: 1.8rem !important;
            font-weight: 800 !important;
        }}

        /* OCULTAR HEADER ROJO */
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
    n = st.text_input("Nombre")
    if st.button("Guardar"):
        if n: ws_cta.append_row([n]); limpiar(); st.rerun()

@st.dialog("➕ Nueva Meta")
def pop_add_meta():
    n = st.text_input("Categoría")
    t = st.number_input("Tope", min_value=0)
    if st.button("Guardar"):
        if n: ws_pre.append_row([n, t]); limpiar(); st.rerun()

@st.dialog("🗑️ Confirmar")
def pop_delete(tipo, id_o_nombre):
    st.warning(f"¿Borrar **{id_o_nombre}**?")
    if st.button("Sí, BORRAR"):
        if tipo == "reg": ws_reg.delete_rows(int(id_o_nombre))
        elif tipo == "cta": 
            c = ws_cta.find(id_o_nombre); ws_cta.delete_rows(c.row)
        elif tipo == "meta":
            c = ws_pre.find(id_o_nombre); ws_pre.delete_rows(c.row)
        limpiar(); st.rerun()

# --- 6. LÓGICA ---
pe_zone = pytz.timezone('America/Lima')
now = datetime.now(pe_zone)
df = get_data()

# --- 7. HEADER (CAJA SÓLIDA SUPERIOR) ---
# Título flotante (blanco con borde negro)
st.markdown("<h1>🐹 CAPIGASTOS</h1>", unsafe_allow_html=True)

# Filtros y KPI en una caja sólida blanca
with st.container():
    c1, c2, c3 = st.columns([1.5, 1, 1])
    
    ahorro_vida = df[df['Tipo']=='Ingreso']['Monto'].sum() - df[df['Tipo']=='Gasto']['Monto'].sum()
    with c1:
        st.metric("💰 Ahorro Total (Vida)", f"S/ {ahorro_vida:,.2f}")
        
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    with c2:
        sel_mes = st.selectbox("Mes", meses, index=now.month-1)
    with c3:
        sel_anio = st.number_input("Año", value=now.year)
    
    mes_idx = meses.index(sel_mes) + 1

# Filtrado
if not df.empty and 'Fecha_dt' in df.columns:
    df_f = df[(df['Fecha_dt'].dt.month == mes_idx) & (df['Fecha_dt'].dt.year == sel_anio)]
else: df_f = df

st.write("") # Espacio

# --- 8. CUERPO PRINCIPAL ---
col_L, col_R = st.columns([1.2, 2.5], gap="large")

# === IZQUIERDA: REGISTRO (CAJA BLANCA CON BORDE NEGRO) ===
with col_L:
    with st.container(): # Contenedor
        st.subheader("📝 Registrar Movimiento")
        
        # Formulario
        op = st.radio("Acción", ["Gasto 📤", "Ingreso 📥", "Transferencia 🔄"], horizontal=True)
        st.divider()
        
        with st.form("frm_main", clear_on_submit=True):
            ctas = get_cuentas()
            metas = get_metas()
            cats = [m['Categoria'] for m in metas] + ["Otros", "Sueldo", "Regalo"]
            
            u = st.selectbox("Usuario", ["Rodrigo", "Krys"])
            
            if op == "Transferencia 🔄":
                c1, c2 = st.columns(2)
                c_ori = c1.selectbox("Desde", ctas)
                c_des = c2.selectbox("Hacia", ctas)
            else:
                cta = st.selectbox("Cuenta", ctas)
                if "Gasto" in op: cat = st.selectbox("Categoría", cats)
                else: cat = st.selectbox("Fuente", ["Sueldo", "Otros"])
            
            monto = st.number_input("Monto S/", min_value=0.01, format="%.2f")
            desc = st.text_input("Nota")
            
            st.write("")
            if st.form_submit_button("💾 GUARDAR OPERACIÓN", use_container_width=True):
                fd = datetime.now(pe_zone).strftime("%Y-%m-%d")
                ft = datetime.now(pe_zone).strftime("%H:%M:%S")
                if op == "Transferencia 🔄":
                    if c_ori == c_des: st.error("Cuentas iguales")
                    else:
                        ws_reg.append_row([fd, ft, u, c_ori, "Gasto", "Transferencia/Salida", monto, f"-> {c_des}: {desc}"])
                        ws_reg.append_row([fd, ft, u, c_des, "Ingreso", "Transferencia/Entrada", monto, f"<- {c_ori}: {desc}"])
                        limpiar(); st.success("OK"); time.sleep(1); st.rerun()
                else:
                    t = "Gasto" if "Gasto" in op else "Ingreso"
                    ws_reg.append_row([fd, ft, u, cta, t, cat, monto, desc])
                    limpiar(); st.success("OK"); time.sleep(1); st.rerun()

    # Botones rápidos abajo
    with st.container():
        st.write("**Administrar:**")
        bt1, bt2 = st.columns(2)
        if bt1.button("➕ Cuenta", use_container_width=True): pop_add_cta()
        if bt2.button("➕ Meta", use_container_width=True): pop_add_meta()

# === DERECHA: DASHBOARD (CAJAS BLANCAS CON BORDE NEGRO) ===
with col_R:
    # 1. RESUMEN MES
    with st.container():
        st.subheader(f"📊 Reporte: {sel_mes}")
        m_ing = df_f[df_f['Tipo']=='Ingreso']['Monto'].sum()
        m_gas = df_f[df_f['Tipo']=='Gasto']['Monto'].sum()
        
        k1, k2, k3 = st.columns(3)
        k1.metric("Ingresos", f"S/ {m_ing:,.2f}")
        k2.metric("Gastos", f"S/ {m_gas:,.2f}", delta="-Gasto", delta_color="inverse")
        k3.metric("Ahorro Mes", f"S/ {m_ing - m_gas:,.2f}", delta="Neto")

    # 2. CUENTAS
    with st.container():
        # Título y botón borrar al lado (como pediste)
        st.subheader("💳 Mis Cuentas")
        cols_c = st.columns(3)
        for i, c in enumerate(ctas):
            ing = df[(df['Cuenta']==c)&(df['Tipo']=='Ingreso')]['Monto'].sum()
            gas = df[(df['Cuenta']==c)&(df['Tipo']=='Gasto')]['Monto'].sum()
            sal = ing - gas
            
            with cols_c[i % 3]:
                with st.container(): # Tarjeta interna
                    # Layout: Nombre a la izquierda, Borrar a la derecha
                    h1, h2 = st.columns([3, 1])
                    h1.write(f"**{c}**")
                    if h2.button("🗑️", key=f"d_c_{i}"): pop_delete("cta", c)
                    
                    st.metric("Saldo", f"S/ {sal:,.2f}")
                    if ing > 0: st.progress(min(max(sal/ing, 0.0), 1.0))

    # 3. METAS
    with st.container():
        st.subheader("🚦 Presupuestos")
        g_cat = df_f[df_f['Tipo']=='Gasto'].groupby('Categoria')['Monto'].sum()
        
        cols_m = st.columns(2)
        for i, m in enumerate(metas):
            cat = m['Categoria']; top = m['Tope_Mensual']
            real = g_cat.get(cat, 0); pct = (real/top) if top > 0 else 0
            
            with cols_m[i % 2]:
                with st.container():
                    m1, m2 = st.columns([3, 1])
                    m1.write(f"**{cat}**")
                    if m2.button("🗑️", key=f"d_m_{i}"): pop_delete("meta", cat)
                    
                    st.caption(f"S/ {real:,.0f} / {top:,.0f}")
                    if pct > 1: st.progress(1.0); st.error("Excedido")
                    else: st.progress(pct)

# --- 9. HISTORIAL ---
with st.container():
    st.subheader("📂 Últimos Movimientos")
    if not df.empty:
        rows = df_f.sort_values('ID_Fila', ascending=False).head(10)
        for idx, row in rows.iterrows():
            with st.container():
                rc1, rc2, rc3, rc4, rc5 = st.columns([1, 1.5, 3, 1.5, 0.5])
                rc1.caption(row['Fecha_dt'].strftime('%d/%m'))
                rc2.write(f"**{row['Usuario']}**")
                rc3.write(row['Descripcion'] or row['Categoria'])
                col = "green" if row['Tipo']=="Ingreso" else "red"
                rc4.markdown(f":{col}[**S/ {row['Monto']:.2f}**]")
                # Botón de borrado simple (x)
                if rc5.button("❌", key=f"del_{row['ID_Fila']}"): pop_delete("reg", row['ID_Fila'])
