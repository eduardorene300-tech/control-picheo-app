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
</style>
""", unsafe_allow_html=True)

DB = "betapro.db"

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
            query += " AND fecha >= ?"
            params.append(filtros['fecha_desde'])
        if filtros.get('fecha_hasta'):
            query += " AND fecha <= ?"
            params.append(filtros['fecha_hasta'])
        if filtros.get('control'):
            query += " AND control LIKE ?"
            params.append(f"%{filtros['control']}%")
        if filtros.get('anio') and filtros['anio'] != 'todos':
            query += " AND strftime('%Y', fecha) = ?"
            params.append(str(filtros['anio']))
        if filtros.get('mes') and filtros['mes'] != 'todos':
            query += " AND strftime('%m', fecha) = ?"
            params.append(f"{int(filtros['mes']):02d}")
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

# ========== LOGO CENTRADO ==========
def logo():
    st.markdown("<div style='display: flex; justify-content: center;'>", unsafe_allow_html=True)
    st.image("logo.png", width=300)
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

# ========== LOGIN ==========
if 'logueado' not in st.session_state:
    st.session_state.logueado = False

if not st.session_state.logueado:
    logo()
    st.markdown('<h1 class="main-title">BetaPro Mining</h1>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔐 Iniciar Sesión", "📝 Registrarse"])
    
    with tab1:
        usuario_login = st.text_input("Usuario", key="login_user")
        password_login = st.text_input("Contraseña", type="password", key="login_pass")
        if st.button("Ingresar", use_container_width=True, key="login_btn"):
            u = login(usuario_login, password_login)
            if u:
                st.session_state.logueado = True
                st.session_state.usuario = u[1]
                st.session_state.rol = u[3]
                st.session_state.user_id = u[0]
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos")
    
    with tab2:
        nuevo_usuario = st.text_input("Usuario *", key="reg_user")
        nuevo_email = st.text_input("Email", key="reg_email")
        nueva_pass = st.text_input("Contraseña *", type="password", key="reg_pass")
        confirmar_pass = st.text_input("Confirmar *", type="password", key="reg_confirm")
        if st.button("Registrarse", use_container_width=True, key="reg_btn"):
            if not nuevo_usuario or not nueva_pass:
                st.error("Usuario y contraseña son obligatorios")
            elif nueva_pass != confirmar_pass:
                st.error("Las contraseñas no coinciden")
            else:
                if registrar_usuario(nuevo_usuario, nueva_pass, nuevo_email):
                    st.success("✅ Registrado! Ahora inicia sesión")
                else:
                    st.error("El usuario ya existe")

# ========== PANEL PRINCIPAL ==========
else:
    with st.sidebar:
        st.image("logo.png", width=200)
        st.markdown(f"### 👤 {st.session_state.usuario}")
        st.markdown(f"*Rol: {st.session_state.rol}*")
        st.divider()
    
    menu = st.sidebar.radio("MENÚ", ["📊 Dashboard", "📝 Registrar", "📋 Registros", "🔐 Cambiar Pass", "⚙️ Admin"])
    
    if menu == "📊 Dashboard":
        logo()
        st.markdown('<h1 class="main-title">📊 Dashboard</h1>', unsafe_allow_html=True)
        
        st.subheader("🔍 FILTRAR POR FECHAS")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            fecha_desde = st.date_input("📅 Desde", datetime.now() - timedelta(days=30))
        with col_f2:
            fecha_hasta = st.date_input("📅 Hasta", datetime.now())
        
        buscar_control = st.text_input("🔍 Buscar por ID Control", placeholder="Ej: CTL-001")
        
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
            st.download_button("📊 EXPORTAR A EXCEL", excel, f"reporte_{fecha_desde}_a_{fecha_hasta}.xlsx")
        else:
            st.warning(f"No hay registros entre {fecha_desde} y {fecha_hasta}")
    
    elif menu == "📝 Registrar":
        logo()
        st.markdown('<h1 class="main-title">📝 Registrar Picheo</h1>', unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            fecha = st.date_input("📅 Fecha", datetime.now())
        with c2:
            control = st.text_input("🏷️ ID Control")
        with c3:
            cantidad = st.number_input("⛏️ Cantidad", min_value=1, step=1)
        
        operador = st.text_input("👤 Operador", value=st.session_state.usuario)
        notas = st.text_area("📝 Notas")
        
        if st.button("💾 Guardar", use_container_width=True):
            if control and cantidad:
                guardar_picheo(fecha.strftime('%Y-%m-%d'), control, cantidad, operador, notas)
                st.success("✅ Guardado!")
                st.rerun()
    
    elif menu == "📋 Registros":
        logo()
        st.markdown('<h1 class="main-title">📋 Todos los Registros</h1>', unsafe_allow_html=True)
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            desde = st.date_input("Desde", datetime.now() - timedelta(days=30))
        with col_f2:
            hasta = st.date_input("Hasta", datetime.now())
        
        filtros = {
            'fecha_desde': desde.strftime('%Y-%m-%d'),
            'fecha_hasta': hasta.strftime('%Y-%m-%d')
        }
        
        df = get_picheos(filtros, 
                        st.session_state.usuario if st.session_state.rol != 'admin' else None,
                        st.session_state.rol == 'admin')
        
        if not df.empty:
            st.dataframe(df[['id', 'fecha', 'control', 'cantidad', 'ganancia', 'operador', 'notas']], use_container_width=True)
            excel = export_excel(df)
            st.download_button("📊 Exportar Excel", excel, f"reporte_{datetime.now().strftime('%Y%m%d')}.xlsx")
            
            st.subheader("🗑️ Eliminar")
            id_elim = st.number_input("ID a eliminar", min_value=0, step=1)
            if st.button("Eliminar"):
                if id_elim > 0:
                    eliminar_picheo(id_elim, st.session_state.usuario, st.session_state.rol == 'admin')
                    st.success("Eliminado!")
                    st.rerun()
        else:
            st.info("No hay registros")
    
    elif menu == "🔐 Cambiar Pass":
        logo()
        st.markdown('<h1 class="main-title">🔐 Cambiar Contraseña</h1>', unsafe_allow_html=True)
        
        actual = st.text_input("Contraseña actual", type="password")
        nueva = st.text_input("Nueva contraseña", type="password")
        confirma = st.text_input("Confirmar", type="password")
        
        if st.button("Actualizar"):
            if nueva == confirma:
                if cambiar_pass(st.session_state.usuario, actual, nueva):
                    st.success("✅ Contraseña cambiada")
                else:
                    st.error("Contraseña actual incorrecta")
            else:
                st.error("No coinciden")
    
    elif menu == "⚙️ Admin":
        if st.session_state.rol == 'admin':
            logo()
            st.markdown('<h1 class="main-title">⚙️ Administración</h1>', unsafe_allow_html=True)
            
            tab_a1, tab_a2, tab_a3 = st.tabs(["💰 Precio", "👥 Usuarios", "📊 Producción por Usuario"])
            
            with tab_a1:
                st.subheader("💰 Configurar Precio por Picheo")
                precio_act = get_precio()
                nuevo = st.number_input("Precio (USD)", value=precio_act, step=0.001, format="%.4f")
                if st.button("Actualizar precio"):
                    set_precio(nuevo)
                    st.success(f"✅ Precio: ${nuevo:.4f}")
            
            with tab_a2:
                st.subheader("👥 LISTA DE USUARIOS")
                conn = sqlite3.connect(DB)
                users = pd.read_sql_query("SELECT id, nombre, email, rol, fecha_registro FROM usuarios", conn)
                conn.close()
                st.dataframe(users, use_container_width=True)
                
                st.subheader("📊 ESTADÍSTICAS POR USUARIO")
                conn = sqlite3.connect(DB)
                stats = pd.read_sql_query("""
                    SELECT operador, COUNT(*) as registros, SUM(cantidad) as total_picheos, SUM(ganancia) as total_ganancias
                    FROM picheos GROUP BY operador
                """, conn)
                conn.close()
                if not stats.empty:
                    st.dataframe(stats, use_container_width=True)
            
            with tab_a3:
                st.subheader("📊 PRODUCCIÓN POR USUARIO")
                conn = sqlite3.connect(DB)
                usuarios_lista = pd.read_sql_query("SELECT nombre FROM usuarios", conn)
                conn.close()
                usuario_sel = st.selectbox("Seleccionar Usuario", usuarios_lista['nombre'].tolist())
                
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    f_desde = st.date_input("Desde", datetime.now() - timedelta(days=30))
                with col_f2:
                    f_hasta = st.date_input("Hasta", datetime.now())
                
                conn = sqlite3.connect(DB)
                df_user = pd.read_sql_query(
                    "SELECT fecha, control, cantidad, ganancia, notas FROM picheos WHERE operador = ? AND fecha BETWEEN ? AND ? ORDER BY fecha DESC",
                    conn, params=(usuario_sel, f_desde.strftime('%Y-%m-%d'), f_hasta.strftime('%Y-%m-%d'))
                )
                conn.close()
                
                if not df_user.empty:
                    st.write(f"**Total Picheos:** {int(df_user['cantidad'].sum()):,}")
                    st.write(f"**Ganancias:** ${df_user['ganancia'].sum():,.2f}")
                    st.dataframe(df_user, use_container_width=True)
                    excel_user = export_excel(df_user)
                    st.download_button(f"📊 Exportar producción de {usuario_sel}", excel_user, f"produccion_{usuario_sel}.xlsx")
                else:
                    st.info("No hay registros")
        else:
            st.error("Acceso restringido")
