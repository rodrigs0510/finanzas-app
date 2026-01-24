import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import base64
import pytz

# --- 1. CONFIGURACIÓN (PANTALLA ANCHA) ---
st.set_page_config(page_title="CAPIGASTOS", layout="wide", page_icon="🐹")

# --- 2. ESTILO VISUAL (CORREGIDO: TEXTO OSCURO) ---
def poner_fondo(imagen_local):
    try:
        with open(imagen_local, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
        
        css = f"""
        <style>
        /* Fondo General de Carpinchos */
        .stApp {{
            background-image: url(data:image/jpg;base64,{encoded_string});
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        
        /* Título Principal (H1) en Blanco con Sombra (porque está sobre el fondo azul) */
        h1 {{
            color: #FFFFFF !important;
            text-shadow: 3px 3px 6px rgba(0,0,0,0.8);
            font-weight: 900;
        }}
        
        /* Contenedores de Cristal (Glassmorphism) */
        div[data-testid="stExpander"], div[data-testid="stContainer"], div[data-testid="stMetric"], form {{
            background-color: rgba(255, 255, 255, 0.92); /* Blanco casi sólido para legibilidad */
            border-radius: 15px;
            padding: 20px;
            border: 1px solid rgba(255, 255, 255, 0.5);
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        }}
        
        /* CORRECCIÓN: Todo texto dentro de contenedores será OSCURO */
        h2, h3, h4, p, span, label, div[data-testid="stMarkdownContainer"] p {{
            color: #262730 !important; /* Gris oscuro casi negro */
        }}
        
        /* Botones personalizados */
        button {{
            font-weight: bold !important;
        }}
        
        /* Ajuste para que las columnas no se peguen */
        div[data-testid="column"] {{
            padding: 10px;
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

# Retry Logic
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
    st.error("⚠️ Error de conexión. Recarga."); st.stop()

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
    cuentas = intento_seguro(lambda: ws_cuentas.col_values(1))
    return cuentas[1:] if len(cuentas)>1 else ["Efectivo"]

@st.cache_data(ttl=300)
def obtener_presupuestos():
    return intento_seguro(lambda: ws_presupuestos.get_all_records())

# --- 5. INTERFAZ SUPERIOR (HEADER) ---
zona_pe = pytz.timezone('America/Lima')
now_pe = datetime.now(zona_pe)

c_tit, c_conf = st.columns([4, 1])
with c_tit:
    st.title("🐹 CAPIGASTOS")
with c_conf:
    # Botón discreto para configuración
    with st.expander("⚙️ Ajustes"):
        st.caption("Gestión Rápida")
        if st.button("Limpiar Caché"): limpiar_cache(); st.rerun()

# --- 6. PANEL DE CONTROL (FILTROS) ---
df = obtener_datos()
ing_hist = df[df['Tipo']=='Ingreso']['Monto'].sum()
gas_hist = df[df['Tipo']=='Gasto']['Monto'].sum()

# Contenedor de Filtros Horizontal
with st.container():
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        st.subheader(f"💰 Ahorro Histórico: S/ {ing_hist - gas_hist:,.2f}")
    with c2:
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        mes_nom = st.selectbox("Mes", meses, index=now_pe.month-1, label_visibility="collapsed")
    with c3:
        anio = st.number_input("Año", value=now_pe.year, min_value=2024, label_visibility="collapsed")
    
    mes_idx = meses.index(mes_nom) + 1

# Filtrado
if not df.empty and 'Fecha_dt' in df.columns:
    df_f = df[(df['Fecha_dt'].dt.month == mes_idx) & (df['Fecha_dt'].dt.year == anio)]
else: df_f = df

# --- 7. LAYOUT PRINCIPAL (IZQUIERDA: REGISTRO | DERECHA: DASHBOARD) ---
col_izq, col_der = st.columns([1, 2], gap="large") # 1/3 para registro, 2/3 para datos

# === COLUMNA IZQUIERDA: REGISTRO ===
with col_izq:
    st.subheader("📝 Registrar")
    
    with st.container(): # Contenedor Blanco
        tipo_op = st.radio("Acción", ["Gasto 📤", "Ingreso 📥", "Transferencia 🔄"], horizontal=True, label_visibility="collapsed")
        
        with st.form("form_reg", clear_on_submit=True):
            user = st.selectbox("Usuario", ["Rodrigo", "Krys"])
            
            lista_ctas = obtener_cuentas()
            metas = obtener_presupuestos()
            cats_disp = [m['Categoria'] for m in metas] + ["Otros", "Sueldo", "Regalo"]
            
            if tipo_op == "Transferencia 🔄":
                c_ori = st.selectbox("Desde", lista_ctas)
                c_des = st.selectbox("Hacia", lista_ctas)
                cat = "Transferencia"
            else:
                cta = st.selectbox("Cuenta", lista_ctas)
                cat = st.selectbox("Categoría", cats_disp)
            
            monto = st.number_input("Monto S/", min_value=0.01, format="%.2f")
            desc = st.text_input("Nota", placeholder="Detalle...")
            
            if st.form_submit_button("💾 Guardar Movimiento", use_container_width=True):
                fecha = datetime.now(zona_pe).strftime("%Y-%m-%d")
                hora = datetime.now(zona_pe).strftime("%H:%M:%S")
                
                if tipo_op == "Transferencia 🔄":
                    if c_ori == c_des: st.error("Cuentas iguales")
                    else:
                        ws_registro.append_row([fecha, hora, user, c_ori, "Gasto", "Transferencia/Salida", monto, f"-> {c_des}: {desc}"])
                        ws_registro.append_row([fecha, hora, user, c_des, "Ingreso", "Transferencia/Entrada", monto, f"<- {c_ori}: {desc}"])
                        limpiar_cache(); st.success("¡Listo!"); time.sleep(1); st.rerun()
                else:
                    t_real = "Gasto" if "Gasto" in tipo_op else "Ingreso"
                    ws_registro.append_row([fecha, hora, user, cta, t_real, cat, monto, desc])
                    limpiar_cache(); st.success("¡Listo!"); time.sleep(1); st.rerun()
    
    # Gestión Rápida (Abajo del registro)
    with st.expander("🛠️ Administrar Cuentas/Metas"):
        t1, t2 = st.tabs(["Cuentas", "Metas"])
        with t1:
            nueva_c = st.text_input("Nueva Cuenta")
            if st.button("Crear Cta") and nueva_c:
                ws_cuentas.append_row([nueva_c]); limpiar_cache(); st.rerun()
            del_c = st.selectbox("Borrar Cta", ["-"]+lista_ctas)
            if st.button("Eliminar Cta") and del_c != "-":
                cell = ws_cuentas.find(del_c); ws_cuentas.delete_rows(cell.row); limpiar_cache(); st.rerun()
        with t2:
            nueva_m = st.text_input("Nueva Meta")
            tope_m = st.number_input("Tope", 0)
            if st.button("Crear Meta") and nueva_m:
                ws_presupuestos.append_row([nueva_m, tope_m]); limpiar_cache(); st.rerun()

# === COLUMNA DERECHA: DASHBOARD ===
with col_der:
    # 1. Métricas del Mes
    m_ing = df_f[df_f['Tipo']=='Ingreso']['Monto'].sum()
    m_gas = df_f[df_f['Tipo']=='Gasto']['Monto'].sum()
    m_bal = m_ing - m_gas
    
    c_m1, c_m2, c_m3 = st.columns(3)
    c_m1.metric("Ingresos Mes", f"S/ {m_ing:,.2f}")
    c_m2.metric("Gastos Mes", f"S/ {m_gas:,.2f}", delta="-Gasto", delta_color="inverse")
    c_m3.metric("Balance Mes", f"S/ {m_bal:,.2f}", delta="Ahorro")
    
    st.write("---")
    
    # 2. Tarjetas de Cuentas (Saldos Reales)
    st.subheader("💳 Mis Cuentas")
    cols_ctas = st.columns(3)
    for i, c in enumerate(lista_ctas):
        ing_c = df[(df['Cuenta']==c)&(df['Tipo']=='Ingreso')]['Monto'].sum()
        gas_c = df[(df['Cuenta']==c)&(df['Tipo']=='Gasto')]['Monto'].sum()
        saldo = ing_c - gas_c
        
        with cols_ctas[i % 3]:
            with st.container():
                st.write(f"**{c}**")
                st.metric("Saldo", f"S/ {saldo:,.2f}", label_visibility="collapsed")
                # Barra simple
                if ing_c > 0: st.progress(min(max(saldo/ing_c, 0.0), 1.0))
    
    st.write("---")
    
    # 3. Metas de Presupuesto
    st.subheader("🚦 Metas Mensuales")
    gastos_cat = df_f[df_f['Tipo']=='Gasto'].groupby('Categoria')['Monto'].sum()
    
    col_p1, col_p2 = st.columns(2)
    for i, m in enumerate(metas):
        cat = m['Categoria']
        tope = m['Tope_Mensual']
        real = gastos_cat.get(cat, 0)
        pct = (real/tope) if tope>0 else 0
        
        with col_p1 if i%2==0 else col_p2:
            with st.container():
                c_txt, c_val = st.columns([2,1])
                c_txt.write(f"**{cat}**")
                c_val.caption(f"{real:.0f} / {tope}")
                if pct > 1: st.progress(1.0); st.error("Excedido")
                elif pct > 0.8: st.progress(pct); st.warning("Cuidado")
                else: st.progress(pct)

# --- 8. HISTORIAL ABAJO ---
st.write("---")
with st.expander("📂 Historial de Movimientos (Click para ver)"):
    if not df.empty:
        df_show = df[['ID_Fila','Fecha','Usuario','Cuenta','Tipo','Categoria','Monto','Descripcion']].copy()
        df_show['Fecha'] = pd.to_datetime(df_show['Fecha']).dt.strftime('%d/%m/%Y')
        st.dataframe(df_show.sort_values('ID_Fila', ascending=False), use_container_width=True)
        
        cd1, cd2 = st.columns([4, 1])
        id_del = cd1.number_input("ID a Borrar", min_value=0)
        if cd2.button("Borrar ID"):
            ws_registro.delete_rows(int(id_del)); limpiar_cache(); st.rerun()
