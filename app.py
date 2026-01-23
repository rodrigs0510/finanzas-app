import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import calendar # Nueva librería para manejar nombres de meses

# --- CONFIGURACIÓN ESTÉTICA ---
st.set_page_config(page_title="Finanzas R&K", layout="centered", page_icon="💰")

# --- CONEXIÓN A GOOGLE SHEETS ---
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
    st.error(f"Error de conexión: {e}")
    st.stop()

# --- FUNCIONES DE LECTURA ---
def obtener_datos():
    data = ws_registro.get_all_records()
    if not data:
        return pd.DataFrame(columns=['Fecha', 'Hora', 'Usuario', 'Cuenta', 'Tipo', 'Categoria', 'Monto', 'Descripcion'])
    df = pd.DataFrame(data)
    df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)
    df['Fecha'] = pd.to_datetime(df['Fecha'], format="%Y-%m-%d", errors='coerce') 
    return df

def obtener_cuentas():
    cuentas = ws_cuentas.col_values(1)
    return cuentas[1:] if len(cuentas) > 1 else ["Efectivo"]

def obtener_presupuestos():
    records = ws_presupuestos.get_all_records()
    presupuestos = {row['Categoria']: row['Tope_Mensual'] for row in records}
    return presupuestos

# --- BARRA LATERAL (CONFIGURACIÓN) ---
with st.sidebar:
    st.header("⚙️ Configuración")
    
    with st.expander("➕ Agregar Nueva Cuenta"):
        nueva_cuenta = st.text_input("Nombre cuenta nueva")
        if st.button("Crear Cuenta"):
            if nueva_cuenta:
                ws_cuentas.append_row([nueva_cuenta])
                st.success(f"Cuenta {nueva_cuenta} creada.")
                st.rerun()

    with st.expander("🎯 Agregar Nuevo Presupuesto"):
        nueva_cat = st.text_input("Nombre Categoría")
        nuevo_tope = st.number_input("Tope Mensual", min_value=0)
        if st.button("Crear Presupuesto"):
            if nueva_cat:
                ws_presupuestos.append_row([nueva_cat, nuevo_tope])
                st.success(f"Categoría {nueva_cat} creada.")
                st.rerun()

# --- TÍTULO Y SELECTOR DE TIEMPO (LO NUEVO) ---
st.title("💰 Finanzas Rodrigo & Krys")

# Cargamos datos una sola vez
df = obtener_datos()

# Contenedor para elegir FECHA
with st.container(border=True):
    col_f1, col_f2 = st.columns(2)
    
    # Nombres de meses en español
    meses_es = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    
    mes_actual = datetime.now().month
    anio_actual = datetime.now().year

    # Selectores (Por defecto muestra el mes actual)
    mes_seleccionado_nombre = col_f1.selectbox("📅 Seleccionar Mes", meses_es, index=mes_actual-1)
    anio_seleccionado = col_f2.number_input("Seleccionar Año", min_value=2024, max_value=2030, value=anio_actual, step=1)

    # Convertir nombre de mes a número (Enero = 1)
    mes_seleccionado_idx = meses_es.index(mes_seleccionado_nombre) + 1

# --- LÓGICA DE FILTRADO ---
# 1. Datos del MES ELEGIDO (Para presupuestos y reporte mensual)
df_filtrado = df[
    (df['Fecha'].dt.month == mes_seleccionado_idx) & 
    (df['Fecha'].dt.year == anio_seleccionado)
]

# 2. Datos TOTALES (Para calcular saldo real actual de cuentas)
# (Las cuentas no dependen del mes, sino de todo el historial)
saldos = {}
lista_cuentas = obtener_cuentas()
for c in lista_cuentas:
    ing = df[(df['Cuenta'] == c) & (df['Tipo'] == 'Ingreso')]['Monto'].sum()
    gas = df[(df['Cuenta'] == c) & (df['Tipo'] == 'Gasto')]['Monto'].sum()
    saldos[c] = ing - gas
capital_total_actual = sum(saldos.values())

# --- BLOQUE 1: RESUMEN DEL MES ELEGIDO ---
st.subheader(f"📊 Resumen de {mes_seleccionado_nombre} {anio_seleccionado}")

# Cálculos del mes
ingreso_mes = df_filtrado[df_filtrado['Tipo'] == 'Ingreso']['Monto'].sum()
gasto_mes = df_filtrado[df_filtrado['Tipo'] == 'Gasto']['Monto'].sum()
balance_mes = ingreso_mes - gasto_mes

m1, m2, m3 = st.columns(3)
m1.metric("Ingresos (Mes)", f"S/ {ingreso_mes:.2f}")
m2.metric("Gastos (Mes)", f"S/ {gasto_mes:.2f}", delta_color="inverse")
# El balance muestra cuánto "sobró" o "faltó" ese mes específico
m3.metric("Ahorro del Mes", f"S/ {balance_mes:.2f}", 
          delta=f"{(balance_mes/ingreso_mes)*100:.0f}% Ahorrado" if ingreso_mes > 0 else None)

