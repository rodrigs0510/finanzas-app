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

# --- 2. ESTILOS CSS (CORRECCIÓN DE CONTRASTE TOTAL) ---
def poner_fondo(imagen_local):
    try:
        with open(imagen_local, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
        
        css = f"""
        <style>
        /* FONDO */
        .stApp {{
            background-image: url(data:image/jpg;base64,{encoded_string});
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        
        /* TÍTULOS PRINCIPALES (EN EL FONDO AZUL) -> BLANCOS */
        h1, .titulo-principal {{
            color: #FFFFFF !important;
            text-shadow: 4px 4px 8px #000000;
            font-weight: 900 !important;
            font-size: 3.5rem !important;
        }}
        
        /* SUBTÍTULOS DENTRO DE CAJAS -> NEGROS */
        h2, h3, h4 {{
            color: #1E1E1E !important;
            font-weight: 700;
        }}

        /* CONTENEDORES (CAJAS BLANCAS) */
        div[data-testid="stExpander"], div[data-testid="stContainer"], form {{
            background-color: rgba(255, 255, 255, 0.95); /* Blanco casi opaco */
            border-radius: 15px;
            padding: 15px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.2);
            border: 1px solid rgba(255,255,255,0.5);
        }}

        /* TEXTOS GENERALES, ETIQUETAS Y INPUTS -> NEGRO */
        p, div, label, span, div[data-testid="stMarkdownContainer"] p {{
            color: #000000 !important;
        }}
        
        /* MÉTRICAS (NÚMEROS GRANDES) */
        div[data-testid="stMetricValue"] {{
            color: #000000 !important;
            font-weight: bold;
        }}
        div[data-testid="stMetricLabel"] {{
            color: #444444 !important;
        }}

        /* BOTONES */
        button {{
            font-weight: bold !important;
            border-radius: 10px !important;
        }}
        </style>
        """
        st.markdown(css, unsafe_allow_html=True)
    except: pass

poner_fondo("fondo.jpg")

# --- 3. CONEXIÓN ---
@st.cache_resource
def conectar_google_sheets():
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
    sh = conectar_google_sheets()
    ws_registro = sh.worksheet("Registro")
    ws_cuentas = sh.worksheet("Cuentas")
    ws_presupuestos = sh.worksheet("Presupuestos")
except:
    st.error("⚠️ Error de conexión."); st.stop()

# --- 4. GESTIÓN DE DATOS ---
def limpiar_cache(): st.cache_data.clear()

@st.cache_data(ttl=60)
def obtener_datos():
    data = intento_seguro(lambda: ws_registro.get_all_records())
    if not data: return pd.DataFrame(columns=['ID','Fecha','Hora','Usuario','Cuenta','Tipo','Categoria','Monto','Descripcion'])
    df = pd.DataFrame(data)
    df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)
    df['Fecha_dt'] = pd.to_datetime(df['Fecha'], format="%Y-%m-%d", errors='coerce')
    df['ID_Fila'] = df.index + 2
    return df

@st.cache_data(ttl=300)
def obtener_cuentas():
    return intento_seguro(lambda: ws_cuentas.col_values(1))[1:] or ["Efectivo"]

@st.cache_data(ttl=300)
def obtener_presupuestos():
    return intento_seguro(lambda: ws_presupuestos.get_all_records())

# --- 5. CABECERA EJECUTIVA (TODO EN UNA LÍNEA) ---
zona_pe = pytz.timezone('America/Lima')
now_pe = datetime.now(zona_pe)
df = obtener_datos()
ahorro_vida = df[df['Tipo']=='Ingreso']['Monto'].sum() - df[df['Tipo']=='Gasto']['Monto'].sum()

# Layout Superior: Logo/Título - Ahorro Total - Filtro Fecha
c_head1, c_head2, c_head3 = st.columns([3, 2, 2])

with c_head1:
    st.markdown('<h1 class="titulo-principal">🐹 CAPIGASTOS</h1>', unsafe_allow_html=True)

