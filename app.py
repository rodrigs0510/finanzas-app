import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import pytz 

# --- 1. CONFIGURACIÓN (NATIVA Y LIMPIA) ---
st.set_page_config(
    page_title="CAPIGASTOS (Operativo)", 
    layout="wide",
    page_icon="💰"
)

# --- 2. CONEXIÓN A GOOGLE SHEETS ---
@st.cache_resource
def conectar_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    if "gcp_service_account" in st.secrets:
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    else:
        # Asegúrate de tener tu archivo credentials.json en la misma carpeta
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
    st.error(f"❌ Error de Conexión: {e}")
    st.stop()

# --- 3. FUNCIONES DE DATOS (LÓGICA PURA) ---
def limpiar_cache():
    st.cache_data.clear()

def intento_seguro(funcion_gspread):
    # Reintenta la conexión si falla momentáneamente
    try:
        return funcion_gspread()
    except Exception as e:
        time.sleep(2)
        return funcion_gspread()

@st.cache_data(ttl=60)
def obtener_datos():
    # Estructura esperada
    cols = ['Fecha', 'Hora', 'Usuario', 'Cuenta', 'Tipo', 'Categoria', 'Monto', 'Descripcion']
    try:
        data = intento_seguro(lambda: ws_registro.get_all_records())
        if not data: return pd.DataFrame(columns=cols)
        
        df = pd.DataFrame(data)
        
        # Validación de columnas
        for c in cols:
            if c not in df.columns: df[c] = ""
            
        # Limpieza Crítica de Montos
        df['Monto'] = df['Monto'].astype(str).str.replace(r'[^\d.]', '', regex=True) # Solo deja números y puntos
        df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)
        
        # Limpieza de Fechas
        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
        return df.dropna(subset=['Fecha'])
    except Exception as e:
        st.error(f"Error leyendo datos: {e}")
        return pd.DataFrame(columns=cols)

@st.cache_data(ttl=600)
def obtener_cuentas():
    try:
        lista = intento_seguro(lambda: ws_cuentas.col_values(1))
        return lista[1:] if len(lista) > 1 else ["Efectivo"] # Salta encabezado
    except: return ["Efectivo"]

@st.cache_data(ttl=600)
def obtener_presupuestos():
    try:
        data = intento_seguro(lambda: ws_presupuestos.get_all_records())
        return {d['Categoria']: d['Tope_Mensual'] for d in data}
    except: return {}

# --- 4. GESTIÓN DE CUENTAS (DIALOGS NATIVOS) ---
@st.dialog("Nueva Cuenta")
def pop_agregar_cuenta():
    nombre = st.text_input("Nombre del Banco/Cuenta")
    if st.button("Guardar Cuenta"):
        if nombre:
            ws_cuentas.append_row([nombre])
            limpiar_cache()
            st.success("Guardado")
            time.sleep(1)
            st.rerun()

@st.dialog("Borrar Cuenta")
def pop_eliminar_cuenta(lista):
    sel = st.selectbox("Selecciona cuenta a borrar", lista)
    if st.button("Confirmar Borrado", type="primary"):
        cell = ws_cuentas.find(sel)
        ws_cuentas.delete_rows(cell.row)
        limpiar_cache()
        st.success("Eliminado")
        time.sleep(1)
        st.rerun()

# --- 5. INTERFAZ OPERATIVA (LAYOUT) ---
zona_peru = pytz.timezone('America/Lima')
df = obtener_datos()
lista_cuentas = obtener_cuentas()
presupuestos = obtener_presupuestos()

# --- CÁLCULOS GLOBALES ---
saldo_global = 0
ingreso_total_hist = df[df['Tipo'] == 'Ingreso']['Monto'].sum()
gasto_total_hist = df[df['Tipo'] == 'Gasto']['Monto'].sum()
ahorro_hist = ingreso_total_hist - gasto_total_hist

# Calculamos saldo por cuenta
saldos_por_cuenta = {}
for c in lista_cuentas:
    ing = df[(df['Cuenta'] == c) & (df['Tipo'] == 'Ingreso')]['Monto'].sum()
    gas = df[(df['Cuenta'] == c) & (df['Tipo'] == 'Gasto')]['Monto'].sum()
    saldo = ing - gas
    saldos_por_cuenta[c] = saldo
    saldo_global += saldo

# --- ENCABEZADO ---
st.title("💰 CAPIGASTOS: Panel de Control")
top1, top2, top3, top4 = st.columns(4)
top1.metric("Saldo Disponible Total", f"S/ {saldo_global:,.2f}")
top2.metric("Ahorro Histórico", f"S/ {ahorro_hist:,.2f}")

# Filtros de Fecha
meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
hoy = datetime.now(zona_peru)
mes_sel = top3.selectbox("Mes", meses, index=hoy.month-1)
anio_sel = top4.number_input("Año", value=hoy.year)
mes_idx = meses.index(mes_sel) + 1

st.divider()

# --- CONSOLIDADO DEL MES ---
if not df.empty:
    df_mes = df[(df['Fecha'].dt.month == mes_idx) & (df['Fecha'].dt.year == anio_sel)]
else:
    df_mes = df

m_ing = df_mes[df_mes['Tipo'] == 'Ingreso']['Monto'].sum()
m_gas = df_mes[df_mes['Tipo'] == 'Gasto']['Monto'].sum()
m_bal = m_ing - m_gas

