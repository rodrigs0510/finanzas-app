import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pytz
import base64
import time

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="CAPIGASTOS", layout="wide", page_icon="🐹")

# --- 2. CARGADOR DE IMÁGENES (PARA CSS) ---
def get_img_b64(path):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except: return ""

bg_fondo = get_img_b64("fondo.jpg")
bg_tarjeta = get_img_b64("Tarjeta fondo.png")
img_logo = get_img_b64("logo.png")

# --- 3. CSS "CAPIGASTOS REAL" (ESTILO VIDEOJUEGO/STICKER) ---
st.markdown(f"""
<style>
    /* FUENTE GENERAL */
    @import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@400;600&display=swap');
    
    html, body, [class*="css"] {{
        font-family: 'Fredoka', sans-serif;
        color: #000000;
    }}

    /* FONDO DE PANTALLA */
    .stApp {{
        background-image: url("data:image/jpg;base64,{bg_fondo}");
        background-size: cover;
        background-attachment: fixed;
    }}

    /* --- CLASE MAESTRA: CAJA CONTENEDORA (ESTILO 'HOJA BOND' / BEIGE) --- */
    .bloque-capibara {{
        background-color: #FDF5E6; /* Beige Crema */
        border: 2px solid #4A3B2A; /* Borde Marrón Café */
        border-radius: 15px;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 4px 4px 0px rgba(0,0,0,0.2);
    }}

    /* TÍTULOS */
    h1, h2, h3, h4 {{
        color: #4A3B2A !important;
        font-weight: 800 !important;
        margin: 0px !important;
        padding-bottom: 5px;
    }}

    /* INPUTS (CAJAS DE TEXTO Y SELECTORES) */
    .stTextInput input, .stNumberInput input, .stSelectbox div, .stDateInput input {{
        background-color: #FFFFFF !important;
        border: 2px solid #4A3B2A !important;
        border-radius: 10px !important;
        color: #000000 !important;
        font-weight: 600;
    }}
    
    /* Arreglo específico para que el dropdown se vea bien */
    div[data-baseweb="select"] > div {{
        background-color: #FFFFFF !important;
        border: 2px solid #4A3B2A !important;
        color: #000000 !important;
    }}
    
    /* BOTONES (ESTILO MARRÓN) */
    .stButton > button {{
        background-color: #D2B48C;
        color: #4A3B2A;
        border: 2px solid #4A3B2A;
        border-radius: 12px;
        font-weight: 900;
        box-shadow: 2px 2px 0px #4A3B2A;
        width: 100%;
    }}
    .stButton > button:hover {{
        background-color: #E6C29A;
        transform: translateY(-2px);
    }}
    
    /* TARJETA DE CRÉDITO PERSONALIZADA (CSS + IMAGEN) */
    .card-box {{
        background-image: url("data:image/png;base64,{bg_tarjeta}");
        background-size: 100% 100%;
        height: 160px;
        border-radius: 15px;
        position: relative;
        margin-bottom: 10px;
        box-shadow: 3px 3px 5px rgba(0,0,0,0.3);
        color: white;
        padding: 15px;
    }}
    .card-title {{
        font-size: 14px;
        opacity: 0.9;
        font-weight: bold;
    }}
    .card-saldo {{
        font-size: 26px;
        font-weight: 900;
        margin-top: 35px;
        text-shadow: 1px 1px 2px black;
    }}
    .card-name {{
        position: absolute;
        bottom: 15px;
        left: 15px;
        font-size: 12px;
        opacity: 0.8;
    }}

    /* Ocultar header de Streamlit */
    header {{visibility: hidden;}}
    
    /* KPI BOX (SALDO/AHORRO) */
    .kpi-box {{
        background-color: #E8DCC5;
        border: 2px solid #4A3B2A;
        border-radius: 20px;
        text-align: center;
        padding: 10px;
    }}
</style>
""", unsafe_allow_html=True)

# --- 4. CONEXIÓN (CON FIX DE ERROR KEYERROR) ---
@st.cache_resource
def conectar():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    if "gcp_service_account" in st.secrets:
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    return gspread.authorize(creds).open("Finanzas_RodrigoKrys")

try:
    sh = conectar()
    ws_reg = sh.worksheet("Registro")
    ws_cta = sh.worksheet("Cuentas")
    ws_pre = sh.worksheet("Presupuestos")
except:
    st.error("⚠️ Error de conexión. Verifica tu internet o credentials.json"); st.stop()

def limpiar(): st.cache_data.clear()

