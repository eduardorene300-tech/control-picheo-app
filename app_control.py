import streamlit as st
import sqlite3
import hashlib
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
    with get_conn() as conn:
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

        c.execute('''CREATE TABLE IF NOT EXISTS auditoria (
            id INTEGER PRIMARY KEY,
            fecha TEXT,
            usuario TEXT,
            accion TEXT,
            detalle TEXT
        )''')

        # Precio por defecto
        c.execute("INSERT OR IGNORE INTO config (clave, valor) VALUES ('precio', '0.025')")

        # Admin por defecto
        admin_hash = hashlib.sha256("admin123".encode()).hexdigest()
        c.execute(
            "INSERT OR IGNORE INTO usuarios (nombre, pass, rol, email) VALUES ('admin', ?, 'admin', 'admin@betapro.com')",
            (admin_hash,)
        )

init_db()

# ==========================
# AUDITORÍA
# ==========================
def auditar(usuario, accion, detalle=""):
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO auditoria (fecha, usuario, accion, detalle) VALUES (?,?,?,?)",
            (fecha, usuario, accion, detalle)
        )
        conn.commit()

# ==========================
# SEGURIDAD / AUTH
# ==========================
def hash_pass(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login(usuario, password):
    hashed = hash_pass(password)
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM usuarios WHERE nombre=? AND pass=?", (usuario, hashed))
        row = c.fetchone()
    if row:
        auditar(usuario, "login", "Inicio de sesión exitoso")
    return row

def registrar_usuario(usuario, password, email):
    hashed = hash_pass(password)
    try:
        with get_conn() as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO usuarios (nombre, pass, rol, email) VALUES (?, ?, 'usuario', ?)",
                (usuario, hashed, email)
            )
            conn.commit()
        auditar(usuario, "registro", f"Nuevo usuario: {usuario}")
        return True
    except:
        return False

def cambiar_pass(usuario, actual, nueva):
    hashed_actual = hash_pass(actual)
    hashed_nueva = hash_pass(nueva)
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "UPDATE usuarios SET pass=? WHERE nombre=? AND pass=?",
            (hashed_nueva, usuario, hashed_actual)
        )
        ok = c.rowcount > 0
        conn.commit()
    if ok:
        auditar(usuario, "cambio_clave", "Cambio de contraseña")
    return ok

# ==========================
# PICHEOS
# ==========================
def get_precio():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT valor FROM config WHERE clave='precio'")
        row = c.fetchone()
    return float(row[0])

def set_precio(nuevo, usuario):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("UPDATE config SET valor=? WHERE clave='precio'", (str(nuevo),))
        conn.commit()
    auditar(usuario, "cambio_precio", f"Nuevo precio: {nuevo}")