c1, c2, c3 = st.columns(3)
c1.metric("Ingresos (Mes)", f"S/ {m_ing:,.2f}", border=True)
c2.metric("Gastos (Mes)", f"S/ {m_gas:,.2f}", delta_color="inverse", border=True)
c3.metric("Ahorro (Mes)", f"S/ {m_bal:,.2f}", border=True)

st.divider()

# --- ÁREA DE TRABAJO (2 COLUMNAS) ---
col_izq, col_der = st.columns([1, 2], gap="large")

# === IZQUIERDA: FORMULARIO ===
with col_izq:
    st.subheader("📝 Registrar Operación")
    with st.container(border=True):
        tipo = st.radio("Tipo", ["Gasto", "Ingreso", "Transferencia"], horizontal=True)
        
        with st.form("form_operacion", clear_on_submit=True):
            usuario = st.selectbox("Usuario", ["Rodrigo", "Krys"])
            
            # Lógica dinámica de campos
            if tipo == "Transferencia":
                c_origen = st.selectbox("Desde", lista_cuentas)
                c_destino = st.selectbox("Hacia", lista_cuentas)
                categoria = "Transferencia"
                cuenta_final = c_origen # Referencia para el registro de salida
            else:
                cuenta_final = st.selectbox("Cuenta", lista_cuentas)
                if tipo == "Gasto":
                    categoria = st.selectbox("Categoría", list(presupuestos.keys()) + ["Otros", "Comida", "Taxi"])
                else:
                    categoria = st.selectbox("Categoría", ["Sueldo", "Negocio", "Regalo", "Otros"])
            
            monto = st.number_input("Monto (S/)", min_value=0.01, format="%.2f")
            desc = st.text_input("Descripción")
            
            # BOTÓN DE GUARDADO
            submitted = st.form_submit_button("💾 GUARDAR MOVIMIENTO", type="primary", use_container_width=True)
            
            if submitted:
                try:
                    fecha_str = datetime.now(zona_peru).strftime("%Y-%m-%d")
                    hora_str = datetime.now(zona_peru).strftime("%H:%M:%S")
                    
                    if tipo == "Transferencia":
                        if c_origen == c_destino:
                            st.error("¡Origen y destino son iguales!")
                        else:
                            # Salida
                            ws_registro.append_row([fecha_str, hora_str, usuario, c_origen, "Gasto", "Transferencia", monto, f"-> {c_destino}: {desc}"])
                            # Entrada
                            ws_registro.append_row([fecha_str, hora_str, usuario, c_destino, "Ingreso", "Transferencia", monto, f"<- {c_origen}: {desc}"])
                            limpiar_cache()
                            st.success("✅ Transferencia realizada")
                            time.sleep(1)
                            st.rerun()
                    else:
                        ws_registro.append_row([fecha_str, hora_str, usuario, cuenta_final, tipo, categoria, monto, desc])
                        limpiar_cache()
                        st.success("✅ Operación registrada")
                        time.sleep(1)
                        st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

# === DERECHA: PANELES DE INFORMACIÓN ===
with col_der:
    # 1. CUENTAS
    c_head, c_btn1, c_btn2 = st.columns([2, 1, 1])
    c_head.subheader("💳 Estado de Cuentas")
    if c_btn1.button("➕ Nueva Cuenta"): pop_agregar_cuenta()
    if c_btn2.button("🗑️ Borrar Cuenta"): pop_eliminar_cuenta(lista_cuentas)
    
    # Grid de cuentas (usando metrics nativos)
    cols = st.columns(3)
    for i, (cta, saldo) in enumerate(saldos_por_cuenta.items()):
        with cols[i % 3]:
            st.metric(label=cta, value=f"S/ {saldo:,.2f}", border=True)
    
    st.write("") # Espacio
    
    # 2. METAS
    st.subheader("🎯 Metas del Mes")
    if not df_mes.empty:
        gastos_por_cat = df_mes[df_mes['Tipo'] == 'Gasto'].groupby('Categoria')['Monto'].sum()
    else:
        gastos_por_cat = {}
        
    for cat, tope in presupuestos.items():
        real = gastos_por_cat.get(cat, 0.0)
        # Calcular porcentaje seguro
        pct = min(real / tope, 1.0) if tope > 0 else 0
        
        col_bar, col_txt = st.columns([3, 1])
        with col_bar:
            st.progress(pct, text=cat)
        with col_txt:
            st.caption(f"S/ {real:.0f} / {tope}")

st.divider()

# --- PIE: HISTORIAL ---
st.subheader("📜 Historial de Movimientos")
with st.expander("Ver tabla de datos", expanded=True):
    if not df_mes.empty:
        # Mostramos columnas clave
        st.dataframe(
            df_mes[['Fecha', 'Cuenta', 'Tipo', 'Categoria', 'Monto', 'Descripcion']].sort_values('Fecha', ascending=False),
            use_container_width=True,
            hide_index=True
        )
        # Botón de borrado de emergencia
        if st.button("⚠️ Borrar último registro (No hay vuelta atrás)"):
            rows = len(ws_registro.get_all_values())
            if rows > 1:
                ws_registro.delete_rows(rows)
                limpiar_cache()
                st.warning("Registro borrado.")
                time.sleep(1)
                st.rerun()
    else:
        st.info("No hay movimientos registrados en este mes.")
