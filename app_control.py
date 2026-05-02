import streamlit as st
import sqlite3
import hashlib
from datetime import datetime, timedelta
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="BetaPro - Control de Picheo", layout="wide")

st.markdown("""
<style>
.stApp { background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%); }
.main-title { text-align: center; color: #3399FF; font-size: 2.5rem; }
.metric-card { background: #1e1e2e; border-radius: 10px; padding: 15px; border-left: 4px solid #3399FF; margin: 10px 0; }
</style>
""", unsafe_allow_html=True)

DB = "betapro.db"

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY, nombre TEXT UNIQUE, pass TEXT, rol TEXT, email TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS picheos (id INTEGER PRIMARY KEY, fecha TEXT, control TEXT, cantidad INTEGER, ganancia REAL, operador TEXT, notas TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS config (clave TEXT PRIMARY KEY, valor TEXT)')
    
    hash_admin = hashlib.sha256("admin123".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO usuarios VALUES (1, 'admin', ?, 'admin', 'admin@betapro.com')", (hash_admin,))
    c.execute("INSERT OR IGNORE INTO config VALUES ('precio', '0.025')")
    conn.commit()
    conn.close()

init_db()

def login(usuario, pw):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    hp = hashlib.sha256(pw.encode()).hexdigest()
    c.execute("SELECT * FROM usuarios WHERE nombre=? AND pass=?", (usuario, hp))
    r = c.fetchone()
    conn.close()
    return r

def registrar_usuario(nombre, pw, email):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    hp = hashlib.sha256(pw.encode()).hexdigest()
    try:
        c.execute("INSERT INTO usuarios (nombre, pass, rol, email) VALUES (?, ?, 'usuario', ?)", (nombre, hp, email))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def cambiar_pass(usuario, actual, nueva):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    ha = hashlib.sha256(actual.encode()).hexdigest()
    hn = hashlib.sha256(nueva.encode()).hexdigest()
    c.execute("UPDATE usuarios SET pass=? WHERE nombre=? AND pass=?", (hn, usuario, ha))
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
            query += " AND fecha >= ?"
            params.append(filtros['fecha_desde'])
        if filtros.get('fecha_hasta'):
            query += " AND fecha <= ?"
            params.append(filtros['fecha_hasta'])
        if filtros.get('control'):
            query += " AND control LIKE ?"
            params.append(f"%{filtros['control']}%")
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

if 'logueado' not in st.session_state:
    st.session_state.logueado = False

if not st.session_state.logueado:
    st.markdown('<h1 class="main-title">⛏️ BetaPro Mining</h1>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔐 Iniciar Sesión", "📝 Registrarse"])
    
    with tab1:
        usuario = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        if st.button("Ingresar", use_container_width=True):
            user = login(usuario, password)
            if user:
                st.session_state.logueado = True
                st.session_state.usuario = user[1]
                st.session_state.rol = user[3]
                st.session_state.user_id = user[0]
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos")
    
    with tab2:
        nuevo_user = st.text_input("Usuario *")
        nuevo_email = st.text_input("Email")
        nueva_pass = st.text_input("Contraseña *", type="password")
        confirm_pass = st.text_input("Confirmar *", type="password")
        if st.button("Registrarse", use_container_width=True):
            if not nuevo_user or not nueva_pass:
                st.error("Usuario y contraseña son obligatorios")
            elif nueva_pass != confirm_pass:
                st.error("Las contraseñas no coinciden")
            else:
                if registrar_usuario(nuevo_user, nueva_pass, nuevo_email):
                    st.success("✅ Registrado! Ahora inicia sesión")
                else:
                    st.error("El usuario ya existe")

else:
    st.sidebar.markdown(f"### 👤 {st.session_state.usuario}")
    st.sidebar.markdown(f"*Rol: {st.session_state.rol}*")
    st.sidebar.divider()
    
    menu = st.sidebar.radio("Menú", ["📊 Dashboard", "📝 Registrar", "📋 Registros", "🔐 Cambiar Pass", "⚙️ Admin"])
    
    if menu == "📊 Dashboard":
        st.markdown('<h1 class="main-title">📊 Dashboard</h1>', unsafe_allow_html=True)
        
        df = get_picheos(operador=st.session_state.usuario, es_admin=st.session_state.rol=='admin')
        
        if not df.empty:
            precio = get_precio()
            total_picheos = df['cantidad'].sum()
            total_ganancias = total_picheos * precio
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f'<div class="metric-card">📋 Registros<br><h2>{len(df)}</h2></div>', unsafe_allow_html=True)
            with col2:
                st.markdown(f'<div class="metric-card">⛏️ Picheos<br><h2>{int(total_picheos):,}</h2></div>', unsafe_allow_html=True)
            with col3:
                st.markdown(f'<div class="metric-card">💰 Ganancias<br><h2>${total_ganancias:,.2f}</h2></div>', unsafe_allow_html=True)
            
            st.subheader("📋 Últimos Registros")
            st.dataframe(df.head(10)[['fecha', 'control', 'cantidad', 'ganancia', 'operador']], use_container_width=True)
        else:
            st.info("No hay registros aún")
    
    elif menu == "📝 Registrar":
        st.markdown('<h1 class="main-title">📝 Registrar Picheo</h1>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            fecha = st.date_input("📅 Fecha", datetime.now())
        with col2:
            control = st.text_input("🏷️ ID Control")
        with col3:
            cantidad = st.number_input("⛏️ Cantidad", min_value=1, step=1)
        
        operador = st.text_input("👤 Operador", value=st.session_state.usuario)
        notas = st.text_area("📝 Notas")
        
        if st.button("💾 Guardar", use_container_width=True):
            if control and cantidad:
                guardar_picheo(fecha.strftime('%Y-%m-%d'), control, cantidad, operador, notas)
                st.success("✅ Registro guardado!")
                st.rerun()
            else:
                st.warning("Completa los campos obligatorios")
    
    elif menu == "📋 Registros":
        st.markdown('<h1 class="main-title">📋 Mis Registros</h1>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            desde = st.date_input("📅 Desde", datetime.now() - timedelta(days=30))
        with col2:
            hasta = st.date_input("📅 Hasta", datetime.now())
        
        df = get_picheos(
            filtros={'fecha_desde': desde.strftime('%Y-%m-%d'), 'fecha_hasta': hasta.strftime('%Y-%m-%d')},
            operador=st.session_state.usuario,
            es_admin=st.session_state.rol=='admin'
        )
        
        if not df.empty:
            st.dataframe(df[['id', 'fecha', 'control', 'cantidad', 'ganancia', 'operador', 'notas']], use_container_width=True)
            
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            st.download_button("📊 Exportar a Excel", output.getvalue(), f"reporte_{datetime.now().strftime('%Y%m%d')}.xlsx")
            
            st.subheader("🗑️ Eliminar Registro")
            id_elim = st.number_input("ID a eliminar", min_value=0, step=1)
            if st.button("Eliminar"):
                if id_elim > 0:
                    eliminar_picheo(id_elim, st.session_state.usuario, st.session_state.rol=='admin')
                    st.success("✅ Eliminado!")
                    st.rerun()
        else:
            st.info("No hay registros")
    
    elif menu == "🔐 Cambiar Pass":
        st.markdown('<h1 class="main-title">🔐 Cambiar Contraseña</h1>', unsafe_allow_html=True)
        
        actual = st.text_input("Contraseña actual", type="password")
        nueva = st.text_input("Nueva contraseña", type="password")
        confirma = st.text_input("Confirmar nueva", type="password")
        
        if st.button("Actualizar"):
            if nueva == confirma:
                if cambiar_pass(st.session_state.usuario, actual, nueva):
                    st.success("✅ Contraseña cambiada")
                else:
                    st.error("Contraseña actual incorrecta")
            else:
                st.error("Las nuevas contraseñas no coinciden")
    
    elif menu == "⚙️ Admin":
        if st.session_state.rol == 'admin':
            st.markdown('<h1 class="main-title">⚙️ Administración</h1>', unsafe_allow_html=True)
            
            precio_act = get_precio()
            nuevo_precio = st.number_input("Precio por picheo (USD)", value=precio_act, step=0.001, format="%.4f")
            if st.button("Actualizar Precio"):
                set_precio(nuevo_precio)
                st.success(f"✅ Precio actualizado a ${nuevo_precio:.4f}")
            
            st.divider()
            conn = sqlite3.connect(DB)
            usuarios = pd.read_sql_query("SELECT id, nombre, email, rol FROM usuarios", conn)
            conn.close()
            st.subheader("👥 Usuarios del Sistema")
            st.dataframe(usuarios, use_container_width=True)
        else:
            st.error("🔒 Acceso restringido a administradores")
