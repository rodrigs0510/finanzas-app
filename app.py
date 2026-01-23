import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
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
    ws_presupuestos = sh.worksheet("Presupuestos") # ¡Nueva conexión!
except Exception as e:
    st.error(f"Error de conexión: {e}")
    st.stop()

# --- FUNCIONES DE DATOS ---
def obtener_datos():
    data = ws_registro.get_all_records()
    if not data:
        return pd.DataFrame(columns=['Fecha', 'Hora', 'Usuario', 'Cuenta', 'Tipo', 'Categoria', 'Monto', 'Descripcion'])
    df = pd.DataFrame(data)
    # Convertir Monto a número y Fecha a datetime
    df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)
    df['Fecha'] = pd.to_datetime(df['Fecha'])
    return df

def obtener_cuentas():
    cuentas = ws_cuentas.col_values(1)
    return cuentas[1:] if len(cuentas) > 1 else ["Efectivo"]

def obtener_presupuestos():
    # Devuelve un diccionario: {'Comida': 400, 'Transporte': 150...}
    records = ws_presupuestos.get_all_records()
    presupuestos = {row['Categoria']: row['Tope_Mensual'] for row in records}
    return presupuestos

# --- INTERFAZ: DASHBOARD PRINCIPAL ---
st.title("💰 Finanzas Inteligentes R&K")

df = obtener_datos()

# Filtrar SOLO mes actual para los cálculos
mes_actual = datetime.now().month
anio_actual = datetime.now().year
df_mes = df[(df['Fecha'].dt.month == mes_actual) & (df['Fecha'].dt.year == anio_actual)]

# Métricas Globales del Mes
ingresos_mes = df_mes[df_mes['Tipo'] == 'Ingreso']['Monto'].sum()
gastos_mes = df_mes[df_mes['Tipo'] == 'Gasto']['Monto'].sum()
ahorro_mes = ingresos_mes - gastos_mes

c1, c2, c3 = st.columns(3)
c1.metric("Ingresos (Mes)", f"S/ {ingresos_mes:.2f}")
c2.metric("Gastos (Mes)", f"S/ {gastos_mes:.2f}", delta_color="inverse") # Rojo si sube
c3.metric("Ahorro Neto", f"S/ {ahorro_mes:.2f}", delta=f"{(ahorro_mes/ingresos_mes)*100:.1f}%" if ingresos_mes > 0 else "0%")

st.divider()

# --- SECCIÓN DE ALERTAS Y PRESUPUESTOS (NUEVO) ---
st.subheader("📊 Control de Presupuestos (Alertas)")

presupuestos = obtener_presupuestos()
# Calcular gasto por categoría este mes
gastos_por_cat = df_mes[df_mes['Tipo'] == 'Gasto'].groupby('Categoria')['Monto'].sum()

# Crear grid de 2 columnas para las tarjetas
cols = st.columns(2)
idx = 0

for categoria, tope in presupuestos.items():
    gasto_real = gastos_por_cat.get(categoria, 0)
    porcentaje = (gasto_real / tope) if tope > 0 else 0
    
    # Definir color de alerta
    estado = "🟢 Bien"
    color_barra = "green"
    
    if porcentaje >= 1.0:
        estado = "🔴 ¡EXCEDIDO!"
        color_barra = "red"
    elif porcentaje >= 0.8:
        estado = "🟡 Cuidado"
        color_barra = "orange" # Streamlit usa yellow/orange auto, pero logicamente es advertencia

    # Mostrar tarjeta en la columna correspondiente
    with cols[idx % 2]:
        with st.container(border=True):
            st.write(f"**{categoria}**")
            st.progress(min(porcentaje, 1.0)) # La barra no puede pasar de 1.0 (100%)
            st.caption(f"{estado}: S/ {gasto_real:.0f} / S/ {tope} ({porcentaje*100:.0f}%)")
            
            if porcentaje >= 1.0:
                st.error(f"¡Te pasaste por S/ {gasto_real - tope:.2f}!")
    
    idx += 1

st.divider()

# --- FORMULARIO DE REGISTRO ---
with st.expander("➕ Registrar Nuevo Movimiento", expanded=False):
    with st.form("formulario_nube", clear_on_submit=True):
        col1, col2 = st.columns(2)
        usuario = col1.selectbox("Usuario", ["Rodrigo", "Krys"])
        tipo = col2.radio("Tipo", ["Gasto", "Ingreso"], horizontal=True)
        monto = st.number_input("Monto (S/)", min_value=0.01, step=1.0, format="%.2f")
        cuenta = st.selectbox("Cuenta", obtener_cuentas())
        # Cargamos categorías directo del presupuesto para mantener consistencia
        cat_opciones = list(presupuestos.keys()) + ["Otros", "Ingreso Extra"]
        categoria = st.selectbox("Categoría", cat_opciones)
        desc = st.text_input("Descripción")
        
        if st.form_submit_button("Guardar"):
            fecha = datetime.now().strftime("%Y-%m-%d")
            hora = datetime.now().strftime("%H:%M:%S")
            nueva_fila = [fecha, hora, usuario, cuenta, tipo, categoria, monto, desc]
            ws_registro.append_row(nueva_fila)
            st.success("Guardado")
            st.rerun()

# --- HISTORIAL ---
st.subheader("📜 Historial Reciente")
st.dataframe(df.sort_values(by="Fecha", ascending=False).head(10), use_container_width=True)
