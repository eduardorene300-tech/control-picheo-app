import streamlit as st
import sqlite3
import os

st.set_page_config(page_title="Diagnóstico - BetaPro", layout="wide")

st.title("🔍 DIAGNÓSTICO DE BASE DE DATOS")

# Buscar todos los archivos .db en el directorio
archivos_db = [f for f in os.listdir('.') if f.endswith('.db')]

st.subheader("📁 ARCHIVOS .db ENCONTRADOS:")
if archivos_db:
    for db in archivos_db:
        st.write(f"- {db}")
        
        # Intentar conectar y mostrar tablas
        try:
            conn = sqlite3.connect(db)
            c = conn.cursor()
            c.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tablas = c.fetchall()
            st.write(f"  Tablas: {[t[0] for t in tablas]}")
            
            # Contar usuarios
            if ('usuarios' in [t[0] for t in tablas]) or ('usuarios' in str(tablas)):
                try:
                    c.execute("SELECT COUNT(*) FROM usuarios")
                    count = c.fetchone()[0]
                    st.write(f"  👥 Usuarios registrados: {count}")
                except:
                    pass
            
            # Contar picheos
            if ('picheos' in [t[0] for t in tablas]) or ('picheos' in str(tablas)):
                try:
                    c.execute("SELECT COUNT(*) FROM picheos")
                    count = c.fetchone()[0]
                    st.write(f"  ⛏️ Registros de picheo: {count}")
                except:
                    pass
            
            conn.close()
        except Exception as e:
            st.write(f"  Error: {e}")
else:
    st.warning("❌ No se encontraron archivos .db")

st.divider()

# Intentar conectar con nombres comunes
nombres_comunes = ["betapro.db", "datos.db", "data.db", "picheos.db", "BETAPRO.db", "picheo.db"]

st.subheader("🔌 INTENTANDO CONEXIÓN CON NOMBRES COMUNES:")
for nombre in nombres_comunes:
    try:
        conn = sqlite3.connect(nombre)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tablas = c.fetchall()
        st.success(f"✅ {nombre} - Conectado! Tablas: {[t[0] for t in tablas]}")
        conn.close()
    except:
        st.error(f"❌ {nombre} - No se pudo conectar")
