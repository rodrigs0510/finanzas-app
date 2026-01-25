import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import pytz 
import base64

# --- 1. CONFIGURACIÓN ---
st.set_page_config(
    page_title="CAPIGASTOS", 
    layout="wide",
    page_icon="🐹",
    initial_sidebar_state="collapsed"
)

# --- CARGAR IMÁGENES ---
def get_image_as_base64(file_path):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except Exception:
        return ""

img_tarjeta = get_image_as_base64("Tarjeta fondo.png")
img_logo = get_image_as_base64("logo.png") 
img_fondo = get_image_as_base64("fondo.jpg") 
img_btn_add = get_image_as_base64("boton_agregar.png")
img_btn_del = get_image_as_base64("boton_eliminar.png")

# --- CONEXIÓN ---
@st.cache_resource
def conectar_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    if "gcp_service_account" in st.secrets:
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open("Finanzas_RodrigoKrys")
    return sheet

try:
    sh = conectar_google_sheets()
    ws_registro = sh.worksheet("Registro")
    ws_cuentas = sh.worksheet("Cuentas")
    ws_presupuestos = sh.worksheet("Presupuestos")
except Exception as e:
    st.error("Error conectando a Google. Espera 1 minuto y recarga.")
    st.stop()

# --- FUNCIONES ---
def intento_seguro(funcion_gspread):
    max_retries = 3
    for i in range(max_retries):
        try:
            return funcion_gspread()
        except gspread.exceptions.APIError as e:
            if i == max_retries - 1: raise e
            time.sleep(2 * (i + 1))
        except Exception as e: raise e

@st.cache_data(ttl=60)
def obtener_datos():
    columnas_base = ['Fecha', 'Hora', 'Usuario', 'Cuenta', 'Tipo', 'Categoria', 'Monto', 'Descripcion']
    try:
        data = intento_seguro(lambda: ws_registro.get_all_records())
        if not data: 
            return pd.DataFrame(columns=columnas_base)
        
        df = pd.DataFrame(data)
        for col in columnas_base:
            if col not in df.columns:
                df[col] = ""
        
        df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)
        df['Fecha'] = pd.to_datetime(df['Fecha'], format="%Y-%m-%d", errors='coerce')
        return df
    except:
        return pd.DataFrame(columns=columnas_base)

@st.cache_data(ttl=600)
def obtener_cuentas():
    try:
        cuentas = intento_seguro(lambda: ws_cuentas.col_values(1))
        return cuentas[1:] if len(cuentas) > 1 else ["Efectivo"]
    except: return ["Efectivo"]

@st.cache_data(ttl=600)
def obtener_presupuestos():
    try:
        records = intento_seguro(lambda: ws_presupuestos.get_all_records())
        return {row['Categoria']: row['Tope_Mensual'] for row in records}
    except: return {}

def limpiar_cache(): st.cache_data.clear()

# --- DIALOGS ---
@st.dialog("Agregar Nueva Cuenta")
def dialog_agregar_cuenta():
    nombre_cuenta = st.text_input("Nombre de la cuenta")
    if st.button("Crear Cuenta"):
        if nombre_cuenta:
            ws_cuentas.append_row([nombre_cuenta])
            limpiar_cache(); st.success("¡Creada!"); time.sleep(1); st.rerun()

@st.dialog("Eliminar Cuenta")
def dialog_eliminar_cuenta(lista_actual):
    cuenta_a_borrar = st.selectbox("Selecciona cuenta:", lista_actual)
    st.warning(f"¿Eliminar **{cuenta_a_borrar}**?")
    c1, c2 = st.columns(2)
    if c1.button("Sí, Eliminar"):
        cell = ws_cuentas.find(cuenta_a_borrar)
        ws_cuentas.delete_rows(cell.row)
        limpiar_cache(); st.success("Eliminada"); time.sleep(1); st.rerun()
    if c2.button("Cancelar"): st.rerun()

