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

def limpiar_cache(): 
    st.cache_data.clear()

@st.cache_data(ttl=60)
def obtener_datos():
    columnas_base = ['Fecha', 'Hora', 'Usuario', 'Cuenta', 'Tipo', 'Categoria', 'Monto', 'Descripcion']
    try:
        data = intento_seguro(lambda: ws_registro.get_all_records())
        if not data: 
            return pd.DataFrame(columns=columnas_base + ['Fila_Original'])
        
        df = pd.DataFrame(data)
        
        # Validación de columnas
        for col in columnas_base:
            if col not in df.columns: df[col] = ""
        
        # CRÍTICO: Guardamos el número de fila original antes de filtrar nada
        # (Index 0 del DF = Fila 2 del Excel porque la 1 es header)
        df['Fila_Original'] = df.index + 2 
        
        df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)
        df['Fecha'] = pd.to_datetime(df['Fecha'], format="%Y-%m-%d", errors='coerce')
        return df
    except:
        return pd.DataFrame(columns=columnas_base + ['Fila_Original'])

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

# --- ACCIÓN DE BORRADO ---
def borrar_fila_especifica(numero_fila):
    try:
        ws_registro.delete_rows(numero_fila)
        limpiar_cache()
        st.toast(f"✅ Registro eliminado correctamente")
        time.sleep(1)
    except Exception as e:
        st.error(f"Error al borrar: {e}")

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

