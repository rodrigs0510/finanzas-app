import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import base64
import pytz # Para la hora de Perú

# --- 1. CONFIGURACIÓN DE PÁGINA (WIDE MODE) ---
st.set_page_config(page_title="CAPIGASTOS", layout="wide", page_icon="🐹")

# --- 2. ESTILOS CSS (GLASSMORPHISM & UI) ---
def poner_fondo(imagen_local):
    try:
        with open(imagen_local, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
        
        css = f"""
        <style>
        /* Fondo General */
        .stApp {{
            background-image: url(data:image/jpg;base64,{encoded_string});
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        
        /* Efecto Cristal (Glassmorphism) para contenedores */
        div[data-testid="stExpander"], div[data-testid="stContainer"], div[data-testid="stMetric"], div[data-testid="stDataFrame"] {{
            background-color: rgba(255, 255, 255, 0.85); /* Blanco al 85% */
            backdrop-filter: blur(10px); /* Efecto borroso detrás */
            border-radius: 15px;
            padding: 15px;
            border: 1px solid rgba(255, 255, 255, 0.3);
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        
        /* Títulos más bonitos */
        h1, h2, h3 {{
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
            color: #ffffff !important; 
            font-weight: 800;
        }}
        
        /* Ajuste de métricas */
        [data-testid="stMetricValue"] {{
            font-size: 1.8rem !important;
        }}
        </style>
        """
        st.markdown(css, unsafe_allow_html=True)
    except:
        pass # Si falla en local por falta de imagen, no rompe la app

# Intentamos cargar fondo
poner_fondo("fondo.jpg")

# --- 3. CONEXIÓN ROBUSTA ---
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

def intento_seguro(funcion):
    max_retries = 3
    for i in range(max_retries):
        try:
            return funcion()
        except Exception:
            time.sleep(2)
            if i == max_retries - 1: raise

try:
    sh = conectar_google_sheets()
    ws_registro = sh.worksheet("Registro")
    ws_cuentas = sh.worksheet("Cuentas")
    ws_presupuestos = sh.worksheet("Presupuestos")
except:
    st.error("⚠️ Error de conexión. Recarga la página.")
    st.stop()

# --- 4. GESTIÓN DE DATOS ---
def limpiar_cache(): st.cache_data.clear()

@st.cache_data(ttl=60)
def obtener_datos():
    data = intento_seguro(lambda: ws_registro.get_all_records())
    if not data: 
        return pd.DataFrame(columns=['ID', 'Fecha', 'Hora', 'Usuario', 'Cuenta', 'Tipo', 'Categoria', 'Monto', 'Descripcion'])
    df = pd.DataFrame(data)
    
    # Limpieza y Formato
    df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)
    # Convertimos fecha string a objeto fecha
    df['Fecha_dt'] = pd.to_datetime(df['Fecha'], format="%Y-%m-%d", errors='coerce')
    # Añadimos columna ID visual (Fila Excel = Index + 2)
    df['ID_Fila'] = df.index + 2 
    return df

@st.cache_data(ttl=300)
def obtener_cuentas():
    cuentas = intento_seguro(lambda: ws_cuentas.col_values(1))
    return cuentas[1:] if len(cuentas) > 1 else ["Efectivo"]

@st.cache_data(ttl=300)
def obtener_presupuestos():
    records = intento_seguro(lambda: ws_presupuestos.get_all_records())
    # Devolvemos lista de diccionarios para poder iterar y borrar
    return records

# --- 5. LÓGICA DE TIEMPO (PERÚ) ---
zona_peru = pytz.timezone('America/Lima')
fecha_hoy_peru = datetime.now(zona_peru)

# --- 6. INTERFAZ: TÍTULO Y FILTROS LATERALES (O SUPERIORES) ---
col_logo, col_titulo = st.columns([1, 6])
with col_logo:
    st.write("🐹") # Aquí podrías poner st.image si tuvieras logo