st.divider()

# --- BLOQUE 2: CAPITAL REAL (CUENTAS) ---
# Esto siempre muestra la realidad actual, independiente del mes que mires
st.subheader(f"💳 Saldos Actuales (Total Disponible: S/ {capital_total_actual:.2f})")

cols_c = st.columns(3)
idx_c = 0
for cuenta, saldo in saldos.items():
    with cols_c[idx_c % 3]:
        with st.container(border=True):
            st.write(f"**{cuenta}**")
            if saldo >= 0:
                st.metric("Saldo", f"S/ {saldo:.2f}")
                pct = (saldo / capital_total_actual) if capital_total_actual > 0 else 0
                st.progress(min(max(pct, 0.0), 1.0))
            else:
                st.metric("Saldo", f"S/ {saldo:.2f}", delta="Deuda", delta_color="inverse")
    idx_c += 1

st.divider()

# --- BLOQUE 3: PRESUPUESTOS (Dinámicos según Mes Elegido) ---
st.subheader(f"🚦 Control de Gastos: {mes_seleccionado_nombre}")
presupuestos_dict = obtener_presupuestos()
# Agrupamos gastos solo del mes seleccionado
gastos_cat = df_filtrado[df_filtrado['Tipo'] == 'Gasto'].groupby('Categoria')['Monto'].sum()

cols_p = st.columns(2)
idx_p = 0
for cat, tope in presupuestos_dict.items():
    gastado = gastos_cat.get(cat, 0)
    pct = (gastado / tope) if tope > 0 else 0
    
    with cols_p[idx_p % 2]:
        st.write(f"**{cat}**")
        st.progress(min(pct, 1.0))
        st.caption(f"S/ {gastado:.1f} / S/ {tope} ({pct*100:.0f}%)")
        if pct >= 1: st.error("¡Límite excedido!")
    idx_p += 1

st.divider()

# --- BLOQUE 4: NUEVA OPERACIÓN ---
st.subheader("📝 Registrar Operación (Tiempo Real)")
tipo_op = st.radio("Acción", ["Gasto 📤", "Ingreso 📥", "Transferencia 🔄"], horizontal=True)

with st.form("main_form", clear_on_submit=True):
    c1, c2 = st.columns(2)
    user = c1.selectbox("Usuario", ["Rodrigo", "Krys"])
    
    if tipo_op == "Transferencia 🔄":
        st.info("Mover dinero entre cuentas")
        cta_origen = c2.selectbox("Desde", lista_cuentas)
        cta_destino = st.selectbox("Hacia", lista_cuentas)
        cat = "Transferencia"
    else:
        cta = c2.selectbox("Cuenta", lista_cuentas)
        if tipo_op == "Gasto 📤":
            # Unimos las categorías de presupuesto con "Otros"
            cat = st.selectbox("Categoría", list(presupuestos_dict.keys()) + ["Otros"])
        else:
            cat = st.selectbox("Categoría", ["Sueldo", "Negocio", "Regalo", "Otros"])

    monto = st.number_input("Monto", min_value=0.01, format="%.2f")
    desc = st.text_input("Descripción")
    
    if st.form_submit_button("Registrar"):
        # Usamos fecha y hora actuales del servidor
        fecha = datetime.now().strftime("%Y-%m-%d")
        hora = datetime.now().strftime("%H:%M:%S")
        
        if tipo_op == "Transferencia 🔄":
            if cta_origen == cta_destino:
                st.error("Origen y Destino son iguales")
            else:
                r1 = [fecha, hora, user, cta_origen, "Gasto", "Transferencia/Salida", monto, f"A {cta_destino}: {desc}"]
                r2 = [fecha, hora, user, cta_destino, "Ingreso", "Transferencia/Entrada", monto, f"De {cta_origen}: {desc}"]
                ws_registro.append_row(r1)
                ws_registro.append_row(r2)
                st.success("Transferencia exitosa")
                st.rerun()
        else:
            tipo_real = "Gasto" if "Gasto" in tipo_op else "Ingreso"
            row = [fecha, hora, user, cta, tipo_real, cat, monto, desc]
            ws_registro.append_row(row)
            st.success("Registrado")
            st.rerun()

# --- BLOQUE 5: ELIMINACIÓN ---
with st.expander("🗑️ Eliminar Registros"):
    st.dataframe(df.sort_values(by="Fecha", ascending=False).head(5), use_container_width=True)
    if st.button("BORRAR ÚLTIMO MOVIMIENTO"):
        total_rows = len(ws_registro.get_all_values())
        if total_rows > 1:
            ws_registro.delete_rows(total_rows)
            st.success("Borrado. Actualizando...")
            st.rerun()
        else:
            st.warning("Nada que borrar")
