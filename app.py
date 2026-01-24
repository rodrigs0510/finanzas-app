import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import base64
import pytz

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="CAPIGASTOS", layout="wide")

# --- 2. CSS DE ALTO CONTRASTE ---
def cargar_estilos(imagen_local):
    try:
        with open(imagen_local, "rb") as f:
            b64_img = base64.b64encode(f.read()).decode()
        
        st.markdown(f"""
        <style>
        /* FONDO GENERAL */
        .stApp {{
            background-image: url(data:image/jpg;base64,{b64_img});
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}

        /* TARJETAS BLANCAS SÓLIDAS (Para que se lea todo) */
        div[data-testid="stVerticalBlock"] > div > div {{
            background-color: #FFFFFF;
            border-radius: 12px;
            padding: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            border: 1px solid #E0E0E0;
        }}
        
        /* TÍTULO PRINCIPAL */
        h1 {{
            color: #FFFFFF !important;
            text-shadow: 3px 3px 0px #000000;
            font-weight: 900 !important;
            font-size: 3rem !important;
        }}

        /* TEXTOS INTERNOS -> NEGRO PURO */
        h2, h3, h4, p, span, div, label {{
            color: #000000 !important;
        }}
        
        /* BOTONES DE ACCIÓN */
        button {{
            border-radius: 8px !important;
            font-weight: bold !important;
        }}
        
        /* OCULTAR HEADER STREAMLIT */
        header {{visibility: hidden;}}
        </style>
        """, unsafe_allow_html=True)
    except: pass

cargar_estilos("fondo.jpg")

# --- 3. CONEXIÓN ---
@st.cache_resource
def conectar():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    if "gcp_service_account" in st.secrets:
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    return gspread.authorize(creds).open("Finanzas_RodrigoKrys")

def intento(func):
    try: return func()
    except: time.sleep(1)

try:
    sh = conectar()
    ws_reg = sh.worksheet("Registro")
    ws_cta = sh.worksheet("Cuentas")
    ws_pre = sh.worksheet("Presupuestos")
except:
    st.error("⚠️ Error de conexión. Recarga."); st.stop()

# --- 4. DATOS & CACHÉ ---
def limpiar(): st.cache_data.clear()

@st.cache_data(ttl=60)
def get_data():
    d = intento(lambda: ws_reg.get_all_records())
    if not d: return pd.DataFrame(columns=['ID','Fecha','Hora','Usuario','Cuenta','Tipo','Categoria','Monto','Descripcion'])
    df = pd.DataFrame(d)
    df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)
    df['Fecha_dt'] = pd.to_datetime(df['Fecha'], format="%Y-%m-%d", errors='coerce')
    df['ID_Fila'] = df.index + 2 # Guardamos la fila real de Excel
    return df

@st.cache_data(ttl=300)
def get_cuentas():
    return intento(lambda: ws_cta.col_values(1))[1:] or ["Efectivo"]

@st.cache_data(ttl=300)
def get_metas():
    return intento(lambda: ws_pre.get_all_records())

# --- 5. VENTANAS EMERGENTES (DIALOGS) ---
# Esta es la magia: Ventanas que saltan sobre la app

@st.dialog("➕ Agregar Nueva Cuenta")
def dialog_add_cuenta():
    nombre = st.text_input("Nombre de la cuenta (Ej: BCP Ahorros)")
    if st.button("Crear Cuenta"):
        if nombre:
            ws_cta.append_row([nombre])
            limpiar(); st.rerun()

@st.dialog("⚠️ Eliminar Cuenta")
def dialog_del_cuenta(nombre_cuenta):
    st.write(f"¿Estás seguro de eliminar **{nombre_cuenta}**?")
    st.warning("¡Esto no borrará el historial de gastos, solo la cuenta de la lista!")
    if st.button("Sí, Eliminar Definitivamente", type="primary"):
        cell = ws_cta.find(nombre_cuenta)
        ws_cta.delete_rows(cell.row)
        limpiar(); st.rerun()

@st.dialog("➕ Agregar Meta/Presupuesto")
def dialog_add_meta():
    cat = st.text_input("Nombre Categoría (Ej: Ropa)")
    tope = st.number_input("Presupuesto Mensual S/", min_value=0)
    if st.button("Crear Meta"):
        if cat:
            ws_pre.append_row([cat, tope])
            limpiar(); st.rerun()

