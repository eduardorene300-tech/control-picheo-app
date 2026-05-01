@"
import streamlit as st
import sqlite3
import hashlib
from datetime import datetime
import pandas as pd

st.set_page_config(page_title="Control Picheo", layout="wide")

conn = sqlite3.connect('datos.db')
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS picheos (id INTEGER PRIMARY KEY, fecha TEXT, control TEXT, cantidad INTEGER)')
conn.commit()

st.title("⛏️ Control de Picheo")

with st.form("nuevo"):
    fecha = st.date_input("Fecha", datetime.now())
    control = st.text_input("ID Control")
    cantidad = st.number_input("Picheos", min_value=1)
    if st.form_submit_button("Guardar"):
        c.execute("INSERT INTO picheos (fecha, control, cantidad) VALUES (?,?,?)", 
                 (fecha, control, cantidad))
        conn.commit()
        st.success("Guardado!")

st.subheader("Registros")
df = pd.read_sql_query("SELECT * FROM picheos ORDER BY fecha DESC", conn)
st.dataframe(df)
"@ | Out-File -FilePath app_simple.py -Encoding utf8

streamlit run app_simple.py
