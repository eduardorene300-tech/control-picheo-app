import streamlit as st
import sqlite3
import hashlib
from datetime import datetime, timedelta
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="BetaPro", layout="wide")

DB = "datos.db"

conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY, nombre TEXT UNIQUE, pass TEXT, rol TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS picheos (id INTEGER PRIMARY KEY, fecha TEXT, control TEXT, cantidad INTEGER, operador TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS config (clave TEXT PRIMARY KEY, valor TEXT)')

hash_admin = hashlib.sha256("admin123".encode()).hexdigest()
c.execute("INSERT OR IGNORE INTO usuarios VALUES (1, 'admin', ?, 'admin')", (hash_admin,))
c.execute("INSERT OR IGNORE INTO config VALUES ('precio', '0.025')")
conn.commit()
conn.close()

def login(u, p):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    hp = hashlib.sha256(p.encode()).hexdigest()
    c.execute("SELECT * FROM usuarios WHERE nombre=? AND pass=?", (u, hp))
    r = c.fetchone()
    conn.close()
    return r

if 'logueado' not in st.session_state:
    st.session_state.logueado = False

if not st.session_state.logueado:
    st.title("BetaPro - Control de Picheo")
    usuario = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        if login(usuario, password):
            st.session_state.logueado = True
            st.session_state.usuario = usuario
            st.rerun()
        else:
            st.error("Error")
else:
    st.sidebar.title(f"{st.session_state.usuario}")
    menu = st.sidebar.radio("Menu", ["Dashboard", "Registrar", "Registros"])
    
    if menu == "Dashboard":
        st.title("Dashboard")
        conn = sqlite3.connect(DB)
        df = pd.read_sql_query("SELECT * FROM picheos ORDER BY fecha DESC", conn)
        conn.close()
        if not df.empty:
            st.metric("Total Picheos", f"{int(df['cantidad'].sum()):,}")
            st.dataframe(df.head(10))
        else:
            st.info("Sin datos")
    
    elif menu == "Registrar":
        st.title("Nuevo Registro")
        fecha = st.date_input("Fecha", datetime.now())
        control = st.text_input("ID Control")
        cantidad = st.number_input("Cantidad", min_value=1)
        operador = st.text_input("Operador", value=st.session_state.usuario)
        if st.button("Guardar"):
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            c.execute("INSERT INTO picheos (fecha, control, cantidad, operador) VALUES (?,?,?,?)",
                     (fecha.strftime('%Y-%m-%d'), control, cantidad, operador))
            conn.commit()
            conn.close()
            st.success("Guardado!")
            st.rerun()
    
    elif menu == "Registros":
        st.title("Registros")
        conn = sqlite3.connect(DB)
        df = pd.read_sql_query("SELECT * FROM picheos ORDER BY fecha DESC", conn)
        conn.close()
        st.dataframe(df)