@st.dialog("⚠️ Eliminar Meta")
def dialog_del_meta(nombre_meta):
    st.write(f"¿Borrar el presupuesto para **{nombre_meta}**?")
    if st.button("Sí, Borrar", type="primary"):
        cell = ws_pre.find(nombre_meta)
        ws_pre.delete_rows(cell.row)
        limpiar(); st.rerun()

@st.dialog("❌ Borrar Movimiento")
def dialog_del_movimiento(id_fila, descripcion, monto):
    st.write(f"¿Borrar el registro: **{descripcion}** (S/ {monto})?")
    if st.button("Confirmar Borrado", type="primary"):
        ws_reg.delete_rows(id_fila)
        limpiar(); st.rerun()

# --- 6. LÓGICA DE TIEMPO ---
pe_zone = pytz.timezone('America/Lima')
now = datetime.now(pe_zone)
df = get_data()

# --- 7. INTERFAZ: ENCABEZADO ---
c1, c2, c3 = st.columns([2, 1, 1.5])
with c1:
    st.markdown("<h1>CAPIGASTOS</h1>", unsafe_allow_html=True)
with c2:
    ahorro_vida = df[df['Tipo']=='Ingreso']['Monto'].sum() - df[df['Tipo']=='Gasto']['Monto'].sum()
    with st.container():
        st.metric("💰 Ahorro Total", f"S/ {ahorro_vida:,.2f}")
with c3:
    with st.container():
        cm, ca = st.columns(2)
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        sel_mes = cm.selectbox("Mes", meses, index=now.month-1, label_visibility="collapsed")
        sel_anio = ca.number_input("Año", value=now.year, label_visibility="collapsed")
        mes_idx = meses.index(sel_mes) + 1

# Filtrado
if not df.empty and 'Fecha_dt' in df.columns:
    df_f = df[(df['Fecha_dt'].dt.month == mes_idx) & (df['Fecha_dt'].dt.year == sel_anio)]
else: df_f = df

st.write("") # Espaciador

# --- 8. CUERPO PRINCIPAL (2 COLUMNAS) ---
col_L, col_R = st.columns([1, 2], gap="large")

# === IZQUIERDA: REGISTRO ===
with col_L:
    st.subheader("📝 Nuevo Registro")
    with st.container():
        op = st.radio("Acción", ["Gasto 📤", "Ingreso 📥", "Transferencia 🔄"], horizontal=True, label_visibility="collapsed")
        
        with st.form("frm_main", clear_on_submit=True):
            ctas = get_cuentas()
            metas = get_metas()
            cats = [m['Categoria'] for m in metas] + ["Otros", "Sueldo", "Regalo"]
            
            us = st.selectbox("Usuario", ["Rodrigo", "Krys"])
            
            if op == "Transferencia 🔄":
                c_or = st.selectbox("Desde", ctas)
                c_de = st.selectbox("Hacia", ctas)
                cat = "Transferencia"
                cta = c_or # Placeholder
            else:
                cta = st.selectbox("Cuenta", ctas)
                if "Gasto" in op: cat = st.selectbox("Categoría", cats)
                else: cat = st.selectbox("Fuente", ["Sueldo", "Negocio", "Regalo", "Otros"])
            
            monto = st.number_input("Monto S/", min_value=0.01, format="%.2f")
            desc = st.text_input("Descripción")
            
            if st.form_submit_button("💾 Guardar", use_container_width=True):
                fd = datetime.now(pe_zone).strftime("%Y-%m-%d")
                ft = datetime.now(pe_zone).strftime("%H:%M:%S")
                
                if op == "Transferencia 🔄":
                    if c_or == c_de: st.error("Misma cuenta")
                    else:
                        ws_reg.append_row([fd, ft, us, c_or, "Gasto", "Transferencia/Salida", monto, f"-> {c_de}: {desc}"])
                        ws_reg.append_row([fd, ft, us, c_de, "Ingreso", "Transferencia/Entrada", monto, f"<- {c_or}: {desc}"])
                        limpiar(); st.success("Listo"); time.sleep(1); st.rerun()
                else:
                    tipo = "Gasto" if "Gasto" in op else "Ingreso"
                    ws_reg.append_row([fd, ft, us, cta, tipo, cat, monto, desc])
                    limpiar(); st.success("Listo"); time.sleep(1); st.rerun()