with c_head2:
    with st.container():
        st.metric("💰 Ahorro Histórico Total", f"S/ {ahorro_vida:,.2f}")

with c_head3:
    with st.container():
        col_m, col_a = st.columns(2)
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        mes_nom = col_m.selectbox("Mes", meses, index=now_pe.month-1, label_visibility="collapsed")
        anio = col_a.number_input("Año", value=now_pe.year, min_value=2024, label_visibility="collapsed")
        mes_idx = meses.index(mes_nom) + 1

# Filtrado Global
if not df.empty and 'Fecha_dt' in df.columns:
    df_f = df[(df['Fecha_dt'].dt.month == mes_idx) & (df['Fecha_dt'].dt.year == anio)]
else: df_f = df

st.markdown("---")

# --- 6. CUERPO PRINCIPAL (2 COLUMNAS: OPERACIÓN vs VISUALIZACIÓN) ---
# Columna Izquierda (35%): Registro y Gestión
# Columna Derecha (65%): Dashboard
col_op, col_dash = st.columns([1.2, 2.5], gap="medium")

# === COLUMNA IZQUIERDA: OPERACIONES ===
with col_op:
    st.subheader("📝 Panel de Control")
    
    # 1. REGISTRO
    with st.container():
        st.write("##### Nuevo Movimiento")
        op = st.radio("Tipo", ["Gasto 📤", "Ingreso 📥", "Transferencia 🔄"], horizontal=True, label_visibility="collapsed")
        
        with st.form("main_form", clear_on_submit=True):
            lista_ctas = obtener_cuentas()
            metas_data = obtener_presupuestos()
            cats = [m['Categoria'] for m in metas_data] + ["Otros", "Sueldo", "Regalo"]
            
            u = st.selectbox("Usuario", ["Rodrigo", "Krys"])
            
            if op == "Transferencia 🔄":
                c1, c2 = st.columns(2)
                ori = c1.selectbox("Desde", lista_ctas)
                des = c2.selectbox("Hacia", lista_ctas)
                cat = "Transferencia"
            else:
                cta = st.selectbox("Cuenta", lista_ctas)
                cat = st.selectbox("Categoría", cats)
            
            monto = st.number_input("Monto S/", min_value=0.01, format="%.2f")
            desc = st.text_input("Nota", placeholder="Detalle...")
            
            if st.form_submit_button("💾 Guardar", use_container_width=True):
                f_date = datetime.now(zona_pe).strftime("%Y-%m-%d")
                f_time = datetime.now(zona_pe).strftime("%H:%M:%S")
                
                if op == "Transferencia 🔄":
                    if ori == des: st.error("¡Mismas cuentas!")
                    else:
                        ws_registro.append_row([f_date, f_time, u, ori, "Gasto", "Transferencia/Salida", monto, f"-> {des}: {desc}"])
                        ws_registro.append_row([f_date, f_time, u, des, "Ingreso", "Transferencia/Entrada", monto, f"<- {ori}: {desc}"])
                        limpiar_cache(); st.success("Transferido"); time.sleep(1); st.rerun()
                else:
                    tipo = "Gasto" if "Gasto" in op else "Ingreso"
                    ws_registro.append_row([f_date, f_time, u, cta, tipo, cat, monto, desc])
                    limpiar_cache(); st.success("Registrado"); time.sleep(1); st.rerun()

    st.write("") # Espacio

    # 2. GESTIÓN (EXPANDIBLE)
    with st.expander("🛠️ Configurar Cuentas y Metas"):
        tabs = st.tabs(["Cuentas", "Metas", "Ajustes"])
        
        with tabs[0]: # Cuentas
            n_cta = st.text_input("Nueva Cuenta")
            if st.button("➕ Crear Cta") and n_cta:
                ws_cuentas.append_row([n_cta]); limpiar_cache(); st.rerun()
            d_cta = st.selectbox("Borrar", ["-"]+lista_ctas)
            if st.button("🗑️ Eliminar Cta") and d_cta != "-":
                cell = ws_cuentas.find(d_cta); ws_cuentas.delete_rows(cell.row); limpiar_cache(); st.rerun()
                
        with tabs[1]: # Metas
            n_met = st.text_input("Meta")
            n_top = st.number_input("Tope", 0)
            if st.button("➕ Crear Meta") and n_met:
                ws_presupuestos.append_row([n_met, n_top]); limpiar_cache(); st.rerun()
            
        with tabs[2]: # Ajustes
            if st.button("🧹 Refrescar Todo"): limpiar_cache(); st.rerun()

