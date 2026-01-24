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

# --- 2. CSS: DISEÑO DE TARJETAS LIMPIAS (CONTRASTE REAL) ---
def cargar_estilos(imagen_local):
    try:
        with open(imagen_local, "rb") as f:
            b64_img = base64.b64encode(f.read()).decode()
        
        st.markdown(f"""
        <style>
        /* 1. FONDO DE CARPINCHOS */
        .stApp {{
            background-image: url(data:image/jpg;base64,{b64_img});
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}

        /* 2. CLASE PARA LAS "TARJETAS BLANCAS" */
        /* Forzamos que los contenedores sean blancos y opacos */
        div[data-testid="stVerticalBlock"] > div > div[data-testid="stContainer"], 
        div[data-testid="stForm"],
        div[data-testid="stExpander"] {{
            background-color: #FFFFFF !important;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1); /* Sombra suave */
            border: 1px solid #E0E0E0;
            margin-bottom: 20px;
        }}

        /* 3. TIPOGRAFÍA (NEGRO PURO) */
        h1, h2, h3, h4, h5, p, span, div, label, li {{
            color: #212121 !important;
            font-family: sans-serif;
        }}
        
        /* 4. INPUTS Y SELECTORES (LIMPIOS Y LEGIBLES) */
        /* Fondo gris muy claro, letra negra */
        .stTextInput input, .stNumberInput input, .stSelectbox div, .stDateInput input {{
            background-color: #F8F9FA !important; 
            color: #000000 !important;
            border: 1px solid #CCCCCC !important;
            border-radius: 8px !important;
        }}
        
        /* Arreglo para menús desplegables */
        ul[data-baseweb="menu"] {{
            background-color: #FFFFFF !important;
        }}
        div[data-baseweb="select"] span {{
            color: #000000 !important;
        }}

        /* 5. HEADER PERSONALIZADO (Caja blanca para el título) */
        .header-box {{
            background-color: #FFFFFF;
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            border: 1px solid #E0E0E0;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        
        .titulo-grande {{
            font-size: 3rem;
            font-weight: 900;
            margin: 0;
            color: #FF8C00 !important; /* Un naranja Capibara */
            text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
        }}

        /* 6. BOTONES */
        .stButton > button {{
            border-radius: 8px !important;
            font-weight: 600 !important;
            background-color: #F0F2F6;
            color: #000000 !important;
            border: 1px solid #D1D5DB !important;
        }}
        .stButton > button:hover {{
            border-color: #FF8C00 !important;
            color: #FF8C00 !important;
        }}
        
        /* Botón primario (Guardar) */
        button[kind="primary"] {{
            background-color: #FF8C00 !important;
            color: white !important;
            border: none !important;
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

# --- 5. POPUPS ---
@st.dialog("➕ Nueva Cuenta")
def pop_add_cta():
    n = st.text_input("Nombre")
    if st.button("Guardar", type="primary"):
        if n: ws_cta.append_row([n]); limpiar(); st.rerun()

@st.dialog("➕ Nueva Meta")
def pop_add_meta():
    n = st.text_input("Categoría")
    t = st.number_input("Tope", min_value=0)
    if st.button("Guardar", type="primary"):
        if n: ws_pre.append_row([n, t]); limpiar(); st.rerun()

@st.dialog("🗑️ Confirmar")
def pop_delete(tipo, id_o_nombre):
    st.warning(f"¿Borrar **{id_o_nombre}**?")
    if st.button("Sí, BORRAR", type="primary"):
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

# --- 7. HEADER (CAJA BLANCA COMPLETA) ---
# Usamos HTML para crear una caja blanca unificada para el título
ahorro_vida = df[df['Tipo']=='Ingreso']['Monto'].sum() - df[df['Tipo']=='Gasto']['Monto'].sum()

st.markdown(f"""
<div class="header-box">
    <div>
        <h1 class="titulo-grande">🐹 CAPIGASTOS</h1>
        <p style="margin:0; color:#666;">Control de Finanzas R&K</p>
    </div>
    <div style="text-align:right;">
        <h3 style="margin:0; color:#212121;">💰 Ahorro Total</h3>
        <h2 style="margin:0; color:#2E7D32;">S/ {ahorro_vida:,.2f}</h2>
    </div>
</div>
""", unsafe_allow_html=True)

# FILTROS (En su propia caja blanca abajo del título)
with st.container():
    c_f1, c_f2 = st.columns(2)
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    with c_f1:
        sel_mes = st.selectbox("📅 Mes de Visualización", meses, index=now.month-1)
    with c_f2:
        sel_anio = st.number_input("📅 Año", value=now.year)
    mes_idx = meses.index(sel_mes) + 1

# Filtrado
if not df.empty and 'Fecha_dt' in df.columns:
    df_f = df[(df['Fecha_dt'].dt.month == mes_idx) & (df['Fecha_dt'].dt.year == sel_anio)]
else: df_f = df

# --- 8. CUERPO (COLUMNAS) ---
col_izq, col_der = st.columns([1, 2], gap="medium")

# === IZQUIERDA: REGISTRO (TODA LA SECCIÓN EN UNA TARJETA BLANCA) ===
with col_izq:
    # AQUI ESTA LA CAJA BLANCA QUE PEDISTE PARA EL REGISTRO
    with st.container():
        st.subheader("📝 Nuevo Registro")
        st.divider()
        
        # Todo esto está dentro del fondo blanco
        op = st.radio("Acción", ["Gasto 📤", "Ingreso 📥", "Transferencia 🔄"], horizontal=True)
        st.write("") # Espacio
        
        # El formulario
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
                else: cat = st.selectbox("Fuente", ["Sueldo", "Negocio", "Regalo", "Otros"])
            
            monto = st.number_input("Monto S/", min_value=0.01, format="%.2f")
            desc = st.text_input("Nota")
            
            st.write("")
            # Botón primario (Color Naranja)
            if st.form_submit_button("💾 GUARDAR", type="primary", use_container_width=True):
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
                    
    # Gestión Rápida (En otra tarjeta blanca pequeña)
    with st.container():
        st.write("⚙️ **Gestión Rápida**")
        b1, b2 = st.columns(2)
        if b1.button("➕ Cuenta", use_container_width=True): pop_add_cta()
        if b2.button("➕ Meta", use_container_width=True): pop_add_meta()

# === DERECHA: DASHBOARD (CADA SECCIÓN EN SU CAJA BLANCA) ===
with col_der:
    # 1. RESUMEN MES (CAJA BLANCA)
    with st.container():
        st.subheader(f"📊 Resumen: {sel_mes}")
        m_ing = df_f[df_f['Tipo']=='Ingreso']['Monto'].sum()
        m_gas = df_f[df_f['Tipo']=='Gasto']['Monto'].sum()
        
        k1, k2, k3 = st.columns(3)
        k1.metric("Ingresos", f"S/ {m_ing:,.2f}")
        k2.metric("Gastos", f"S/ {m_gas:,.2f}", delta="-Gasto", delta_color="inverse")
        k3.metric("Balance", f"S/ {m_ing - m_gas:,.2f}", delta="Ahorro")

    # 2. CUENTAS (CAJA BLANCA)
    with st.container():
        st.subheader("💳 Mis Cuentas")
        cols_c = st.columns(3)
        for i, c in enumerate(ctas):
            ing = df[(df['Cuenta']==c)&(df['Tipo']=='Ingreso')]['Monto'].sum()
            gas = df[(df['Cuenta']==c)&(df['Tipo']=='Gasto')]['Monto'].sum()
            sal = ing - gas
            
            with cols_c[i % 3]:
                # Tarjeta interna grisácea para diferenciar
                with st.container(border=True):
                    h1, h2 = st.columns([3, 1])
                    h1.write(f"**{c}**")
                    if h2.button("🗑️", key=f"dc_{i}"): pop_delete("cta", c)
                    st.metric("Saldo", f"S/ {sal:,.2f}", label_visibility="collapsed")
                    if ing > 0: st.progress(min(max(sal/ing, 0.0), 1.0))

    # 3. METAS (CAJA BLANCA)
    with st.container():
        st.subheader("🚦 Presupuestos")
        g_cat = df_f[df_f['Tipo']=='Gasto'].groupby('Categoria')['Monto'].sum()
        
        cols_m = st.columns(2)
        for i, m in enumerate(metas):
            cat = m['Categoria']; top = m['Tope_Mensual']
            real = g_cat.get(cat, 0); pct = (real/top) if top > 0 else 0
            
            with cols_m[i % 2]:
                with st.container(border=True):
                    m1, m2 = st.columns([3, 1])
                    m1.write(f"**{cat}**")
                    if m2.button("🗑️", key=f"dm_{i}"): pop_delete("meta", cat)
                    st.caption(f"S/ {real:,.0f} / {top:,.0f}")
                    if pct > 1: st.progress(1.0); st.error("Excedido")
                    else: st.progress(pct)

# --- 9. HISTORIAL (CAJA BLANCA FINAL) ---
with st.container():
    st.subheader("📂 Últimos Movimientos")
    if not df.empty:
        rows = df_f.sort_values('ID_Fila', ascending=False).head(8)
        for idx, row in rows.iterrows():
            with st.container(border=True):
                rc1, rc2, rc3, rc4, rc5 = st.columns([1, 1.5, 3, 1.5, 0.5])
                rc1.caption(row['Fecha_dt'].strftime('%d/%m'))
                rc2.write(f"**{row['Usuario']}**")
                rc3.write(row['Descripcion'] or row['Categoria'])
                col = "green" if row['Tipo']=="Ingreso" else "red"
                rc4.markdown(f":{col}[**S/ {row['Monto']:.2f}**]")
                if rc5.button("❌", key=f"d_r_{row['ID_Fila']}"): pop_delete("reg", row['ID_Fila'])
