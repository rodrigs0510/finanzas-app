import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import pytz 

# --- 1. CONFIGURACIÓN ---
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
    # Intentamos conectar con la nueva hoja, si no existe, avisamos
    try:
        ws_pendientes = sh.worksheet("Pendientes")
    except:
        st.error("⚠️ FALTA LA HOJA 'Pendientes' EN TU EXCEL. CREALA con columnas: Descripcion, Monto, FechaLimite")
        st.stop()
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
        time.sleep(1)
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
            
        df['Fila_Original'] = df.index + 2 
        
        # Limpieza
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

@st.cache_data(ttl=60)
def obtener_pendientes():
    cols = ['Descripcion', 'Monto', 'FechaLimite']
    try:
        data = intento_seguro(lambda: ws_pendientes.get_all_records())
        if not data: return pd.DataFrame(columns=cols + ['Fila_Original'])
        df = pd.DataFrame(data)
        
        # Guardar Fila Original para borrar bien
        df['Fila_Original'] = df.index + 2
        df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)
        return df
    except:
        return pd.DataFrame(columns=cols + ['Fila_Original'])

# --- ACCIONES DE BORRADO ---
def borrar_registro(fila):
    ws_registro.delete_rows(fila)
    limpiar_cache(); st.toast("Registro eliminado"); time.sleep(0.5); st.rerun()

def pagar_pendiente(fila):
    ws_pendientes.delete_rows(fila)
    limpiar_cache(); st.toast("✅ ¡Pago Registrado/Eliminado!"); time.sleep(0.5); st.rerun()

# --- 4. VENTANAS EMERGENTES (POPUPS) ---
@st.dialog("➕ Nueva Cuenta")
def dialog_cuenta():
    n = st.text_input("Nombre del Banco")
    if st.button("Guardar"):
        ws_cuentas.append_row([n])
        limpiar_cache(); st.rerun()

@st.dialog("🗑️ Eliminar Cuenta")
def dialog_borrar_cuenta(lista):
    s = st.selectbox("Elegir cuenta", lista)
    if st.button("Confirmar Eliminación"):
        cell = ws_cuentas.find(s)
        ws_cuentas.delete_rows(cell.row)
        limpiar_cache(); st.rerun()

@st.dialog("⏰ Agregar Gasto Pendiente")
def dialog_agregar_pendiente():
    desc = st.text_input("Descripción (Ej: Luz del Sur)")
    monto = st.number_input("Monto a Pagar (S/)", min_value=0.01)
    fecha = st.date_input("Fecha Límite")
    
    if st.button("Agendar Pago"):
        ws_pendientes.append_row([desc, monto, str(fecha)])
        limpiar_cache()
        st.success("Agendado")
        time.sleep(1)
        st.rerun()

# --- 5. INTERFAZ OPERATIVA (SECCIONES) ---
zona_peru = pytz.timezone('America/Lima')
df = obtener_datos()
df_pendientes = obtener_pendientes()
lista_cuentas = obtener_cuentas()
presupuestos = obtener_presupuestos()

# Header y Filtros
st.title("💰 CAPIGASTOS: Panel de Control")
top1, top2, top3, top4 = st.columns(4)

# Cálculos Totales
saldo_global = (df[df['Tipo']=='Ingreso']['Monto'].sum() - df[df['Tipo']=='Gasto']['Monto'].sum())
ahorro_hist = saldo_global # Simplificado

top1.metric("Saldo Total Disponible", f"S/ {saldo_global:,.2f}")
top2.metric("Ahorro Histórico", f"S/ {ahorro_hist:,.2f}")

meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
hoy = datetime.now(zona_peru)
sel_mes = top3.selectbox("Mes", meses, index=hoy.month-1)
sel_anio = top4.number_input("Año", value=hoy.year)
idx_mes = meses.index(sel_mes) + 1

# Filtrado de Datos Mensuales
if not df.empty:
    df_mes = df[(df['Fecha'].dt.month == idx_mes) & (df['Fecha'].dt.year == sel_anio)]
else: df_mes = df

st.divider()

# --- BLOQUE 1: CONSOLIDADO ---
with st.container(border=True):
    st.subheader(f"📊 Resumen: {sel_mes} {sel_anio}")
    mi = df_mes[df_mes['Tipo']=='Ingreso']['Monto'].sum()
    mg = df_mes[df_mes['Tipo']=='Gasto']['Monto'].sum()
    c1, c2, c3 = st.columns(3)
    c1.metric("Ingresos", f"S/ {mi:,.2f}")
    c2.metric("Gastos", f"S/ {mg:,.2f}")
    c3.metric("Balance Mes", f"S/ {mi-mg:,.2f}")

st.write("") 

# --- BLOQUE 2: ZONA DE TRABAJO ---
col_izq, col_der = st.columns([1, 1.5], gap="medium")

