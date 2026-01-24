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

# --- 2. CSS: DISEÑO "SOLID CARDS" (CONTRASTE TOTAL) ---
def cargar_estilos(imagen_local):
    try:
        with open(imagen_local, "rb") as f:
            b64_img = base64.b64encode(f.read()).decode()
        
        st.markdown(f"""
        <style>
        /* 1. EL FONDO (MANTEL) */
        .stApp {{
            background-image: url(data:image/jpg;base64,{b64_img});
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}

        /* 2. EL "PISO" (CONTENEDORES BLANCOS SÓLIDOS) */
        /* Todo lo que sea un contenedor o formulario será BLANCO OPACO */
        div[data-testid="stVerticalBlock"] > div > div[data-testid="stContainer"], 
        form, 
        div[data-testid="stExpander"] {{
            background-color: #FFFFFF !important; /* BLANCO PURO */
            border-radius: 15px;
            padding: 20px;
            border: 2px solid #E5E5E5; /* Borde gris suave */
            box-shadow: 0 4px 10px rgba(0,0,0,0.2); /* Sombra para que flote */
        }}

        /* 3. TIPOGRAFÍA (NEGRA SIEMPRE) */
        h1, h2, h3, h4 {{
            color: #000000 !important;
            font-weight: 800 !important;
        }}
        
        p, div, span, label, li {{
            color: #333333 !important; /* Gris muy oscuro */
        }}

        /* 4. INPUTS Y SELECTORES (FONDO GRIS CLARO) */
        .stTextInput input, .stNumberInput input, .stSelectbox div, .stDateInput input {{
            background-color: #F0F2F6 !important; /* Gris muy clarito para diferenciar del fondo blanco */
            color: #000000 !important;
            border-radius: 8px !important;
            border: 1px solid #CCC !important;
        }}
        
        /* 5. TARJETAS DE MÉTRICAS (KPIs) */
        div[data-testid="stMetric"] {{
            background-color: #F9F9F9 !important;
            padding: 15px;
            border-radius: 10px;
            border: 1px solid #eee;
            text-align: center;
        }}
        div[data-testid="stMetricValue"] {{
            font-size: 1.8rem !important;
            color: #2E86C1 !important; /* Azul profesional */
        }}

        /* 6. BOTONES */
        button {{
            border-radius: 8px !important;
            font-weight: bold !important;
            transition: transform 0.1s;
        }}
        button:active {{
            transform: scale(0.98);
        }}

        /* Ocultar header rojo de Streamlit */
        header {{visibility: hidden;}}
        
        /* Ajuste especial para el Título Principal (lo dejamos flotar con sombra) */
        .titulo-app {{
            color: #FFFFFF !important;
            text-shadow: 4px 4px 0px #000000;
            font-size: 4rem;
            font-weight: 900;
            margin-bottom: 20px;
        }}
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

# --- 7. HEADER (TÍTULO Y FILTROS) ---
c_title, c_filtros = st.columns([1, 2], gap="large")

with c_title:
    st.markdown('<h1 class="titulo-app">🐹 CAPIGASTOS</h1>', unsafe_allow_html=True)

with c_filtros:
    # EL CONTENEDOR BLANCO PARA LOS FILTROS
    with st.container():
        c1, c2, c3 = st.columns(3)
        
        # KPI: AHORRO TOTAL DE LA VIDA (Como la pastilla rosa que pediste)
        ahorro_vida = df[df['Tipo']=='Ingreso']['Monto'].sum() - df[df['Tipo']=='Gasto']['Monto'].sum()
        with c1:
            st.metric("💰 Ahorro Histórico", f"S/ {ahorro_vida:,.2f}")
            
        # FILTROS DE TIEMPO
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        with c2:
            sel_mes = st.selectbox("Mes", meses, index=now.month-1, label_visibility="collapsed")
        with c3:
            sel_anio = st.number_input("Año", value=now.year, label_visibility="collapsed")
            
        mes_idx = meses.index(sel_mes) + 1

# Filtrado
if not df.empty and 'Fecha_dt' in df.columns:
    df_f = df[(df['Fecha_dt'].dt.month == mes_idx) & (df['Fecha_dt'].dt.year == sel_anio)]
else: df_f = df

# --- 8. CUERPO (DOS COLUMNAS SÓLIDAS) ---
col_L, col_R = st.columns([1.2, 2.5], gap="large")

# === IZQUIERDA: REGISTRO ===
with col_L:
    # ESTO ES UN "PISO" BLANCO SÓLIDO
    with st.form("frm_main", clear_on_submit=True):
        st.subheader("📝 Registrar")
        st.divider()
        
        op = st.radio("Acción", ["Gasto 📤", "Ingreso 📥", "Transferencia 🔄"], horizontal=True, label_visibility="collapsed")
        st.write("")
        
        ctas = get_cuentas()
        metas = get_metas()
        cats = [m['Categoria'] for m in metas] + ["Otros", "Sueldo", "Regalo"]
        
        u = st.selectbox("Usuario", ["Rodrigo", "Krys"])
        
        if op == "Transferencia 🔄":
            cc1, cc2 = st.columns(2)
            c_ori = cc1.selectbox("Desde", ctas)
            c_des = cc2.selectbox("Hacia", ctas)
        else:
            cta = st.selectbox("Cuenta", ctas)
            if "Gasto" in op: cat = st.selectbox("Categoría", cats)
            else: cat = st.selectbox("Fuente", ["Sueldo", "Otros"])
        
        monto = st.number_input("Monto S/", min_value=0.01, format="%.2f")
        desc = st.text_input("Nota")
        
        st.write("")
        if st.form_submit_button("💾 GUARDAR", use_container_width=True):
            fd = datetime.now(pe_zone).strftime("%Y-%m-%d")
            ft = datetime.now(pe_zone).strftime("%H:%M:%S")
            if op == "Transferencia 🔄":
                if c_ori == c_des: st.error("¡Iguales!")
                else:
                    ws_reg.append_row([fd, ft, u, c_ori, "Gasto", "Transferencia/Salida", monto, f"-> {c_des}: {desc}"])
                    ws_reg.append_row([fd, ft, u, c_des, "Ingreso", "Transferencia/Entrada", monto, f"<- {c_ori}: {desc}"])
                    limpiar(); st.success("OK"); time.sleep(1); st.rerun()
            else:
                t = "Gasto" if "Gasto" in op else "Ingreso"
                ws_reg.append_row([fd, ft, u, cta, t, cat, monto, desc])
                limpiar(); st.success("OK"); time.sleep(1); st.rerun()

    # Botones de gestión rápida abajo
    with st.container():
        st.write("**Gestión Rápida**")
        cg1, cg2 = st.columns(2)
        if cg1.button("➕ Cuenta", use_container_width=True): pop_add_cta()
        if cg2.button("➕ Meta", use_container_width=True): pop_add_meta()

# === DERECHA: DASHBOARD ===
with col_R:
    # 1. TARJETA DE RESUMEN
    with st.container():
        st.subheader(f"📊 Reporte de {sel_mes}")
        m_ing = df_f[df_f['Tipo']=='Ingreso']['Monto'].sum()
        m_gas = df_f[df_f['Tipo']=='Gasto']['Monto'].sum()
        
        kp1, kp2, kp3 = st.columns(3)
        kp1.metric("Ingresos", f"S/ {m_ing:,.2f}")
        kp2.metric("Gastos", f"S/ {m_gas:,.2f}", delta="-Gasto", delta_color="inverse")
        kp3.metric("Ahorro Mes", f"S/ {m_ing - m_gas:,.2f}", delta="Neto")

    # 2. TARJETA DE CUENTAS
    with st.container():
        st.subheader("💳 Mis Cuentas")
        cols_c = st.columns(3)
        for i, c in enumerate(ctas):
            ing = df[(df['Cuenta']==c)&(df['Tipo']=='Ingreso')]['Monto'].sum()
            gas = df[(df['Cuenta']==c)&(df['Tipo']=='Gasto')]['Monto'].sum()
            sal = ing - gas
            
            with cols_c[i % 3]:
                # Tarjeta interna para resaltar la cuenta
                with st.container(border=True):
                    ch1, ch2 = st.columns([4, 1])
                    ch1.write(f"**{c}**")
                    if ch2.button("🗑️", key=f"d_c_{i}"): pop_delete("cta", c)
                    st.metric("Saldo", f"S/ {sal:,.2f}", label_visibility="collapsed")
                    if ing > 0: st.progress(min(max(sal/ing, 0.0), 1.0))

    # 3. TARJETA DE METAS
    with st.container():
        st.subheader("🚦 Presupuestos")
        g_cat = df_f[df_f['Tipo']=='Gasto'].groupby('Categoria')['Monto'].sum()
        
        cols_m = st.columns(2)
        for i, m in enumerate(metas):
            cat = m['Categoria']; top = m['Tope_Mensual']
            real = g_cat.get(cat, 0); pct = (real/top) if top > 0 else 0
            
            with cols_m[i % 2]:
                with st.container(border=True):
                    mh1, mh2 = st.columns([4, 1])
                    mh1.write(f"**{cat}**")
                    if mh2.button("🗑️", key=f"d_m_{i}"): pop_delete("meta", cat)
                    st.caption(f"{real:,.0f} / {top:,.0f}")
                    if pct > 1: st.progress(1.0); st.error("Excedido")
                    else: st.progress(pct)

# --- 9. HISTORIAL (TARJETA INFERIOR) ---
with st.container():
    st.subheader("📂 Últimos Movimientos")
    if not df.empty:
        rows = df_f.sort_values('ID_Fila', ascending=False).head(10)
        for idx, row in rows.iterrows():
            with st.container(border=True):
                rc1, rc2, rc3, rc4, rc5 = st.columns([1, 2, 3, 2, 1])
                rc1.caption(row['Fecha_dt'].strftime('%d/%m'))
                rc2.write(f"**{row['Usuario']}**")
                rc3.write(row['Descripcion'] or row['Categoria'])
                col = "green" if row['Tipo']=="Ingreso" else "red"
                rc4.markdown(f":{col}[**S/ {row['Monto']:.2f}**]")
                if rc5.button("🗑️", key=f"del_{row['ID_Fila']}"): pop_delete("reg", row['ID_Fila'])
