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
    # Intentamos obtener datos, si falla o está vacío, devolvemos estructura vacía segura
    try:
        data = intento_seguro(lambda: ws_registro.get_all_records())
        if not data: 
            return pd.DataFrame(columns=['Fecha', 'Hora', 'Usuario', 'Cuenta', 'Tipo', 'Categoria', 'Monto', 'Descripcion'])
        
        df = pd.DataFrame(data)
        
        # Asegurar columnas críticas
        if 'Monto' not in df.columns: df['Monto'] = 0
        if 'Fecha' not in df.columns: df['Fecha'] = ""
        if 'Tipo' not in df.columns: df['Tipo'] = "Desconocido"
        if 'Cuenta' not in df.columns: df['Cuenta'] = "Desconocido"

        df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)
        df['Fecha'] = pd.to_datetime(df['Fecha'], format="%Y-%m-%d", errors='coerce')
        return df
    except:
        return pd.DataFrame(columns=['Fecha', 'Hora', 'Usuario', 'Cuenta', 'Tipo', 'Categoria', 'Monto', 'Descripcion'])

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

# --- DIALOGS (POP-UPS) ---
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

# --- CSS MAESTRO (SOLUCIÓN VISUAL COMPLETA) ---
st.markdown(f"""
<style>
    /* 1. FONDO DE PANTALLA */
    .stApp {{
        background-image: url("data:image/jpg;base64,{img_fondo}");
        background-size: cover; 
        background-position: center top; 
        background-attachment: fixed;
    }}

    /* 2. CONTENEDOR TIPO "CRISTAL" */
    .block-container {{
        background-color: rgba(253, 245, 230, 0.95); /* Beige casi sólido */
        border-radius: 15px;
        padding: 2rem !important;
        margin-top: 20px;
        border: 2px solid #4A3B2A;
    }}

    /* 3. FORZAR COLOR DE TEXTO (IGNORAR MODO OSCURO) */
    html, body, [class*="css"], h1, h2, h3, h4, p, span, label, div {{
        color: #4A3B2A !important; 
        font-family: sans-serif;
    }}
    
    /* Excepción: Textos dentro de tarjetas o botones oscuros deben ser blancos/negros según corresponda */
    .tarjeta-capigastos *, div.stButton > button * {{
        color: inherit !important; 
    }}

    /* 4. INPUTS Y SELECTORES (LIMPIEZA DE BORDES FEOS) */
    /* Input de Texto y Número */
    .stTextInput input, .stNumberInput input {{
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 2px solid #4A3B2A !important;
        border-radius: 10px !important;
    }}
    
    /* Selectbox (El cuadro desplegable) */
    div[data-baseweb="select"] > div {{
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 2px solid #4A3B2A !important;
        border-radius: 10px !important;
    }}
    
    /* Eliminar contornos de foco extraños de Streamlit */
    .stSelectbox div:focus-within, .stTextInput div:focus-within {{
        box-shadow: none !important;
        border-color: #8B4513 !important;
    }}

    /* 5. BOTONES (PASTILLA Y COLORES) */
    div.stButton > button {{
        background-color: #8B4513 !important;
        color: white !important;
        border: 2px solid #5e2f0d !important;
        border-radius: 50px !important;
        font-weight: bold !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2) !important;
    }}
    
    /* Botón AGREGAR (Verde) */
    div.stButton > button:has(p:contains('Agregar')) {{
        background-color: #A2D149 !important; 
        border-color: #556B2F !important; 
        color: black !important;
    }}
    
    /* Botón ELIMINAR (Rojo) */
    div.stButton > button:has(p:contains('Eliminar')), 
    div.stButton > button:has(div p:contains('Sí, Eliminar')) {{
        background-color: #EA6B66 !important; 
        border-color: #8B0000 !important; 
        color: black !important;
    }}

    /* 6. TARJETAS */
    .tarjeta-capigastos {{
        border-radius: 15px;
        padding: 20px;
        color: white !important;
        margin-bottom: 15px;
        box-shadow: 0 4px 12px 0 rgba(0,0,0,0.4);
        position: relative;
        height: 220px;
        background-size: 100% 100%; 
        background-position: center;
    }}
    /* Texto interno de tarjeta siempre blanco */
    .tarjeta-capigastos div, .tarjeta-capigastos span {{
        color: white !important;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.8);
    }}
    
    .barra-fondo {{ background-color: rgba(255, 255, 255, 0.3); border-radius: 5px; height: 8px; width: 100%; margin-top: 5px; }}
    .barra-progreso {{ background-color: #4CAF50; height: 100%; border-radius: 5px; }}

</style>
""", unsafe_allow_html=True)

# --- LOGICA ---
zona_peru = pytz.timezone('America/Lima')
try:
    df = obtener_datos()
    lista_cuentas = obtener_cuentas()
    presupuestos_dict = obtener_presupuestos()