# --- CSS DEFINITIVO (CORRECCIÓN DE FONDOS) ---
st.markdown(f"""
<style>
    /* 1. FONDO DE LA PANTALLA PRINCIPAL */
    .stApp {{
        background-image: url("data:image/jpg;base64,{img_fondo}");
        background-size: cover; 
        background-position: center top; 
        background-attachment: fixed;
    }}
    
    /* 2. ESTILO PARA LOS CONTENEDORES (LAS CAJAS) */
    /* Aquí está la magia: Pintamos el fondo de beige para tapar la imagen de atrás */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: rgba(253, 245, 230, 0.95) !important; /* Beige 'Old Lace' Sólido */
        border: 2px solid #8B4513 !important; /* Borde Marrón */
        border-radius: 15px !important;
        padding: 20px !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }}

    /* 3. TEXTOS (Color Marrón Capigastos) */
    html, body, [class*="css"], h1, h2, h3, h4, p, span, label, div, .stMarkdown {{
        color: #4A3B2A !important; 
    }}
    /* Excepción: Textos dentro de las tarjetas de crédito (blanco) */
    .tarjeta-capigastos *, .tarjeta-capigastos div {{ 
        color: white !important; 
    }}

    /* 4. INPUTS (Cajas de texto y selectores) */
    .stTextInput input, .stNumberInput input, div[data-baseweb="select"] > div {{
        background-color: #FFFFFF !important; /* Fondo Blanco puro */
        color: #000000 !important;
        border: 2px solid #8B4513 !important;
        border-radius: 8px !important;
    }}
    /* Quitar brillo azul al seleccionar */
    .stTextInput > div[data-baseweb="input-container"]:focus-within {{
        border-color: #A0522D !important;
        box-shadow: none !important;
    }}

    /* 5. TARJETAS VISUALES */
    .tarjeta-capigastos {{
        border-radius: 15px; padding: 15px; color: white !important; margin-bottom: 10px;
        box-shadow: 0 4px 8px 0 rgba(0,0,0,0.3); position: relative; height: 180px;
        background-size: 100% 100%; background-position: center;
    }}
    .barra-fondo {{ background-color: rgba(255, 255, 255, 0.3); border-radius: 5px; height: 6px; width: 100%; margin-top: 5px; }}
    .barra-progreso {{ background-color: #4CAF50; height: 100%; border-radius: 5px; }}

    /* 6. BOTONES CON IMÁGENES */
    div.stButton > button[title="AGREGAR_IMG"] {{
        background-image: url("data:image/png;base64,{img_btn_add}");
        background-size: 100% 100%; border: none !important; background-color: transparent !important;
        height: 45px; width: 100%;
    }}
    div.stButton > button[title="ELIMINAR_IMG"] {{
        background-image: url("data:image/png;base64,{img_btn_del}");
        background-size: 100% 100%; border: none !important; background-color: transparent !important;
        height: 45px; width: 100%;
    }}
    /* Botón Genérico (Guardar, etc) */
    div.stButton > button {{
        background-color: #8B4513 !important; color: white !important; 
        border-radius: 20px; border: 2px solid #5e2f0d !important;
    }}

</style>
""", unsafe_allow_html=True)

# --- LOGICA DE DATOS ---
zona_peru = pytz.timezone('America/Lima')
try:
    df = obtener_datos()
    lista_cuentas = obtener_cuentas()
    presupuestos_dict = obtener_presupuestos()
except:
    st.warning("Cargando..."); time.sleep(1); st.rerun()

# --- DATOS GLOBALES ---
ing_hist, gas_hist, ahorro_vida, saldo_actual = 0,0,0,0
if not df.empty:
    ing_hist = df[df['Tipo']=='Ingreso']['Monto'].sum()
    gas_hist = df[df['Tipo']=='Gasto']['Monto'].sum()
    ahorro_vida = ing_hist - gas_hist
    for c in lista_cuentas:
        i = df[(df['Cuenta']==c)&(df['Tipo']=='Ingreso')]['Monto'].sum()
        g = df[(df['Cuenta']==c)&(df['Tipo']=='Gasto')]['Monto'].sum()
        saldo_actual += (i-g)

# ==============================================================================
# 1. HEADER (LOGO | SELECCION MES | TOTALES)
# ==============================================================================
with st.container(border=True): # <--- AHORA ESTA CAJA TENDRA FONDO BEIGE
    c1, c2, c3 = st.columns([1.5, 1.5, 1.5], vertical_alignment="center")
    
    with c1:
        cc1, cc2 = st.columns([1, 3])
        with cc1:
            if img_logo: st.markdown(f'<img src="data:image/png;base64,{img_logo}" width="80">', unsafe_allow_html=True)
        with cc2:
            st.markdown("<h2>CAPIGASTOS</h2>", unsafe_allow_html=True)

    with c2:
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        now = datetime.now(zona_peru)
        col_m, col_a = st.columns(2)
        sel_mes = col_m.selectbox("Mes", meses, index=now.month-1, label_visibility="collapsed")
        sel_anio = col_a.number_input("Año", value=now.year, label_visibility="collapsed")
        mes_idx = meses.index(sel_mes) + 1

    with c3:
        st.markdown(f"<div style='text-align:right;'><b>Saldo Total:</b> S/ {saldo_actual:,.2f}<br><b>Ahorro Histórico:</b> S/ {ahorro_vida:,.2f}</div>", unsafe_allow_html=True)

