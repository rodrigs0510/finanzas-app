import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import pytz 
import base64
import math

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="CAPIGASTOS", layout="centered", page_icon="🐹")

# --- CARGAR IMÁGENES (CON CONTROL DE ERRORES) ---
def get_image_as_base64(file_path):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except Exception:
        return "" # Retorna vacío si falla para no romper la app

# Cargamos las imágenes en memoria
img_tarjeta = get_image_as_base64("Tarjeta fondo.png")
img_logo = get_image_as_base64("logo.png") 
img_btn_agregar = get_image_as_base64("boton_agregar.png") 
img_btn_eliminar = get_image_as_base64("boton_eliminar.png")

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

# --- FUNCIONES BLINDADAS ---
def intento_seguro(funcion_gspread):
    max_retries = 3
    for i in range(max_retries):
        try:
            return funcion_gspread()
        except gspread.exceptions.APIError as e:
            if i == max_retries - 1:
                raise e
            time.sleep(2 * (i + 1))
        except Exception as e:
            raise e

@st.cache_data(ttl=60)
def obtener_datos():
    data = intento_seguro(lambda: ws_registro.get_all_records())
    columnas = ['Fecha', 'Hora', 'Usuario', 'Cuenta', 'Tipo', 'Categoria', 'Monto', 'Descripcion']
    if not data:
        df = pd.DataFrame(columns=columnas)
    else:
        df = pd.DataFrame(data)

    df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)
    df['Fecha'] = pd.to_datetime(df['Fecha'], format="%Y-%m-%d", errors='coerce')
    return df

@st.cache_data(ttl=600)
def obtener_cuentas():
    cuentas = intento_seguro(lambda: ws_cuentas.col_values(1))
    return cuentas[1:] if len(cuentas) > 1 else ["Efectivo"]

@st.cache_data(ttl=600)
def obtener_presupuestos():
    records = intento_seguro(lambda: ws_presupuestos.get_all_records())
    presupuestos = {row['Categoria']: row['Tope_Mensual'] for row in records}
    return presupuestos

def limpiar_cache():
    st.cache_data.clear()

# --- VENTANAS EMERGENTES ---
@st.dialog("Agregar Nueva Cuenta")
def dialog_agregar_cuenta():
    nombre_cuenta = st.text_input("Nombre de la cuenta (Ej: BCP Ahorros)")
    if st.button("Crear Cuenta"):
        if nombre_cuenta:
            ws_cuentas.append_row([nombre_cuenta])
            limpiar_cache()
            st.success("¡Cuenta creada!")
            time.sleep(1)
            st.rerun()
        else:
            st.warning("Escribe un nombre primero.")

@st.dialog("Eliminar Cuenta")
def dialog_eliminar_cuenta(lista_actual):
    cuenta_a_borrar = st.selectbox("Selecciona la cuenta a eliminar:", lista_actual)
    st.warning(f"¿Estás seguro de que quieres eliminar **{cuenta_a_borrar}**? Esta acción no se puede deshacer.")
    
    col_d1, col_d2 = st.columns(2)
    if col_d1.button("Sí, Eliminar"):
        try:
            cell = ws_cuentas.find(cuenta_a_borrar)
            ws_cuentas.delete_rows(cell.row)
            limpiar_cache()
            st.success("Cuenta eliminada.")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
    
    if col_d2.button("Cancelar"):
        st.rerun()

# --- HEADER ---
col_logo, col_titulo = st.columns([1, 4]) 
with col_logo:
    if img_logo:
        st.markdown(f'<img src="data:image/png;base64,{img_logo}" width="80">', unsafe_allow_html=True)
    else:
        st.write("🐹") 
with col_titulo:
    st.title("CAPIGASTOS")

# ZONA HORARIA
zona_peru = pytz.timezone('America/Lima')

try:
    df = obtener_datos()
    lista_cuentas = obtener_cuentas()
    presupuestos_dict = obtener_presupuestos()
except Exception:
    st.warning("Cargando datos...")
    time.sleep(2)
    st.rerun()

# --- CÁLCULOS GLOBALES ---
total_ingresos_historico = 0
total_gastos_historico = 0
saldo_cuentas_total = 0

