import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Finanzas R&K", layout="centered")

# --- CONEXIÓN A GOOGLE SHEETS (El "Backend") ---
# Usamos @st.cache_resource para que no se reconecte cada vez que tocas un botón (ahorra datos)
@st.cache_resource
def conectar_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # LÓGICA HÍBRIDA:
    # 1. Si existe el "baúl de secretos" (Nube), usa eso.
    # 2. Si no, busca el archivo local (Tu PC).
    
    if "gcp_service_account" in st.secrets:
        # Estamos en la Nube
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    else:
        # Estamos en local
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        
    client = gspread.authorize(creds)
    sheet = client.open("Finanzas_RodrigoKrys")
    return sheet

# ---------------------------------------------------
try:
    sh = conectar_google_sheets()
    # Conectamos con las pestañas específicas
    ws_registro = sh.worksheet("Registro")
    ws_cuentas = sh.worksheet("Cuentas")
except Exception as e:
    st.error(f"Error de conexión: {e}")
    st.stop()

# --- FUNCIONES DE LECTURA DE DATOS ---
def obtener_datos():
    # Baja todos los datos de la hoja 'Registro' a un DataFrame de Pandas
    data = ws_registro.get_all_records()
    if not data:
        return pd.DataFrame(columns=['Fecha', 'Hora', 'Usuario', 'Cuenta', 'Tipo', 'Categoria', 'Monto', 'Descripcion'])
    return pd.DataFrame(data)

def obtener_cuentas():
    # Baja las cuentas de la hoja 'Cuentas'
    cuentas_raw = ws_cuentas.col_values(1) # Asume que los nombres están en la columna A
    if len(cuentas_raw) > 1:
        return cuentas_raw[1:] # Saltamos el encabezado
    return ["Efectivo (Default)"]

# --- INTERFAZ GRÁFICA ---
st.title("💸 Finanzas Rodrigo & Krys (Nube)")

# Cargar datos frescos de la nube
df = obtener_datos()

# Asegurar que la columna Monto sea numérica (a veces Google Sheets la manda como texto)
if not df.empty:
    df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)

# --- MÉTRICAS ---
st.divider()
total_ingresos = df[df['Tipo'] == 'Ingreso']['Monto'].sum() if not df.empty else 0
total_gastos = df[df['Tipo'] == 'Gasto']['Monto'].sum() if not df.empty else 0
saldo = total_ingresos - total_gastos

c1, c2, c3 = st.columns(3)
c1.metric("Ingresos", f"S/ {total_ingresos:.2f}")
c2.metric("Gastos", f"S/ {total_gastos:.2f}")
c3.metric("Saldo Total", f"S/ {saldo:.2f}")

# --- FORMULARIO DE REGISTRO ---
st.subheader("📝 Nuevo Movimiento")

with st.form("formulario_nube", clear_on_submit=True):
    col1, col2 = st.columns(2)
    usuario = col1.selectbox("Usuario", ["Rodrigo", "Krys"])
    tipo = col2.radio("Tipo", ["Gasto", "Ingreso"], horizontal=True)
    
    monto = st.number_input("Monto (S/)", min_value=0.0, step=1.0, format="%.2f")
    
    # Cargar cuentas desde la hoja 'Cuentas'
    lista_cuentas = obtener_cuentas()
    cuenta = st.selectbox("Cuenta Afectada", lista_cuentas)
    
    categoria = st.selectbox("Categoría", ["Comida", "Transporte", "Servicios", "Citas", "Universidad", "Otros"])
    desc = st.text_input("Descripción", placeholder="Ej: Taxi a casa")
    
    enviar = st.form_submit_button("Guardar en la Nube")
    
    if enviar:
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        hora_hoy = datetime.now().strftime("%H:%M:%S")
        
        # Lista de datos a insertar (Mismo orden que tus columnas en Sheets)
        nueva_fila = [fecha_hoy, hora_hoy, usuario, cuenta, tipo, categoria, monto, desc]
        
        # ¡Aquí ocurre la magia! Escribe en el Excel de Google
        ws_registro.append_row(nueva_fila)
        
        st.success("¡Guardado correctamente en Google Sheets!")
        # Recargamos la app para que se actualice la tabla y el saldo
        st.rerun()

# --- HISTORIAL ---
st.subheader("📜 Historial en Tiempo Real")
if not df.empty:
    # Mostramos los más recientes primero
    st.dataframe(df.sort_values(by="Fecha", ascending=False), use_container_width=True)
else:
    st.info("La base de datos está vacía. ¡Haz tu primer registro!")