def guardar_picheo(fecha, control, cantidad, operador, notas):
    precio = get_precio()
    ganancia = cantidad * precio
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            """INSERT INTO picheos (fecha, control, cantidad, ganancia, operador, notas)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (fecha, control, cantidad, ganancia, operador, notas)
        )
        conn.commit()
    auditar(operador, "alta_picheo", f"Control: {control}, Cantidad: {cantidad}")

def eliminar_picheo(id_reg, operador, es_admin):
    with get_conn() as conn:
        c = conn.cursor()
        if es_admin:
            c.execute("DELETE FROM picheos WHERE id=?", (id_reg,))
        else:
            c.execute("DELETE FROM picheos WHERE id=? AND operador=?", (id_reg, operador))
        borrados = c.rowcount
        conn.commit()
    if borrados > 0:
        auditar(operador, "baja_picheo", f"ID eliminado: {id_reg}")

def get_picheos(filtros, operador, es_admin):
    with get_conn() as conn:
        query = "SELECT * FROM picheos WHERE 1=1"
        params = []

        if not es_admin:
            query += " AND operador=?"
            params.append(operador)

        if filtros.get("desde"):
            query += " AND fecha >= ?"
            params.append(filtros["desde"])

        if filtros.get("hasta"):
            query += " AND fecha <= ?"
            params.append(filtros["hasta"])

        df = pd.read_sql_query(query, conn, params=params)
    return df

def get_usuarios_df():
    with get_conn() as conn:
        return pd.read_sql_query(
            "SELECT id, nombre, email, rol, fecha_registro FROM usuarios",
            conn
        )

def get_auditoria_df():
    with get_conn() as conn:
        return pd.read_sql_query(
            "SELECT fecha, usuario, accion, detalle FROM auditoria ORDER BY fecha DESC",
            conn
        )

# ==========================
# UTILIDADES
# ==========================
def mostrar_logo(tamano=250):
    st.markdown(
        f"""
        <div style="width:100%; text-align:center; margin-bottom:15px;">
            <img src="logo.png" style="width:{tamano}px;">
        </div>
        """,
        unsafe_allow_html=True
    )

def export_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# ==========================
# SESIÓN
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
        u = st.text_input("Usuario", key="login_user")
        p = st.text_input("Contraseña", type="password", key="login_pass")
        if st.button("Ingresar", key="login_btn"):
            user = login(u, p)
            if user:
                st.session_state.logueado = True
                st.session_state.usuario = user[1]
                st.session_state.rol = user[3]
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos")

    with tab2:
        nu = st.text_input("Nuevo usuario", key="reg_user")
        em = st.text_input("Email", key="reg_email")
        pw = st.text_input("Contraseña", type="password", key="reg_pass")
        cf = st.text_input("Confirmar", type="password", key="reg_confirm")
        if st.button("Registrar", key="reg_btn"):
            if pw != cf:
                st.error("Las contraseñas no coinciden")
            elif registrar_usuario(nu, pw, em):
                st.success("Registrado correctamente")
            else:
                st.error("El usuario ya existe")

# ==========================
# PANEL PRINCIPAL
# ==========================
else:
    with st.sidebar:
        st.markdown(
            """
            <div style="width:100%; text-align:center; margin-bottom:10px;">
                <img src="logo.png" style="width:150px;">
            </div>
            """,
            unsafe_allow_html=True
        )
        st.write(f"👤 {st.session_state.usuario}")
        st.write(f"Rol: {st.session_state.rol}")
        menu = st.radio("Menú", ["📊 Dashboard", "📝 Registrar", "📋 Registros", "🔐 Cambiar Pass", "⚙️ Admin"])

    # DASHBOARD
    if menu == "📊 Dashboard":
        mostrar_logo(200)
        st.header("📊 Dashboard")

        f1 = st.date_input("Desde", datetime.now() - timedelta(days=30), key="dash_desde")
        f2 = st.date_input("Hasta", datetime.now(), key="dash_hasta")

        filtros = {
            "desde": f1.strftime("%Y-%m-%d"),
            "hasta": f2.strftime("%Y-%m-%d")
        }

        df = get_picheos(filtros, st.session_state.usuario, st.session_state.rol == "admin")

        if not df.empty:
            precio = get_precio()
            total = int(df["cantidad"].sum())
            ganancia = total * precio

            st.metric("Total Picheos", total)
            st.metric("Ganancias USD", f"${ganancia:,.2f}")

            st.dataframe(df)

            excel = export_excel(df)
            st.download_button("📊 Exportar Excel", excel, "dashboard.xlsx")
        else:
            st.warning("No hay registros")

    # REGISTRAR
    elif menu == "📝 Registrar":
        mostrar_logo(200)
        st.header("📝 Registrar Picheo")

        fecha = st.date_input("Fecha", datetime.now(), key="reg_fecha")
        control = st.text_input("ID Control", key="reg_control")
        cantidad = st.number_input("Cantidad", min_value=1, key="reg_cantidad")
        notas = st.text_area("Notas", key="reg_notas")

        if st.button("Guardar", key="reg_guardar"):
            guardar_picheo(fecha.strftime("%Y-%m-%d"), control, cantidad, st.session_state.usuario, notas)
            st.success("Guardado correctamente")
            st.rerun()

    # REGISTROS
    elif menu == "📋 Registros":
        mostrar_logo(200)
        st.header("📋 Registros")

        f1 = st.date_input("Desde", datetime.now() - timedelta(days=30), key="regs_desde")
        f2 = st.date_input("Hasta", datetime.now(), key="regs_hasta")

        filtros = {
            "desde": f1.strftime("%Y-%m-%d"),
            "hasta": f2.strftime("%Y-%m-%d")
        }

        df = get_picheos(filtros, st.session_state.usuario, st.session_state.rol == "admin")

        if not df.empty:
            st.dataframe(df)

            excel = export_excel(df)
            st.download_button("📊 Exportar Excel", excel, "registros.xlsx")

            id_elim = st.number_input("ID a eliminar", min_value=0, key="elim_id")
            if st.button("Eliminar", key="elim_btn"):
                eliminar_picheo(id_elim, st.session_state.usuario, st.session_state.rol == "admin")
                st.success("Eliminado")
                st.rerun()
        else:
            st.info("No hay registros")

    # CAMBIAR PASS
    elif menu == "🔐 Cambiar Pass":
        mostrar_logo(200)
        st.header("🔐 Cambiar Contraseña")

        actual = st.text_input("Actual", type="password", key="pass_actual")
        nueva = st.text_input("Nueva", type="password", key="pass_nueva")
        conf = st.text_input("Confirmar", type="password", key="pass_conf")

        if st.button("Actualizar", key="pass_btn"):
            if nueva != conf:
                st.error("No coinciden")
            elif cambiar_pass(st.session_state.usuario, actual, nueva):
                st.success("Contraseña actualizada")
            else:
                st.error("Contraseña actual incorrecta")

    # ADMIN
    elif menu == "⚙️ Admin":
        if st.session_state.rol != "admin":
            st.error("Acceso restringido")
        else:
            mostrar_logo(200)
            st.header("⚙️ Administración")

            tab1, tab2, tab3 = st.tabs(["💰 Precio", "👥 Usuarios", "📜 Auditoría"])

            with tab1:
                precio = get_precio()
                nuevo = st.number_input("Precio por picheo", value=precio, step=0.001, key="precio_input")
                if st.button("Actualizar precio", key="precio_btn"):
                    set_precio(nuevo, st.session_state.usuario)
                    st.success("Precio actualizado")

            with tab2:
                users = get_usuarios_df()
                st.dataframe(users)

            with tab3:
                aud = get_auditoria_df()
                st.dataframe(aud)
                excel = export_excel(aud)
                st.download_button("📜 Exportar Auditoría", excel, "auditoria.xlsx")