if not df.empty:
    total_ingresos_historico = df[df['Tipo'] == 'Ingreso']['Monto'].sum()
    total_gastos_historico = df[df['Tipo'] == 'Gasto']['Monto'].sum()
    ahorro_total_historico = total_ingresos_historico - total_gastos_historico
    
    for c in lista_cuentas:
        i = df[(df['Cuenta'] == c) & (df['Tipo'] == 'Ingreso')]['Monto'].sum()
        g = df[(df['Cuenta'] == c) & (df['Tipo'] == 'Gasto')]['Monto'].sum()
        saldo_cuentas_total += (i - g)
else:
    ahorro_total_historico = 0
    saldo_cuentas_total = 0

# --- ESTADO GLOBAL ---
st.subheader("Estado Global (Histórico)")
col_g1, col_g2 = st.columns(2)
col_g1.metric("Saldo Total Disponible", f"S/ {saldo_cuentas_total:.2f}")
col_g2.metric("Ahorro Total Acumulado", f"S/ {ahorro_total_historico:.2f}", delta="Total Histórico")

st.divider()

# --- FILTROS DE TIEMPO ---
with st.container(border=True):
    c1, c2 = st.columns(2)
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
             "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    
    now = datetime.now(zona_peru)
    mes_nom = c1.selectbox("Mes", meses, index=now.month-1)
    anio = c2.number_input("Año", value=now.year, min_value=2024, max_value=2030)
    mes_idx = meses.index(mes_nom) + 1

# Lógica Datos Filtrados
if not df.empty and df['Fecha'].notna().any():
    df_f = df[(df['Fecha'].dt.month == mes_idx) & (df['Fecha'].dt.year == anio)]
else:
    df_f = df

# 1. Resumen Mes
st.subheader(f"Resumen {mes_nom} {anio}")
if not df_f.empty:
    ing_m = df_f[df_f['Tipo']=='Ingreso']['Monto'].sum()
    gas_m = df_f[df_f['Tipo']=='Gasto']['Monto'].sum()
    bal_m = ing_m - gas_m
else:
    ing_m, gas_m, bal_m = 0,0,0

m1, m2, m3 = st.columns(3)
m1.metric("Ingresos (Mes)", f"S/ {ing_m:.2f}")
m2.metric("Gastos (Mes)", f"S/ {gas_m:.2f}", delta_color="inverse")
m3.metric("Ahorro (Mes)", f"S/ {bal_m:.2f}", delta=f"{(bal_m/ing_m)*100:.0f}%" if ing_m>0 else None)

st.divider()

# =========================================================
# 2. SECCIÓN CUENTAS (CONTENEDOR) 💳
# =========================================================

c_cont = st.container()