except:
    st.warning("Cargando..."); time.sleep(1); st.rerun()

# Calculos Globales Seguros
try:
    if not df.empty:
        ing_hist = df[df['Tipo']=='Ingreso']['Monto'].sum()
        gas_hist = df[df['Tipo']=='Gasto']['Monto'].sum()
        ahorro_vida = ing_hist - gas_hist
        saldo_actual = 0
        for c in lista_cuentas:
            i = df[(df['Cuenta']==c)&(df['Tipo']=='Ingreso')]['Monto'].sum()
            g = df[(df['Cuenta']==c)&(df['Tipo']=='Gasto')]['Monto'].sum()
            saldo_actual += (i-g)
    else:
        ing_hist, gas_hist, ahorro_vida, saldo_actual = 0, 0, 0, 0
except:
    ing_hist, gas_hist, ahorro_vida, saldo_actual = 0, 0, 0, 0

# ==============================================================================
# FILA 1: HEADER
# ==============================================================================
c_brand, c_filt, c_kpi1, c_kpi2 = st.columns([1.5, 1.5, 1.5, 1.5], vertical_alignment="center")

with c_brand:
    col_img, col_txt = st.columns([1, 3])
    with col_img:
        if img_logo: st.markdown(f'<img src="data:image/png;base64,{img_logo}" width="90">', unsafe_allow_html=True)
        else: st.write("🐹")
    with col_txt:
        st.markdown("<h2 style='margin:0; padding:0;'>CAPIGASTOS</h2>", unsafe_allow_html=True)

with c_filt:
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    now = datetime.now(zona_peru)
    c_m, c_a = st.columns(2)
    sel_mes = c_m.selectbox("Mes", meses, index=now.month-1, label_visibility="collapsed")
    sel_anio = c_a.number_input("Año", value=now.year, label_visibility="collapsed")
    mes_idx = meses.index(sel_mes) + 1

with c_kpi1:
    st.metric("Saldo Total Disponible", f"S/ {saldo_actual:,.2f}")

with c_kpi2:
    st.metric("Ahorro Histórico", f"S/ {ahorro_vida:,.2f}")

st.markdown("---")

# ==============================================================================
# FILA 2: RESUMEN MENSUAL
# ==============================================================================
# Filtrado de datos del mes (CON PROTECCIÓN CONTRA KEYERROR)
if not df.empty and 'Fecha' in df.columns:
    df_f = df[(df['Fecha'].dt.month == mes_idx) & (df['Fecha'].dt.year == sel_anio)]
else: 
    df_f = pd.DataFrame()

ing_m = df_f[df_f['Tipo']=='Ingreso']['Monto'].sum() if not df_f.empty else 0
gas_m = df_f[df_f['Tipo']=='Gasto']['Monto'].sum() if not df_f.empty else 0
bal_m = ing_m - gas_m

# Conteo seguro de operaciones (FIX KEYERROR)
ops_ing = len(df_f[df_f['Tipo']=='Ingreso']) if not df_f.empty and 'Tipo' in df_f.columns else 0
ops_gas = len(df_f[df_f['Tipo']=='Gasto']) if not df_f.empty and 'Tipo' in df_f.columns else 0

st.markdown(f"<h3 style='text-align: center;'>RESUMEN: {sel_mes.upper()} {sel_anio}</h3>", unsafe_allow_html=True)
k1, k2, k3 = st.columns(3)
k1.metric("Ingresos Mes", f"S/ {ing_m:,.2f}", f"{ops_ing} ops")
k2.metric("Gastos Mes", f"S/ {gas_m:,.2f}", f"{ops_gas} ops", delta_color="inverse")
k3.metric("Ahorro Mes", f"S/ {bal_m:,.2f}", delta="Balance")

st.markdown("---")

# ==============================================================================
# FILA 3: CUERPO
# ==============================================================================
col_izq, col_der = st.columns([1, 2], gap="large")