with col_titulo:
    st.title("CAPIGASTOS")

# --- 7. PANEL DE CONTROL (AGREGAR/ELIMINAR) ---
with st.expander("⚙️ GESTIONAR CUENTAS Y METAS (Control Total)", expanded=False):
    col_g1, col_g2 = st.columns(2)
    
    # GESTIÓN CUENTAS
    with col_g1:
        st.subheader("💳 Mis Cuentas")
        nueva_cuenta = st.text_input("Nueva Cuenta", placeholder="Ej: BCP Ahorros")
        if st.button("➕ Agregar Cuenta", key="add_cta"):
            if nueva_cuenta:
                ws_cuentas.append_row([nueva_cuenta])
                limpiar_cache(); st.success("Agregada"); time.sleep(1); st.rerun()
        
        st.write("---")
        st.write("**Borrar Cuenta:**")
        cuentas_existentes = obtener_cuentas()
        cta_a_borrar = st.selectbox("Selecciona cuenta a borrar", ["-- Seleccionar --"] + cuentas_existentes)
        if st.button("🗑️ Eliminar Cuenta", key="del_cta"):
            if cta_a_borrar != "-- Seleccionar --":
                # Buscamos la celda y borramos
                cell = ws_cuentas.find(cta_a_borrar)
                ws_cuentas.delete_rows(cell.row)
                limpiar_cache(); st.success("Eliminada"); time.sleep(1); st.rerun()

    # GESTIÓN METAS (CATEGORÍAS)
    with col_g2:
        st.subheader("🎯 Mis Metas/Categorías")
        c_cat, c_tope = st.columns(2)
        n_cat = c_cat.text_input("Nueva Categoría", placeholder="Ej: Ropa")
        n_tope = c_tope.number_input("Presupuesto Mensual", min_value=0.0)
        
        if st.button("➕ Agregar Meta", key="add_meta"):
            if n_cat:
                ws_presupuestos.append_row([n_cat, n_tope])
                limpiar_cache(); st.success("Agregada"); time.sleep(1); st.rerun()
        
        st.write("---")
        st.write("**Borrar Meta:**")
        lista_metas = [r['Categoria'] for r in obtener_presupuestos()]
        meta_a_borrar = st.selectbox("Selecciona meta a borrar", ["-- Seleccionar --"] + lista_metas)
        if st.button("🗑️ Eliminar Meta", key="del_meta"):
            if meta_a_borrar != "-- Seleccionar --":
                cell = ws_presupuestos.find(meta_a_borrar)
                ws_presupuestos.delete_rows(cell.row)
                limpiar_cache(); st.success("Eliminada"); time.sleep(1); st.rerun()

# --- 8. FILTROS DE TIEMPO Y AHORRO TOTAL ---
df = obtener_datos()

# Cálculo Ahorro Histórico TOTAL (De siempre)
ingreso_historico = df[df['Tipo'] == 'Ingreso']['Monto'].sum()
gasto_historico = df[df['Tipo'] == 'Gasto']['Monto'].sum()
ahorro_total_vida = ingreso_historico - gasto_historico

st.markdown("---")
# Layout superior
col_filtros, col_ahorro_total = st.columns([2, 1])

with col_filtros:
    with st.container():
        st.subheader("📅 Periodo de Visualización")
        cf1, cf2 = st.columns(2)
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        mes_nom = cf1.selectbox("Mes", meses, index=fecha_hoy_peru.month-1)
        anio = cf2.number_input("Año", value=fecha_hoy_peru.year, min_value=2024, max_value=2030)
        mes_idx = meses.index(mes_nom) + 1

with col_ahorro_total:
    with st.container():
        st.metric("💰 AHORRO TOTAL (Histórico)", f"S/ {ahorro_total_vida:,.2f}")

# FILTRADO DE DATOS
if not df.empty and 'Fecha_dt' in df.columns:
    df_filtrado = df[
        (df['Fecha_dt'].dt.month == mes_idx) & 
        (df['Fecha_dt'].dt.year == anio)
    ]