with c_cont:
    # Alineación vertical "bottom" para alinear botones con el texto
    c1, c2, c3 = st.columns([3, 1, 1], vertical_alignment="bottom")

    with c1:
        st.subheader("CUENTAS")
    with c2:
        # Texto invisible para que el botón tenga tamaño pero muestre la imagen
        if st.button("⠀   ⠀", key="btn_add_img", help="AGREGAR_IMG"):
            dialog_agregar_cuenta()
    with c3:
        if st.button("⠀   ⠀", key="btn_del_img", help="ELIMINAR_IMG"):
            dialog_eliminar_cuenta(lista_cuentas)

    # --- CSS MAESTRO CORREGIDO ---
    st.markdown(f"""
    <style>
        /* 1. BOTÓN AGREGAR (IMAGEN DE FONDO) */
        /* Buscamos por el tooltip (help) que es único */
        div.stButton > button[title="AGREGAR_IMG"] {{
            background-image: url("data:image/png;base64,{img_btn_agregar}");
            background-size: 100% 100%;
            background-repeat: no-repeat;
            background-position: center;
            background-color: transparent !important;
            border: none !important;
            height: 45px; /* Altura forzada para ver la imagen */
            width: 100%;
            box-shadow: none !important;
        }}
        div.stButton > button[title="AGREGAR_IMG"]:hover {{
            transform: scale(1.05);
        }}

        /* 2. BOTÓN ELIMINAR (IMAGEN DE FONDO) */
        div.stButton > button[title="ELIMINAR_IMG"] {{
            background-image: url("data:image/png;base64,{img_btn_eliminar}");
            background-size: 100% 100%;
            background-repeat: no-repeat;
            background-position: center;
            background-color: transparent !important;
            border: none !important;
            height: 45px;
            width: 100%;
            box-shadow: none !important;
        }}
        div.stButton > button[title="ELIMINAR_IMG"]:hover {{
            transform: scale(1.05);
        }}

        /* 3. BOTONES FLECHA (Carrusel) - COLOR CAPIBARA */
        /* Seleccionamos botones con texto flecha */
        div.stButton > button:has(p:contains('◀')),
        div.stButton > button:has(p:contains('▶')) {{
            background-color: #8B4513 !important; /* Marrón Capibara */
            border: 2px solid #5e2f0d !important;
            color: white !important;
            border-radius: 50% !important;
            width: 45px !important;
            height: 45px !important;
            padding: 0px !important;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: auto 0; /* Centrado extra */
        }}
        div.stButton > button:has(p:contains('◀')):hover,
        div.stButton > button:has(p:contains('▶')):hover {{
             background-color: #A0522D !important;
             transform: scale(1.1);
        }}

        /* 4. ESTILOS TARJETA (ANIMACIÓN FADE IN) */
        @keyframes fadeIn {{
            from {{ opacity: 0; }}
            to {{ opacity: 1; }}
        }}
        .tarjeta-capigastos {{
            animation: fadeIn 0.8s ease-in-out;
            border-radius: 15px;
            padding: 20px;
            color: white;
            margin-bottom: 10px;
            box-shadow: 0 4px 12px 0 rgba(0,0,0,0.4);
            position: relative;
            height: 220px;
            background-size: 100% 100%; 
            background-position: center;
        }}
        .texto-sombra {{ text-shadow: 2px 2px 4px rgba(0,0,0,0.8); }}
        .barra-fondo {{ background-color: rgba(255, 255, 255, 0.3); border-radius: 5px; height: 8px; width: 100%; margin-top: 5px; }}
        .barra-progreso {{ background-color: #4CAF50; height: 100%; border-radius: 5px; }}

    </style>
    """, unsafe_allow_html=True)

    # --- LÓGICA DE CARRUSEL ---
    TARJETAS_POR_PAGINA = 2 

    if 'pagina_cuentas' not in st.session_state:
        st.session_state.pagina_cuentas = 0

    total_cuentas = len(lista_cuentas)
    total_paginas = math.ceil(total_cuentas / TARJETAS_POR_PAGINA)

    # Layout Carrusel: Centrado Vertical
    # IMPORTANTE: vertical_alignment="center" alinea las flechas al medio de las tarjetas
    col_nav_izq, col_tarjetas, col_nav_der = st.columns([1, 12, 1], vertical_alignment="center")

    with col_nav_izq:
        if st.button("◀", key="prev_page"):
            if st.session_state.pagina_cuentas > 0:
                st.session_state.pagina_cuentas -= 1
                st.rerun()

    with col_nav_der:
        if st.button("▶", key="next_page"):
            if st.session_state.pagina_cuentas < total_paginas - 1:
                st.session_state.pagina_cuentas += 1
                st.rerun()

    with col_tarjetas:
        start_idx = st.session_state.pagina_cuentas * TARJETAS_POR_PAGINA
        end_idx = start_idx + TARJETAS_POR_PAGINA
        cuentas_pagina = lista_cuentas[start_idx:end_idx]
        
        cols_display = st.columns(TARJETAS_POR_PAGINA)
        
        for i, cuenta in enumerate(cuentas_pagina):
            # Lógica
            if not df.empty:
                ingresos_h = df[(df['Cuenta'] == cuenta) & (df['Tipo'] == 'Ingreso')]['Monto'].sum()
                gastos_h = df[(df['Cuenta'] == cuenta) & (df['Tipo'] == 'Gasto')]['Monto'].sum()
                saldo_d = ingresos_h - gastos_h
            else:
                ingresos_h, gastos_h, saldo_d = 0, 0, 0

            pct = min(max(saldo_d / ingresos_h, 0.0), 1.0) * 100 if ingresos_h > 0 else 0
            bg = f"background-image: url('data:image/png;base64,{img_tarjeta}');" if img_tarjeta else "background-color: #8B4513;"

            html = f"""
            <div class="tarjeta-capigastos" style="{bg}">
                <div style="position: absolute; top: 20px; left: 20px;">
                    <div class="texto-sombra" style="font-weight: bold; font-size: 14px; opacity: 0.9;">CAPIGASTOS CARD</div>
                    <div class="texto-sombra" style="font-size: 18px; font-weight: bold; margin-top: 5px; text-transform: uppercase;">{cuenta}</div>
                </div>
                <div style="position: absolute; top: 75px; right: 20px; text-align: right;">
                    <div class="texto-sombra" style="font-size: 10px; opacity: 0.9;">SALDO DISPONIBLE</div>
                    <div class="texto-sombra" style="font-size: 24px; font-weight: bold;">S/ {saldo_d:,.2f}</div>
                </div>
                <div style="position: absolute; bottom: 20px; left: 20px; right: 20px;">
                    <div style="display: flex; justify-content: space-between; font-size: 10px; margin-bottom: 5px;" class="texto-sombra">
                        <span>⬇ Ing: {ingresos_h:,.0f}</span>
                        <span style="color: #ffcccb;">⬆ Gas: {gastos_h:,.0f}</span>
                    </div>
                    <div class="barra-fondo"><div class="barra-progreso" style="width: {pct}%;"></div></div>
                    <div style="text-align: right; font-size: 9px; margin-top: 2px;" class="texto-sombra">{pct:.0f}% Disp.</div>
                </div>
            </div>
            """
            
            if i < len(cols_display):
                with cols_display[i]:
                    st.markdown(html, unsafe_allow_html=True)

