import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import pytz 

# --- 1. CONFIGURACIÓN (NATIVA) ---
st.set_page_config(page_title="CAPIGASTOS", layout="wide", page_icon="💰")

# --- 2. CONEXIÓN ---
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

# --- 3. FUNCIONES LÓGICAS ---
def limpiar_cache():
    st.cache_data.clear()

def intento_seguro(funcion):
    try:
        return funcion()
    except Exception:
        time.sleep(2)
        return funcion()

@st.cache_data(ttl=60)
def obtener_datos():
    cols = ['Fecha', 'Hora', 'Usuario', 'Cuenta', 'Tipo', 'Categoria', 'Monto', 'Descripcion']
    try:
        data = intento_seguro(lambda: ws_registro.get_all_records())
        if not data: return pd.DataFrame(columns=cols + ['Fila_Original'])
        
        df = pd.DataFrame(data)
        for c in cols:
            if c not in df.columns: df[c] = ""
            
        # GUARDAR ÍNDICE ORIGINAL (Para borrar correctamente)
        df['Fila_Original'] = df.index + 2 
        
        # Limpieza de datos
        df['Monto'] = df['Monto'].astype(str).str.replace(',', '', regex=False)
        df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)
        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
        return df.dropna(subset=['Fecha'])
    except:
        return pd.DataFrame(columns=cols + ['Fila_Original'])

@st.cache_data(ttl=600)
def obtener_cuentas():
    try:
        l = intento_seguro(lambda: ws_cuentas.col_values(1))
        return l[1:] if len(l) > 1 else ["Efectivo"]
    except: return ["Efectivo"]

@st.cache_data(ttl=600)
def obtener_presupuestos():
    try:
        d = intento_seguro(lambda: ws_presupuestos.get_all_records())
        return {r['Categoria']: r['Tope_Mensual'] for r in d}
    except: return {}

# --- FUNCIÓN DE BORRADO ---
def borrar_fila(fila_excel):
    try:
        ws_registro.delete_rows(fila_excel)
        limpiar_cache()
        st.success("✅ Registro eliminado.")
        time.sleep(1)
        st.rerun()
    except Exception as e:
        st.error(f"Error borrando: {e}")

# --- 4. VENTANAS EMERGENTES (NATIVAS) ---
@st.dialog("Nueva Cuenta")
def dialog_cuenta():
    n = st.text_input("Nombre")
    if st.button("Guardar"):
        ws_cuentas.append_row([n])
        limpiar_cache(); st.rerun()

@st.dialog("Borrar Cuenta")
def dialog_borrar_cuenta(lista):
    s = st.selectbox("Elegir", lista)
    if st.button("Confirmar"):
        cell = ws_cuentas.find(s)
        ws_cuentas.delete_rows(cell.row)
        limpiar_cache(); st.rerun()

# --- 5. INTERFAZ (SIN CSS) ---
zona_peru = pytz.timezone('America/Lima')
df = obtener_datos()
lista_cuentas = obtener_cuentas()
presupuestos = obtener_presupuestos()

# Cálculos
ing_t = df[df['Tipo']=='Ingreso']['Monto'].sum()
gas_t = df[df['Tipo']=='Gasto']['Monto'].sum()
saldo_global = ing_t - gas_t

# Header
st.title("CAPIGASTOS (Modo Operativo)")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Saldo Total", f"S/ {saldo_global:,.2f}")
k2.metric("Ahorro Histórico", f"S/ {ing_t - gas_t:,.2f}")

# Filtros
meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
hoy = datetime.now(zona_peru)
sel_mes = k3.selectbox("Mes", meses, index=hoy.month-1)
sel_anio = k4.number_input("Año", value=hoy.year)
idx_mes = meses.index(sel_mes) + 1

st.divider()

# Filtrado Mes
if not df.empty:
    df_mes = df[(df['Fecha'].dt.month == idx_mes) & (df['Fecha'].dt.year == sel_anio)]
else:
    df_mes = df

# Métricas Mes
mi = df_mes[df_mes['Tipo']=='Ingreso']['Monto'].sum()
mg = df_mes[df_mes['Tipo']=='Gasto']['Monto'].sum()
mb = mi - mg

