import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pytz
import base64

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="CAPIGASTOS", layout="wide", page_icon="🐹")

# --- 2. FUNCIONES DE UTILIDAD (CARGAR IMÁGENES) ---
def get_img_as_base64(file):
    try:
        with open(file, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except: return ""

# Cargamos las imágenes en memoria para usarlas en el CSS
img_fondo = get_img_as_base64("fondo.jpg")
img_tarjeta = get_img_as_base64("tarjeta.png") # Tu imagen marrón de tarjeta
img_logo = get_img_as_base64("logo.png") # Tu logo

# Colores extraídos de tu diseño
COLOR_TEXTO = "#4A3B2A" # Marrón oscuro café
COLOR_INPUT_BG = "#E8DCC5" # Beige oscurito para inputs
COLOR_TITULOS = "#000000"

# --- 3. CSS "CAPIGASTOS GAME UI" ---
st.markdown(f"""
<style>
/* FUENTE */
@import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@400;600&display=swap');

html, body, [class*="css"] {{
    font-family: 'Fredoka', sans-serif;
    color: {COLOR_TEXTO};
}}

/* FONDO PRINCIPAL */
.stApp {{
    background-image: url("data:image/jpg;base64,{img_fondo}");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}}

/* --- PANEL IZQUIERDO (REGISTRO) --- */
/* Creamos el estilo del papel beige largo */
.panel-registro {{
    background-color: #E6D2B5; /* Color arena/papel */
    border: 3px solid #5C4033; /* Borde marrón grueso */
    border-radius: 15px;
    padding: 20px;
    box-shadow: 5px 5px 0px rgba(0,0,0,0.3);
}}

/* --- TARJETAS DE CUENTAS (Estilo Imagen) --- */
.tarjeta-capibara {{
    background-image: url("data:image/png;base64,{img_tarjeta}");
    background-size: cover;
    border-radius: 15px;
    padding: 20px;
    height: 140px; /* Altura fija para que se vea igual a tu foto */
    color: #FFFFFF; /* Texto blanco dentro de la tarjeta marrón */
    box-shadow: 3px 3px 5px rgba(0,0,0,0.4);
    display: flex;
    flex-direction: column;
    justify-content: center;
    margin-bottom: 10px;
}}

/* --- BOTONES PERSONALIZADOS --- */
/* Forzamos estilos a los botones de Streamlit para que parezcan los tuyos */
div.stButton > button {{
    background-color: #D2B48C;
    color: #4A3B2A;
    border: 2px solid #4A3B2A;
    border-radius: 20px;
    font-weight: bold;
    box-shadow: 2px 2px 0px #4A3B2A;
}}
div.stButton > button:active {{
    transform: translateY(2px);
    box-shadow: none;
}}

/* --- INPUTS QUE PAREZCAN DEL JUEGO --- */
.stTextInput input, .stNumberInput input, .stSelectbox div, .stDateInput input {{
    background-color: {COLOR_INPUT_BG} !important;
    border: 1px solid #8B5A2B !important;
    border-radius: 8px !important;
    color: #4A3B2A !important;
}}

/* --- TABLAS (MOVIMIENTOS) --- */
/* Cabecera naranja/marrón como tu diseño */
thead tr th {{
    background-color: #D2691E !important; /* Chocolate */
    color: white !important;
    border: 1px solid #4A3B2A !important;
}}
tbody tr td {{
    background-color: #FFF8DC !important; /* Crema */
    border: 1px solid #DEB887 !important;
    color: black !important;
}}

/* Ocultar header rojo */
header {{visibility: hidden;}}
</style>
""", unsafe_allow_html=True)

# --- 4. CONEXIÓN BACKEND ---
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
    ws_pag = sh.worksheet("Pagos") # ¡Nueva hoja para Pagos Pendientes!
except:
    st.error("⚠️ Conexión fallida. Revisa internet."); st.stop()

def limpiar(): st.cache_data.clear()

# --- 5. FUNCIONES DE DATOS ---
@st.cache_data(ttl=10)
def get_data():
    d = intento(lambda: ws_reg.get_all_records())
    if not d: return pd.DataFrame(columns=['ID','Fecha','Hora','Usuario','Cuenta','Tipo','Categoria','Monto','Descripcion'])
    df = pd.DataFrame(d)
    df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)
    df['Fecha_dt'] = pd.to_datetime(df['Fecha'], format="%Y-%m-%d", errors='coerce')
    df['ID_Fila'] = df.index + 2
    return df

@st.cache_data(ttl=10)
def get_cuentas():
    return intento(lambda: ws_cta.col_values(1))[1:] or ["Efectivo"]

@st.cache_data(ttl=10)
def get_metas():
    return intento(lambda: ws_pre.get_all_records())

