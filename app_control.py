import streamlit as st
import os
import sqlite3
import pandas as pd

st.set_page_config(page_title="Recuperar Datos - BetaPro", layout="wide")

st.title("🔍 SISTEMA DE RECUPERACIÓN DE DATOS")
st.markdown("---")

# ========== 1. LISTAR TODOS LOS ARCHIVOS ==========
st.subheader("📁 ARCHIVOS EN EL SERVIDOR")

archivos = os.listdir('.')
archivos_ordenados = sorted(archivos)

for archivo in archivos_ordenados:
    try:
        tamaño = os.path.getsize(archivo)
        if tamaño < 1024:
            tamaño_str = f"{tamaño} bytes"
        elif tamaño < 1024*1024:
            tamaño_str = f"{tamaño/1024:.2f} KB"
        else:
            tamaño_str = f"{tamaño/(1024*1024):.2f} MB"
        st.write(f"- **{archivo}** ({tamaño_str})")
    except:
        st.write(f"- **{archivo}**")

st.markdown("---")

# ========== 2. BUSCAR ARCHIVOS .db ==========
st.subheader("💾 BASES DE DATOS ENCONTRADAS")

dbs = [a for a in archivos if a.endswith('.db')]

if dbs:
    for db in dbs:
        tamaño = os.path.getsize(db)
        st.success(f"✅ **{db}** - {tamaño} bytes")
        
        # Intentar leer cada base de datos
        try:
            conn = sqlite3.connect(db)
            c = conn.cursor()
            
            # Ver tablas
            c.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tablas = c.fetchall()
            st.write(f"   📋 Tablas: {[t[0] for t in tablas]}")
            
            # Contar usuarios
            try:
                c.execute("SELECT COUNT(*) FROM usuarios")
                count_usuarios = c.fetchone()[0]
                st.write(f"   👥 Usuarios: {count_usuarios}")
                
                # Mostrar usuarios
                if count_usuarios > 0:
                    c.execute("SELECT nombre, rol FROM usuarios")
                    usuarios = c.fetchall()
                    for u in usuarios:
                        st.write(f"      - {u[0]} (rol: {u[1]})")
            except:
                pass
            
            # Contar picheos
            try:
                c.execute("SELECT COUNT(*) FROM picheos")
                count_picheos = c.fetchone()[0]
                st.write(f"   ⛏️ Registros de picheo: {count_picheos}")
                
                # Mostrar algunos registros
                if count_picheos > 0:
                    c.execute("SELECT fecha, control, cantidad, operador FROM picheos LIMIT 5")
                    picheos = c.fetchall()
                    st.write("   📝 Últimos registros:")
                    for p in picheos:
                        st.write(f"      - {p[0]} | {p[1]} | {p[2]} picheos | {p[3]}")
            except:
                pass
            
            conn.close()
            st.write("")
        except Exception as e:
            st.error(f"   Error al leer {db}: {e}")
else:
    st.warning("❌ No se encontraron archivos .db")

st.markdown("---")

# ========== 3. BUSCAR ARCHIVOS DE RESpaldo ==========
st.subheader("📋 POSIBLES RESPALDOS")

backups = [a for a in archivos if 'backup' in a.lower() or 'back' in a.lower() or 'bak' in a.lower() or 'old' in a.lower()]

if backups:
    for b in backups:
        tamaño = os.path.getsize(b)
        st.write(f"- {b} ({tamaño} bytes)")
else:
    st.info("No se encontraron archivos de respaldo evidentes")

st.markdown("---")

# ========== 4. RECOMENDACIÓN ==========
st.subheader("💡 RECOMENDACIÓN")

st.write("""
**Si aparece alguna base de datos con datos**, copia el nombre exacto y luego:
1. Edita `app_control.py`
2. Cambia `DB = "datos.db"` por `DB = "nombre_que_viste.db"`
3. Guarda y prueba

**Si no hay bases de datos con datos**, lamentablemente los registros se perdieron.
""")

st.markdown("---")
st.info("Este código solo LEE archivos, no modifica ni borra nada.")