c1, c2, c3 = st.columns(3)
c1.metric("Ingresos Mes", f"S/ {mi:,.2f}")
c2.metric("Gastos Mes", f"S/ {mg:,.2f}")
c3.metric("Balance Mes", f"S/ {mb:,.2f}")

st.divider()

# CUERPO PRINCIPAL
col_izq, col_der = st.columns([1, 2])

# --- FORMULARIO ---
with col_izq:
    st.header("📝 Registro")
    with st.container(border=True):
        tipo = st.radio("Operación", ["Gasto", "Ingreso", "Transferencia"])
        usuario = st.selectbox("Usuario", ["Rodrigo", "Krys"])
        
        if tipo == "Transferencia":
            origen = st.selectbox("Desde", lista_cuentas)
            destino = st.selectbox("Hacia", lista_cuentas)
            cuenta_final = origen
            categoria = "Transferencia"
        else:
            cuenta_final = st.selectbox("Cuenta", lista_cuentas)
            if tipo == "Gasto":
                categoria = st.selectbox("Categoría", list(presupuestos.keys()) + ["Otros", "Comida"])
            else:
                categoria = st.selectbox("Categoría", ["Sueldo", "Negocio", "Otros"])
        
        monto = st.number_input("Monto", min_value=0.01)
        desc = st.text_input("Detalle")
        
        if st.button("GUARDAR", type="primary", use_container_width=True):
            fecha = datetime.now(zona_peru).strftime("%Y-%m-%d")
            hora = datetime.now(zona_peru).strftime("%H:%M:%S")
            try:
                if tipo == "Transferencia":
                    r1 = [fecha, hora, usuario, origen, "Gasto", "Transferencia", monto, f"-> {destino}: {desc}"]
                    r2 = [fecha, hora, usuario, destino, "Ingreso", "Transferencia", monto, f"<- {origen}: {desc}"]
                    ws_registro.append_row(r1); ws_registro.append_row(r2)
                else:
                    ws_registro.append_row([fecha, hora, usuario, cuenta_final, tipo, categoria, monto, desc])
                
                limpiar_cache()
                st.success("Guardado")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

# --- PANELES ---
with col_der:
    # CUENTAS
    c_head, c_btn = st.columns([3, 1])
    c_head.subheader("💳 Cuentas")
    if c_btn.button("Gestionar Cuentas"): dialog_cuenta()
    
    # Saldos
    cols_saldos = st.columns(3)
    for i, c in enumerate(lista_cuentas):
        ing_c = df[(df['Cuenta']==c) & (df['Tipo']=='Ingreso')]['Monto'].sum()
        gas_c = df[(df['Cuenta']==c) & (df['Tipo']=='Gasto')]['Monto'].sum()
        with cols_saldos[i%3]:
            st.metric(c, f"S/ {ing_c - gas_c:,.2f}", border=True)
            
    st.divider()
    
    # HISTORIAL INTERACTIVO
    st.subheader("📜 Historial (Con Borrado)")
    
    if not df_mes.empty:
        # Mostramos lista manual para poner botón
        # Ordenamos reciente primero
        df_show = df_mes.sort_values('Fecha', ascending=False)
        
        # Encabezados simples
        h1, h2, h3, h4, h5 = st.columns([2, 2, 2, 3, 1])
        h1.markdown("**Fecha**")
        h2.markdown("**Cuenta**")
        h3.markdown("**Monto**")
        h4.markdown("**Detalle**")
        h5.markdown("**X**")
        
        for idx, row in df_show.iterrows():
            c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 3, 1])
            c1.write(row['Fecha'].strftime("%d/%m"))
            c2.write(row['Cuenta'])
            c3.write(f"S/ {row['Monto']}")
            c4.write(f"{row['Categoria']} - {row['Descripcion']}")
            
            # BOTÓN BORRAR POR FILA
            # Usamos la Fila_Original para saber qué borrar en Excel
            fila_real = row['Fila_Original']
            if c5.button("🗑️", key=f"btn_{fila_real}"):
                borrar_fila(fila_real)
            
            st.markdown("---") # Separador
    else:
        st.info("No hay datos en este mes.")