st.divider()

# 3. Metas
st.subheader("Metas del Mes")
if not df_f.empty:
    gastos_cat = df_f[df_f['Tipo']=='Gasto'].groupby('Categoria')['Monto'].sum()
else:
    gastos_cat = {}

cp = st.columns(2)
ip = 0
for cat, tope in presupuestos_dict.items():
    real = gastos_cat.get(cat, 0)
    pct = (real/tope) if tope>0 else 0
    with cp[ip%2]:
        st.write(f"**{cat}**")
        st.progress(min(pct, 1.0))
        st.caption(f"{real:.0f} / {tope} ({pct*100:.0f}%)")
    ip += 1

st.divider()

# 4. Registro
st.subheader("Operación")
op = st.radio("Tipo", ["Gasto", "Ingreso", "Transferencia"], horizontal=True)

with st.form("op_form", clear_on_submit=True):
    fc1, fc2 = st.columns(2)
    u = fc1.selectbox("Usuario", ["Rodrigo", "Krys"])
    
    if op == "Transferencia":
        c_origen = fc2.selectbox("Desde", lista_cuentas)
        c_dest = st.selectbox("Hacia", lista_cuentas)
        cat = "Transferencia"
    else:
        cta = fc2.selectbox("Cuenta", lista_cuentas)
        if "Gasto" in op:
            cat = st.selectbox("Categoría", list(presupuestos_dict.keys())+["Otros"])
        else:
            cat = st.selectbox("Categoría", ["Sueldo", "Negocio", "Regalo", "Otros"])
            
    monto = st.number_input("Monto", min_value=0.01, format="%.2f")
    desc = st.text_input("Detalle")
    
    if st.form_submit_button("Guardar"):
        try:
            now_str = datetime.now(zona_peru).strftime("%Y-%m-%d")
            time_str = datetime.now(zona_peru).strftime("%H:%M:%S")
            
            if op == "Transferencia":
                if c_origen == c_dest:
                    st.error("Cuentas iguales")
                else:
                    r1 = [now_str, time_str, u, c_origen, "Gasto", "Transferencia/Salida", monto, f"-> {c_dest}: {desc}"]
                    r2 = [now_str, time_str, u, c_dest, "Ingreso", "Transferencia/Entrada", monto, f"<- {c_origen}: {desc}"]
                    intento_seguro(lambda: ws_registro.append_row(r1))
                    intento_seguro(lambda: ws_registro.append_row(r2))
                    limpiar_cache()
                    st.success("Transferencia OK")
                    time.sleep(1)
                    st.rerun()
            else:
                tipo = "Gasto" if "Gasto" in op else "Ingreso"
                row = [now_str, time_str, u, cta, tipo, cat, monto, desc]
                intento_seguro(lambda: ws_registro.append_row(row))
                limpiar_cache()
                st.success("Guardado OK")
                time.sleep(1)
                st.rerun()
        except Exception as e:
            st.error(f"Error guardando: {e}")

# 5. Borrar
with st.expander("Borrar Último"):
    if not df.empty:
        st.dataframe(df.sort_values("Fecha", ascending=False).head(3), use_container_width=True)
        if st.button("BORRAR"):
            try:
                rows = len(ws_registro.get_all_values())
                if rows > 1:
                    intento_seguro(lambda: ws_registro.delete_rows(rows))
                    limpiar_cache()
                    st.success("Borrado")
                    time.sleep(1)
                    st.rerun()
            except Exception as e:
                st.error(f"Error borrando: {e}")