# === COLUMNA DERECHA: DASHBOARD VISUAL ===
with col_dash:
    # 1. TARJETAS RESUMEN DEL MES
    m_ing = df_f[df_f['Tipo']=='Ingreso']['Monto'].sum()
    m_gas = df_f[df_f['Tipo']=='Gasto']['Monto'].sum()
    m_bal = m_ing - m_gas
    
    with st.container():
        st.subheader(f"📊 Reporte de {mes_nom}")
        k1, k2, k3 = st.columns(3)
        k1.metric("Ingresos", f"S/ {m_ing:,.2f}")
        k2.metric("Gastos", f"S/ {m_gas:,.2f}", delta="-Gasto", delta_color="inverse")
        k3.metric("Balance", f"S/ {m_bal:,.2f}", delta="Ahorro")

    st.write("") 

    # 2. ESTADO DE CUENTAS (GRID)
    st.subheader("💳 Mis Cuentas (Saldos Reales)")
    cols_c = st.columns(3)
    for i, c in enumerate(lista_ctas):
        ing = df[(df['Cuenta']==c)&(df['Tipo']=='Ingreso')]['Monto'].sum()
        gas = df[(df['Cuenta']==c)&(df['Tipo']=='Gasto')]['Monto'].sum()
        saldo = ing - gas
        
        with cols_c[i % 3]:
            with st.container():
                st.write(f"**{c}**")
                st.metric("Saldo", f"S/ {saldo:,.2f}", label_visibility="collapsed")
                if ing > 0: st.progress(min(max(saldo/ing, 0.0), 1.0))
    
    st.write("")

    # 3. METAS DE PRESUPUESTO
    st.subheader("🚦 Semáforo de Metas")
    g_cat = df_f[df_f['Tipo']=='Gasto'].groupby('Categoria')['Monto'].sum()
    
    c_p1, c_p2 = st.columns(2)
    for i, m in enumerate(metas_data):
        cat = m['Categoria']
        tope = m['Tope_Mensual']
        real = g_cat.get(cat, 0)
        pct = (real/tope) if tope > 0 else 0
        
        with c_p1 if i%2==0 else c_p2:
            with st.container():
                c_t, c_v = st.columns([2,1])
                c_t.write(f"**{cat}**")
                c_v.caption(f"{real:.0f} / {tope}")
                if pct > 1: st.progress(1.0); st.caption("❌ ¡EXCEDIDO!")
                elif pct > 0.8: st.progress(pct); st.caption("⚠️ Cuidado")
                else: st.progress(pct)

# --- 7. HISTORIAL (ABAJO DEL TODO) ---
st.write("---")
with st.expander("📂 Ver Historial Detallado y Editar"):
    if not df.empty:
        df_ver = df[['ID_Fila','Fecha','Usuario','Cuenta','Tipo','Categoria','Monto','Descripcion']].copy()
        df_ver['Fecha'] = pd.to_datetime(df_ver['Fecha']).dt.strftime('%d/%m/%Y')
        st.dataframe(df_ver.sort_values('ID_Fila', ascending=False), use_container_width=True)
        
        cl1, cl2 = st.columns([4, 1])
        del_id = cl1.number_input("ID a Borrar", min_value=0)
        if cl2.button("❌ Borrar ID") and del_id > 0:
            ws_registro.delete_rows(int(del_id)); limpiar_cache(); st.rerun()
