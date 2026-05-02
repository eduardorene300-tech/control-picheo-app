import streamlit as st
import sqlite3
import bcrypt
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO

# ==========================
# CONFIGURACIÓN GENERAL
# ==========================
st.set_page_config(page_title="BetaPro - Control de Picheo", layout="wide")

DB = "betapro.db"

# ==========================
# BASE DE DATOS
# ==========================
def get_conn():
    return sqlite3.connect(DB, check_same_thread=False)

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY,
        nombre TEXT UNIQUE,
        pass TEXT,
        rol TEXT,
        email TEXT,
        fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS picheos (
        id INTEGER PRIMARY KEY,
        fecha TEXT,
        control TEXT,
        cantidad INTEGER,
        ganancia REAL,
        operador TEXT,
        notas TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS config (
        clave TEXT PRIMARY KEY,
        valor TEXT
    )''')

    # No modifica datos existentes
    c.execute("INSERT OR IGNORE INTO config VALUES ('precio', '0.025')")

    conn.commit()
    conn.close()

init_db()

# ==========================
# SEGURIDAD / AUTH
# ==========================
def hash_pass(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_pass(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def login(usuario, password):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM usuarios WHERE nombre=?", (usuario,))
    row = c.fetchone()
    conn.close()

    if row and verify_pass(password, row[2]):
        return row
    return None

def registrar_usuario(usuario, password, email):
    conn = get_conn()
    c = conn.cursor()
    try:
        hashed = hash_pass(password)
        c.execute("INSERT INTO usuarios (nombre, pass, rol, email) VALUES (?, ?, 'usuario', ?)",
                  (usuario, hashed, email))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def cambiar_pass(usuario, actual, nueva):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT pass FROM usuarios WHERE nombre=?", (usuario,))
    row = c.fetchone()

    if not row or not verify_pass(actual, row[0]):
        return False

    new_hash = hash_pass(nueva)
    c.execute("UPDATE usuarios SET pass=? WHERE nombre=?", (new_hash, usuario))
    conn.commit()
    conn.close()
    return True

# ==========================
# LÓGICA DE PICHEOS
# ==========================
def get_precio():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT valor FROM config WHERE clave='precio'")
    p = float(c.fetchone()[0])
    conn.close()
    return p

def set_precio(nuevo):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE config SET valor=? WHERE clave='precio'", (str(nuevo),))
    conn.commit()
    conn.close()

def guardar_picheo(fecha, control, cantidad, operador, notas):
    conn = get_conn()
    c = conn.cursor()
    precio = get_precio()
    ganancia = cantidad * precio

    c.execute("""INSERT INTO picheos (fecha, control, cantidad, ganancia, operador, notas)
                 VALUES (?, ?, ?, ?, ?, ?)""",
              (fecha, control, cantidad, ganancia, operador, notas))

    conn.commit()
    conn.close()

def eliminar_picheo(id_reg, operador, es_admin):
    conn = get_conn()
    c = conn.cursor()
    if es_admin:
        c.execute("DELETE FROM picheos WHERE id=?", (id_reg,))
    else:
        c.execute("DELETE FROM picheos WHERE id=? AND operador=?", (id_reg, operador))
    conn.commit()
    conn.close()

def get_picheos(filtros=None, operador=None, es_admin=False):
    conn = get_conn()
    query = "SELECT * FROM picheos WHERE 1=1"
    params = []

    if not es_admin and operador:
        query += " AND operador=?"
        params.append(operador)

    if filtros:
        if filtros.get("fecha_desde"):
            query += " AND fecha >= ?"
            params.append(filtros["fecha_desde"])
        if filtros.get("fecha_hasta"):
            query += " AND fecha <= ?"
            params.append(filtros["fecha_hasta"])
        if filtros.get("control"):
            query += " AND control LIKE ?"
            params.append(f"%{filtros['control']}%")

    query += " ORDER BY fecha DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

# ==========================
# UTILIDADES
# ==========================
def mostrar_logo(tamano=250):
    st.markdown('<div style="display:flex; justify-content:center;">', unsafe_allow_html=True)
    st.image("logo.png", width=tamano)
    st.markdown('</div>', unsafe_allow_html=True)

def export_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# ==========================
# INTERFAZ STREAMLIT
# ==========================
if "logueado" not in st.session_state:
    st.session_state.logueado = False

# ==========================
# LOGIN
# ==========================
if not st.session_state.logueado:
    mostrar_logo(250)

    tab1, tab2 = st.tabs(["🔐 Iniciar Sesión", "📝 Registrarse"])

    with tab1:
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            user = login(u, p)
            if user:
                st.session_state.logueado = True
                st.session_state.usuario = user[1]
                st.session_state.rol = user[3]
                st.rerun()
            else:
                st.error("Credenciales incorrectas")

    with tab2:
        nu = st.text_input("Nuevo usuario")
        em = st.text_input("Email")
        pw = st.text_input("Contraseña", type="password")
        cf = st.text_input("Confirmar", type="password")
        if st.button("Registrar"):
            if pw == cf:
                if registrar_usuario(nu, pw, em):
                    st.success("Registrado correctamente")
                else:
                    st.error("Usuario ya existe")
            else:
                st.error("Las contraseñas no coinciden")

# ==========================
# PANEL PRINCIPAL
# ==========================
else:
    with st.sidebar:
        st.image("logo.png", width=150)
        st.write(f"👤 {st.session_state.usuario}")
        st.write(f"Rol: {st.session_state.rol}")
        menu = st.radio("Menú", ["📊 Dashboard", "📝 Registrar", "📋 Registros", "🔐 Cambiar Pass", "⚙️ Admin"])

    # ==========================
    # DASHBOARD
    # ==========================
    if menu == "📊 Dashboard":
        mostrar_logo(200)
        st.header("📊 Dashboard")

        col1, col2 = st.columns(2)
        with col1:
            f1 = st.date_input("Desde", datetime.now() - timedelta(days=30))
        with col2:
            f2 = st.date_input("Hasta", datetime.now())

        filtros = {
            "fecha_desde": f1.strftime("%Y-%m-%d"),
            "fecha_hasta": f2.strftime("%Y-%m-%d")
        }

        df = get_picheos(filtros, None, st.session_state.rol == "admin")

        if not df.empty:
            precio = get_precio()
            total_p = int(df["cantidad"].sum())
            total_g = total_p * precio

            st.metric("Total Picheos", f"{total_p:,}")
            st.metric("Ganancias USD", f"${total_g:,.2f}")

            st.dataframe(df)

            excel = export_excel(df)
            st.download_button("📊 Exportar Excel", excel, "dashboard.xlsx")

        else:
            st.warning("No hay registros en este rango")

    # ==========================
    # REGISTRAR PICHEO
    # ==========================
    elif menu == "📝 Registrar":
        mostrar_logo(200)
        st.header("📝 Registrar Picheo")

        c1, c2, c3 = st.columns(3)
        with c1:
            fecha = st.date_input("Fecha", datetime.now())
        with c2:
            control = st.text_input("ID Control")
        with c3:
            cantidad = st.number_input("Cantidad", min_value=1)

        operador = st.text_input("Operador", value=st.session_state.usuario)
        notas = st.text_area("Notas")

        if st.button("Guardar"):
            guardar_picheo(fecha.strftime("%Y-%m-%d"), control, cantidad, operador, notas)
            st.success("Guardado correctamente")
            st.rerun()

    # ==========================
    # REGISTROS
    # ==========================
    elif menu == "📋 Registros":
        mostrar_logo(200)
        st.header("📋 Registros")

        d1, d2 = st.columns(2)
        with d1:
            f1 = st.date_input("Desde", datetime.now() - timedelta(days=30))
        with d2:
            f2 = st.date_input("Hasta", datetime.now())

        filtros = {
            "fecha_desde": f1.strftime("%Y-%m-%d"),
            "fecha_hasta": f2.strftime("%Y-%m-%d")
        }

        df = get_picheos(filtros,
                         st.session_state.usuario if st.session_state.rol != "admin" else None,
                         st.session_state.rol == "admin")

        if not df.empty:
            st.dataframe(df)

            excel = export_excel(df)
            st.download_button("📊 Exportar Excel", excel, "registros.xlsx")

            st.subheader("Eliminar registro")
            id_elim = st.number_input("ID", min_value=0)
            if st.button("Eliminar"):
                eliminar_picheo(id_elim, st.session_state.usuario, st.session_state.rol == "admin")
                st.success("Eliminado")
                st.rerun()
        else:
            st.info("No hay registros")

    # ==========================
    # CAMBIAR CONTRASEÑA
    # ==========================
    elif menu == "🔐 Cambiar Pass":
        mostrar_logo(200)
        st.header("🔐 Cambiar Contraseña")

        actual = st.text_input("Actual", type="password")
        nueva = st.text_input("Nueva", type="password")
        conf = st.text_input("Confirmar", type="password")

        if st.button("Actualizar"):
            if nueva == conf:
                if cambiar_pass(st.session_state.usuario, actual, nueva):
                    st.success("Contraseña actualizada")
                else:
                    st.error("Contraseña actual incorrecta")
            else:
                st.error("No coinciden")

    # ==========================
    # ADMIN
    # ==========================
    elif menu == "⚙️ Admin":
        if st.session_state.rol != "admin":
            st.error("Acceso restringido")
        else:
            mostrar_logo(200)
            st.header("⚙️ Administración")

            tab1, tab2 = st.tabs(["💰 Precio", "👥 Usuarios"])

            with tab1:
                precio = get_precio()
                nuevo = st.number_input("Precio por picheo", value=precio, step=0.001)
                if st.button("Actualizar precio"):
                    set_precio(nuevo)
                    st.success("Precio actualizado")

            with tab2:
                conn = get_conn()
                users = pd.read_sql_query("SELECT id, nombre, email, rol, fecha_registro FROM usuarios", conn)
                conn.close()
                st.dataframe(users)
