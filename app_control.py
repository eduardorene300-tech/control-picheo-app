import streamlit as st
import sqlite3
import hashlib
from datetime import datetime, timedelta
import pandas as pd
from io import BytesIO
import os

# --- CONFIGURACIÓN ---
DB = "betapro.db"
LOGO = "logo.png"

st.set_page_config(page_title="BetaPro - Control de Picheo", layout="wide", page_icon=LOGO if os.path.exists(LOGO) else None)

st.markdown("""
<style>
.stApp { background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%); }
.main-title { text-align: center; color: #3399FF; font-size: 2.5rem; }
.metric-card { background: #1e1e2e; border-radius: 10px; padding: 15px; border-left: 4px solid #3399FF; margin: 10px 0; }
</style>
""", unsafe_allow_html=True)

# --- FUNCIONES BASE DE DATOS ---
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

# --- LÓGICA DE USUARIOS Y DATOS ---
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

def get_picheos(filtros=None, operador=None, es_admin=False):
    conn = sqlite3.connect(DB)
    query = "SELECT * FROM picheos WHERE 1=1"
    params = []
    if not es_admin:
        query += " AND operador = ?"
        params.append(operador)
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

# --- INTERFAZ ---
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
else:
    with st.sidebar:
        if os.path.exists(LOGO): st.image(LOGO, use_container_width=True)
        st.markdown(f"### 👤 {st.session_state.usuario}")
        menu = st.radio("MENÚ", ["📊 Dashboard", "📝 Registrar", "📋 Registros", "⚙️ Admin"])
    
    if menu == "📊 Dashboard":
        df = get_picheos(operador=st.session_state.usuario, es_admin=(st.session_state.rol=='admin'))
        st.metric("Total Picheos", f"{int(df['cantidad'].sum()):,}")
        st.dataframe(df, use_container_width=True)
        
    elif menu == "📝 Registrar":
        with st.form("reg"):
            fecha = st.date_input("Fecha", datetime.now())
            control = st.text_input("ID Control")
            cantidad = st.number_input("Cantidad", 1)
            notas = st.text_area("Notas")
            if st.form_submit_button("Guardar"):
                guardar_picheo(fecha.strftime('%Y-%m-%d'), control, cantidad, st.session_state.usuario, notas)
                st.success("Guardado!")
                
    elif menu == "📋 Registros":
        df = get_picheos(operador=st.session_state.usuario, es_admin=(st.session_state.rol=='admin'))
        st.dataframe(df, use_container_width=True)
        
    elif menu == "⚙️ Admin" and st.session_state.rol == 'admin':
        st.subheader("Configuración")
        # Aquí iría tu lógica de actualización de precio