# --- COLUMNA IZQUIERDA: REGISTRO ---
with col_izq:
    st.subheader("📝 REGISTRO")
    with st.container(border=True):
        st.write("TIPO DE OPERACIÓN:")
        op = st.radio("Tipo", ["Gasto", "Ingreso", "Transferencia"], horizontal=True, label_visibility="collapsed")
        
        with st.form("form_registro", clear_on_submit=True):
            u = st.selectbox("USUARIO:", ["Rodrigo", "Krys"])
            
            if op == "Transferencia":
                c1, c2 = st.columns(2)
                c_ori = c1.selectbox("Desde:", lista_cuentas)
                c_des = c2.selectbox("Hacia:", lista_cuentas)
                cat = "Transferencia"
                cta = c_ori
            else:
                cta = st.selectbox("CUENTA:", lista_cuentas)
                if "Gasto" in op:
                    cat = st.selectbox("CATEGORÍA:", list(presupuestos_dict.keys())+["Otros", "Comida", "Taxi", "Gustitos"])
                else:
                    cat = st.selectbox("CATEGORÍA:", ["Sueldo", "Negocio", "Regalo", "Otros"])
            
            monto = st.number_input("MONTO S/:", min_value=0.01, format="%.2f")
            desc = st.text_input("DESCRIPCIÓN:")
            
            if st.form_submit_button("GUARDAR MOVIMIENTO", use_container_width=True):
                try:
                    now_str = datetime.now(zona_peru).strftime("%Y-%m-%d")
                    time_str = datetime.now(zona_peru).strftime("%H:%M:%S")
                    if op == "Transferencia":
                        if c_ori == c_des: st.error("Cuentas iguales")
                        else:
                            r1 = [now_str, time_str, u, c_ori, "Gasto", "Transferencia/Salida", monto, f"-> {c_des}: {desc}"]
                            r2 = [now_str, time_str, u, c_des, "Ingreso", "Transferencia/Entrada", monto, f"<- {c_ori}: {desc}"]
                            ws_registro.append_row(r1); ws_registro.append_row(r2)
                            limpiar_cache(); st.success("Transferencia OK"); time.sleep(1); st.rerun()
                    else:
                        tipo = "Gasto" if "Gasto" in op else "Ingreso"
                        ws_registro.append_row([now_str, time_str, u, cta, tipo, cat, monto, desc])
                        limpiar_cache(); st.success("Guardado OK"); time.sleep(1); st.rerun()
                except Exception as e: st.error(f"Error: {e}")

# --- COLUMNA DERECHA: DASHBOARD ---
with col_der:
    # SECCIÓN CUENTAS
    c_tit, c_add, c_del = st.columns([4, 1, 1], vertical_alignment="bottom")
    c_tit.subheader("💳 CUENTAS")
    if c_add.button("Agregar", use_container_width=True): dialog_agregar_cuenta()
    if c_del.button("Eliminar", use_container_width=True): dialog_eliminar_cuenta(lista_cuentas)
    
    # GRID DE 3 TARJETAS
    cols_display = st.columns(3)
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
            <div style="position:absolute; top:20px; left:20px;">
                <div style="font-size:12px; opacity:0.9;">CAPIGASTOS CARD</div>
                <div style="font-size:16px; font-weight:bold; text-transform:uppercase; margin-top:5px;">{cuenta}</div>
            </div>
            <div style="position:absolute; top:70px; right:20px; text-align:right;">
                <div style="font-size:10px; opacity:0.9;">DISPONIBLE</div>
                <div style="font-size:22px; font-weight:bold;">S/ {saldo:,.2f}</div>
            </div>
            <div style="position:absolute; bottom:20px; left:20px; right:20px;">
                <div style="display:flex; justify-content:space-between; font-size:10px; margin-bottom:5px;">
                    <span>⬇ {ing_h:,.0f}</span><span>⬆ {gas_h:,.0f}</span>
                </div>
                <div class="barra-fondo"><div class="barra-progreso" style="width:{pct}%;"></div></div>
            </div>
        </div>
        """
        with cols_display[i%3]: st.markdown(html, unsafe_allow_html=True)
    
    st.divider()
    
    # SECCIÓN METAS
    st.subheader("🎯 METAS DEL MES")
    if not df_f.empty: gas_cat = df_f[df_f['Tipo']=='Gasto'].groupby('Categoria')['Monto'].sum()
    else: gas_cat = {}
    
    cm1, cm2 = st.columns(2)
    idx_m = 0
    for cat, tope in presupuestos_dict.items():
        real = gas_cat.get(cat, 0)
        pct_meta = min(real/tope, 1.0) if tope > 0 else 0
        with (cm1 if idx_m % 2 == 0 else cm2):
            st.write(f"**{cat}**")
            st.progress(pct_meta)
            st.caption(f"S/ {real:,.0f} / {tope:,.0f}")
        idx_m += 1

# ==============================================================================
# FILA 4: HISTORIAL
# ==============================================================================
st.divider()
st.subheader("📜 HISTORIAL DE MOVIMIENTOS")
with st.expander("Ver tabla completa", expanded=True):
    if not df_f.empty:
        st.dataframe(
            df_f[['Fecha', 'Usuario', 'Cuenta', 'Tipo', 'Categoria', 'Monto', 'Descripcion']].sort_values('Fecha', ascending=False),
            use_container_width=True,
            hide_index=True
        )
        if st.button("BORRAR ÚLTIMO MOVIMIENTO (DANGER)", type="primary"):
             rows = len(ws_registro.get_all_values())
             if rows > 1:
                 ws_registro.delete_rows(rows)
                 limpiar_cache(); st.success("Borrado"); time.sleep(1); st.rerun()
    else:
        st.info("No hay movimientos registrados en este mes.")