# --- CSS NUCLEAR ---
st.markdown(f"""
<style>
    /* 1. FONDO DE PANTALLA */
    .stApp {{
        background-image: url("data:image/jpg;base64,{img_fondo}");
        background-size: cover; 
        background-position: center; 
        background-attachment: fixed;
    }}

    /* 2. CAJAS BLANCAS SÓLIDAS */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: #FFF8DC !important;
        border: 3px solid #8B4513 !important;
        border-radius: 15px !important;
        padding: 15px !important;
        opacity: 1 !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3) !important;
    }}
    div[data-testid="stVerticalBlockBorderWrapper"] > div {{
        background-color: transparent !important;
    }}

    /* 3. TEXTOS NEGROS/MARRONES */
    h1, h2, h3, h4, p, span, label, div, .stMarkdown, .stMetricLabel {{
        color: #4A3B2A !important;
        text-shadow: none !important;
    }}
    
    /* 4. TARJETAS (TEXTO BLANCO) */
    .tarjeta-capigastos *, .tarjeta-capigastos div {{ 
        color: white !important; 
        text-shadow: 1px 1px 2px rgba(0,0,0,0.8) !important;
    }}

    /* 5. INPUTS */
    .stTextInput input, .stNumberInput input, div[data-baseweb="select"] > div {{
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 2px solid #8B4513 !important;
    }}

    /* 6. BOTONES ESTILO PASTILLA */
    div.stButton > button:has(p:contains('Agregar')) {{
        background-color: #9ACD32 !important; color: #2F4F4F !important;
        border: 3px solid #556B2F !important; border-radius: 50px !important;
        font-weight: 900 !important;
    }}
    div.stButton > button:has(p:contains('Eliminar')) {{
        background-color: #FA8072 !important; color: #581818 !important;
        border: 3px solid #8B0000 !important; border-radius: 50px !important;
        font-weight: 900 !important;
    }}
    /* Botón Guardar */
    div.stButton > button:has(p:contains('GUARDAR')) {{
        background-color: #8B4513 !important; color: white !important;
        border: 2px solid #5e2f0d !important; border-radius: 20px !important;
    }}
    /* Botón Pequeño de Borrar Fila (Icono) */
    div.stButton > button:has(p:contains('🗑️')) {{
        background-color: #FFE4E1 !important;
        color: red !important;
        border: 1px solid red !important;
        border-radius: 5px !important;
        padding: 0px 5px !important;
        height: 35px !important;
    }}

    /* 7. TARJETA VISUAL */
    .tarjeta-capigastos {{
        background-color: #8B4513;
        border-radius: 15px; padding: 15px; margin-bottom: 10px;
        box-shadow: 0 4px 8px 0 rgba(0,0,0,0.3); position: relative; height: 180px;
        background-size: 100% 100%; background-position: center;
    }}
    .barra-fondo {{ background-color: rgba(255, 255, 255, 0.3); border-radius: 5px; height: 6px; width: 100%; margin-top: 5px; }}
    .barra-progreso {{ background-color: #4CAF50; height: 100%; border-radius: 5px; }}
    
    /* 8. LISTA DE MOVIMIENTOS (Fila estilizada) */
    .fila-movimiento {{
        background-color: #FFFFFF;
        border-bottom: 1px solid #D3D3D3;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 5px;
    }}

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

# DATOS GLOBALES
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
# HEADER
# ==============================================================================
with st.container(border=True):
    c1, c2, c3 = st.columns([1.5, 1.5, 1.5], vertical_alignment="center")
    with c1:
        cc1, cc2 = st.columns([1, 3])
        with cc1:
            if img_logo: st.markdown(f'<img src="data:image/png;base64,{img_logo}" width="80">', unsafe_allow_html=True)
        with cc2: st.markdown("<h2>CAPIGASTOS</h2>", unsafe_allow_html=True)
    with c2:
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        now = datetime.now(zona_peru)
        cm, ca = st.columns(2)
        sel_mes = cm.selectbox("Mes", meses, index=now.month-1, label_visibility="collapsed")
        sel_anio = ca.number_input("Año", value=now.year, label_visibility="collapsed")
        mes_idx = meses.index(sel_mes) + 1
    with c3:
        st.markdown(f"<div style='text-align:right;'><b>Saldo Total:</b> S/ {saldo_actual:,.2f}<br><b>Ahorro Histórico:</b> S/ {ahorro_vida:,.2f}</div>", unsafe_allow_html=True)

# ==============================================================================
# CONSOLIDADO
# ==============================================================================
if not df.empty and 'Fecha' in df.columns:
    df_f = df[(df['Fecha'].dt.month == mes_idx) & (df['Fecha'].dt.year == sel_anio)]
else: df_f = pd.DataFrame(columns=df.columns)

ing_m = df_f[df_f['Tipo']=='Ingreso']['Monto'].sum() if not df_f.empty else 0
gas_m = df_f[df_f['Tipo']=='Gasto']['Monto'].sum() if not df_f.empty else 0
bal_m = ing_m - gas_m

with st.container(border=True):
    st.markdown(f"<h4 style='text-align:center; margin:0;'>CONSOLIDADO: {sel_mes.upper()} {sel_anio}</h4>", unsafe_allow_html=True)
    k1, k2, k3 = st.columns(3)
    k1.metric("Ingresos", f"S/ {ing_m:,.2f}")
    k2.metric("Gastos", f"S/ {gas_m:,.2f}")
    k3.metric("Ahorro", f"S/ {bal_m:,.2f}")

st.write("")

# ==============================================================================
# CUERPO (FORMULARIO Y CUENTAS)
# ==============================================================================
col_izq, col_der = st.columns([1, 1.8], gap="medium")

# --- IZQUIERDA: FORMULARIO ---
with col_izq:
    with st.container(border=True):
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
                if "Gasto" in op: cat = st.selectbox("Categoría", list(presupuestos_dict.keys())+["Otros", "Comida", "Taxi"])
                else: cat = st.selectbox("Categoría", ["Sueldo", "Negocio", "Regalo"])
            
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
with col_der:
    with st.container(border=True):
        ch1, ch2, ch3 = st.columns([4, 1, 1], vertical_alignment="bottom")
        ch1.markdown("### 💳 CUENTAS")
        if ch2.button("Agregar", key="add", use_container_width=True): dialog_agregar_cuenta()
        if ch3.button("Eliminar", key="del", use_container_width=True): dialog_eliminar_cuenta(lista_cuentas)
        
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

    with st.container(border=True):
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
# 4. PIE DE PÁGINA: HISTORIAL CON BORRADO INDIVIDUAL
# ==============================================================================
col_foot_left, col_foot_right = st.columns([1.5, 1], gap="medium")

with col_foot_left:
    with st.container(border=True):
        st.markdown("### 📜 HISTORIAL (BORRADO INDIVIDUAL)")
        
        if not df_f.empty:
            # Ordenamos por fecha descendente pero mantenemos la fila original
            df_mostrar = df_f.sort_values('Fecha', ascending=False).reset_index(drop=True)
            
            # Encabezados
            h1, h2, h3, h4, h5, h6 = st.columns([2, 3, 2, 2, 3, 1])
            h1.write("**Fecha**")
            h2.write("**Cuenta**")
            h3.write("**Monto**")
            h4.write("**Categ**")
            h5.write("**Desc**")
            h6.write("**Acción**")
            st.divider()
            
            # ITERAMOS FILA POR FILA
            for idx, row in df_mostrar.iterrows():
                c1, c2, c3, c4, c5, c6 = st.columns([2, 3, 2, 2, 3, 1])
                
                # Color del monto (Verde ingreso, Rojo gasto)
                color_monto = "green" if row['Tipo'] == 'Ingreso' else "red"
                str_monto = f":{color_monto}[S/ {row['Monto']:.2f}]"
                
                with c1: st.write(row['Fecha'].strftime("%d/%m"))
                with c2: st.caption(row['Cuenta'])
                with c3: st.markdown(str_monto)
                with c4: st.caption(row['Categoria'])
                with c5: st.caption(row['Descripcion'] if row['Descripcion'] else "-")
                
                # BOTÓN BORRAR INDIVIDUAL
                with c6:
                    # Usamos la Fila_Original que guardamos en obtener_datos
                    fila_a_borrar = row['Fila_Original']
                    if st.button("🗑️", key=f"btn_del_{fila_a_borrar}"):
                        borrar_fila_especifica(fila_a_borrar)
                        st.rerun() # Recargamos inmediatamente
                
        else:
            st.info("Sin datos para este mes.")

with col_foot_right:
    with st.container(border=True):
        st.markdown("### ⏰ PAGOS PENDIENTES")
        st.info("Próximos vencimientos:")
        st.markdown("- 📅 **Luz del Sur:** 15/Feb (S/ 120.00)\n- 📅 **Internet:** 20/Feb (S/ 89.00)")
        st.text_input("Agregar recordatorio:")
        st.button("Añadir")