# ==============================================================================
# 2. CONSOLIDADO DEL MES
# ==============================================================================
if not df.empty and 'Fecha' in df.columns:
    df_f = df[(df['Fecha'].dt.month == mes_idx) & (df['Fecha'].dt.year == sel_anio)]
else: df_f = pd.DataFrame(columns=df.columns)

ing_m = df_f[df_f['Tipo']=='Ingreso']['Monto'].sum() if not df_f.empty else 0
gas_m = df_f[df_f['Tipo']=='Gasto']['Monto'].sum() if not df_f.empty else 0
bal_m = ing_m - gas_m

with st.container(border=True): # <--- CAJA BEIGE
    st.markdown(f"<h4 style='text-align:center; margin:0;'>CONSOLIDADO: {sel_mes.upper()} {sel_anio}</h4>", unsafe_allow_html=True)
    k1, k2, k3 = st.columns(3)
    k1.metric("Ingresos", f"S/ {ing_m:,.2f}")
    k2.metric("Gastos", f"S/ {gas_m:,.2f}")
    k3.metric("Ahorro", f"S/ {bal_m:,.2f}")

st.write("")

# ==============================================================================
# 3. CUERPO PRINCIPAL DIVIDIDO
# ==============================================================================
col_main_left, col_main_right = st.columns([1, 1.8], gap="medium")

# --- IZQUIERDA: FORMULARIO ---
with col_main_left:
    with st.container(border=True): # <--- CAJA BEIGE
        st.markdown("### 📝 FORMULARIO")
        st.write("**Registrar:**")
        op = st.radio("Tipo", ["Gasto", "Ingreso", "Transferencia"], horizontal=True, label_visibility="collapsed")
        
        with st.form("form_main", clear_on_submit=True):
            u = st.selectbox("Usuario", ["Rodrigo", "Krys"])
            
            if op == "Transferencia":
                c_ori = st.selectbox("Desde", lista_cuentas)
                c_des = st.selectbox("Hacia", lista_cuentas)
                cta = c_ori; cat = "Transferencia"
            else:
                cta = st.selectbox("Cuenta", lista_cuentas)
                if "Gasto" in op:
                    cat = st.selectbox("Categoría", list(presupuestos_dict.keys())+["Otros", "Comida", "Taxi"])
                else:
                    cat = st.selectbox("Categoría", ["Sueldo", "Negocio", "Regalo"])
            
            monto = st.number_input("Monto S/", min_value=0.01, format="%.2f")
            desc = st.text_input("Descripción")
            
            st.write("")
            if st.form_submit_button("GUARDAR", use_container_width=True):
                try:
                    now_str = datetime.now(zona_peru).strftime("%Y-%m-%d")
                    time_str = datetime.now(zona_peru).strftime("%H:%M:%S")
                    if op == "Transferencia":
                        r1 = [now_str, time_str, u, c_ori, "Gasto", "Transferencia/Salida", monto, f"-> {c_des}: {desc}"]
                        r2 = [now_str, time_str, u, c_des, "Ingreso", "Transferencia/Entrada", monto, f"<- {c_ori}: {desc}"]
                        ws_registro.append_row(r1); ws_registro.append_row(r2)
                    else:
                        tipo = "Gasto" if "Gasto" in op else "Ingreso"
                        ws_registro.append_row([now_str, time_str, u, cta, tipo, cat, monto, desc])
                    limpiar_cache(); st.success("OK"); time.sleep(1); st.rerun()
                except Exception as e: st.error(f"Error: {e}")

