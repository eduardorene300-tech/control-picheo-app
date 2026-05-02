import streamlit as st
import sqlite3
import hashlib
from datetime import datetime, timedelta
import pandas as pd
from io import BytesIO
import os

# --- CONFIGURACIÓN DE PÁGINA ---
DB = "betapro.db"
LOGO = "logo.png"

st.set_page_config(page_title="BetaPro - Control de Picheo", layout="wide", page_icon=LOGO if os.path.exists(LOGO) else None)

# --- CSS INTEGRADO ---
st.markdown("""
<style>
.stApp { background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%); }
.main-title { text-align: center; color: #3399FF; font-size: 2.5rem; }
.metric-card { background: #1e1e2e; border-radius: 10px; padding: 15px; border-left: 4px solid #3399FF; margin: 10px 0; }
</style>
""", unsafe_allow_html=True)

# --- BASE DE DATOS (MANTIENE TUS DATOS EXISTENTES) ---
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY, nombre TEXT UNIQUE, pass TEXT, rol TEXT, email TEXT, fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS picheos (id INTEGER PRIMARY KEY, fecha TEXT, control TEXT, cantidad INTEGER, ganancia REAL, operador TEXT, notas TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS config (clave TEXT PRIMARY KEY, valor TEXT)''')
    
    hash_admin = hashlib.sha256("admin123".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO usuarios (nombre, pass, rol, email) VALUES ('admin', ?, 'admin', 'admin@betapro.com')", (hash_admin,))
    c.execute("INSERT OR IGNORE INTO config VALUES ('precio', '0.025')")
    conn.commit()
    conn.close()

init_db()

# --- FUNCIONES DE LÓGICA ---
def login(u, p):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    hp = hashlib.sha256(p.encode()).hexdigest()
    c.execute("SELECT * FROM usuarios WHERE nombre=? AND pass=?", (u, hp))
    r = c.fetchone()
    conn.close()
    return r

def guardar_picheo(fecha, control, cantidad, operador, notas):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT valor FROM config WHERE clave='precio'")
    precio = float(c.fetchone()[0])
    ganancia = cantidad * precio
    c.execute("INSERT INTO picheos (fecha, control, cantidad, ganancia, operador, notas) VALUES (?,?,?,?,?,?)", (fecha, control, cantidad, ganancia, operador, notas))
    conn.commit()
    conn.close()

def get_picheos(operador=None, es_admin=False):
    conn = sqlite3.connect(DB)
    if es_admin:
        df = pd.read_sql_query("SELECT * FROM picheos ORDER BY fecha DESC", conn)
    else:
        df = pd.read_sql_query("SELECT * FROM picheos WHERE operador = ? ORDER BY fecha DESC", conn, params=(operador,))
    conn.close()
    return df

# --- INTERFAZ PRINCIPAL ---
if 'logueado' not in st.session_state: st.session_state.logueado = False

if not st.session_state.logueado:
    st.markdown('<h1 class="main-title">⛏️ BetaPro Mining</h1>', unsafe_allow_html=True)
    if os.path.exists(LOGO): st.image(LOGO, width=200)
    
    u_login = st.text_input("Usuario")
    p_login = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        u = login(u_login, p_login)
        if u:
            st.session_state.update({'logueado': True, 'usuario': u[1], 'rol': u[3]})
            st.rerun()
        else: st.error("Usuario o contraseña incorrectos")
else:
    with st.sidebar:
        if os.path.exists(LOGO): st.image(LOGO, use_container_width=True)
        st.write(f"### 👤 {st.session_state.usuario}")
        menu = st.radio("MENÚ", ["📊 Dashboard", "📝 Registrar", "📋 Registros", "⚙️ Admin"])
        if st.button("Cerrar Sesión"): 
            st.session_state.logueado = False
            st.rerun()

    if menu == "📊 Dashboard":
        st.markdown('<h1 class="main-title">📊 Dashboard</h1>', unsafe_allow_html=True)
        df = get_picheos(st.session_state.usuario, st.session_state.rol == 'admin')
        if not df.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Registros", len(df))
            c2.metric("Total", f"{int(df['cantidad'].sum()):,}")
            c3.metric("Ganancia", f"${df['ganancia'].sum():,.2f}")
            st.dataframe(df, use_container_width=True)
        else: st.info("No hay datos")

    elif menu == "📝 Registrar":
        with st.form("reg"):
            fecha = st.date_input("Fecha", datetime.now())
            control = st.text_input("ID Control")
            cant = st.number_input("Cantidad", 1)
            notas = st.text_area("Notas")
            if st.form_submit_button("Guardar"):
                guardar_picheo(fecha.strftime('%Y-%m-%d'), control, cant, st.session_state.usuario, notas)
                st.success("Guardado!")
                st.rerun()

    elif menu == "📋 Registros":
        df = get_picheos(st.session_state.usuario, st.session_state.rol == 'admin')
        st.dataframe(df, use_container_width=True)
        
    elif menu == "⚙️ Admin" and st.session_state.rol == 'admin':
        st.header("Configuración")
        conn = sqlite3.connect(DB)
        actual = float(conn.execute("SELECT valor FROM config WHERE clave='precio'").fetchone()[0])
        nuevo = st.number_input("Precio por picheo", value=actual, format="%.4f")
        if st.button("Actualizar"):
            conn.execute("UPDATE config SET valor=? WHERE clave='precio'", (str(nuevo),))
            conn.commit()
            st.success("Actualizado")
        conn.close()