# --- 5. OBTENER DATOS (BLINDADO CONTRA ERRORES) ---
@st.cache_data(ttl=10)
def get_data():
    try:
        data = ws_reg.get_all_records()
        # Si la hoja está vacía, devolvemos un DataFrame vacío pero con columnas correctas
        if not data:
            return pd.DataFrame(columns=['Fecha', 'Hora', 'Usuario', 'Cuenta', 'Tipo', 'Categoria', 'Monto', 'Descripcion'])
        
        df = pd.DataFrame(data)
        
        # FIX KEYERROR: Asegurarnos que existan las columnas críticas
        if 'Monto' not in df.columns: df['Monto'] = 0
        if 'Fecha' not in df.columns: df['Fecha'] = ""
        
        df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)
        df['Fecha_dt'] = pd.to_datetime(df['Fecha'], format="%Y-%m-%d", errors='coerce')
        df['ID_Fila'] = df.index + 2
        return df
    except Exception as e:
        st.error(f"Error leyendo datos: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=10)
def get_cuentas():
    try:
        return ws_cta.col_values(1)[1:] # Ignorar encabezado
    except: return ["Efectivo"]

@st.cache_data(ttl=10)
def get_metas():
    try:
        return ws_pre.get_all_records()
    except: return []

# --- 6. LOGICA ---
pe_zone = pytz.timezone('America/Lima')
now = datetime.now(pe_zone)
df = get_data()
ctas = get_cuentas() if get_cuentas() else ["Efectivo"] # Asegurar al menos una cuenta
metas = get_metas()

# --- 7. HEADER (LOGO + FILTROS + KPI) ---
# Usamos un contenedor invisible para organizar el top
c_logo, c_filtros, c_kpi = st.columns([1, 2, 2], gap="medium")

with c_logo:
    # LOGO DIRECTO (Sin bordes raros)
    if img_logo:
        st.markdown(f'<img src="data:image/png;base64,{img_logo}" width="140">', unsafe_allow_html=True)
    else:
        st.title("🐹")

with c_filtros:
    # CAJA BEIGE PARA FILTROS (Para que se vea el texto 'Mes' y 'Año')
    st.markdown('<div class="bloque-capibara" style="padding: 10px;">', unsafe_allow_html=True)
    col_m, col_a = st.columns(2)
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    sel_mes = col_m.selectbox("MES", meses, index=now.month-1, label_visibility="collapsed")
    sel_anio = col_a.number_input("AÑO", value=now.year, label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)
    mes_idx = meses.index(sel_mes) + 1

# Filtrado de Datos
if not df.empty and 'Fecha_dt' in df.columns:
    df_f = df[(df['Fecha_dt'].dt.month == mes_idx) & (df['Fecha_dt'].dt.year == sel_anio)]
else:
    df_f = pd.DataFrame()

# Cálculos Totales
ingreso_total = df['Monto'][df['Tipo']=='Ingreso'].sum() if not df.empty else 0
gasto_total = df['Monto'][df['Tipo']=='Gasto'].sum() if not df.empty else 0
ahorro_vida = ingreso_total - gasto_total

with c_kpi:
    # KPIs Estilo Burbuja (Imagen 4)
    k1, k2 = st.columns(2)
    with k1:
        st.markdown(f"""
        <div class="kpi-box">
            <div style="font-size:12px; font-weight:bold;">SALDO TOTAL</div>
            <div style="font-size:20px; font-weight:900; color:#4A3B2A;">S/ {ahorro_vida:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    with k2:
        st.markdown(f"""
        <div class="kpi-box">
            <div style="font-size:12px; font-weight:bold;">AHORRO TOTAL</div>
            <div style="font-size:20px; font-weight:900; color:#2E8B57;">S/ {ahorro_vida:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)

# --- 8. CUERPO PRINCIPAL ---
col_izq, col_der = st.columns([1, 3], gap="medium")

# ================= IZQUIERDA: REGISTRO (CON FONDO BEIGE) =================
with col_izq:
    st.markdown('<div class="bloque-capibara">', unsafe_allow_html=True)
    st.markdown("### 📝 REGISTRO")
    
    # Formulario dentro de la caja beige
    with st.form("form_reg", clear_on_submit=True):
        st.write("TYPE:")
        op = st.radio("Acción", ["GASTO", "INGRESO", "TRANSFERENCIA"], label_visibility="collapsed")
        
        st.write("USUARIO:")
        u = st.selectbox("Us", ["Rodrigo", "Krys"], label_visibility="collapsed")
        
        cats = [m['Categoria'] for m in metas] + ["COMIDA", "TAXI", "OTROS"]
        
        if op == "TRANSFERENCIA":
            st.write("DE CUENTA -> A CUENTA:")
            c1, c2 = st.columns(2)
            c_ori = c1.selectbox("De", ctas, label_visibility="collapsed")
            c_des = c2.selectbox("A", ctas, label_visibility="collapsed")
            cat = "Transferencia"
            cta = c_ori
        else:
            st.write("CUENTA AFECTADA:")
            cta = st.selectbox("Cta", ctas, label_visibility="collapsed")
            st.write("CATEGORÍA:")
            if op == "GASTO": cat = st.selectbox("Cat", cats, label_visibility="collapsed")
            else: cat = st.selectbox("Cat", ["SUELDO", "OTROS"], label_visibility="collapsed")
            
        st.write("MONTO S/:")
        monto = st.number_input("S/", min_value=0.01, format="%.2f", label_visibility="collapsed")
        st.write("DESCRIPCIÓN:")
        desc = st.text_input("Desc", label_visibility="collapsed")
        
        st.write("")
        if st.form_submit_button("💾 GUARDAR"):
            fd = datetime.now(pe_zone).strftime("%Y-%m-%d")
            ft = datetime.now(pe_zone).strftime("%H:%M:%S")
            # Lógica de guardado segura
            try:
                if op == "TRANSFERENCIA":
                    ws_reg.append_row([fd, ft, u, c_ori, "Gasto", "Transferencia", monto, f"-> {c_des}: {desc}"])
                    ws_reg.append_row([fd, ft, u, c_des, "Ingreso", "Transferencia", monto, f"<- {c_ori}: {desc}"])
                else:
                    tipo_real = "Gasto" if op == "GASTO" else "Ingreso"
                    ws_reg.append_row([fd, ft, u, cta, tipo_real, cat, monto, desc])
                limpiar(); st.success("Guardado!"); time.sleep(1); st.rerun()
            except Exception as e:
                st.error(f"Error guardando: {e}")
                
    st.markdown('</div>', unsafe_allow_html=True)

# ================= DERECHA: DASHBOARD (CAJAS SEPARADAS) =================
with col_der:
    
    # 1. RESUMEN MENSUAL
    st.markdown('<div class="bloque-capibara">', unsafe_allow_html=True)
    st.markdown(f"### RESUMEN: {sel_mes.upper()}")
    
    # Métricas del mes
    if not df_f.empty:
        ing_m = df_f[df_f['Tipo']=='Ingreso']['Monto'].sum()
        gas_m = df_f[df_f['Tipo']=='Gasto']['Monto'].sum()
    else:
        ing_m, gas_m = 0, 0
        
    rm1, rm2, rm3 = st.columns(3)
    rm1.metric("INGRESOS", f"S/ {ing_m:,.2f}")
    rm2.metric("GASTOS", f"S/ {gas_m:,.2f}")
    rm3.metric("BALANCE", f"S/ {ing_m - gas_m:,.2f}")
    st.markdown('</div>', unsafe_allow_html=True)

    # 2. CUENTAS (CON TARJETA DE FONDO)
    st.markdown('<div class="bloque-capibara">', unsafe_allow_html=True)
    h_cta, b_cta = st.columns([4, 2])
    h_cta.markdown("### 💳 MIS CUENTAS")
    
    # Botones Agregar/Eliminar
    with b_cta:
        bt1, bt2 = st.columns(2)
        if bt1.button("➕"): 
            n = st.text_input("Nueva Cuenta:")
            if n and st.button("OK"): ws_cta.append_row([n]); limpiar(); st.rerun()
        if bt2.button("➖"):
             d = st.selectbox("Borrar:", ctas)
             if d and st.button("Confirmar Borrar"): 
                 cell = ws_cta.find(d); ws_cta.delete_rows(cell.row); limpiar(); st.rerun()

    # Grid de Tarjetas
    cols_c = st.columns(3)
    for i, c in enumerate(ctas):
        # Calcular saldo
        if not df.empty:
            ing = df[(df['Cuenta']==c)&(df['Tipo']=='Ingreso')]['Monto'].sum()
            gas = df[(df['Cuenta']==c)&(df['Tipo']=='Gasto')]['Monto'].sum()
            saldo = ing - gas
        else: saldo = 0
        
        with cols_c[i % 3]:
            # HTML PARA TARJETA
            st.markdown(f"""
            <div class="card-box">
                <div class="card-title">CAPIGASTOS</div>
                <div class="card-saldo">S/ {saldo:,.2f}</div>
                <div class="card-name">{c.upper()}</div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # 3. MOVIMIENTOS (TABLA)
    st.markdown('<div class="bloque-capibara">', unsafe_allow_html=True)
    st.markdown("### 📋 ÚLTIMOS MOVIMIENTOS")
    
    if not df_f.empty:
        # Mostramos tabla limpia
        st.dataframe(
            df_f[['Fecha', 'Usuario', 'Cuenta', 'Categoria', 'Monto', 'Descripcion']].sort_index(ascending=False),
            use_container_width=True,
            hide_index=True
        )
        # Eliminador simple por ID (Fila)
        st.write("---")
        cd1, cd2 = st.columns([3, 1])
        id_borrar = cd1.number_input("N° de Fila a Eliminar (Ver Google Sheet)", min_value=2, step=1)
        if cd2.button("ELIMINAR REGISTRO"):
            try:
                ws_reg.delete_rows(int(id_borrar))
                limpiar(); st.success("Eliminado"); time.sleep(1); st.rerun()
            except:
                st.error("Error al borrar. Verifica el ID.")
    else:
        st.info("No hay movimientos este mes.")
        
    st.markdown('</div>', unsafe_allow_html=True)
