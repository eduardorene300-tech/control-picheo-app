"""
BetaPro - Sistema Profesional de Control de Picheo
Versión: 3.0
Características:
- Registro de usuarios
- Filtros por día, semana, quincena, mes, año
- Exportación a Excel y PDF
- Diseño moderno con colores
- Cambio de contraseña
- Seguridad por roles
"""

import streamlit as st
import sqlite3
import hashlib
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from io import BytesIO
import base64

# =================================================================
# CONFIGURACIÓN DE LA PÁGINA
# =================================================================
st.set_page_config(
    page_title="BetaPro - Control de Picheo",
    page_icon="⛏️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =================================================================
# ESTILOS PERSONALIZADOS (CSS MODERNO)
# =================================================================
st.markdown("""
<style>
    /* Fondo general */
    .stApp {
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
    }
    
    /* Tarjetas de métricas */
    .metric-card {
        background: linear-gradient(135deg, #1e1e2e 0%, #2a2a3e 100%);
        border-radius: 15px;
        padding: 20px;
        border-left: 4px solid #3399FF;
        box-shadow: 0 4px 15px rgba(51, 153, 255, 0.2);
        transition: transform 0.3s ease;
    }
    .metric-card:hover {
        transform: translateY(-5px);
    }
    
    /* Títulos */
    .main-title {
        background: linear-gradient(90deg, #3399FF, #FFD700, #33FF66);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    
    .sub-title {
        text-align: center;
        color: #888;
        margin-bottom: 2rem;
    }
    
    /* Botones */
    .stButton > button {
        background: linear-gradient(90deg, #3399FF, #00ccff);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.6rem 1.2rem;
        font-weight: bold;
        transition: all 0.3s ease;
        width: 100%;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 20px rgba(51, 153, 255, 0.4);
    }
    
    /* Botón peligroso (eliminar) */
    .stButton > button[key="danger"] {
        background: linear-gradient(90deg, #ff3333, #cc0000);
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f0f1a 0%, #1a1a2e 100%);
        border-right: 1px solid #3399FF33;
    }
    
    /* Inputs */
    .stTextInput > div > div > input, 
    .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea {
        background-color: #2a2a3e;
        color: white;
        border-radius: 10px;
        border: 1px solid #3399FF;
    }
    
    /* Select boxes */
    .stSelectbox > div > div {
        background-color: #2a2a3e;
        border-radius: 10px;
    }
    
    /* Dataframe */
    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px;
        padding: 8px 16px;
        background-color: #2a2a3e;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(90deg, #3399FF, #00ccff);
    }
    
    /* Divider */
    hr {
        border-color: #3399FF33;
    }
</style>
""", unsafe_allow_html=True)

# =================================================================
# BASE DE DATOS MEJORADA
# =================================================================
DB = "betapro.db"

def init_database():
    """Inicializa la base de datos con todas las tablas"""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    # Tabla de usuarios
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT UNIQUE NOT NULL,
        pass TEXT NOT NULL,
        email TEXT,
        rol TEXT DEFAULT 'usuario',
        fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Tabla de picheos
    c.execute('''CREATE TABLE IF NOT EXISTS picheos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha DATE NOT NULL,
        control_id TEXT NOT NULL,
        cantidad INTEGER NOT NULL,
        ganancia REAL,
        precio_unitario REAL,
        operador TEXT,
        notas TEXT,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Tabla de configuración
    c.execute('''CREATE TABLE IF NOT EXISTS config (
        clave TEXT PRIMARY KEY,
        valor TEXT,
        actualizado TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Usuario admin por defecto
    hash_admin = hashlib.sha256("admin123".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO usuarios (nombre, pass, rol) VALUES ('admin', ?, 'admin')", (hash_admin,))
    
    # Configuración por defecto
    c.execute("INSERT OR IGNORE INTO config VALUES ('precio', '0.025', CURRENT_TIMESTAMP)")
    c.execute("INSERT OR IGNORE INTO config VALUES ('empresa', 'BetaPro Mining', CURRENT_TIMESTAMP)")
    
    conn.commit()
    conn.close()

init_database()

# =================================================================
# FUNCIONES DE BASE DE DATOS
# =================================================================
def registrar_usuario(nombre, password, email=""):
    """Registra un nuevo usuario"""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    hash_pass = hashlib.sha256(password.encode()).hexdigest()
    try:
        c.execute("INSERT INTO usuarios (nombre, pass, email) VALUES (?, ?, ?)", 
                 (nombre, hash_pass, email))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login(usuario, password):
    """Verifica credenciales"""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    hash_pass = hashlib.sha256(password.encode()).hexdigest()
    c.execute("SELECT id, nombre, rol FROM usuarios WHERE nombre=? AND pass=?", 
             (usuario, hash_pass))
    r = c.fetchone()
    conn.close()
    return r

def cambiar_contrasena(usuario, contrasena_actual, contrasena_nueva):
    """Cambia la contraseña de un usuario"""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    hash_actual = hashlib.sha256(contrasena_actual.encode()).hexdigest()
    
    c.execute("SELECT id FROM usuarios WHERE nombre=? AND pass=?", (usuario, hash_actual))
    if c.fetchone():
        hash_nueva = hashlib.sha256(contrasena_nueva.encode()).hexdigest()
        c.execute("UPDATE usuarios SET pass=? WHERE nombre=?", (hash_nueva, usuario))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def guardar_picheo(fecha, control_id, cantidad, operador, notas=""):
    """Guarda un registro de picheo"""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    c.execute("SELECT valor FROM config WHERE clave='precio'")
    precio = float(c.fetchone()[0])
    ganancia = cantidad * precio
    
    c.execute('''INSERT OR REPLACE INTO picheos 
                 (fecha, control_id, cantidad, ganancia, precio_unitario, operador, notas)
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
             (fecha, control_id, cantidad, ganancia, precio, operador, notas))
    conn.commit()
    conn.close()
    return True

def eliminar_picheo(id_registro, operador_actual, es_admin):
    """Elimina un registro (solo si es admin o es suyo)"""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    if es_admin:
        c.execute("DELETE FROM picheos WHERE id=?", (id_registro,))
    else:
        c.execute("DELETE FROM picheos WHERE id=? AND operador=?", (id_registro, operador_actual))
    
    conn.commit()
    conn.close()

def obtener_picheos(filtros=None, operador_actual=None, es_admin=False):
    """Obtiene registros con filtros avanzados"""
    conn = sqlite3.connect(DB)
    query = "SELECT * FROM picheos WHERE 1=1"
    params = []
    
    # Filtro por operador (si no es admin)
    if not es_admin and operador_actual:
        query += " AND operador = ?"
        params.append(operador_actual)
    
    if filtros:
        if filtros.get('año'):
            query += " AND strftime('%Y', fecha) = ?"
            params.append(str(filtros['año']))
        
        if filtros.get('mes') and filtros['mes'] != "TODOS":
            query += " AND strftime('%m', fecha) = ?"
            params.append(f"{int(filtros['mes']):02d}")
        
        if filtros.get('dia') and filtros['dia'] != "TODOS":
            query += " AND strftime('%d', fecha) = ?"
            params.append(f"{int(filtros['dia']):02d}")
        
        if filtros.get('quincena') and filtros['quincena'] != "TODAS":
            if filtros['quincena'] == "1":
                query += " AND CAST(strftime('%d', fecha) AS INTEGER) BETWEEN 1 AND 15"
            else:
                query += " AND CAST(strftime('%d', fecha) AS INTEGER) BETWEEN 16 AND 31"
        
        if filtros.get('semana') and filtros['semana'] != "TODAS":
            semanas = {"1": (1,7), "2": (8,14), "3": (15,21), "4": (22,31)}
            s, e = semanas[filtros['semana']]
            query += f" AND CAST(strftime('%d', fecha) AS INTEGER) BETWEEN {s} AND {e}"
        
        if filtros.get('buscar'):
            query += " AND control_id LIKE ?"
            params.append(f"%{filtros['buscar']}%")
        
        if filtros.get('fecha_desde'):
            query += " AND fecha >= ?"
            params.append(filtros['fecha_desde'])
        
        if filtros.get('fecha_hasta'):
            query += " AND fecha <= ?"
            params.append(filtros['fecha_hasta'])
    
    query += " ORDER BY fecha DESC, id DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def obtener_precio():
    """Obtiene el precio actual"""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT valor FROM config WHERE clave='precio'")
    precio = float(c.fetchone()[0])
    conn.close()
    return precio

def actualizar_precio(nuevo_precio):
    """Actualiza el precio"""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE config SET valor=?, actualizado=CURRENT_TIMESTAMP WHERE clave='precio'", 
             (str(nuevo_precio),))
    conn.commit()
    conn.close()

def obtener_operadores():
    """Lista de operadores únicos"""
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query("SELECT DISTINCT operador FROM picheos WHERE operador IS NOT NULL", conn)
    conn.close()
    return df['operador'].tolist() if not df.empty else []

def obtener_estadisticas(df):
    """Calcula estadísticas del DataFrame"""
    if df.empty:
        return {
            'total_registros': 0,
            'total_picheos': 0,
            'total_ganancias': 0,
            'promedio_picheos': 0,
            'max_picheos': 0,
            'min_picheos': 0,
            'dias_trabajados': 0
        }
    return {
        'total_registros': len(df),
        'total_picheos': int(df['cantidad'].sum()),
        'total_ganancias': df['ganancia'].sum(),
        'promedio_picheos': df['cantidad'].mean(),
        'max_picheos': df['cantidad'].max(),
        'min_picheos': df['cantidad'].min(),
        'dias_trabajados': df['fecha'].nunique()
    }

# =================================================================
# FUNCIONES DE EXPORTACIÓN
# =================================================================
def exportar_excel(df):
    """Exporta a Excel con formato profesional"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Datos', index=False)
        
        if not df.empty:
            stats = obtener_estadisticas(df)
            resumen = pd.DataFrame([
                ['Total Registros', stats['total_registros']],
                ['Total Picheos', f"{stats['total_picheos']:,}"],
                ['Ganancias USD', f"${stats['total_ganancias']:,.2f}"],
                ['Promedio por Día', f"{stats['promedio_picheos']:.1f}"],
                ['Fecha Reporte', datetime.now().strftime('%d/%m/%Y %H:%M')]
            ], columns=['Métrica', 'Valor'])
            resumen.to_excel(writer, sheet_name='Resumen', index=False)
    
    return output.getvalue()

def exportar_pdf(df):
    """Exporta a PDF"""
    if df.empty:
        return None
    
    output = BytesIO()
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    
    doc = SimpleDocTemplate(output, pagesize=A4)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('CustomTitle', parent=styles['Title'], fontSize=16, textColor=colors.HexColor('#3399FF'))
    elements = [Paragraph("Reporte de Producción - BetaPro", title_style), Spacer(1, 20)]
    
    table_data = [['Fecha', 'ID Control', 'Picheos', 'Ganancia USD']]
    for _, row in df.head(50).iterrows():
        table_data.append([
            row['fecha'], row['control_id'], str(int(row['cantidad'])), f"${row['ganancia']:.2f}"
        ])
    
    table = Table(table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#3399FF')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 1, colors.grey),
        ('FONTSIZE', (0,0), (-1,-1), 8),
    ]))
    
    elements.append(table)
    doc.build(elements)
    return output.getvalue()

# =================================================================
# INICIALIZAR SESIÓN
# =================================================================
if 'logueado' not in st.session_state:
    st.session_state.logueado = False
if 'usuario' not in st.session_state:
    st.session_state.usuario = None
if 'rol' not in st.session_state:
    st.session_state.rol = None
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'mostrar_cambio_pass' not in st.session_state:
    st.session_state.mostrar_cambio_pass = False

# =================================================================
# PANTALLA DE LOGIN / REGISTRO
# =================================================================
if not st.session_state.logueado:
    st.markdown('<h1 class="main-title">⛏️ BetaPro Mining</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Sistema Profesional de Control de Picheo</p>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔐 Iniciar Sesión", "📝 Crear Cuenta"])
    
    with tab1:
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            usuario = st.text_input("Usuario", key="login_user")
            password = st.text_input("Contraseña", type="password", key="login_pass")
            
            if st.button("Ingresar", use_container_width=True):
                user = login(usuario, password)
                if user:
                    st.session_state.logueado = True
                    st.session_state.usuario = user[1]
                    st.session_state.rol = user[2]
                    st.session_state.user_id = user[0]
                    st.rerun()
                else:
                    st.error("❌ Usuario o contraseña incorrectos")
    
    with tab2:
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            nuevo_usuario = st.text_input("Usuario *")
            nuevo_email = st.text_input("Email (opcional)")
            nueva_pass = st.text_input("Contraseña *", type="password")
            confirm_pass = st.text_input("Confirmar Contraseña *", type="password")
            
            if st.button("Registrarse", use_container_width=True):
                if not nuevo_usuario or not nueva_pass:
                    st.error("Usuario y contraseña son obligatorios")
                elif nueva_pass != confirm_pass:
                    st.error("Las contraseñas no coinciden")
                else:
                    if registrar_usuario(nuevo_usuario, nueva_pass, nuevo_email):
                        st.success("✅ Usuario registrado exitosamente. ¡Ahora inicia sesión!")
                    else:
                        st.error("❌ El usuario ya existe")

# =================================================================
# PANEL PRINCIPAL
# =================================================================
else:
    # Sidebar
    with st.sidebar:
        st.markdown(f"""
        <div style="text-align: center; padding: 20px 0;">
            <h2 style="color: #3399FF;">⛏️ BetaPro</h2>
            <p style="color: #FFD700; font-size: 18px;">{st.session_state.usuario}</p>
            <p style="color: #888; font-size: 12px;">Rol: {st.session_state.rol.upper()}</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        menu = st.radio(
            "📋 MENÚ PRINCIPAL",
            ["📊 Dashboard", "📝 Registrar Picheo", "📋 Mis Registros", "📈 Reportes", "⚙️ Configuración"],
            index=0
        )
        
        st.divider()
        
        # Botón cambiar contraseña
        if st.button("🔐 Cambiar Contraseña", use_container_width=True):
            st.session_state.mostrar_cambio_pass = True
        
        st.divider()
        
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            for key in ['logueado', 'usuario', 'rol', 'user_id', 'mostrar_cambio_pass']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    
    # Modal cambiar contraseña
    if st.session_state.mostrar_cambio_pass:
        with st.expander("🔐 Cambiar Contraseña", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                pass_actual = st.text_input("Contraseña actual", type="password")
                pass_nueva = st.text_input("Contraseña nueva", type="password")
            with col2:
                pass_confirm = st.text_input("Confirmar nueva contraseña", type="password")
            
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("✅ Actualizar", use_container_width=True):
                    if pass_nueva == pass_confirm:
                        if cambiar_contrasena(st.session_state.usuario, pass_actual, pass_nueva):
                            st.success("✅ Contraseña actualizada correctamente")
                            st.session_state.mostrar_cambio_pass = False
                            st.rerun()
                        else:
                            st.error("❌ Contraseña actual incorrecta")
                    else:
                        st.error("❌ Las contraseñas nuevas no coinciden")
            with col_b2:
                if st.button("❌ Cancelar", use_container_width=True):
                    st.session_state.mostrar_cambio_pass = False
                    st.rerun()

    # =============================================================
    # DASHBOARD
    # =============================================================
    if menu == "📊 Dashboard":
        st.markdown('<h1 class="main-title">📊 Dashboard</h1>', unsafe_allow_html=True)
        
        # Filtros
        st.subheader("🔍 Filtros de Búsqueda")
        col1, col2, col3, col4, col5 = st.columns(5)
        
        año_actual = datetime.now().year
        with col1:
            año_filtro = st.selectbox("Año", ["TODOS", año_actual, año_actual-1, año_actual-2], index=0)
        with col2:
            mes_filtro = st.selectbox("Mes", ["TODOS"] + [str(i) for i in range(1,13)], index=0)
        with col3:
            quincena_filtro = st.selectbox("Quincena", ["TODAS", "1", "2"], index=0)
        with col4:
            semana_filtro = st.selectbox("Semana", ["TODAS", "1", "2", "3", "4"], index=0)
        with col5:
            dia_filtro = st.selectbox("Día", ["TODOS"] + [str(i) for i in range(1,32)], index=0)
        
        filtros = {}
        if año_filtro != "TODOS":
            filtros['año'] = año_filtro
        if mes_filtro != "TODOS":
            filtros['mes'] = mes_filtro
        if quincena_filtro != "TODAS":
            filtros['quincena'] = quincena_filtro
        if semana_filtro != "TODAS":
            filtros['semana'] = semana_filtro
        if dia_filtro != "TODOS":
            filtros['dia'] = dia_filtro
        
        df = obtener_picheos(filtros, st.session_state.usuario, st.session_state.rol == 'admin')
        
        if not df.empty:
            stats = obtener_estadisticas(df)
            precio_actual = obtener_precio()
            
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            with col_m1:
                st.markdown(f"""
                <div class="metric-card">
                    <p style="color: #888; margin:0;">📋 Registros</p>
                    <h2 style="color: #3399FF; margin:0;">{stats['total_registros']}</h2>
                </div>
                """, unsafe_allow_html=True)
            with col_m2:
                st.markdown(f"""
                <div class="metric-card">
                    <p style="color: #888; margin:0;">⛏️ Total Picheos</p>
                    <h2 style="color: #FFD700; margin:0;">{stats['total_picheos']:,}</h2>
                </div>
                """, unsafe_allow_html=True)
            with col_m3:
                st.markdown(f"""
                <div class="metric-card">
                    <p style="color: #888; margin:0;">💰 Ganancias</p>
                    <h2 style="color: #33FF66; margin:0;">${stats['total_ganancias']:,.2f}</h2>
                </div>
                """, unsafe_allow_html=True)
            with col_m4:
                st.markdown(f"""
                <div class="metric-card">
                    <p style="color: #888; margin:0;">💵 Precio/Picheo</p>
                    <h2 style="color: #3399FF; margin:0;">${precio_actual:.3f}</h2>
                </div>
                """, unsafe_allow_html=True)
            
            # Gráfico tendencia
            tendencia = df.groupby('fecha')['cantidad'].sum().reset_index()
            fig = px.line(tendencia, x='fecha', y='cantidad', 
                         title='📈 Tendencia de Producción',
                         labels={'fecha': 'Fecha', 'cantidad': 'Picheos'},
                         line_shape='spline')
            fig.update_layout(template='plotly_dark', hovermode='x unified')
            st.plotly_chart(fig, use_container_width=True)
            
            # Top controles
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                top = df.groupby('control_id')['cantidad'].sum().nlargest(10).reset_index()
                fig2 = px.bar(top, x='control_id', y='cantidad', 
                             title='🏆 Top 10 Controles',
                             color='cantidad', color_continuous_scale='Viridis')
                fig2.update_layout(template='plotly_dark')
                st.plotly_chart(fig2, use_container_width=True)
            
            with col_g2:
                if 'operador' in df.columns and df['operador'].nunique() > 1:
                    por_operador = df.groupby('operador')['cantidad'].sum().reset_index()
                    fig3 = px.pie(por_operador, values='cantidad', names='operador',
                                 title='👥 Distribución por Operador',
                                 color_discrete_sequence=px.colors.sequential.Viridis)
                    fig3.update_layout(template='plotly_dark')
                    st.plotly_chart(fig3, use_container_width=True)
            
            st.subheader("📋 Últimos Registros")
            st.dataframe(df.head(10)[['fecha', 'control_id', 'cantidad', 'ganancia', 'operador']], 
                        use_container_width=True)
        else:
            st.info("ℹ️ No hay datos para mostrar con los filtros seleccionados")
    
    # =============================================================
    # REGISTRAR PICHEO
    # =============================================================
    elif menu == "📝 Registrar Picheo":
        st.markdown('<h1 class="main-title">📝 Registrar Picheo</h1>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            fecha = st.date_input("📅 Fecha", datetime.now())
        with col2:
            control_id = st.text_input("🏷️ ID Control")
        with col3:
            cantidad = st.number_input("⛏️ Cantidad de Picheos", min_value=1, step=1)
        
        operador = st.text_input("👤 Operador", value=st.session_state.usuario)
        notas = st.text_area("📝 Notas (opcional)")
        
        if st.button("💾 Guardar Registro", use_container_width=True):
            if control_id and cantidad > 0:
                if guardar_picheo(fecha.strftime('%Y-%m-%d'), control_id, cantidad, operador, notas):
                    st.success("✅ Registro guardado exitosamente!")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("❌ Error al guardar")
            else:
                st.warning("⚠️ ID Control y Cantidad son obligatorios")
    
    # =============================================================
    # MIS REGISTROS
    # =============================================================
    elif menu == "📋 Mis Registros":
        st.markdown('<h1 class="main-title">📋 Mis Registros</h1>', unsafe_allow_html=True)
        
        st.subheader("🔍 Buscar Registros")
        col1, col2, col3 = st.columns(3)
        with col1:
            buscar_control = st.text_input("Buscar por ID Control", placeholder="Ej: CONTROL-001")
        with col2:
            fecha_desde = st.date_input("Fecha Desde", datetime.now() - timedelta(days=30))
        with col3:
            fecha_hasta = st.date_input("Fecha Hasta", datetime.now())
        
        filtros = {}
        if buscar_control:
            filtros['buscar'] = buscar_control
        filtros['fecha_desde'] = fecha_desde.strftime('%Y-%m-%d')
        filtros['fecha_hasta'] = fecha_hasta.strftime('%Y-%m-%d')
        
        df = obtener_picheos(filtros, st.session_state.usuario, st.session_state.rol == 'admin')
        
        if not df.empty:
            st.dataframe(df[['id', 'fecha', 'control_id', 'cantidad', 'ganancia', 'operador', 'notas']], 
                        use_container_width=True)
            
            col_exp1, col_exp2 = st.columns(2)
            with col_exp1:
                excel_data = exportar_excel(df)
                st.download_button("📊 Exportar a Excel", excel_data,
                                 f"reporte_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                                 "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            
            with col_exp2:
                pdf_data = exportar_pdf(df)
                if pdf_data:
                    st.download_button("📄 Exportar a PDF", pdf_data,
                                     f"reporte_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                                     "application/pdf")
            
            st.subheader("🗑️ Eliminar Registro")
            id_eliminar = st.number_input("ID del registro a eliminar", min_value=0, step=1)
            if st.button("Eliminar", use_container_width=True):
                if id_eliminar > 0:
                    eliminar_picheo(id_eliminar, st.session_state.usuario, st.session_state.rol == 'admin')
                    st.success("✅ Registro eliminado")
                    st.rerun()
                else:
                    st.warning("Ingrese un ID válido")
        else:
            st.info("No hay registros con esos filtros")
    
    # =============================================================
    # REPORTES
    # =============================================================
    elif menu == "📈 Reportes":
        st.markdown('<h1 class="main-title">📈 Reportes Avanzados</h1>', unsafe_allow_html=True)
        
        tipo_reporte = st.selectbox("Seleccionar Reporte", 
                                   ["Producción Diaria", "Por Operador", "Top Controles", "Resumen Mensual"])
        
        col1, col2 = st.columns(2)
        with col1:
            fecha_desde = st.date_input("Desde", datetime.now() - timedelta(days=90))
        with col2:
            fecha_hasta = st.date_input("Hasta", datetime.now())
        
        filtros = {
            'fecha_desde': fecha_desde.strftime('%Y-%m-%d'),
            'fecha_hasta': fecha_hasta.strftime('%Y-%m-%d')
        }
        
        df = obtener_picheos(filtros, st.session_state.usuario, st.session_state.rol == 'admin')
        
        if not df.empty:
            if tipo_reporte == "Producción Diaria":
                reporte = df.groupby('fecha')['cantidad'].sum().reset_index()
                reporte.columns = ['Fecha', 'Picheos']
                st.dataframe(reporte, use_container_width=True)
                fig = px.bar(reporte, x='Fecha', y='Picheos', title='Producción Diaria')
                st.plotly_chart(fig, use_container_width=True)
            
            elif tipo_reporte == "Por Operador":
                reporte = df.groupby('operador')['cantidad'].sum().reset_index()
                fig = px.pie(reporte, values='cantidad', names='operador', title='Producción por Operador')
                st.plotly_chart(fig, use_container_width=True)
            
            elif tipo_reporte == "Top Controles":
                reporte = df.groupby('control_id')['cantidad'].sum().nlargest(20).reset_index()
                st.dataframe(reporte, use_container_width=True)
                fig = px.bar(reporte, x='control_id', y='cantidad', title='Top 20 Controles')
                st.plotly_chart(fig, use_container_width=True)
            
            elif tipo_reporte == "Resumen Mensual":
                df['Mes'] = pd.to_datetime(df['fecha']).dt.strftime('%Y-%m')
                reporte = df.groupby('Mes')['cantidad'].sum().reset_index()
                st.dataframe(reporte, use_container_width=True)
                fig = px.line(reporte, x='Mes', y='cantidad', title='Producción Mensual')
                st.plotly_chart(fig, use_container_width=True)
            
            st.divider()
            excel_data = exportar_excel(df)
            st.download_button("📥 Descargar Reporte Completo (Excel)", excel_data,
                             f"reporte_completo_{datetime.now().strftime('%Y%m%d')}.xlsx",
                             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.info("No hay datos en el período seleccionado")
    
    # =============================================================
    # CONFIGURACIÓN
    # =============================================================
    elif menu == "⚙️ Configuración":
        if st.session_state.rol == 'admin':
            st.markdown('<h1 class="main-title">⚙️ Configuración del Sistema</h1>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("💰 Precio por Picheo")
                precio_actual = obtener_precio()
                nuevo_precio = st.number_input("Precio (USD)", min_value=0.0, value=precio_actual, step=0.001, format="%.4f")
                if st.button("Actualizar Precio"):
                    actualizar_precio(nuevo_precio)
                    st.success(f"✅ Precio actualizado a ${nuevo_precio:.4f}")
                    st.rerun()
            
            with col2:
                st.subheader("👥 Usuarios del Sistema")
                conn = sqlite3.connect(DB)
                usuarios_df = pd.read_sql_query("SELECT id, nombre, email, rol, fecha_registro FROM usuarios", conn)
                conn.close()
                st.dataframe(usuarios_df, use_container_width=True)
            
            st.divider()
            st.info(f"💾 Base de datos: {DB}")
            st.info("🔐 Usuario admin por defecto: admin / admin123 - ¡Cambia esta contraseña!")
        else:
            st.error("🔒 Acceso restringido. Solo administradores pueden acceder a la configuración.")
            