# === DERECHA: DASHBOARD ===
with col_R:
    # A. RESUMEN MES
    m_ing = df_f[df_f['Tipo']=='Ingreso']['Monto'].sum()
    m_gas = df_f[df_f['Tipo']=='Gasto']['Monto'].sum()
    
    with st.container():
        k1, k2, k3 = st.columns(3)
        k1.metric("Ingresos Mes", f"S/ {m_ing:,.2f}")
        k2.metric("Gastos Mes", f"S/ {m_gas:,.2f}", delta="-Gasto", delta_color="inverse")
        k3.metric("Balance Mes", f"S/ {m_ing - m_gas:,.2f}", delta="Ahorro")
    
    st.write("")
    
    # B. CUENTAS (CON BOTONES + Y -)
    c_head_cta, c_btn_cta = st.columns([4, 1])
    c_head_cta.subheader("💳 Cuentas")
    if c_btn_cta.button("➕ Agregar", key="btn_add_cta"):
        dialog_add_cuenta() # Llama al popup
        
    cols_ctas = st.columns(3)
    for i, c in enumerate(ctas):
        ing = df[(df['Cuenta']==c)&(df['Tipo']=='Ingreso')]['Monto'].sum()
        gas = df[(df['Cuenta']==c)&(df['Tipo']=='Gasto')]['Monto'].sum()
        sal = ing - gas
        
        with cols_ctas[i % 3]:
            with st.container():
                # Cabecera de la tarjeta con botón borrar pequeño
                ct1, ct2 = st.columns([3, 1])
                ct1.write(f"**{c}**")
                if ct2.button("🗑️", key=f"del_c_{i}"):
                    dialog_del_cuenta(c) # Llama al popup de confirmación
                
                st.metric("Saldo", f"S/ {sal:,.2f}", label_visibility="collapsed")
                if ing > 0: st.progress(min(max(sal/ing, 0.0), 1.0))
    
    st.write("")

    # C. METAS (CON BOTONES + Y -)
    c_head_met, c_btn_met = st.columns([4, 1])
    c_head_met.subheader("🚦 Metas")
    if c_btn_met.button("➕ Agregar", key="btn_add_met"):
        dialog_add_meta()

    g_cat = df_f[df_f['Tipo']=='Gasto'].groupby('Categoria')['Monto'].sum()
    
    cp1, cp2 = st.columns(2)
    for i, m in enumerate(metas):
        cat = m['Categoria']
        tope = m['Tope_Mensual']
        real = g_cat.get(cat, 0)
        pct = (real/tope) if tope > 0 else 0
        
        with cp1 if i%2==0 else cp2:
            with st.container():
                mt1, mt2 = st.columns([4, 1])
                mt1.write(f"**{cat}**")
                if mt2.button("🗑️", key=f"del_m_{i}"):
                    dialog_del_meta(cat)
                    
                st.caption(f"{real:.0f} / {tope}")
                if pct > 1: st.progress(1.0); st.error("Excedido")
                elif pct > 0.8: st.progress(pct); st.warning("Alerta")
                else: st.progress(pct)

# --- 9. HISTORIAL (ABAJO) ---
st.write("---")
st.subheader("📂 Historial")

if not df.empty:
    # Mostramos los últimos 10 movimientos
    df_show = df_f.sort_values('ID_Fila', ascending=False).head(15)
    
    for index, row in df_show.iterrows():
        # Creamos una fila visual por cada registro
        with st.container():
            c_h1, c_h2, c_h3, c_h4, c_h5 = st.columns([1, 2, 2, 1, 1])
            c_h1.write(f"📅 {row['Fecha_dt'].strftime('%d/%m')}")
            c_h2.write(f"**{row['Categoria']}**")
            c_h3.write(row['Descripcion'])
            
            color = "green" if row['Tipo'] == "Ingreso" else "red"
            c_h4.markdown(f":{color}[S/ {row['Monto']:.2f}]")
            
            # Botón eliminar para ESTA fila específica
            if c_h5.button("🗑️", key=f"del_row_{row['ID_Fila']}"):
                dialog_del_movimiento(row['ID_Fila'], row['Descripcion'], row['Monto'])
else:
    st.info("No hay movimientos en este mes.")
