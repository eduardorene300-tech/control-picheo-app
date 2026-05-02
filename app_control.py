import streamlit as st
import sqlite3
import hashlib
from datetime import datetime, timedelta
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="BetaPro - Control de Picheo", layout="wide")

# ========== ESTILOS ==========
st.markdown("""
<style>
.stApp { background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%); }
.main-title { text-align: center; color: #3399FF; font-size: 2.5rem; }
.metric-card { background: #1e1e2e; border-radius: 10px; padding: 15px; border-left: 4px solid #3399FF; margin: 10px 0; }
.logo-text { color: #FFD700; font-size: 2rem; font-weight: bold; text-align: center; }
</style>
""", unsafe_allow_html=True)

DB = "betapro.db"

# ========== BASE DE DATOS ==========
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY, nombre TEXT UNIQUE, pass TEXT, rol TEXT, email TEXT, fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS picheos (
        id INTEGER PRIMARY KEY, fecha TEXT, control TEXT, cantidad INTEGER, ganancia REAL, operador TEXT, notas TEXT, fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS config (clave TEXT PRIMARY KEY, valor TEXT)''')
    
    hash_admin = hashlib.sha256("admin123".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO usuarios (nombre, pass, rol, email) VALUES ('admin', ?, 'admin', 'admin@betapro.com')", (hash_admin,))
    c.execute("INSERT OR IGNORE INTO config VALUES ('precio', '0.025')")
    c.execute("INSERT OR IGNORE INTO config VALUES ('empresa', 'BetaPro Mining')")
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

# ========== FUNCIÓN PARA MOSTRAR LOGO ==========
def mostrar_logo(tamaño=150):
    try:
        st.image("logo.png", width=tamaño)
    except:
        st.markdown('<p class="logo-text">⛏️ BP</p>', unsafe_allow_html=True)

# ========== LOGIN ==========
if 'logueado' not in st.session_state:
    st.session_state.logueado = False

if not st.session_state.logueado:
    # Logo en pantalla de login
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        mostrar_logo(120)
        st.markdown('<h1 class="main-title">BetaPro Mining</h1>', unsafe_allow_html=True)
        st.markdown('<p style="text-align: center; color: #888;">Sistema de Control de Picheo</p>', unsafe_allow_html=True)
    
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
    # Sidebar con logo
    with st.sidebar:
        mostrar_logo(100)
        st.markdown(f"### 👤 {st.session_state.usuario}")
        st.markdown(f"*Rol: {st.session_state.rol}*")
        st.divider()
    
    menu = st.sidebar.radio("MENÚ", ["📊 Dashboard", "📝 Registrar", "📋 Registros", "🔐 Cambiar Pass", "⚙️ Admin"])
    
    # ========== DASHBOARD ==========
    if menu == "📊 Dashboard":
        st.markdown('<h1 class="main-title">📊 Dashboard</h1>', unsafe_allow_html=True)
        
        # Filtros mejorados
        st.subheader("🔍 Filtros de Búsqueda")
        col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns(5)
        with col_f1:
            fecha_desde = st.date_input("Fecha Desde", datetime.now() - timedelta(days=30))
        with col_f2:
            fecha_hasta = st.date_input("Fecha Hasta", datetime.now())
        with col_f3:
            anio = st.selectbox("Año", ["todos", 2024, 2025, 2026], index=0)
        with col_f4:
            mes = st.selectbox("Mes", ["todos"] + list(range(1,13)), index=0)
        with col_f5:
            buscar_control = st.text_input("Buscar Control", placeholder="ID...")
        
        filtros = {
            'fecha_desde': fecha_desde.strftime('%Y-%m-%d'),
            'fecha_hasta': fecha_hasta.strftime('%Y-%m-%d')
        }
        if anio != "todos":
            filtros['anio'] = anio
        if mes != "todos":
            filtros['mes'] = mes
        if buscar_control:
            filtros['control'] = buscar_control
        
        df = get_picheos(filtros, None, st.session_state.rol == 'admin')
        
        if not df.empty:
            precio = get_precio()
            total_picheos = df['cantidad'].sum()
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("📋 Registros", len(df))
            col2.metric("⛏️ Total Picheos", f"{int(total_picheos):,}")
            col3.metric("💰 Ganancias", f"${total_picheos * precio:,.2f}")
            col4.metric("👥 Operadores", df['operador'].nunique())
            
            st.subheader("📋 TODOS LOS REGISTROS")
            st.dataframe(df[['fecha', 'control', 'cantidad', 'ganancia', 'operador', 'notas']], 
                        use_container_width=True)
            
            excel = export_excel(df)
            st.download_button("📊 Exportar a Excel", excel, f"reporte_{datetime.now().strftime('%Y%m%d')}.xlsx")
            
            st.subheader("📈 Tendencia de Producción")
            tendencia = df.groupby('fecha')['cantidad'].sum().reset_index()
            st.line_chart(tendencia.set_index('fecha'))
        else:
            st.info("No hay datos en el rango seleccionado")
    
    # ========== REGISTRAR ==========
    elif menu == "📝 Registrar":
        st.markdown('<h1 class="main-title">📝 Registrar Picheo</h1>', unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            fecha = st.date_input("📅 Fecha", datetime.now())
        with c2:
            control = st.text_input("🏷️ ID Control")
        with c3:
            cantidad = st.number_input("⛏️ Cantidad de Picheos", min_value=1, step=1)
        
        operador = st.text_input("👤 Operador", value=st.session_state.usuario)
        notas = st.text_area("📝 Notas (opcional)")
        
        if st.button("💾 Guardar Registro", use_container_width=True):
            if control and cantidad:
                guardar_picheo(fecha.strftime('%Y-%m-%d'), control, cantidad, operador, notas)
                st.success("✅ Registro guardado exitosamente!")
                st.balloons()
                st.rerun()
            else:
                st.warning("⚠️ ID Control y Cantidad son obligatorios")
    
    # ========== REGISTROS COMPLETOS ==========
    elif menu == "📋 Registros":
        st.markdown('<h1 class="main-title">📋 Registros Completos</h1>', unsafe_allow_html=True)
        
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            desde = st.date_input("Fecha Desde", datetime.now() - timedelta(days=30))
        with col_f2:
            hasta = st.date_input("Fecha Hasta", datetime.now())
        with col_f3:
            buscar = st.text_input("Buscar por Control ID", placeholder="Ej: CTL-001")
        
        filtros = {
            'fecha_desde': desde.strftime('%Y-%m-%d'),
            'fecha_hasta': hasta.strftime('%Y-%m-%d')
        }
        if buscar:
            filtros['control'] = buscar
        
        df = get_picheos(
            filtros,
            st.session_state.usuario if st.session_state.rol != 'admin' else None,
            st.session_state.rol == 'admin'
        )
        
        if not df.empty:
            st.subheader("📋 LISTA COMPLETA DE REGISTROS")
            st.dataframe(df[['id', 'fecha', 'control', 'cantidad', 'ganancia', 'operador', 'notas']], 
                        use_container_width=True)
            
            precio = get_precio()
            total_picheos = df['cantidad'].sum()
            col_r1, col_r2, col_r3 = st.columns(3)
            col_r1.metric("Total Registros", len(df))
            col_r2.metric("Total Picheos", f"{int(total_picheos):,}")
            col_r3.metric("Total Ganancias", f"${total_picheos * precio:,.2f}")
            
            excel = export_excel(df)
            st.download_button("📊 Exportar a Excel", excel, f"reporte_completo_{datetime.now().strftime('%Y%m%d')}.xlsx")
            
            st.subheader("🗑️ Eliminar Registro")
            id_elim = st.number_input("ID del registro a eliminar", min_value=0, step=1)
            if st.button("Eliminar"):
                if id_elim > 0:
                    eliminar_picheo(id_elim, st.session_state.usuario, st.session_state.rol == 'admin')
                    st.success("✅ Eliminado!")
                    st.rerun()
        else:
            st.info("No hay registros en el rango seleccionado")
    
    # ========== CAMBIAR PASS ==========
    elif menu == "🔐 Cambiar Pass":
        st.markdown('<h1 class="main-title">🔐 Cambiar Contraseña</h1>', unsafe_allow_html=True)
        
        actual = st.text_input("Contraseña actual", type="password")
        nueva = st.text_input("Nueva contraseña", type="password")
        confirma = st.text_input("Confirmar nueva", type="password")
        
        if st.button("Actualizar"):
            if nueva == confirma:
                if cambiar_pass(st.session_state.usuario, actual, nueva):
                    st.success("✅ Contraseña cambiada exitosamente")
                else:
                    st.error("❌ Contraseña actual incorrecta")
            else:
                st.error("❌ Las nuevas contraseñas no coinciden")
    
    # ========== ADMIN ==========
    elif menu == "⚙️ Admin":
        if st.session_state.rol == 'admin':
            st.markdown('<h1 class="main-title">⚙️ Administración</h1>', unsafe_allow_html=True)
            
            tab_admin1, tab_admin2, tab_admin3 = st.tabs(["💰 Precio", "👥 Usuarios", "📊 Producción por Usuario"])
            
            with tab_admin1:
                precio_act = get_precio()
                nuevo = st.number_input("Precio por picheo (USD)", value=precio_act, step=0.001, format="%.4f")
                if st.button("Actualizar precio"):
                    set_precio(nuevo)
                    st.success(f"✅ Precio actualizado a ${nuevo:.4f}")
            
            with tab_admin2:
                st.subheader("👥 Lista de Usuarios")
                conn = sqlite3.connect(DB)
                users = pd.read_sql_query("SELECT id, nombre, email, rol, fecha_registro FROM usuarios", conn)
                conn.close()
                st.dataframe(users, use_container_width=True)
                
                st.subheader("📊 Estadísticas por Usuario")
                conn = sqlite3.connect(DB)
                df_picheos = pd.read_sql_query("SELECT operador, SUM(cantidad) as total_picheos, COUNT(*) as registros FROM picheos GROUP BY operador", conn)
                conn.close()
                if not df_picheos.empty:
                    precio = get_precio()
                    df_picheos['ganancias'] = df_picheos['total_picheos'] * precio
                    st.dataframe(df_picheos, use_container_width=True)
            
            with tab_admin3:
                st.subheader("📊 Producción por Usuario (Detallada)")
                
                conn = sqlite3.connect(DB)
                usuarios_lista = pd.read_sql_query("SELECT nombre FROM usuarios", conn)
                conn.close()
                
                usuarios_opciones = usuarios_lista['nombre'].tolist() if not usuarios_lista.empty else ['admin']
                usuario_seleccionado = st.selectbox("Seleccionar Usuario", usuarios_opciones)
                
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    f_desde = st.date_input("Desde", datetime.now() - timedelta(days=30))
                with col_f2:
                    f_hasta = st.date_input("Hasta", datetime.now())
                
                conn = sqlite3.connect(DB)
                df_usuario = pd.read_sql_query(
                    "SELECT fecha, control, cantidad, ganancia, notas FROM picheos WHERE operador = ? AND fecha BETWEEN ? AND ? ORDER BY fecha DESC",
                    conn, params=(usuario_seleccionado, f_desde.strftime('%Y-%m-%d'), f_hasta.strftime('%Y-%m-%d'))
                )
                conn.close()
                
                if not df_usuario.empty:
                    st.write(f"**Total Picheos:** {int(df_usuario['cantidad'].sum()):,}")
                    st.write(f"**Total Ganancias:** ${df_usuario['ganancia'].sum():,.2f}")
                    st.write(f"**Registros:** {len(df_usuario)}")
                    st.dataframe(df_usuario, use_container_width=True)
                    
                    excel_user = export_excel(df_usuario)
                    st.download_button(f"📊 Exportar producción de {usuario_seleccionado}", excel_user, f"produccion_{usuario_seleccionado}_{datetime.now().strftime('%Y%m%d')}.xlsx")
                else:
                    st.info(f"No hay registros de {usuario_seleccionado} en ese período")
        else:
            st.error("🔒 Acceso restringido a administradores")