@st.cache_data(ttl=10)
def get_pagos():
    # Nueva función para la hoja de Pagos
    try:
        return intento(lambda: ws_pag.get_all_records())
    except: return [] # Si no existe la hoja aun

# --- 6. LOGICA ---
pe_zone = pytz.timezone('America/Lima')
now = datetime.now(pe_zone)
df = get_data()
ctas = get_cuentas()
metas = get_metas()

# --- 7. HEADER (LOGO, USUARIO, FILTROS, KPI) ---
# Usamos columnas para imitar la barra superior
c_h1, c_h2, c_h3, c_h4, c_h5 = st.columns([1, 1.5, 2, 1.5, 1.5], gap="small")

with c_h1:
    # Logo Circular
    st.markdown(f'<img src="data:image/png;base64,{img_logo}" width="130" style="border-radius:50%; border: 3px solid #5C4033;">', unsafe_allow_html=True)

with c_h2:
    st.write("USUARIO:")
    usuario_activo = st.selectbox("Usuario", ["RODRIGO", "KRYS"], label_visibility="collapsed")

with c_h3:
    st.write("SELECCIONA MES/AÑO:")
    col_m, col_a = st.columns(2)
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    sel_mes = col_m.selectbox("Mes", meses, index=now.month-1, label_visibility="collapsed")
    sel_anio = col_a.number_input("Año", value=now.year, label_visibility="collapsed")
    mes_idx = meses.index(sel_mes) + 1

# Filtramos Data
if not df.empty and 'Fecha_dt' in df.columns:
    df_f = df[(df['Fecha_dt'].dt.month == mes_idx) & (df['Fecha_dt'].dt.year == sel_anio)]
else: df_f = df

# Cálculos KPI
ingresos_tot = df[df['Tipo']=='Ingreso']['Monto'].sum()
gastos_tot = df[df['Tipo']=='Gasto']['Monto'].sum()
saldo_total_vida = ingresos_tot - gastos_tot
ahorro_vida = saldo_total_vida # Simplificado por ahora

with c_h4:
    # Burbuja Saldo Total
    st.markdown(f"""
    <div style="background-color:#E6D2B5; border:2px solid black; border-radius:20px; text-align:center; padding:5px;">
        <b>SALDO TOTAL</b><br>
        <span style="font-size:20px;">S/ {saldo_total_vida:,.2f}</span>
    </div>
    """, unsafe_allow_html=True)

with c_h5:
    # Burbuja Ahorro Total
    st.markdown(f"""
    <div style="background-color:#E6D2B5; border:2px solid black; border-radius:20px; text-align:center; padding:5px;">
        <b>AHORRO TOTAL</b><br>
        <span style="font-size:20px;">S/ {ahorro_vida:,.2f}</span>
    </div>
    """, unsafe_allow_html=True)

st.write("") # Espacio

# --- 8. LAYOUT PRINCIPAL (IZQUIERDA: REGISTRO | DERECHA: DASHBOARD) ---
col_L, col_R = st.columns([1, 3], gap="large")

