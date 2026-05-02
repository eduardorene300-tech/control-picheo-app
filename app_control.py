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

        # Precio por defecto si no existe
        c.execute("INSERT OR IGNORE INTO config (clave, valor) VALUES ('precio', '0.025')")

        # Admin por defecto si no existe (SHA-256)
        hash_admin = hashlib.sha256("admin123".encode()).hexdigest()
        c.execute(
            "INSERT OR IGNORE INTO usuarios (nombre, pass, rol, email) VALUES ('admin', ?, 'admin', 'admin@betapro.com')",
            (hash_admin,)
        )

init_db()

# ==========================
# AUDITORÍA
# ==========================
def registrar_auditoria(usuario, accion, detalle=""):
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO auditoria (fecha, usuario, accion, detalle) VALUES (?,?,?,?)",
            (fecha, usuario, accion, detalle)
        )
        conn.commit()

# ==========================
# SEGURIDAD / AUTH (SHA-256)
# ==========================
def hash_pass(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def login(usuario, password):
    hashed = hash_pass(password)
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM usuarios WHERE nombre=? AND pass=?", (usuario, hashed))
        row = c.fetchone()
    if row:
        registrar_auditoria(usuario, "login", "Inicio de sesión exitoso")
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
        registrar_auditoria(usuario, "registro", f"Registro de nuevo usuario: {usuario}")
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
        registrar_auditoria(usuario, "cambio_clave", "Cambio de contraseña")
    return ok

# ==========================
# LÓGICA DE PICHEOS
# ==========================
def get_precio():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT valor FROM config WHERE clave='precio'")
        row = c.fetchone()
    return float(row[0]) if row else 0.0

def set_precio(nuevo, usuario):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("UPDATE config SET valor=? WHERE clave='precio'", (str(nuevo),))
        conn.commit()
    registrar_auditoria(usuario, "cambio_precio", f"Nuevo precio: {nuevo}")

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
    registrar_auditoria(operador, "alta_picheo", f"Control: {control}, Cantidad: {cantidad}")

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
        registrar_auditoria(operador, "baja_picheo", f"ID eliminado: {id_reg}")

def get_picheos(filtros=None, operador=None, es_admin=False):
    with get_conn() as conn:
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
    return df

def get_usuarios_df():
    with get_conn() as conn:
        df = pd.read_sql_query(
            "SELECT id, nombre, email, rol, fecha_registro FROM usuarios",
            conn
        )
    return df

def get_auditoria_df():
    with get_conn() as conn:
        df = pd.read_sql_query(
            "SELECT fecha, usuario, accion, detalle FROM auditoria ORDER BY fecha DESC",
            conn
        )
    return df

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
# ESTADO DE SESIÓN
# ==========================
if "logueado" not in st.session_state:
    st.session_state.logueado = False

# ==========================
# LOGIN / REGISTRO
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
        if st.button("Registrarse", key="reg_btn"):
            if not nu or not pw:
                st.error("Usuario y contraseña son obligatorios")
            elif pw != cf:
                st.error("Las contraseñas no coinciden")
            else:
                if registrar_usuario(nu, pw, em):
                    st.success("✅ Registrado! Ahora inicia sesión")
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
        st.markdown(f"### 👤 {st.session_state.usuario}")
        st.markdown(f"*Rol: {st.session_state.rol}*")
        st.divider()
        menu = st.radio(
            "MENÚ",
            ["📊 Dashboard", "📝 Registrar", "📋 Registros", "🔐 Cambiar Pass", "⚙️ Admin"],
            key="menu_radio"
        )

    # DASHBOARD
    if menu == "📊 Dashboard":
        mostrar_logo(200)
        st.markdown("## 📊 Dashboard")

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            fecha_desde = st.date_input("📅 Desde", datetime.now() - timedelta(days=30), key="dash_desde")
        with col_f2:
            fecha_hasta = st.date_input("📅 Hasta", datetime.now(), key="dash_hasta")

        buscar_control = st.text_input("🔍 Buscar por ID Control", key="dash_buscar")

        filtros = {
            'fecha_desde': fecha_desde.strftime('%Y-%m-%d'),
            'fecha_hasta': fecha_hasta.strftime('%Y-%m-%d')
        }
        if buscar_control:
            filtros['control'] = buscar_control

        df = get_picheos(filtros, None, st.session_state.rol == 'admin')

        if not df.empty:
            precio = get_precio()
            total_registros = len(df)
            total_picheos = int(df['cantidad'].sum())
            total_ganancias = total_picheos * precio

            col_r1, col_r2, col_r3 = st.columns(3)
            col_r1.metric("📋 REGISTROS", total_registros)
            col_r2.metric("⛏️ TOTAL PICHEOS", f"{total_picheos:,}")
            col_r3.metric("💰 GANANCIAS USD", f"${total_ganancias:,.2f}")

            st.subheader("📋 LISTA COMPLETA")
            st.dataframe(df[['fecha', 'control', 'cantidad', 'ganancia', 'operador', 'notas']], use_container_width=True)

            excel = export_excel(df)
            st.download_button(
                "📊 EXPORTAR A EXCEL",
                excel,
                f"reporte_{fecha_desde}_a_{fecha_hasta}.xlsx",
                key="dash_export"
            )
        else:
            st.warning(f"No hay registros entre {fecha_desde} y {fecha_hasta}")

    # REGISTRAR
    elif menu == "📝 Registrar":
        mostrar_logo(200)
        st.markdown("## 📝 Registrar Picheo")

        c1, c2, c3 = st.columns(3)
        with c1:
            fecha = st.date_input("📅 Fecha", datetime.now(), key="reg_fecha")
        with c2:
            control = st.text_input("🏷️ ID Control", key="reg_control")
        with c3:
            cantidad = st.number_input("⛏️ Cantidad", min_value=1, step=1, key="reg_cantidad")

        operador = st.text_input("👤 Operador", value=st.session_state.usuario, key="reg_operador")
        notas = st.text_area("📝 Notas", key="reg_notas")

        if st.button("💾 Guardar", use_container_width=True, key="reg_guardar_btn"):
            if control and cantidad:
                guardar_picheo(fecha.strftime('%Y-%m-%d'), control, cantidad, operador, notas)
                st.success("✅ Guardado!")
                st.rerun()
            else:
                st.error("Control y cantidad son obligatorios")

    # REGISTROS
    elif menu == "📋 Registros":
        mostrar_logo(200)
        st.markdown("## 📋 Todos los Registros")

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            desde = st.date_input("Desde", datetime.now() - timedelta(days=30), key="regs_desde")
        with col_f2:
            hasta = st.date_input("Hasta", datetime.now(), key="regs_hasta")

        filtros = {
            'fecha_desde': desde.strftime('%Y-%m-%d'),
            'fecha_hasta': hasta.strftime('%Y-%m-%d')
        }

        df = get_picheos(
            filtros,
            st.session_state.usuario if st.session_state.rol != 'admin' else None,
            st.session_state.rol == 'admin'
        )

        if not df.empty:
            st.dataframe(df[['id', 'fecha', 'control', 'cantidad', 'ganancia', 'operador', 'notas']], use_container_width=True)
            excel = export_excel(df)
            st.download_button(
                "📊 Exportar Excel",
                excel,
                f"reporte_{datetime.now().strftime('%Y%m%d')}.xlsx",
                key="regs_export"
            )

            st.subheader("🗑️ Eliminar")
            id_elim = st.number_input("ID a eliminar", min_value=0, step=1, key="elim_id")
            if st.button("Eliminar", key="elim_btn"):
                if id_elim > 0:
                    eliminar_picheo(id_elim, st.session_state.usuario, st.session_state.rol == 'admin')
                    st.success("Eliminado!")
                    st.rerun()
        else:
            st.info("No hay registros")

    # CAMBIAR PASS
    elif menu == "🔐 Cambiar Pass":
        mostrar_logo(200)
        st.markdown("## 🔐 Cambiar Contraseña")

        actual = st.text_input("Contraseña actual", type="password", key="pass_actual")
        nueva = st.text_input("Nueva contraseña", type="password", key="pass_nueva")
        confirma = st.text_input("Confirmar", type="password", key="pass_confirma")

        if st.button("Actualizar", key="pass_actualizar"):
            if nueva == confirma:
                if cambiar_pass(st.session_state.usuario, actual, nueva):
                    st.success("✅ Contraseña cambiada")
                else:
                    st.error("Contraseña actual incorrecta")
            else:
                st.error("No coinciden")

    # ADMIN
    elif menu == "⚙️ Admin":
        if st.session_state.rol != 'admin':
            st.error("Acceso restringido")
        else:
            mostrar_logo(200)
            st.markdown("## ⚙️ Administración")

            tab_a1, tab_a2, tab_a3 = st.tabs(["💰 Precio", "👥 Usuarios", "📜 Auditoría"])

            with tab_a1:
                st.subheader("💰 Configurar Precio por Picheo")
                precio_act = get_precio()
                nuevo = st.number_input("Precio (USD)", value=precio_act, step=0.001, format="%.4f", key="precio_admin")
                if st.button("Actualizar precio", key="precio_admin_btn"):
                    set_precio(nuevo, st.session_state.usuario)
                    st.success(f"✅ Precio actualizado: ${nuevo:.4f}")

            with tab_a2:
                st.subheader("👥 LISTA DE USUARIOS")
                users = get_usuarios_df()
                st.dataframe(users, use_container_width=True)

            with tab_a3:
                st.subheader("📜 AUDITORÍA DE ACCIONES")
                aud = get_auditoria_df()
                if not aud.empty:
                    st.dataframe(aud, use_container_width=True)
                    excel_aud = export_excel(aud)
                    st.download_button(
                        "📥 Exportar Auditoría",
                        excel_aud,
                        "auditoria.xlsx",
                        key="aud_export"
                    )
                else:
                    st.info("Sin registros de auditoría aún.")