# --- DERECHA: CUENTAS Y METAS ---
with col_main_right:
    # 3.1 CUENTAS
    with st.container(border=True): # <--- CAJA BEIGE
        ch1, ch2, ch3 = st.columns([4, 1, 1], vertical_alignment="bottom")
        ch1.markdown("### 💳 CUENTAS")
        # Botones Imagen
        if ch2.button("⠀   ⠀", key="add", help="AGREGAR_IMG"): dialog_agregar_cuenta()
        if ch3.button("⠀   ⠀", key="del", help="ELIMINAR_IMG"): dialog_eliminar_cuenta(lista_cuentas)
        
        cols_tarjetas = st.columns(3)
        for i, cuenta in enumerate(lista_cuentas):
            if not df.empty:
                ing_h = df[(df['Cuenta']==cuenta)&(df['Tipo']=='Ingreso')]['Monto'].sum()
                gas_h = df[(df['Cuenta']==cuenta)&(df['Tipo']=='Gasto')]['Monto'].sum()
                saldo = ing_h - gas_h
            else: ing_h, gas_h, saldo = 0, 0, 0
            
            pct = min(max(saldo/ing_h, 0.0), 1.0)*100 if ing_h > 0 else 0
            bg = f"background-image: url('data:image/png;base64,{img_tarjeta}');" if img_tarjeta else "background-color: #8B4513;"
            
            html = f"""
            <div class="tarjeta-capigastos" style="{bg}">
                <div style="position:absolute; top:15px; left:15px;">
                    <div style="font-size:10px; opacity:0.9;">CAPIGASTOS CARD</div>
                    <div style="font-size:14px; font-weight:bold; text-transform:uppercase;">{cuenta}</div>
                </div>
                <div style="position:absolute; top:60px; right:15px; text-align:right;">
                    <div style="font-size:9px;">DISPONIBLE</div>
                    <div style="font-size:20px; font-weight:bold;">S/ {saldo:,.2f}</div>
                </div>
                <div style="position:absolute; bottom:15px; left:15px; right:15px;">
                    <div class="barra-fondo"><div class="barra-progreso" style="width:{pct}%;"></div></div>
                </div>
            </div>
            """
            with cols_tarjetas[i%3]: st.markdown(html, unsafe_allow_html=True)

    st.write("")

    # 3.2 METAS
    with st.container(border=True): # <--- CAJA BEIGE
        st.markdown("### 🎯 METAS")
        if not df_f.empty: gas_cat = df_f[df_f['Tipo']=='Gasto'].groupby('Categoria')['Monto'].sum()
        else: gas_cat = {}
        
        cm1, cm2 = st.columns(2)
        idx_m = 0
        for cat, tope in presupuestos_dict.items():
            real = gas_cat.get(cat, 0)
            pct = min(real/tope, 1.0) if tope > 0 else 0
            with (cm1 if idx_m % 2 == 0 else cm2):
                st.write(f"**{cat}**")
                st.progress(pct)
                st.caption(f"S/ {real:,.0f} de {tope:,.0f}")
            idx_m += 1

st.write("") 

# ==============================================================================
# 4. PIE DE PÁGINA (MOVIMIENTOS | PAGOS PENDIENTES)
# ==============================================================================
col_foot_left, col_foot_right = st.columns([1.5, 1], gap="medium")

# --- MOVIMIENTOS ---
with col_foot_left:
    with st.container(border=True): # <--- CAJA BEIGE
        st.markdown("### 📜 MOVIMIENTOS")
        if not df_f.empty:
            st.dataframe(
                df_f[['Fecha', 'Cuenta', 'Categoria', 'Monto', 'Descripcion']].sort_values('Fecha', ascending=False),
                use_container_width=True,
                hide_index=True,
                height=300
            )
            if st.button("Borrar Último Reg"):
                rows = len(ws_registro.get_all_values())
                if rows > 1:
                    ws_registro.delete_rows(rows); limpiar_cache(); st.success("Borrado"); st.rerun()
        else:
            st.info("Sin datos este mes.")

# --- PAGOS PENDIENTES ---
with col_foot_right:
    with st.container(border=True): # <--- CAJA BEIGE
        st.markdown("### ⏰ PAGOS PENDIENTES")
        st.info("Próximos vencimientos:")
        st.markdown("""
        - 📅 **Luz del Sur:** 15/Feb (S/ 120.00)
        - 📅 **Internet:** 20/Feb (S/ 89.00)
        - 📅 **Netflix:** 28/Feb (S/ 45.00)
        """)
        st.text_input("Agregar recordatorio rápido:")
        st.button("Añadir")