# ==========================================
# 🟩 PANEL IZQUIERDO: REGISTRO (FORMULARIO)
# ==========================================
with col_L:
    # Usamos HTML para abrir el div "panel-registro"
    st.markdown('<div class="panel-registro">', unsafe_allow_html=True)
    st.markdown("### REGISTRO")
    
    with st.form("frm_registro", clear_on_submit=True):
        st.write("**TIPO DE REGISTRO**")
        op = st.radio("Tipo", ["GASTO", "INGRESO", "TRANSFERENCIA"], label_visibility="collapsed")
        
        st.write("**CUENTA AFECTADA** (Importante)")
        if op == "TRANSFERENCIA":
            c_ori = st.selectbox("Desde:", ctas)
            c_des = st.selectbox("Hacia:", ctas)
        else:
            cta = st.selectbox("Cuenta:", ctas)
            
        st.write("**CATEGORÍA**")
        categorias = ["COMIDA", "TEMU", "TREN", "TAXI", "ESTACIONAMIENTO", "GASOLINA", "MANTENIMIENTO", "COMPRAS", "REGALO", "PERSONAL", "PASAJE", "SUELDO", "OTROS"]
        cat = st.selectbox("Cat:", categorias)
        
        st.write("**MONTO S/**")
        monto = st.number_input("Monto", min_value=0.01, format="%.2f", label_visibility="collapsed")
        
        st.write("**DESCRIPCIÓN**")
        desc = st.text_input("Desc", label_visibility="collapsed")
        
        st.write("**FOTO / EVIDENCIA**")
        foto = st.file_uploader("Subir", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
        
        guardar = st.form_submit_button("GUARDAR", use_container_width=True)
        
        if guardar:
            fecha_pe = datetime.now(pe_zone).strftime("%Y-%m-%d")
            hora_pe = datetime.now(pe_zone).strftime("%H:%M:%S")
            # Lógica de guardado (Simplificada para no alargar el código)
            # Aquí iría la lógica de Drive para la foto, por ahora guardamos texto
            url_foto = "Pendiente Configurar Drive" if foto else ""
            
            if op == "TRANSFERENCIA":
                ws_reg.append_row([fecha_pe, hora_pe, usuario_activo, c_ori, "Gasto", "Transferencia", monto, f"-> {c_des}: {desc}"])
                ws_reg.append_row([fecha_pe, hora_pe, usuario_activo, c_des, "Ingreso", "Transferencia", monto, f"<- {c_ori}: {desc}"])
            else:
                tipo_real = "Gasto" if op == "GASTO" else "Ingreso"
                ws_reg.append_row([fecha_pe, hora_pe, usuario_activo, cta, tipo_real, cat, monto, desc])
            
            limpiar(); st.success("Guardado!"); st.rerun()

    st.markdown('</div>', unsafe_allow_html=True) # Cierra panel registro

# ==========================================
# 🟦 PANEL DERECHO: DASHBOARD
# ==========================================
with col_R:
    # --- FILA 1: RESUMEN MENSUAL (Burbujas) ---
    st.markdown(f"### RESUMEN {sel_mes.upper()}:")
    rm_ing = df_f[df_f['Tipo']=='Ingreso']['Monto'].sum()
    rm_gas = df_f[df_f['Tipo']=='Gasto']['Monto'].sum()
    
    k1, k2, k3 = st.columns(3)
    k1.info(f"Ingresos: S/ {rm_ing:,.2f}")
    k2.warning(f"Gastos: S/ {rm_gas:,.2f}")
    k3.success(f"Balance: S/ {rm_ing - rm_gas:,.2f}")
    
    st.write("---")
    
    # --- FILA 2: MIS CUENTAS (TARJETAS + BOTONES) ---
    c_cta_tit, c_cta_btn = st.columns([3, 2])
    c_cta_tit.markdown("### 💳 MIS CUENTAS")
    with c_cta_btn:
        b1, b2 = st.columns(2)
        if b1.button("AGREGAR CTA"):
            # Aquí iría el popup (st.dialog)
            pass 
        if b2.button("ELIMINAR CTA"):
            pass

    # CARRUSEL DE TARJETAS (Simulado con Columnas)
    cols_cards = st.columns(3)
    for i, c in enumerate(ctas):
        # Calcular saldo real
        ing_c = df[(df['Cuenta']==c)&(df['Tipo']=='Ingreso')]['Monto'].sum()
        gas_c = df[(df['Cuenta']==c)&(df['Tipo']=='Gasto')]['Monto'].sum()
        saldo_c = ing_c - gas_c
        
        with cols_cards[i % 3]:
            # AQUI ESTA LA MAGIA: HTML CON TU IMAGEN DE TARJETA
            st.markdown(f"""
            <div class="tarjeta-capibara">
                <div style="font-size:14px; opacity:0.8;">CAPIGASTOS</div>
                <div style="font-size:24px; font-weight:bold; margin-top:10px;">S/ {saldo_c:,.2f}</div>
                <div style="font-size:12px; margin-top:auto;">{c.upper()}</div>
            </div>
            """, unsafe_allow_html=True)

    st.write("---")

    # --- FILA 3: PRESUPUESTOS (BARRAS GRUESAS) ---
    st.markdown("### 📊 PRESUPUESTOS")
    # (Aquí iría la lógica de barras igual que antes pero con estilo CSS grueso)
    
    st.write("---")

    # --- FILA 4: MOVIMIENTOS Y PAGOS PENDIENTES ---
    col_movs, col_pend = st.columns([2, 1], gap="medium")
    
    with col_movs:
        st.markdown("### MOVIMIENTOS 🐹")
        if not df_f.empty:
            # TABLA PERSONALIZADA HTML PARA QUE SE VEA COMO TU DISEÑO
            # Headers naranjas, filas crema
            html_table = df_f[['ID_Fila','Fecha','Hora','Usuario','Cuenta','Tipo','Categoria','Monto','Descripcion']].sort_values('ID_Fila', ascending=False).to_html(index=False, classes="table", border=0)
            st.markdown(html_table, unsafe_allow_html=True)
            
            # Boton eliminar abajo
            del_id = st.number_input("ID a Eliminar:", min_value=0)
            if st.button("ELIMINAR REGISTRO"):
                ws_reg.delete_rows(int(del_id)); limpiar(); st.rerun()

    with col_pend:
        st.markdown("### PAGOS PENDIENTES 🐻")
        # Aquí iría la tabla de Pagos Pendientes
        st.info("Próximamente: Lista de Deudas")