# LADO IZQUIERDO: FORMULARIO
with col_izq:
    with st.container(border=True):
        st.subheader("📝 Registrar Operación")
        tipo = st.radio("Acción", ["Gasto", "Ingreso", "Transferencia"], horizontal=True)
        usuario = st.selectbox("Usuario", ["Rodrigo", "Krys"])
        
        if tipo == "Transferencia":
            c_ori = st.selectbox("Desde", lista_cuentas)
            c_des = st.selectbox("Hacia", lista_cuentas)
            cta = c_ori; cat = "Transferencia"
        else:
            cta = st.selectbox("Cuenta", lista_cuentas)
            if tipo == "Gasto":
                cat = st.selectbox("Categoría", list(presupuestos.keys()) + ["Otros", "Comida"])
            else:
                cat = st.selectbox("Categoría", ["Sueldo", "Negocio", "Otros"])
        
        monto = st.number_input("Monto S/", min_value=0.01)
        desc = st.text_input("Detalle")
        
        if st.button("GUARDAR MOVIMIENTO", type="primary", use_container_width=True):
            f_str = datetime.now(zona_peru).strftime("%Y-%m-%d")
            h_str = datetime.now(zona_peru).strftime("%H:%M:%S")
            try:
                if tipo == "Transferencia":
                    if c_ori == c_des: st.error("Cuentas iguales")
                    else:
                        ws_registro.append_row([f_str, h_str, usuario, c_ori, "Gasto", "Transferencia", monto, f"-> {c_des}: {desc}"])
                        ws_registro.append_row([f_str, h_str, usuario, c_des, "Ingreso", "Transferencia", monto, f"<- {c_ori}: {desc}"])
                        limpiar_cache(); st.success("Transferencia OK"); time.sleep(1); st.rerun()
                else:
                    ws_registro.append_row([f_str, h_str, usuario, cta, tipo, cat, monto, desc])
                    limpiar_cache(); st.success("Registrado"); time.sleep(1); st.rerun()
            except Exception as e: st.error(f"Error: {e}")

# LADO DERECHO: CUENTAS Y METAS
with col_der:
    # 1. CUENTAS
    with st.container(border=True):
        h1, h2, h3 = st.columns([3, 1, 1])
        h1.subheader("💳 Cuentas")
        if h2.button("➕"): dialog_cuenta()
        if h3.button("🗑️"): dialog_borrar_cuenta(lista_cuentas)
        
        # Saldos individuales
        cs = st.columns(3)
        for i, c in enumerate(lista_cuentas):
            i_c = df[(df['Cuenta']==c)&(df['Tipo']=='Ingreso')]['Monto'].sum()
            g_c = df[(df['Cuenta']==c)&(df['Tipo']=='Gasto')]['Monto'].sum()
            cs[i%3].metric(c, f"S/ {i_c - g_c:,.2f}")

    st.write("")
    
    # 2. METAS (RESTAURADO)
    with st.container(border=True):
        st.subheader("🎯 Metas del Mes")
        if not df_mes.empty:
            gastos_cat = df_mes[df_mes['Tipo']=='Gasto'].groupby('Categoria')['Monto'].sum()
        else: gastos_cat = {}
        
        # Mostramos en 2 columnas
        mc1, mc2 = st.columns(2)
        idx = 0
        for cat, tope in presupuestos.items():
            real = gastos_cat.get(cat, 0)
            pct = min(real/tope, 1.0) if tope > 0 else 0
            
            with (mc1 if idx % 2 == 0 else mc2):
                st.write(f"**{cat}**")
                st.progress(pct)
                st.caption(f"{real:,.0f} / {tope}")
            idx += 1

st.write("")

# --- BLOQUE 3: HISTORIAL Y PENDIENTES ---
col_hist, col_pend = st.columns([1.5, 1], gap="medium")

# 1. HISTORIAL (IZQUIERDA)
with col_hist:
    with st.container(border=True):
        st.subheader("📜 Historial Movimientos")
        if not df_mes.empty:
            # Ordenar y mostrar
            df_show = df_mes.sort_values('Fecha', ascending=False)
            
            # Cabeceras
            c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 3, 1])
            c1.markdown("**Fecha**")
            c2.markdown("**Cuenta**")
            c3.markdown("**Monto**")
            c4.markdown("**Detalle**")
            c5.markdown("**X**")
            st.divider()
            
            for idx, row in df_show.iterrows():
                cc1, cc2, cc3, cc4, cc5 = st.columns([2, 2, 2, 3, 1])
                cc1.write(row['Fecha'].strftime("%d/%m"))
                cc2.caption(row['Cuenta'])
                color = "green" if row['Tipo'] == 'Ingreso' else "red"
                cc3.markdown(f":{color}[{row['Monto']}]")
                cc4.caption(f"{row['Categoria']} - {row['Descripcion']}")
                
                # BOTON ELIMINAR REGISTRO INDIVIDUAL
                fila_real = row['Fila_Original']
                if cc5.button("🗑️", key=f"del_mov_{fila_real}"):
                    borrar_registro(fila_real)
        else:
            st.info("Sin movimientos este mes")

# 2. GASTOS PENDIENTES (DERECHA - NUEVA FUNCIONALIDAD)
with col_pend:
    with st.container(border=True):
        # Cabecera con botón de agregar
        ph1, ph2 = st.columns([3, 1])
        ph1.subheader("⏰ Pendientes")
        if ph2.button("➕ Nuevo"): dialog_agregar_pendiente()
        
        st.divider()
        
        if not df_pendientes.empty:
            for idx, row in df_pendientes.iterrows():
                # Layout de cada pendiente: Info | Boton Pagar
                pc1, pc2 = st.columns([3, 1])
                
                with pc1:
                    st.write(f"**{row['Descripcion']}**")
                    st.caption(f"Monto: S/ {row['Monto']} | Vence: {row['FechaLimite']}")
                
                with pc2:
                    # BOTON PAGADO
                    fila_pend = row['Fila_Original']
                    if st.button("✅ PAGADO", key=f"pay_{fila_pend}"):
                        pagar_pendiente(fila_pend)
                st.divider()
        else:
            st.info("¡Estás al día! No hay deudas pendientes.")
