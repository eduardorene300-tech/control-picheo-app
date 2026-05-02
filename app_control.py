import streamlit as st
import sqlite3
import hashlib
from datetime import datetime, timedelta
import pandas as pd
from io import BytesIO

# Configuración básica
st.set_page_config(page_title="BetaPro - Control de Picheo", layout="wide")

# Estilos CSS originales
st.markdown("""
<style>
.stApp { background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%); }
.main-title { text-align: center; color: #3399FF; font-size: 2.5rem; }
.metric-card { background: #1e1e2e; border-radius: 10px; padding: 15px; border-left: 4px solid #3399FF; margin: 10px 0; }
</style>
""", unsafe_allow_html=True)

DB = "betapro.db"

# --- BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY, nombre TEXT UNIQUE, pass TEXT, rol TEXT, email TEXT, fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS picheos (
        id INTEGER PRIMARY KEY, fecha TEXT, control TEXT, cantidad INTEGER, ganancia REAL, operador TEXT, notas TEXT)''')
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

def registrar_usuario(u, p, email):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    hp = hashlib.sha256(p.encode()).hexdigest()
    try:
        c.execute("INSERT INTO usuarios (nombre, pass, rol, email) VALUES (?, ?, 'usuario', ?)", (u, hp, email))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def cambiar_pass(u, actual, nueva):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    ha = hashlib.sha256(actual.encode()).hexdigest()
    hn = hashlib.sha256(nueva.encode()).hexdigest()
    c.execute("UPDATE usuarios SET pass=? WHERE nombre=? AND pass=?", (hn, u, ha))
    ok = c.rowcount > 0
    conn.commit()
    conn.close()
    return ok

def guardar_picheo(fecha, control, cantidad, operador, notas):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT valor FROM config WHERE clave='precio'")
    precio = float(c.fetchone()[0])
    ganancia = cantidad * precio
    c.execute("INSERT INTO picheos (fecha, control, cantidad, ganancia, operador, notas) VALUES (?,?,?,?,?,?)",
             (fecha, control, cantidad, ganancia, operador, notas))
    conn.commit()
    conn.close()
    return True

def eliminar_picheo(id_reg, operador, es_admin):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    if es_admin:
        c.execute("DELETE FROM picheos WHERE id=?", (id_reg,))
    else:
        c.execute("DELETE FROM picheos WHERE id=? AND operador=?", (id_reg, operador))
    conn.commit()
    conn.close()

def get_picheos(filtros=None, operador=None, es_admin=False):
    conn = sqlite3.connect(DB)
    query = "SELECT * FROM picheos WHERE 1=1"
    params = []
    if not es_admin and operador:
        query += " AND operador = ?"
        params.append(operador)
    if filtros:
        if filtros.get('fecha_desde'):
            query += " AND fecha >= ?"; params.append(filtros['fecha_desde'])
        if filtros.get('fecha_hasta'):
            query += " AND fecha <= ?"; params.append(filtros['fecha_hasta'])
        if filtros.get('control'):
            query += " AND control LIKE ?"; params.append(f"%{filtros['control']}%")
        if filtros.get('anio') and filtros['anio'] != 'todos':
            query += " AND strftime('%Y', fecha) = ?"; params.append(str(filtros['anio']))
        if filtros.get('mes') and filtros['mes'] != 'todos':
            query += " AND strftime('%m', fecha) = ?"; params.append(f"{int(filtros['mes']):02d}")
    query += " ORDER BY fecha DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def get_precio():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT valor FROM config WHERE clave='precio'")
    p = float(c.fetchone()[0])
    conn.close()
    return p

def set_precio(nuevo):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE config SET valor=? WHERE clave='precio'", (str(nuevo),))
    conn.commit()
    conn.close()

def export_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# --- INTERFAZ ---
if 'logueado' not in st.session_state:
    st.session_state.logueado = False

if not st.session_state.logueado:
    st.markdown('<h1 class="main-title">⛏️ BetaPro Mining</h1>', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["🔐 Iniciar Sesión", "📝 Registrarse"])
    
    with tab1:
        usuario_login = st.text_input("Usuario", key="login_user")
        password_login = st.text_input("Contraseña", type="password", key="login_pass")
        if st.button("Ingresar", use_container_width=True):
            u = login(usuario_login, password_login)
            if u:
                st.session_state.logueado = True
                st.session_state.usuario = u[1]
                st.session_state.rol = u[3]
                st.session_state.user_id = u[0]
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
    
    with tab2:
        nuevo_usuario = st.text_input("Usuario *", key="reg_user")
        nuevo_email = st.text_input("Email", key="reg_email")
        nueva_pass = st.text_input("Contraseña *", type="password", key="reg_pass")
        confirmar_pass = st.text_input("Confirmar *", type="password", key="reg_confirm")
        if st.button("Registrarse", use_container_width=True):
            if nueva_pass == confirmar_pass and nuevo_usuario:
                if registrar_usuario(nuevo_usuario, nueva_pass, nuevo_email):
                    st.success("✅ Registrado con éxito")
                else:
                    st.error("El usuario ya existe")
            else:
                st.error("Verifica los datos")

else:
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.usuario}")
        menu = st.radio("MENÚ", ["📊 Dashboard", "📝 Registrar", "📋 Registros", "🔐 Cambiar Pass", "⚙️ Admin"])
        if st.button("Cerrar Sesión"):
            st.session_state.logueado = False
            st.rerun()

    if menu == "📊 Dashboard":
        st.markdown('<h1 class="main-title">📊 Dashboard</h1>', unsafe_allow_html=True)
        df = get_picheos(None, st.session_state.usuario, st.session_state.rol == 'admin')
        if not df.empty:
            precio = get_precio()
            total = df['cantidad'].sum()
            c1, c2, c3 = st.columns(3)
            c1.metric("Registros", len(df))
            c2.metric("Total Picheos", int(total))
            c3.metric("Ganancia", f"${total * precio:,.2f}")
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No hay datos registrados")

    elif menu == "📝 Registrar":
        st.markdown('<h1 class="main-title">📝 Registrar Picheo</h1>', unsafe_allow_html=True)
        with st.form("registro_picheo"):
            f = st.date_input("Fecha", datetime.now())
            c = st.text_input("ID
