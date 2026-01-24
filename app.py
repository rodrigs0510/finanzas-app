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

# --- 2. CSS: DISEÑO DE "BLOQUES SÓLIDOS" (LEGIBILIDAD MÁXIMA) ---
def cargar_estilos(imagen_local):
    try:
        with open(imagen_local, "rb") as f:
            b64_img = base64.b64encode(f.read()).decode()
        
        st.markdown(f"""
        <style>
        /* FONDO GENERAL */
        .stApp {{
            background-image: url(data:image/jpg;base64,{b64_img});
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        
        /* --- LA CLAVE: CONTENEDORES PRINCIPALES BLANCOS --- */
        /* Cada vez que usamos "with st.container():" se crea una caja blanca sólida */
        div[data-testid="stVerticalBlock"] > div[data-testid="stContainer"] {{
            background-color: #FFFFFF; /* Blanco puro */
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 20px rgba(0,0,0,0.15); /* Sombra para que resalte del fondo */
            margin-bottom: 25px; /* Espacio entre bloques */
            border: 1px solid #E0E0E0;
        }}

        /* TIPOGRAFÍA OSCURA (Para que se lea bien sobre blanco) */
        h1, h2, h3, h4 {{
            color: #111111 !important;
            font-weight: 800 !important;
        }}
        p, span, div, label {{
            color: #333333 !important;
        }}

        /* INPUTS Y SELECTORES LIMPIOS */
        .stTextInput input, .stNumberInput input, .stSelectbox div {{
            background-color: #F8F9FA !important; /* Gris muy clarito */
            border-radius: 10px !important;
            color: #000000 !important;
        }}

        /* BOTONES */
        .stButton > button {{
            border-radius: 12px !important;
            font-weight: bold !important;
        }}
        
        /* Métrica grande */
        div[data-testid="stMetricValue"] {{
             color: #000000 !important;
        }}

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

# --- 5. POPUPS (VENTANAS EMERGENTES) ---
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
    st.error(f"¿Estás seguro de borrar **{id_o_nombre}**?")
    if st.button("Sí, Borrar Definitivamente", type="primary"):
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

# --- 7. BLOQUE 1: ENCABEZADO GLOBAL (Caja Blanca Superior) ---
with st.container():
    # Usamos columnas para distribuir el header
    c_tit, c_kpi, c_filt = st.columns([2, 2, 2], gap="medium")
    
    with c_tit:
        st.markdown("<h1>🐹 CAPIGASTOS</h1>", unsafe_allow_html=True)
    
    with c_kpi:
        ahorro_vida = df[df['Tipo']=='Ingreso']['Monto'].sum() - df[df['Tipo']=='Gasto']['Monto'].sum()
        st.metric("💰 Ahorro Total (Histórico)", f"S/ {ahorro_vida:,.2f}")
        
    with c_filt:
        st.write("**📅 Filtros de Visualización**")
        cf1, cf2 = st.columns(2)
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        sel_mes = cf1.selectbox("Mes", meses, index=now.month-1, label_visibility="collapsed")
        sel_anio = cf2.number_input("Año", value=now.year, label_visibility="collapsed")
        mes_idx = meses.index(sel_mes) + 1

# Filtrado
if not df.empty and 'Fecha_dt' in df.columns:
    df_f = df[(df['Fecha_dt'].dt.month == mes_idx) & (df['Fecha_dt'].dt.year == sel_anio)]
else: df_f = df

# --- 8. CUERPO PRINCIPAL (DIVISIÓN 1/3 y 2/3) ---
col_izq, col_der = st.columns([1.2, 2.8], gap="medium")

# === COLUMNA IZQUIERDA: OPERACIONES ===
with col_izq:
    # BLOQUE 2: TARJETA DE REGISTRO
    with st.container():
        st.subheader("📝 Registrar Movimiento")
        op = st.radio("Tipo", ["Gasto 📤", "Ingreso 📥", "Transferencia 🔄"], horizontal=True, label_visibility="collapsed")
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
                else: cat = st.selectbox("Fuente", ["Sueldo", "Negocio", "Regalo", "Otros"])
            
            monto = st.number_input("Monto S/", min_value=0.01, format="%.2f")
            desc = st.text_input("Descripción / Nota")
            
            st.write("")
            if st.form_submit_button("💾 Guardar Operación", use_container_width=True):
                fd = datetime.now(pe_zone).strftime("%Y-%m-%d")
                ft = datetime.now(pe_zone).strftime("%H:%M:%S")
                if op == "Transferencia 🔄":
                    if c_ori == c_des: st.error("¡Cuentas iguales!")
                    else:
                        ws_reg.append_row([fd, ft, u, c_ori, "Gasto", "Transferencia/Salida", monto, f"-> {c_des}: {desc}"])
                        ws_reg.append_row([fd, ft, u, c_des, "Ingreso", "Transferencia/Entrada", monto, f"<- {c_ori}: {desc}"])
                        limpiar(); st.success("Listo"); time.sleep(1); st.rerun()
                else:
                    t = "Gasto" if "Gasto" in op else "Ingreso"
                    ws_reg.append_row([fd, ft, u, cta, t, cat, monto, desc])
                    limpiar(); st.success("Listo"); time.sleep(1); st.rerun()

# === COLUMNA DERECHA: DASHBOARD ===
with col_der:
    # BLOQUE 3: RESUMEN DEL MES
    with st.container():
        st.subheader(f"📊 Resumen: {sel_mes} {sel_anio}")
        m_ing = df_f[df_f['Tipo']=='Ingreso']['Monto'].sum()
        m_gas = df_f[df_f['Tipo']=='Gasto']['Monto'].sum()
        
        k1, k2, k3 = st.columns(3)
        k1.metric("Ingresos", f"S/ {m_ing:,.2f}")
        k2.metric("Gastos", f"S/ {m_gas:,.2f}", delta="-Gasto", delta_color="inverse")
        k3.metric("Balance Neto", f"S/ {m_ing - m_gas:,.2f}", delta="Ahorro")

    # BLOQUE 4: CUENTAS
    with st.container():
        # Encabezado con Botón (+) al lado
        c_h_cta, c_b_cta = st.columns([5, 1])
        c_h_cta.subheader("💳 Mis Cuentas (Saldos Reales)")
        if c_b_cta.button("➕ Agregar", key="add_cta_top"): pop_add_cta()
        st.divider()
        
        cols_c = st.columns(3)
        for i, c in enumerate(ctas):
            ing = df[(df['Cuenta']==c)&(df['Tipo']=='Ingreso')]['Monto'].sum()
            gas = df[(df['Cuenta']==c)&(df['Tipo']=='Gasto')]['Monto'].sum()
            sal = ing - gas
            
            with cols_c[i % 3]:
                # Tarjeta interna para cada cuenta
                with st.container(border=True):
                    h1, h2 = st.columns([4, 1])
                    h1.write(f"**{c}**")
                    # Botón borrar pequeño (x)
                    if h2.button("❌", key=f"del_c_{i}", help="Eliminar Cuenta"):
                        pop_delete("cta", c)
                    
                    st.metric("Saldo", f"S/ {sal:,.2f}", label_visibility="collapsed")
                    if ing > 0: st.progress(min(max(sal/ing, 0.0), 1.0))

    # BLOQUE 5: METAS
    with st.container():
        # Encabezado con Botón (+) al lado
        c_h_met, c_b_met = st.columns([5, 1])
        c_h_met.subheader("🚦 Metas de Presupuesto")
        if c_b_met.button("➕ Agregar", key="add_met_top"): pop_add_meta()
        st.divider()

        g_cat = df_f[df_f['Tipo']=='Gasto'].groupby('Categoria')['Monto'].sum()
        cols_m = st.columns(2)
        for i, m in enumerate(metas):
            cat = m['Categoria']
            top = m['Tope_Mensual']
            real = g_cat.get(cat, 0)
            pct = (real/top) if top > 0 else 0
            
            with cols_m[i % 2]:
                with st.container(border=True):
                    m1, m2 = st.columns([4, 1])
                    m1.write(f"**{cat}**")
                    if m2.button("❌", key=f"del_m_{i}", help="Eliminar Meta"):
                        pop_delete("meta", cat)
                        
                    st.caption(f"Gastado: S/ {real:,.0f} de S/ {top:,.0f}")
                    if pct > 1: st.progress(1.0); st.error("¡Excedido!")
                    elif pct > 0.8: st.progress(pct); st.warning("Alerta")
                    else: st.progress(pct)

# --- 9. BLOQUE 6: HISTORIAL (ABAJO) ---
with st.container():
    st.subheader("📂 Últimos Movimientos")
    if not df.empty:
        # Mostramos los últimos 10 en un formato de lista limpia
        rows = df_f.sort_values('ID_Fila', ascending=False).head(10)
        for idx, row in rows.iterrows():
            with st.container(border=True):
                c_r1, c_r2, c_r3, c_r4, c_r5 = st.columns([1, 1.5, 2, 1.5, 0.5])
                c_r1.caption(row['Fecha_dt'].strftime('%d/%m'))
                c_r2.write(f"**{row['Usuario']}**")
                c_r3.write(row['Descripcion'] or row['Categoria'])
                
                color = "green" if row['Tipo']=="Ingreso" else "red"
                c_r4.markdown(f":{color}[**S/ {row['Monto']:.2f}**]")
                
                if c_r5.button("🗑️", key=f"del_r_{row['ID_Fila']}"):
                    pop_delete("reg", row['ID_Fila'])
    else:
        st.info("No hay movimientos este mes.")
