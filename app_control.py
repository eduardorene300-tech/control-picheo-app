import streamlit as st
import sqlite3
import hashlib
from datetime import datetime, timedelta
import plotly.express as px
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Control de Picheo", layout="wide")

# Base de datos
DB = "datos.db"

def init():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios
                 (id INTEGER PRIMARY KEY, nombre TEXT UNIQUE, pass TEXT, rol TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS picheos
                 (id INTEGER PRIMARY KEY, fecha TEXT, control TEXT, cantidad INTEGER, operador TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS config
                 (clave TEXT PRIMARY KEY, valor TEXT)''')
    
    hash_admin = hashlib.sha256("admin123".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO usuarios VALUES (1, 'admin', ?, 'admin')", (hash_admin,))
    c.execute("INSERT OR IGNORE INTO config VALUES ('precio', '0.025')")
    conn.commit()
    conn.close()

init()

def login(usuario, password):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    hash_p = hashlib.sha256(password.encode()).hexdigest()
    c.execute("SELECT * FROM usuarios WHERE nombre=? AND pass=?", (usuario, hash_p))
    r = c.fetchone()
    conn.close()
    return r

if 'logueado' not in st.session_state:
    st.session_state.logueado = False

if not st.session_state.logueado:
    st.title("🔐 Control de Picheo")
    usuario = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        if login(usuario, password):
            st.session_state.logueado = True
            st.session_state.usuario = usuario
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos")
else:
    st.sidebar.title(f"👤 {st.session_state.usuario}")
    menu = st.sidebar.radio("Menú", ["📊 Dashboard", "📝 Registrar", "📋 Ver Registros"])
    
    if menu == "📊 Dashboard":
        st.title("📊 Dashboard")
        
        conn = sqlite3.connect(DB)
        df = pd.read_sql_query("SELECT * FROM picheos ORDER BY fecha DESC", conn)
        conn.close()
        
        if not df.empty:
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            c.execute("SELECT valor FROM config WHERE clave='precio'")
            precio = float(c.fetchone()[0])
            conn.close()
            
            total_picheos = df['cantidad'].sum()
            total_ganancias = total_picheos * precio
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Picheos", f"{int(total_picheos):,}")
            col2.metric("Ganancias USD", f"${total_ganancias:,.2f}")
            col3.metric("Registros", len(df))
            
            diario = df.groupby('fecha')['cantidad'].sum().reset_index()
            fig = px.line(diario, x='fecha', y='cantidad', title='Producción Diaria')
            st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("Últimos Registros")
            st.dataframe(df.head(10)[['fecha', 'control', 'cantidad', 'operador']])
        else:
            st.info("No hay registros aún. Ve a la pestaña Registrar.")
    
    elif menu == "📝 Registrar":
        st.title("📝 Nuevo Registro de Picheo")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            fecha = st.date_input("Fecha", datetime.now())
        with col2:
            control = st.text_input("ID Control")
        with col3:
            cantidad = st.number_input("Cantidad de Picheos", min_value=1, step=1)
        
        operador = st.text_input("Operador", value=st.session_state.usuario)
        
        if st.button("💾 Guardar", use_container_width=True):
            if control and cantidad > 0:
                conn = sqlite3.connect(DB)
                c = conn.cursor()
                c.execute("INSERT INTO picheos (fecha, control, cantidad, operador) VALUES (?,?,?,?)",
                         (fecha.strftime('%Y-%m-%d'), control, cantidad, operador))
                conn.commit()
                conn.close()
                st.success("✅ Registro guardado!")
                st.rerun()
            else:
                st.warning("Completa todos los campos")
    
    elif menu == "📋 Ver Registros":
        st.title("📋 Lista de Registros")
        
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT valor FROM config WHERE clave='precio'")
        precio = float(c.fetchone()[0])
        
        df = pd.read_sql_query("SELECT * FROM picheos ORDER BY fecha DESC", conn)
        conn.close()
        
        if not df.empty:
            df['ganancia'] = df['cantidad'] * precio
            st.dataframe(df[['id', 'fecha', 'control', 'cantidad', 'ganancia', 'operador']], 
                        use_container_width=True)
            
            if st.button("📊 Exportar a Excel"):
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                st.download_button("Descargar Excel", output.getvalue(),
                                 f"reporte_{datetime.now().strftime('%Y%m%d')}.xlsx",
                                 "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            
            st.subheader("🗑️ Eliminar Registro")
            id_eliminar = st.number_input("ID del registro a eliminar", min_value=0, step=1)
            if st.button("Eliminar"):
                if id_eliminar > 0:
                    conn = sqlite3.connect(DB)
                    c = conn.cursor()
                    c.execute("DELETE FROM picheos WHERE id=?", (id_eliminar,))
                    conn.commit()
                    conn.close()
                    st.success("Eliminado!")
                    st.rerun()
        else:
            st.info("No hay registros")
              Version completa - 350 lineas