else:
    df_filtrado = df

# --- 9. RESUMEN DEL MES SELECCIONADO ---
st.markdown("### 📊 Resumen Mensual")
col_res1, col_res2, col_res3 = st.columns(3)

ing_mes = df_filtrado[df_filtrado['Tipo']=='Ingreso']['Monto'].sum()
gas_mes = df_filtrado[df_filtrado['Tipo']=='Gasto']['Monto'].sum()
bal_mes = ing_mes - gas_mes

col_res1.metric("Ingresos Mes", f"S/ {ing_mes:,.2f}")
col_res2.metric("Gastos Mes", f"S/ {gas_mes:,.2f}", delta_color="inverse")
col_res3.metric("Balance Mes", f"S/ {bal_mes:,.2f}", delta=f"{(bal_mes/ing_mes)*100:.0f}%" if ing_mes>0 else "0%")

# --- 10. TARJETAS DE CUENTAS (Estilo Banco) ---
st.markdown("### 💳 Mis Cuentas (Estado Real)")
lista_cuentas = obtener_cuentas()

# Calculamos saldo por cuenta (Siempre histórico, el dinero no se resetea al cambiar de mes)
cols_cuentas = st.columns(3)
for i, cuenta in enumerate(lista_cuentas):
    # Ingresos totales en esa cuenta
    ing_c = df[(df['Cuenta'] == cuenta) & (df['Tipo'] == 'Ingreso')]['Monto'].sum()
    # Gastos totales de esa cuenta
    gas_c = df[(df['Cuenta'] == cuenta) & (df['Tipo'] == 'Gasto')]['Monto'].sum()
    saldo_c = ing_c - gas_c
    
    with cols_cuentas[i % 3]:
        with st.container():
            st.write(f"**{cuenta}**")
            st.write(f"Saldo: **S/ {saldo_c:,.2f}**")
            
            # Barra de progreso: ¿Cuánto del dinero ingresado en esta cuenta aún me queda?
            # Si ingresé 1000 y gasté 200, me queda 800 (80%) -> Barra al 80%
            if ing_c > 0:
                pct_vivo = max(0.0, min(1.0, saldo_c / ing_c))
            else:
                pct_vivo = 0.0
            
            st.progress(pct_vivo)
            st.caption(f"Ingresos Totales: {ing_c} | Gastado: {gas_c}")

# --- 11. METAS DE PRESUPUESTO (Estilo Semáforo) ---
st.markdown("### 🚦 Ejecución de Presupuesto (Metas)")
metas_data = obtener_presupuestos() # Lista de dicts

cols_metas = st.columns(2)
# Gastos del mes filtrado agrupados por categoría
gastos_cat = df_filtrado[df_filtrado['Tipo']=='Gasto'].groupby('Categoria')['Monto'].sum()

for i, meta in enumerate(metas_data):
    cat = meta['Categoria']
    tope = meta['Tope_Mensual']
    
    real_gastado = gastos_cat.get(cat, 0)
    pct_uso = (real_gastado / tope) if tope > 0 else 0
    
    with cols_metas[i % 2]:
        with st.container():
            col_txt, col_num = st.columns([2,1])
            col_txt.write(f"**{cat}**")
            col_num.write(f"S/ {real_gastado:.0f} / {tope}")
            
            # Color de la barra
            if pct_uso > 1.0:
                st.progress(1.0)
                st.error("¡EXCEDIDO!")
            elif pct_uso > 0.8:
                st.progress(pct_uso)
                st.warning("¡Cuidado!")
            else:
                st.progress(pct_uso)

# --- 12. REGISTRO DE OPERACIONES ---
st.markdown("---")
st.markdown("### 📝 Registrar Movimiento")

# Recuperar categorías dinámicas
categorias_disponibles = [m['Categoria'] for m in metas_data] + ["Otros", "Ingreso Extra", "Sueldo"]

with st.container():
    tipo_op = st.radio("Tipo", ["Gasto 📤", "Ingreso 📥", "Transferencia 🔄"], horizontal=True)
    
    with st.form("form_registro", clear_on_submit=True):
        f_col1, f_col2, f_col3 = st.columns(3)
        
        usuario = f_col1.selectbox("Usuario", ["Rodrigo", "Krys"])
        
        if tipo_op == "Transferencia 🔄":
            cta_origen = f_col2.selectbox("Desde", lista_cuentas)
            cta_destino = f_col3.selectbox("Hacia", lista_cuentas)
            categoria = "Transferencia"
        else:
            cuenta = f_col2.selectbox("Cuenta", lista_cuentas)
            if tipo_op == "Gasto 📤":
                categoria = f_col3.selectbox("Categoría", categorias_disponibles)
            else:
                categoria = f_col3.selectbox("Fuente", ["Sueldo", "Negocio", "Regalo", "Otros"])

        f_monto = st.number_input("Monto (S/)", min_value=0.00, step=0.10, format="%.2f")
        f_desc = st.text_input("Detalle", placeholder="Ej: Pollo a la brasa")
        
        if st.form_submit_button("💾 Guardar Operación"):
            # FECHA Y HORA PERÚ
            fecha_pe = datetime.now(zona_peru).strftime("%Y-%m-%d")
            hora_pe = datetime.now(zona_peru).strftime("%H:%M:%S")
            
            if tipo_op == "Transferencia 🔄":
                if cta_origen == cta_destino:
                    st.error("¡Cuentas iguales!")
                else:
                    r1 = [fecha_pe, hora_pe, usuario, cta_origen, "Gasto", "Transferencia/Salida", f_monto, f"-> {cta_destino}: {f_desc}"]
                    r2 = [fecha_pe, hora_pe, usuario, cta_destino, "Ingreso", "Transferencia/Entrada", f_monto, f"<- {cta_origen}: {f_desc}"]
                    ws_registro.append_row(r1)
                    ws_registro.append_row(r2)
                    limpiar_cache(); st.success("Transferencia Exitosa"); time.sleep(1); st.rerun()
            else:
                tipo_real = "Gasto" if "Gasto" in tipo_op else "Ingreso"
                row = [fecha_pe, hora_pe, usuario, cuenta, tipo_real, categoria, f_monto, f_desc]
                ws_registro.append_row(row)
                limpiar_cache(); st.success("Registrado"); time.sleep(1); st.rerun()

# --- 13. HISTORIAL Y BORRADO QUIRÚRGICO ---
st.markdown("---")
st.markdown("### 🗑️ Historial y Edición")

with st.expander("Ver Historial Completo / Borrar Errores"):
    # Mostramos tabla con formato bonito
    if not df.empty:
        # Creamos una vista bonita para el usuario
        df_view = df[['ID_Fila', 'Fecha', 'Usuario', 'Tipo', 'Monto', 'Categoria', 'Descripcion']].copy()
        # Formatear fecha para verla DD/MM/YYYY
        df_view['Fecha'] = pd.to_datetime(df_view['Fecha']).dt.strftime('%d/%m/%Y')
        
        st.dataframe(df_view.sort_values(by="ID_Fila", ascending=False), use_container_width=True)
        
        st.write("**Borrar Movimiento Específico:**")
        col_del1, col_del2 = st.columns([3, 1])
        id_a_borrar = col_del1.number_input("Ingresa el ID (Número de la primera columna) que quieres borrar:", min_value=0, step=1)
        
        if col_del2.button("❌ Borrar ID"):
            if id_a_borrar > 0:
                try:
                    # Gspread borra por número de fila exacta
                    ws_registro.delete_rows(int(id_a_borrar))
                    limpiar_cache()
                    st.success(f"Fila ID {id_a_borrar} eliminada.")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"No se pudo borrar: {e}")
    else:
        st.info("No hay movimientos registrados aún.")
